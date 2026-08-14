import streamlit as st
import pandas as pd

from databricks.sdk import WorkspaceClient
from datetime import datetime, timezone, timedelta


# =========================================================
# CONSTANTS
# =========================================================

# Workspace display name
WORKSPACE_NAME = "workspace"

# DBU usage period
USAGE_END_DATE = datetime.now(
    timezone.utc
).date()

USAGE_START_DATE = (
    USAGE_END_DATE - timedelta(days=30)
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
# PAGE TITLE
# =========================================================

st.title("📊 Databricks Job Monitor")


# =========================================================
# CURRENT USER
# =========================================================

try:

    current_user = w.current_user.me()

    st.caption(
        f"Authenticated as: {current_user.user_name}"
    )

except Exception:

    st.caption(
        "Authenticated with Databricks"
    )


# =========================================================
# HELPER - FORMAT TIMESTAMP
# =========================================================

def format_timestamp(timestamp):

    if timestamp is None:
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


# =========================================================
# HELPER - GET JOB NAME
# =========================================================

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


# =========================================================
# HELPER - GET CREATED BY
# =========================================================

def get_job_creator(job):

    try:

        if job.creator_user_name:

            return job.creator_user_name

    except Exception:

        pass

    return "-"


# =========================================================
# HELPER - GET CREATED TIME
# =========================================================

def get_created_time(job):

    try:

        value = getattr(
            job,
            "created_time",
            None
        )

        return format_timestamp(
            value
        )

    except Exception:

        return "-"


# =========================================================
# HELPER - GET LAST UPDATE TIME
# =========================================================

def get_updated_time(job):

    """
    Different Databricks SDK versions may expose
    different job metadata fields.

    getattr() is used to avoid errors such as:

        BaseJob object has no attribute change_time
    """

    possible_fields = [

        "updated_time",

        "update_time",

        "last_update_time",

        "change_time"

    ]

    for field in possible_fields:

        try:

            value = getattr(
                job,
                field,
                None
            )

            if value is not None:

                return format_timestamp(
                    value
                )

        except Exception:

            continue

    return "-"


# =========================================================
# HELPER - GET RUN RESULT STATE
# =========================================================

def get_run_result_state(run):

    """
    Returns the final result state of a job run.

    Examples:

        SUCCESS
        FAILED
        TIMED_OUT
        CANCELED

    If a final result state is not available,
    the lifecycle state is returned.
    """

    # -----------------------------------------------------
    # Try final result state
    # -----------------------------------------------------

    try:

        if (
            run.state
            and run.state.result_state
        ):

            result_state = (
                run.state
                .result_state
                .value
            )

            if result_state:

                return str(
                    result_state
                )

    except Exception:

        pass


    # -----------------------------------------------------
    # Try lifecycle state
    # -----------------------------------------------------

    try:

        if (
            run.state
            and run.state.life_cycle_state
        ):

            lifecycle_state = (
                run.state
                .life_cycle_state
                .value
            )

            if lifecycle_state:

                return str(
                    lifecycle_state
                )

    except Exception:

        pass


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
                    "workspace_name":
                        WORKSPACE_NAME,

                    "job_id":
                        job.job_id,

                    "job_name":
                        get_job_name(job),

                    "created_time":
                        get_created_time(job),

                    "updated_time":
                        get_updated_time(job),

                    "created_by":
                        get_job_creator(job)
                }
            )

        return jobs

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# GET JOB RUNS
# =========================================================

@st.cache_data(ttl=60)
def get_job_runs(job_id):

    try:

        response = w.jobs.list_runs(
            job_id=job_id,
            limit=25
        )

        return list(response)

    except Exception:

        return []


# =========================================================
# GET SQL WAREHOUSE
# =========================================================

@st.cache_data(ttl=300)
def get_sql_warehouse_id():

    try:

        warehouses = list(
            w.warehouses.list()
        )

        if not warehouses:

            return None

        # -------------------------------------------------
        # Prefer RUNNING warehouse
        # -------------------------------------------------

        for warehouse in warehouses:

            try:

                if (
                    warehouse.state
                    and
                    warehouse.state.value
                    == "RUNNING"
                ):

                    return warehouse.id

            except Exception:

                continue

        # -------------------------------------------------
        # Otherwise use first warehouse
        # -------------------------------------------------

        return warehouses[0].id

    except Exception:

        return None


