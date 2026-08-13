import streamlit as st

from databricks.sdk import WorkspaceClient

from datetime import datetime, timezone, timedelta

import pandas as pd


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Databricks Job Monitor",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# CONFIGURATION
# =========================================================

# ---------------------------------------------------------
# DBU PRICE
# ---------------------------------------------------------
# This is intentionally NOT displayed as a UI filter.
# Change this according to your applicable DBU price.
# ---------------------------------------------------------

DBU_PRICE = 0.15


# ---------------------------------------------------------
# DBU DATE RANGE
# ---------------------------------------------------------
# Automatically use the last 30 days.
# No DBU/cost date filters are displayed.
# ---------------------------------------------------------

USAGE_END_DATE = datetime.now(
    timezone.utc
).date()

USAGE_START_DATE = (
    USAGE_END_DATE -
    timedelta(days=30)
)


# =========================================================
# DATABRICKS CLIENT
# =========================================================

@st.cache_resource
def get_databricks_client():

    return WorkspaceClient()


try:

    w = get_databricks_client()

except Exception as e:

    st.error(
        "Unable to create Databricks client."
    )

    st.exception(e)

    st.stop()


# =========================================================
# AUTHENTICATION
# =========================================================

try:

    current_user = w.current_user.me()

except Exception as e:

    st.error(
        "Databricks authentication failed."
    )

    st.exception(e)

    st.stop()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_timestamp(timestamp):

    if not timestamp:

        return "-"

    try:

        dt = datetime.fromtimestamp(
            timestamp / 1000,
            tz=timezone.utc
        )

        return dt.strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

    except Exception:

        return "-"


def get_job_name(job):

    try:

        if (
            job.settings
            and job.settings.name
        ):

            return job.settings.name

    except Exception:

        pass

    return f"Job {job.job_id}"


def get_job_created_time(job):

    try:

        if job.created_time:

            return format_timestamp(
                job.created_time
            )

    except Exception:

        pass

    return "-"


def get_job_updated_time(job):

    try:

        if job.change_time:

            return format_timestamp(
                job.change_time
            )

    except Exception:

        pass

    return "-"


def get_job_creator(job):

    try:

        if job.creator_user_name:

            return job.creator_user_name

    except Exception:

        pass

    return "-"


def get_run_status(run):

    if not run.state:

        return "UNKNOWN"

    if run.state.result_state:

        return run.state.result_state.value

    if run.state.life_cycle_state:

        return run.state.life_cycle_state.value

    return "UNKNOWN"


# =========================================================
# GET JOBS
# =========================================================

@st.cache_data(ttl=60)
def get_jobs():

    jobs = []

    try:

        for job in w.jobs.list():

            if job.job_id is None:

                continue

            jobs.append(
                {
                    "job_id":
                        job.job_id,

                    "job_name":
                        get_job_name(job),

                    "created_time":
                        get_job_created_time(job),

                    "updated_time":
                        get_job_updated_time(job),

                    "created_by":
                        get_job_creator(job)
                }
            )

    except Exception as e:

        st.error(
            "Unable to retrieve Databricks jobs."
        )

        st.exception(e)

    return jobs


# =========================================================
# GET JOB RUNS
# =========================================================

@st.cache_data(ttl=60)
def get_job_runs(job_id):

    try:

        response = w.jobs.list_runs(
            job_id=job_id,
            limit=26
        )

        return list(response)

    except Exception as e:

        st.error(
            f"Unable to retrieve runs for Job ID {job_id}"
        )

        st.exception(e)

        return []


# =========================================================
# GET DBU USAGE
# =========================================================
#
# Uses:
#     system.billing.usage
#
# through:
#     Databricks SQL Statement Execution API
#
# Does NOT use spark.sql()
#
# =========================================================

