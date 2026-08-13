import streamlit as st
from databricks.sdk import WorkspaceClient, AccountClient
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
# DATABRICKS WORKSPACE CLIENT
# =========================================================

@st.cache_resource
def get_databricks_client():
    return WorkspaceClient()


try:
    w = get_databricks_client()

except Exception as e:
    st.error("Unable to create Databricks client.")
    st.exception(e)
    st.stop()


# =========================================================
# DATABRICKS ACCOUNT CLIENT
# =========================================================

@st.cache_resource
def get_account_client():

    try:
        return AccountClient()

    except Exception:
        return None


account_client = get_account_client()


# =========================================================
# AUTHENTICATION
# =========================================================

try:

    current_user = w.current_user.me()

except Exception as e:

    st.error("Databricks authentication failed.")
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
                    "job_id": job.job_id,
                    "job_name": get_job_name(job),
                    "created_time": get_job_created_time(job),
                    "updated_time": get_job_updated_time(job),
                    "created_by": get_job_creator(job)
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

        runs = list(response)

        return runs

    except Exception as e:

        st.error(
            f"Unable to retrieve runs for Job ID {job_id}"
        )

        st.exception(e)

        return []


# =========================================================
# GET BILLABLE USAGE
# =========================================================

@st.cache_data(ttl=300)
def get_billable_usage(
    start_date,
    end_date
):

    usage_data = []

    if account_client is None:

        return usage_data

    try:

        start_datetime = datetime.combine(
            start_date,
            datetime.min.time(),
            tzinfo=timezone.utc
        )

        end_datetime = datetime.combine(
            end_date,
            datetime.max.time(),
            tzinfo=timezone.utc
        )

        response = account_client.billable_usage.download(
            start_month=start_datetime.strftime("%Y-%m"),
            end_month=end_datetime.strftime("%Y-%m")
        )

        # Download API returns CSV/text data.
        if response:

            if hasattr(response, "read"):
                content = response.read()
            else:
                content = response

            if isinstance(content, bytes):
                content = content.decode("utf-8")

            from io import StringIO

            df = pd.read_csv(
                StringIO(content)
            )

            usage_data = df.to_dict(
                orient="records"
            )

    except Exception as e:

        st.warning(
            "Unable to retrieve Databricks billable usage. "
            "Check Account API permissions and authentication."
        )

        st.caption(str(e))

    return usage_data


# =========================================================
# CALCULATE JOB DBU USAGE
# =========================================================

def calculate_job_dbu_usage(
    usage_data,
    job_id,
    start_date,
    end_date
):

    total_dbu = 0.0

    if not usage_data:
        return total_dbu

    for row in usage_data:

        try:

            # -------------------------------------------------
            # Extract job ID
            # -------------------------------------------------

            row_job_id = None

            for key in [
                "job_id",
                "jobId",
                "job_id.value"
            ]:

                if key in row:
                    row_job_id = row[key]
                    break

            if row_job_id is None:
                continue

            # Handle values such as "12345"
            # and "job-12345"
            row_job_id_str = str(
                row_job_id
            ).replace(
                "job-",
                ""
            ).strip()

            if row_job_id_str != str(job_id):
                continue

            # -------------------------------------------------
            # Extract DBU quantity
            # -------------------------------------------------

            dbu_value = None

            for key in [
                "usage_quantity",
                "usage_quantity_dbu",
                "dbu_usage",
                "quantity"
            ]:

                if key in row:

                    dbu_value = row[key]

                    break

            if dbu_value is None:
                continue

            total_dbu += float(
                dbu_value
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
# HEADER
# =========================================================

st.title(
    "📊 Databricks Job Monitor"
)

st.caption(
    f"Authenticated as: {current_user.user_name}"
)


# =========================================================
# REFRESH BUTTON
# =========================================================

refresh_col1, refresh_col2 = st.columns(
    [8, 1]
)

with refresh_col2:

    if st.button("🔄 Refresh"):

        st.cache_data.clear()

        st.rerun()


# =========================================================
# FILTER SECTION
# =========================================================

st.subheader("🔎 Filters")


filter_col1, filter_col2, filter_col3 = st.columns(3)


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
# COST / DBU DATE RANGE
# =========================================================

st.subheader("💰 DBU & Cost Configuration")

cost_col1, cost_col2, cost_col3 = st.columns(3)


with cost_col1:

    default_start_date = (
        datetime.now(timezone.utc).date()
        - timedelta(days=30)
    )

    usage_start_date = st.date_input(
        "Usage Start Date",
        value=default_start_date
    )


with cost_col2:

    usage_end_date = st.date_input(
        "Usage End Date",
        value=datetime.now(timezone.utc).date()
    )


with cost_col3:

    dbu_price = st.number_input(
        "DBU Price (USD)",
        min_value=0.0,
        value=0.15,
        step=0.01,
        format="%.4f",
        help="Enter the applicable DBU price for your workload."
    )


# =========================================================
# VALIDATE DATE RANGE
# =========================================================

if usage_start_date > usage_end_date:

    st.error(
        "Usage Start Date cannot be greater than Usage End Date."
    )

    st.stop()


# =========================================================
# LOAD BILLABLE USAGE
# =========================================================

with st.spinner(
    "Loading Databricks billable usage..."
):

    billable_usage = get_billable_usage(
        usage_start_date,
        usage_end_date
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
    # This is kept here for future multi-workspace support.

    filtered_jobs = filtered_jobs


# ---------------------------------------------------------
# MULTIPLE JOB FILTER
# ---------------------------------------------------------

if selected_jobs:

    filtered_jobs = [
        job
        for job in filtered_jobs
        if job["job_name"] in selected_jobs
    ]


# ---------------------------------------------------------
# USER FILTER
# ---------------------------------------------------------

if selected_user != "All Users":

    filtered_jobs = [
        job
        for job in filtered_jobs
        if job["created_by"] == selected_user
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
    # Calculate DBU usage
    # -----------------------------------------------------

    job_dbu = calculate_job_dbu_usage(
        billable_usage,
        job_id,
        usage_start_date,
        usage_end_date
    )

    # -----------------------------------------------------
    # Calculate estimated cost
    # -----------------------------------------------------

    estimated_cost = (
        job_dbu * dbu_price
    )

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
                round(job_dbu, 4),

            "Estimated Cost (USD)":
                round(estimated_cost, 2)
        }
    )


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
    # Get runs
    # -----------------------------------------------------

    runs = get_job_runs(
        job_id
    )


    # -----------------------------------------------------
    # Total runs
    # -----------------------------------------------------

    total_runs = len(runs)


    # -----------------------------------------------------
    # Counters
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
        # Successful runs
        # -------------------------------------------------

        if status in [
            "SUCCESS",
            "SUCCEEDED"
        ]:

            success_runs += 1


        # -------------------------------------------------
        # Failed runs
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
# TOTAL DBU / COST
# =========================================================

total_dbu = sum(
    row["DBU Usage"]
    for row in job_information
)


total_cost = sum(
    row["Estimated Cost (USD)"]
    for row in job_information
)


col1, col2, col3, col4, col5, col6 = st.columns(6)


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