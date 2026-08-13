import streamlit as st
from databricks.sdk import WorkspaceClient, AccountClient
from datetime import datetime, timezone, timedelta
import pandas as pd
import json
import os
from io import StringIO


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Databricks Job Monitor",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# DATABRICKS WORKSPACE CLIENT
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
# DATABRICKS ACCOUNT CLIENT
# =========================================================

@st.cache_resource
def get_account_client():

    try:

        account_id = (
            st.secrets.get(
                "DATABRICKS_ACCOUNT_ID",
                os.getenv("DATABRICKS_ACCOUNT_ID")
            )
        )

        if account_id:

            return AccountClient(
                account_id=account_id
            )

        return AccountClient()

    except Exception as e:

        st.warning(
            "Databricks Account API client could not be initialized."
        )

        st.caption(
            str(e)
        )

        return None


account_client = get_account_client()


# =========================================================
# DBU PRICE
# =========================================================
#
# Replace this value with your actual DBU price.
#
# This is intentionally NOT shown as a Streamlit filter.
# =========================================================

try:

    DBU_PRICE = float(
        st.secrets.get(
            "DBU_PRICE",
            os.getenv(
                "DBU_PRICE",
                "0.15"
            )
        )
    )

except Exception:

    DBU_PRICE = 0.15


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

        if job.settings and job.settings.name:

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
# GET BILLABLE USAGE FROM ACCOUNT API
# =========================================================

@st.cache_data(ttl=300)
def get_billable_usage():

    if account_client is None:

        return pd.DataFrame()

    # -----------------------------------------------------
    # Automatically use last 30 days
    # -----------------------------------------------------

    end_date = (
        datetime.now(
            timezone.utc
        ).date()
    )

    start_date = (
        end_date -
        timedelta(days=30)
    )

    # Account API works at month level.
    # Therefore calculate the first and last month.
    start_month = start_date.strftime(
        "%Y-%m"
    )

    end_month = end_date.strftime(
        "%Y-%m"
    )

    try:

        response = (
            account_client
            .billable_usage
            .download(
                start_month=start_month,
                end_month=end_month,
                personal_data=False
            )
        )

        # -------------------------------------------------
        # Convert API response to text
        # -------------------------------------------------

        if response is None:

            return pd.DataFrame()

        if hasattr(
            response,
            "read"
        ):

            content = response.read()

        else:

            content = response

        if isinstance(
            content,
            bytes
        ):

            content = content.decode(
                "utf-8"
            )

        # -------------------------------------------------
        # Read CSV
        # -------------------------------------------------

        df = pd.read_csv(
            StringIO(
                content
            )
        )

        # -------------------------------------------------
        # Filter exact last-30-day range
        # -------------------------------------------------

        if "usage_date" in df.columns:

            df["usage_date"] = pd.to_datetime(
                df["usage_date"],
                errors="coerce"
            ).dt.date

            df = df[
                (
                    df["usage_date"]
                    >= start_date
                )
                &
                (
                    df["usage_date"]
                    <= end_date
                )
            ]

        return df

    except Exception as e:

        st.error(
            "Unable to retrieve Databricks billable usage "
            "from the Account API."
        )

        st.exception(e)

        return pd.DataFrame()


# =========================================================
# EXTRACT JOB ID FROM USAGE METADATA
# =========================================================