@st.cache_data(ttl=300)
def get_job_dbu_usage():

    # -----------------------------------------------------
    # SQL Warehouse ID
    # -----------------------------------------------------

    warehouse_id = st.secrets.get(
        "SQL_WAREHOUSE_ID",
        None
    )

    if not warehouse_id:

        st.error(
            "SQL_WAREHOUSE_ID is not configured."
        )

        st.info(
            "Add SQL_WAREHOUSE_ID to "
            ".streamlit/secrets.toml"
        )

        return pd.DataFrame(
            columns=[
                "job_id",
                "dbu_usage"
            ]
        )


    # -----------------------------------------------------
    # SQL QUERY
    # -----------------------------------------------------

    query = f"""
    SELECT
        usage_metadata.job_id AS job_id,
        SUM(usage_quantity) AS dbu_usage
    FROM system.billing.usage
    WHERE usage_date >= DATE('{USAGE_START_DATE}')
      AND usage_date <= DATE('{USAGE_END_DATE}')
      AND usage_unit = 'DBU'
      AND usage_metadata.job_id IS NOT NULL
    GROUP BY usage_metadata.job_id
    ORDER BY dbu_usage DESC
    """


    try:

        # -------------------------------------------------
        # Execute SQL using Statement Execution API
        # -------------------------------------------------

        response = (
            w.statement_execution
            .execute_statement(
                warehouse_id=warehouse_id,
                statement=query,
                wait_timeout="50s"
            )
        )


        # -------------------------------------------------
        # Check status
        # -------------------------------------------------

        if response.status is None:

            st.error(
                "SQL execution returned no status."
            )

            return pd.DataFrame(
                columns=[
                    "job_id",
                    "dbu_usage"
                ]
            )


        status = response.status.state.value


        if status != "SUCCEEDED":

            st.error(
                f"DBU SQL query failed. "
                f"Status: {status}"
            )

            try:

                if response.status.error:

                    st.code(
                        str(
                            response.status.error
                        )
                    )

            except Exception:

                pass

            return pd.DataFrame(
                columns=[
                    "job_id",
                    "dbu_usage"
                ]
            )


        # -------------------------------------------------
        # Get result
        # -------------------------------------------------

        result = response.result


        if result is None:

            return pd.DataFrame(
                columns=[
                    "job_id",
                    "dbu_usage"
                ]
            )


        # -------------------------------------------------
        # Extract rows
        # -------------------------------------------------

        rows = []


        if result.data_array:

            for row in result.data_array:

                if len(row) < 2:

                    continue


                job_id = row[0]

                dbu_value = row[1]


                if job_id is None:

                    continue


                try:

                    dbu_value = float(
                        dbu_value
                    )

                except Exception:

                    dbu_value = 0.0


                rows.append(
                    {
                        "job_id":
                            str(job_id),

                        "dbu_usage":
                            dbu_value
                    }
                )


        # -------------------------------------------------
        # No records
        # -------------------------------------------------

        if not rows:

            return pd.DataFrame(
                columns=[
                    "job_id",
                    "dbu_usage"
                ]
            )


        # -------------------------------------------------
        # DataFrame
        # -------------------------------------------------

        df = pd.DataFrame(
            rows
        )


        # -------------------------------------------------
        # Normalize
        # -------------------------------------------------

        df["job_id"] = (
            df["job_id"]
            .astype(str)
            .str.strip()
        )


        df["dbu_usage"] = pd.to_numeric(
            df["dbu_usage"],
            errors="coerce"
        ).fillna(0.0)


        return df


    except Exception as e:

        st.error(
            "Unable to retrieve DBU usage "
            "from system.billing.usage."
        )

        st.exception(e)

        return pd.DataFrame(
            columns=[
                "job_id",
                "dbu_usage"
            ]
        )


# =========================================================
# LOAD JOBS
# =========================================================

jobs = get_jobs()


if not jobs:

    st.error(
        "No Databricks jobs were found."
    )

    st.info(
        "Check the App service principal permissions."
    )

    st.stop()


# =========================================================
# LOAD DBU DATA
# =========================================================

with st.spinner(
    "Loading Databricks job DBU usage..."
):

    job_dbu_df = get_job_dbu_usage()