# =========================================================
# GET DBU USAGE
# =========================================================

@st.cache_data(ttl=300)
def get_job_dbu_usage():

    empty_df = pd.DataFrame(
        columns=[
            "job_id",
            "dbu_usage"
        ]
    )

    warehouse_id = (
        get_sql_warehouse_id()
    )

    if not warehouse_id:

        st.warning(
            "No SQL Warehouse was found. "
            "DBU usage cannot be retrieved."
        )

        return empty_df


    # =====================================================
    # DBU QUERY
    # =====================================================

    query = f"""
    SELECT
        CAST(
            usage_metadata.job_id
            AS STRING
        ) AS job_id,

        SUM(
            usage_quantity
        ) AS dbu_usage

    FROM system.billing.usage

    WHERE usage_date >=
        DATE('{USAGE_START_DATE}')

      AND usage_date <=
        DATE('{USAGE_END_DATE}')

      AND usage_unit = 'DBU'

      AND usage_metadata.job_id
          IS NOT NULL

    GROUP BY
        CAST(
            usage_metadata.job_id
            AS STRING
        )

    ORDER BY
        dbu_usage DESC
    """


    try:

        response = (
            w.statement_execution
            .execute_statement(
                warehouse_id=warehouse_id,
                statement=query,
                wait_timeout="50s"
            )
        )


        if response.status is None:

            return empty_df


        status = (
            response.status
            .state
            .value
        )


        if status != "SUCCEEDED":

            st.warning(
                "Unable to retrieve DBU usage "
                f"from system.billing.usage. "
                f"SQL status: {status}"
            )

            return empty_df


        result = response.result


        if result is None:

            return empty_df


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
                            str(
                                job_id
                            ).strip(),

                        "dbu_usage":
                            dbu_value
                    }
                )


        if not rows:

            return empty_df


        df = pd.DataFrame(
            rows
        )


        df["job_id"] = (
            df["job_id"]
            .astype(str)
            .str.strip()
        )


        df["dbu_usage"] = (
            pd.to_numeric(
                df["dbu_usage"],
                errors="coerce"
            )
            .fillna(0.0)
        )


        # -------------------------------------------------
        # Remove duplicate Job IDs
        # -------------------------------------------------

        df = (
            df.groupby(
                "job_id",
                as_index=False
            )["dbu_usage"]
            .sum()
        )


        return df


    except Exception as e:

        st.warning(
            "Unable to retrieve DBU usage "
            "from system.billing.usage."
        )

        st.caption(
            str(e)
        )

        return empty_df


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
# LOAD JOBS
# =========================================================

jobs_result = get_jobs()


if isinstance(
    jobs_result,
    dict
):

    st.error(
        "Unable to retrieve Databricks jobs."
    )

    st.code(
        jobs_result.get(
            "error",
            "Unknown error"
        )
    )

    st.stop()


jobs = jobs_result


# =========================================================
# CHECK JOBS
# =========================================================

if not jobs:

    st.warning(
        "No Databricks jobs were found."
    )

    st.stop()


# =========================================================
# SUCCESS MESSAGE
# =========================================================

st.success(
    f"Successfully retrieved "
    f"{len(jobs)} Databricks job(s)."
)


# =========================================================
# LOAD DBU
# =========================================================

with st.spinner(
    "Loading DBU usage..."
):

    job_dbu_df = (
        get_job_dbu_usage()
    )


# =========================================================
# CREATE DBU LOOKUP
# =========================================================

dbu_lookup = {}


if not job_dbu_df.empty:

    for _, row in (
        job_dbu_df.iterrows()
    ):

        try:

            job_id = str(
                row["job_id"]
            ).strip()


            dbu_lookup[job_id] = (
                float(
                    row["dbu_usage"]
                )
            )


        except Exception:

            continue


# =========================================================
# FILTERS
# =========================================================

st.subheader(
    "🔎 Filters"
)


filter_col1, filter_col2, filter_col3 = (
    st.columns(3)
)


# =========================================================
# WORKSPACE FILTER
# =========================================================

