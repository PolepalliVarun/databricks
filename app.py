import streamlit as st
from databricks.sdk import WorkspaceClient
from datetime import datetime, timezone


# =========================================================
# Page Configuration
# =========================================================

st.set_page_config(
    page_title="Databricks Job Monitor",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# Databricks Client
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
# Authentication Check
# =========================================================

try:

    current_user = w.current_user.me()

except Exception as e:

    st.error("Databricks authentication failed.")
    st.exception(e)
    st.stop()


# =========================================================
# Helper Functions
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


def get_job_created_time(job):

    """
    Databricks job creation time can be available
    through job settings metadata depending on API version.
    """

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


def get_creator(job):

    try:

        if job.creator_user_name:
            return job.creator_user_name

    except Exception:
        pass

    return "-"


def get_job_name(job):

    try:

        if job.settings and job.settings.name:
            return job.settings.name

    except Exception:
        pass

    return f"Job {job.job_id}"


def get_run_status(run):

    if not run.state:
        return "UNKNOWN"

    # Result state takes priority
    if run.state.result_state:

        return run.state.result_state.value

    # Otherwise lifecycle state
    if run.state.life_cycle_state:

        return run.state.life_cycle_state.value

    return "UNKNOWN"


# =========================================================
# Get Jobs
# =========================================================

@st.cache_data(ttl=60)
def get_jobs():

    jobs = []

    try:

        for job in w.jobs.list():

            if job.job_id is None:
                continue

            job_name = get_job_name(job)

            jobs.append(
                {
                    "job_id": job.job_id,
                    "job_name": job_name,
                    "created_time": get_job_created_time(job),
                    "updated_time": get_job_updated_time(job),
                    "created_by": get_creator(job),
                    "job": job
                }
            )

    except Exception as e:

        st.error("Unable to retrieve Databricks jobs.")
        st.exception(e)

    return jobs


# =========================================================
# Get Job Runs
# =========================================================

@st.cache_data(ttl=60)
def get_job_runs(job_id):

    runs = []

    try:

        response = w.jobs.list_runs(
            job_id=job_id,
            limit=100
        )

        for run in response:

            status = get_run_status(run)

            runs.append(
                {
                    "run_id": run.run_id,
                    "status": status,
                    "run": run
                }
            )

    except Exception as e:

        st.error(
            f"Unable to retrieve runs for Job ID {job_id}"
        )

        st.exception(e)

    return runs


# =========================================================
# Get Workspace Information
# =========================================================

def get_workspace_name():

    """
    Attempts to get the workspace name.

    Databricks Apps generally run against the workspace
    in which the App is deployed.
    """

    try:

        # Try workspace status information
        workspace_status = w.workspace.get_status()

        if workspace_status:

            return "Databricks Workspace"

    except Exception:

        pass

    return "Databricks Workspace"


# =========================================================
# Load Jobs
# =========================================================

jobs = get_jobs()


if not jobs:

    st.error(
        "No Databricks jobs were found."
    )

    st.info(
        "Make sure the App service principal has "
        "Can View permission on the required jobs."
    )

    st.stop()


# =========================================================
# Header
# =========================================================

st.title("📊 Databricks Job Monitor")

st.caption(
    f"Authenticated as: {current_user.user_name}"
)


# =========================================================
# Refresh Button
# =========================================================

col1, col2 = st.columns([8, 1])

with col2:

    if st.button("🔄 Refresh"):

        st.cache_data.clear()

        st.rerun()


# =========================================================
# Workspace Name
# =========================================================

workspace_name = get_workspace_name()


# =========================================================
# TABLE 1
# Job Information
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
# Job Run Summary
# =========================================================

st.subheader("2️⃣ Job Run Summary")


run_summary = []


for job in jobs:

    job_id = job["job_id"]
    job_name = job["job_name"]

    runs = get_job_runs(job_id)

    total_runs = len(runs)

    success_runs = sum(
        1
        for run in runs
        if run["status"] == "SUCCESS"
    )

    failed_runs = sum(
        1
        for run in runs
        if run["status"] in [
            "FAILED",
            "TIMED_OUT",
            "ERROR"
        ]
    )

    if total_runs > 0:

        success_ratio = (
            success_runs / total_runs
        ) * 100

    else:

        success_ratio = 0


    run_summary.append(
        {
            "Job Name": job_name,
            "Total Runs": total_runs,
            "Success Runs": success_runs,
            "Failed Runs": failed_runs,
            "Success Ratio": f"{success_ratio:.2f}%"
        }
    )


st.dataframe(
    run_summary,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# Footer
# =========================================================

st.divider()

st.caption(
    "Databricks Job Monitor"
)