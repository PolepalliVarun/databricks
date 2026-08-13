import streamlit as st
from databricks.sdk import WorkspaceClient
from datetime import datetime, timezone


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Databricks Job Monitor",
    page_icon="📊",
    layout="wide"
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
    st.error("Unable to create Databricks client.")
    st.exception(e)
    st.stop()


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

        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

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
            return format_timestamp(job.created_time)

    except Exception:
        pass

    return "-"


def get_job_updated_time(job):

    try:
        if job.change_time:
            return format_timestamp(job.change_time)

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

    """
    Returns the final result state when available.
    Otherwise returns the current lifecycle state.
    """

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

        st.error("Unable to retrieve Databricks jobs.")
        st.exception(e)

    return jobs


# =========================================================
# GET ALL RUNS FOR A JOB
# =========================================================

@st.cache_data(ttl=60)
def get_job_runs(job_id):

    all_runs = []

    try:

        # -------------------------------------------------
        # First request
        # -------------------------------------------------

        response = w.jobs.list_runs(
            job_id=job_id,
            limit=100,
            expand_tasks=False
        )

        for run in response:
            all_runs.append(run)


        # -------------------------------------------------
        # Pagination
        # -------------------------------------------------

        while response.has_next_page():

            response = response.next_page()

            for run in response:
                all_runs.append(run)


        return all_runs


    except Exception as e:

        st.error(
            f"Unable to retrieve runs for Job ID {job_id}"
        )

        st.error(
            f"Error Type: {type(e).__name__}"
        )

        st.exception(e)

        return []


# =========================================================
# GET WORKSPACE NAME
# =========================================================

def get_workspace_name():

    """
    Databricks Apps run inside the current workspace.

    If the workspace name is not exposed through the SDK,
    this fallback name is used.
    """

    try:

        # Try to get workspace information
        status = w.workspace.get_status()

        if status:
            return "Databricks Workspace"

    except Exception:
        pass

    return "Databricks Workspace"


# =========================================================
# LOAD JOBS
# =========================================================

jobs = get_jobs()


if not jobs:

    st.error(
        "No Databricks jobs were found."
    )

    st.info(
        "Make sure the Databricks App service principal "
        "has Can View permission on the required jobs."
    )

    st.stop()


# =========================================================
# HEADER
# =========================================================

st.title("📊 Databricks Job Monitor")

st.caption(
    f"Authenticated as: {current_user.user_name}"
)


# =========================================================
# REFRESH
# =========================================================

refresh_col1, refresh_col2 = st.columns(
    [8, 1]
)

with refresh_col2:

    if st.button("🔄 Refresh"):

        st.cache_data.clear()

        st.rerun()


# =========================================================
# WORKSPACE
# =========================================================

workspace_name = get_workspace_name()


# =========================================================
# TABLE 1
# JOB INFORMATION
# =========================================================

st.subheader("1️⃣ Job Information")


job_information = []


for job in jobs:

    job_information.append(
        {
            "Workspace Name": workspace_name,
            "Job Name": job["job_name"],
            "Job ID": job["job_id"],
            "Created Date": job["created_time"],
            "Last Update Date": job["updated_time"],
            "Created By": job["created_by"]
        }
    )


st.dataframe(
    job_information,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# TABLE 2
# JOB RUN SUMMARY
# =========================================================

st.subheader("2️⃣ Job Run Summary")


run_summary = []


for job in jobs:

    job_id = job["job_id"]
    job_name = job["job_name"]


    # -----------------------------------------------------
    # Get runs
    # -----------------------------------------------------

    runs = get_job_runs(job_id)


    # -----------------------------------------------------
    # Count runs
    # -----------------------------------------------------

    total_runs = len(runs)

    success_runs = 0

    failed_runs = 0


    for run in runs:

        status = get_run_status(run)

        status = status.upper()


        # Successful runs
        if status in [
            "SUCCESS",
            "SUCCEEDED"
        ]:

            success_runs += 1


        # Failed runs
        elif status in [
            "FAILED",
            "ERROR",
            "TIMED_OUT"
        ]:

            failed_runs += 1


    # -----------------------------------------------------
    # Success ratio
    #
    # Running / pending runs are not included in the
    # denominator.
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
    # Add row
    # -----------------------------------------------------

    run_summary.append(
        {
            "Job Name": job_name,
            "Total Runs": total_runs,
            "Success Runs": success_runs,
            "Failed Runs": failed_runs,
            "Success Ratio": f"{success_ratio:.2f}%"
        }
    )


# =========================================================
# DISPLAY TABLE 2
# =========================================================

st.dataframe(
    run_summary,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# SUMMARY METRICS
# =========================================================

st.divider()

total_jobs = len(jobs)

total_runs_all = sum(
    row["Total Runs"]
    for row in run_summary
)

total_success_all = sum(
    row["Success Runs"]
    for row in run_summary
)

total_failed_all = sum(
    row["Failed Runs"]
    for row in run_summary
)


metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)


with metric_col1:

    st.metric(
        "Total Jobs",
        total_jobs
    )


with metric_col2:

    st.metric(
        "Total Runs",
        total_runs_all
    )


with metric_col3:

    st.metric(
        "Successful Runs",
        total_success_all
    )


with metric_col4:

    st.metric(
        "Failed Runs",
        total_failed_all
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Databricks Job Monitor | Powered by Databricks SDK"
)