with filter_col1:

    workspace_options = [
        "All Workspaces",
        WORKSPACE_NAME
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

created_by_values = sorted(
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
        ["All Users"] + created_by_values
    )


# =========================================================
# APPLY WORKSPACE FILTER
# =========================================================

filtered_jobs = jobs.copy()


if (
    selected_workspace
    != "All Workspaces"
):

    filtered_jobs = [

        job

        for job in filtered_jobs

        if (
            job["workspace_name"]
            == selected_workspace
        )

    ]


# =========================================================
# APPLY JOB NAME FILTER
# =========================================================

if selected_jobs:

    filtered_jobs = [

        job

        for job in filtered_jobs

        if (
            job["job_name"]
            in selected_jobs
        )

    ]


# =========================================================
# APPLY CREATED BY FILTER
# =========================================================

if (
    selected_user
    != "All Users"
):

    filtered_jobs = [

        job

        for job in filtered_jobs

        if (
            job["created_by"]
            == selected_user
        )

    ]


# =========================================================
# FILTER RESULT
# =========================================================

st.info(
    f"Showing **{len(filtered_jobs)}** "
    f"of **{len(jobs)}** jobs"
)


# =========================================================
# TABLE 1 - JOB INFORMATION
# =========================================================

st.subheader(
    "1️⃣ Job Information"
)


job_information = []


for job in filtered_jobs:

    job_id = str(
        job["job_id"]
    ).strip()


    dbu_usage = dbu_lookup.get(
        job_id,
        0.0
    )


    job_information.append(
        {
            "Workspace Name":
                WORKSPACE_NAME,

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
                    dbu_usage,
                    4
                )
        }
    )


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
                st.column_config
                .NumberColumn(
                    "DBU Usage",
                    format="%.4f"
                )

        }
    )


else:

    st.warning(
        "No jobs match the selected filters."
    )


# =========================================================
# TABLE 2 - JOB RUN SUMMARY
# =========================================================

st.subheader(
    "2️⃣ Job Run Summary"
)


run_summary = []


for job in filtered_jobs:

    job_id = job["job_id"]

    job_name = job["job_name"]


    runs = get_job_runs(
        job_id
    )


    total_runs = len(
        runs
    )


    success_runs = 0

    failed_runs = 0


    # =====================================================
    # PROCESS RUNS
    # =====================================================

    for run in runs:

        status = (
            get_run_result_state(
                run
            )
            .upper()
        )


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if status in [
            "SUCCESS",
            "SUCCEEDED"
        ]:

            success_runs += 1


        # -------------------------------------------------
        # FAILED
        # -------------------------------------------------

        elif status in [
            "FAILED",
            "ERROR",
            "TIMED_OUT"
        ]:

            failed_runs += 1


    # =====================================================
    # SUCCESS RATIO
    # =====================================================

    completed_runs = (
        success_runs
        + failed_runs
    )


    if completed_runs > 0:

        success_ratio = (
            success_runs
            / completed_runs
        ) * 100

    else:

        success_ratio = 0.0


    # =====================================================
    # ADD SUMMARY
    # =====================================================

    run_summary.append(
        {
            "Workspace Name":
                WORKSPACE_NAME,

            "Job Name":
                job_name,

            "Job ID":
                job_id,

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
# DISPLAY RUN SUMMARY
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
        "No job run information available."
    )


# =========================================================
# SUMMARY METRICS
# =========================================================

st.divider()


total_jobs = len(
    filtered_jobs
)


total_runs = sum(
    row["Total Runs"]
    for row in run_summary
)


successful_runs = sum(
    row["Success Runs"]
    for row in run_summary
)


failed_runs = sum(
    row["Failed Runs"]
    for row in run_summary
)


total_dbu = sum(
    row["DBU Usage"]
    for row in job_information
)


col1, col2, col3, col4, col5 = (
    st.columns(5)
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
        successful_runs
    )


with col4:

    st.metric(
        "Failed Runs",
        failed_runs
    )


with col5:

    st.metric(
        "Total DBU",
        f"{total_dbu:.4f}"
    )


# =========================================================
# DBU PERIOD
# =========================================================

st.divider()


st.caption(
    f"DBU Usage Period: "
    f"{USAGE_START_DATE} → "
    f"{USAGE_END_DATE}"
)


st.caption(
    "Cost calculation is currently disabled."
)