# =========================================================
# CREATE DBU LOOKUP
# =========================================================

dbu_lookup = {}


if not job_dbu_df.empty:

    for _, row in job_dbu_df.iterrows():

        try:

            job_id = str(
                row["job_id"]
            ).strip()

            dbu_value = float(
                row["dbu_usage"]
            )

            dbu_lookup[
                job_id
            ] = dbu_value

        except Exception:

            continue


# =========================================================
# HEADER
# =========================================================

st.title(
    "📊 Databricks Job Monitor"
)

st.caption(
    f"Authenticated as: "
    f"{current_user.user_name}"
)

st.caption(
    f"DBU usage period: "
    f"{USAGE_START_DATE} → {USAGE_END_DATE}"
)


# =========================================================
# REFRESH BUTTON
# =========================================================

refresh_col1, refresh_col2 = st.columns(
    [8, 1]
)


with refresh_col2:

    if st.button(
        "🔄 Refresh"
    ):

        st.cache_data.clear()

        st.rerun()


# =========================================================
# FILTER SECTION
# =========================================================

st.subheader(
    "🔎 Filters"
)


filter_col1, filter_col2, filter_col3 = st.columns(
    3
)


# =========================================================
# WORKSPACE FILTER
# =========================================================

with filter_col1:

    workspace_options = [
        "All Workspaces",
        "Databricks Workspace"
    ]

    selected_workspace = st.selectbox(
        "Workspace",
        workspace_options
    )


# =========================================================
# JOB NAME FILTER
# =========================================================

job_names = sorted(
    list(
        set(
            job["job_name"]
            for job in jobs
        )
    )
)


with filter_col2:

    selected_jobs = st.multiselect(
        "Job Name",
        options=job_names,
        placeholder="Select one or more jobs"
    )


# =========================================================
# CREATED BY FILTER
# =========================================================

users = sorted(
    list(
        set(
            job["created_by"]
            for job in jobs
            if job["created_by"] != "-"
        )
    )
)


with filter_col3:

    selected_user = st.selectbox(
        "Created By",
        ["All Users"] + users
    )


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_jobs = jobs.copy()


# ---------------------------------------------------------
# WORKSPACE FILTER
# ---------------------------------------------------------

if selected_workspace != "All Workspaces":

    # Current implementation is for the
    # connected workspace.

    filtered_jobs = filtered_jobs


# ---------------------------------------------------------
# JOB NAME FILTER
# ---------------------------------------------------------

if selected_jobs:

    filtered_jobs = [
        job
        for job in filtered_jobs
        if job["job_name"]
        in selected_jobs
    ]


# ---------------------------------------------------------
# CREATED BY FILTER
# ---------------------------------------------------------

if selected_user != "All Users":

    filtered_jobs = [
        job
        for job in filtered_jobs
        if job["created_by"]
        == selected_user
    ]


# =========================================================
# FILTER RESULT
# =========================================================

st.info(
    f"Showing **{len(filtered_jobs)}** of "
    f"**{len(jobs)}** jobs"
)


# =========================================================
# TABLE 1
# JOB INFORMATION + DBU + COST
# =========================================================

st.subheader(
    "1️⃣ Job Information"
)


job_information = []


for job in filtered_jobs:

    job_id = str(
        job["job_id"]
    ).strip()


    # -----------------------------------------------------
    # DBU
    # -----------------------------------------------------

    job_dbu = dbu_lookup.get(
        job_id,
        0.0
    )


    # -----------------------------------------------------
    # COST
    # -----------------------------------------------------

    estimated_cost = (
        job_dbu *
        DBU_PRICE
    )


    # -----------------------------------------------------
    # ROW
    # -----------------------------------------------------

    job_information.append(
        {
            "Workspace Name":
                "Databricks Workspace",

            "Job Name":
                job["job_name"],

            "Job ID":
                job["job_id"],

            "Created Date":
                job["created_time"],

            "Last Update Date":
                job["updated_time"],

            "Created By":
                job["created_by"],

            "DBU Usage":
                round(
                    job_dbu,
                    4
                ),

            "Estimated Cost (USD)":
                round(
                    estimated_cost,
                    2
                )
        }
    )