def extract_job_id(value):

    if value is None:

        return None

    # -----------------------------------------------------
    # Already a dictionary
    # -----------------------------------------------------

    if isinstance(
        value,
        dict
    ):

        return (
            value.get("job_id")
            or
            value.get("jobId")
        )

    # -----------------------------------------------------
    # JSON string
    # -----------------------------------------------------

    if isinstance(
        value,
        str
    ):

        value = value.strip()

        if not value:

            return None

        try:

            parsed = json.loads(
                value
            )

            if isinstance(
                parsed,
                dict
            ):

                return (
                    parsed.get("job_id")
                    or
                    parsed.get("jobId")
                )

        except Exception:

            pass

        # -------------------------------------------------
        # Fallback for strings containing job_id
        # -------------------------------------------------

        if "job_id" in value:

            try:

                parts = value.split(
                    "job_id"
                )

                if len(parts) > 1:

                    job_value = (
                        parts[1]
                        .replace(
                            ":",
                            ""
                        )
                        .replace(
                            "\"",
                            ""
                        )
                        .replace(
                            "'",
                            ""
                        )
                        .replace(
                            "{",
                            ""
                        )
                        .replace(
                            "}",
                            ""
                        )
                        .strip()
                    )

                    return job_value

            except Exception:

                pass

    return None


# =========================================================
# CALCULATE DBU BY JOB
# =========================================================

def get_job_dbu_usage(
    usage_df,
    job_id
):

    if usage_df.empty:

        return 0.0

    if "usage_quantity" not in usage_df.columns:

        return 0.0

    if "usage_metadata" not in usage_df.columns:

        return 0.0

    total_dbu = 0.0

    for _, row in usage_df.iterrows():

        try:

            usage_job_id = extract_job_id(
                row.get(
                    "usage_metadata"
                )
            )

            if usage_job_id is None:

                continue

            if str(
                usage_job_id
            ) != str(job_id):

                continue

            # -------------------------------------------------
            # Only DBU records
            # -------------------------------------------------

            if "usage_unit" in usage_df.columns:

                usage_unit = str(
                    row.get(
                        "usage_unit",
                        ""
                    )
                ).upper()

                if usage_unit != "DBU":

                    continue

            # -------------------------------------------------
            # Add usage
            # -------------------------------------------------

            usage_quantity = row.get(
                "usage_quantity",
                0
            )

            if pd.isna(
                usage_quantity
            ):

                continue

            total_dbu += float(
                usage_quantity
            )

        except Exception:

            continue

    return total_dbu


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
# LOAD BILLABLE USAGE
# =========================================================

with st.spinner(
    "Loading Databricks billable usage..."
):

    billable_usage_df = (
        get_billable_usage()
    )


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
# JOB NAME MULTISELECT FILTER
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
# USER FILTER
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

    # Currently all jobs are from the App's workspace.
    # Kept for future multi-workspace support.

    filtered_jobs = filtered_jobs


# ---------------------------------------------------------
# JOB FILTER
# ---------------------------------------------------------

if selected_jobs:

    filtered_jobs = [
        job
        for job in filtered_jobs
        if job["job_name"]
        in selected_jobs
    ]


# ---------------------------------------------------------
# USER FILTER
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
# JOB INFORMATION
# =========================================================

st.subheader(
    "1️⃣ Job Information"
)

job_information = []


for job in filtered_jobs:

    job_id = job["job_id"]

    # -----------------------------------------------------
    # DBU USAGE
    # -----------------------------------------------------

    job_dbu = get_job_dbu_usage(
        billable_usage_df,
        job_id
    )

    # -----------------------------------------------------
    # ESTIMATED COST
    # -----------------------------------------------------

    estimated_cost = (
        job_dbu *
        DBU_PRICE
    )

    # -----------------------------------------------------
    # ADD JOB INFORMATION
    # -----------------------------------------------------

    job_information.append(
        {
            "Workspace Name":
                "Databricks Workspace",

            "Job Name":
                job["job_name"],

            "Job ID":
                job_id,

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

    st.dataframe(
        job_information,
        use_container_width=True,
        hide_index=True
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
    # TOTAL RUNS
    # -----------------------------------------------------

    total_runs = len(
        runs
    )

    # -----------------------------------------------------
    # COUNTERS
    # -----------------------------------------------------

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

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if status in [
            "SUCCESS",
            "SUCCEEDED"
        ]:

            success_runs += 1

        # -------------------------------------------------
        # FAILURE
        # -------------------------------------------------

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

    st.dataframe(
        run_summary,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "No job run data available for the selected filters."
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