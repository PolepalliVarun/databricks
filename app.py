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

    selected_job = st.selectbox(
        "Job Name",
        ["All Jobs"] + job_names
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


# Workspace filter

if selected_workspace != "All Workspaces":

    # Currently all jobs belong to this workspace.
    # This structure allows multiple workspaces later.

    filtered_jobs = filtered_jobs


# Job filter

if selected_job != "All Jobs":

    filtered_jobs = [
        job
        for job in filtered_jobs
        if job["job_name"] == selected_job
    ]


# User filter

if selected_user != "All Users":

    filtered_jobs = [
        job
        for job in filtered_jobs
        if job["created_by"] == selected_user
    ]


# =========================================================
# FILTER RESULT COUNT
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
                job["created_by"]
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


    # Get runs
    runs = get_job_runs(job_id)


    # Total runs
    total_runs = len(runs)


    # Counters
    success_runs = 0

    failed_runs = 0


    # -----------------------------------------------------
    # PROCESS RUNS
    # -----------------------------------------------------

    for run in runs:

        status = get_run_status(run)

        status = status.upper()


        # Success
        if status in [
            "SUCCESS",
            "SUCCEEDED"
        ]:

            success_runs += 1


        # Failed
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


total_jobs = len(filtered_jobs)


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


col1, col2, col3, col4 = st.columns(4)


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


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Databricks Job Monitor"
)