# =========================================================
# DISPLAY TABLE 1
# =========================================================

if job_information:

    job_information_df = pd.DataFrame(
        job_information
    )


    st.dataframe(
        job_information_df,
        use_container_width=True,
        hide_index=True,

        column_config={

            "DBU Usage":
                st.column_config.NumberColumn(
                    "DBU Usage",
                    format="%.4f"
                ),

            "Estimated Cost (USD)":
                st.column_config.NumberColumn(
                    "Estimated Cost (USD)",
                    format="$%.2f"
                )
        }
    )

else:

    st.warning(
        "No jobs match the selected filters."
    )


# =========================================================
# TABLE 2
# JOB RUN SUMMARY
# =========================================================

st.subheader(
    "2️⃣ Job Run Summary"
)


run_summary = []


for job in filtered_jobs:

    job_id = job["job_id"]

    job_name = job["job_name"]


    # -----------------------------------------------------
    # GET RUNS
    # -----------------------------------------------------

    runs = get_job_runs(
        job_id
    )


    # -----------------------------------------------------
    # COUNTERS
    # -----------------------------------------------------

    total_runs = len(
        runs
    )

    success_runs = 0

    failed_runs = 0


    # -----------------------------------------------------
    # PROCESS RUNS
    # -----------------------------------------------------

    for run in runs:

        status = get_run_status(
            run
        )

        status = status.upper()


        if status in [
            "SUCCESS",
            "SUCCEEDED"
        ]:

            success_runs += 1


        elif status in [
            "FAILED",
            "ERROR",
            "TIMED_OUT"
        ]:

            failed_runs += 1


    # -----------------------------------------------------
    # SUCCESS RATIO
    # -----------------------------------------------------

    completed_runs = (
        success_runs +
        failed_runs
    )


    if completed_runs > 0:

        success_ratio = (
            success_runs /
            completed_runs
        ) * 100

    else:

        success_ratio = 0


    # -----------------------------------------------------
    # ADD ROW
    # -----------------------------------------------------

    run_summary.append(
        {
            "Job Name":
                job_name,

            "Total Runs":
                total_runs,

            "Success Runs":
                success_runs,

            "Failed Runs":
                failed_runs,

            "Success Ratio":
                f"{success_ratio:.2f}%"
        }
    )


# =========================================================
# DISPLAY TABLE 2
# =========================================================

if run_summary:

    run_summary_df = pd.DataFrame(
        run_summary
    )

    st.dataframe(
        run_summary_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "No job run data available "
        "for the selected filters."
    )


# =========================================================
# OVERALL METRICS
# =========================================================

st.divider()


total_jobs = len(
    filtered_jobs
)


total_runs = sum(
    row["Total Runs"]
    for row in run_summary
)


total_success = sum(
    row["Success Runs"]
    for row in run_summary
)


total_failed = sum(
    row["Failed Runs"]
    for row in run_summary
)


# =========================================================
# TOTAL DBU
# =========================================================

total_dbu = sum(
    row["DBU Usage"]
    for row in job_information
)


# =========================================================
# TOTAL COST
# =========================================================

total_cost = sum(
    row["Estimated Cost (USD)"]
    for row in job_information
)


# =========================================================
# METRICS
# =========================================================

col1, col2, col3, col4, col5, col6 = st.columns(
    6
)


with col1:

    st.metric(
        "Total Jobs",
        total_jobs
    )


with col2:

    st.metric(
        "Total Runs",
        total_runs
    )


with col3:

    st.metric(
        "Successful Runs",
        total_success
    )


with col4:

    st.metric(
        "Failed Runs",
        total_failed
    )


with col5:

    st.metric(
        "Total DBU",
        f"{total_dbu:.4f}"
    )


with col6:

    st.metric(
        "Estimated Cost",
        f"${total_cost:.2f}"
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Databricks Job Monitor"
)