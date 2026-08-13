import streamlit as st
from datetime import datetime, timezone

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import RunLifeCycleState


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Databricks Job Monitor",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------
# Databricks client
# ---------------------------------------------------------

@st.cache_resource
def get_databricks_client():
    """
    Creates a Databricks SDK client using the authentication
    configured for the Databricks App.
    """
    return WorkspaceClient()


try:
    w = get_databricks_client()
except Exception as e:
    st.error("Unable to connect to Databricks.")
    st.exception(e)
    st.stop()


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def format_timestamp(timestamp):
    """Convert Unix timestamp in milliseconds to readable time."""
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


def calculate_duration(start_time, end_time):
    """Calculate run duration."""

    if not start_time:
        return "-"

    if not end_time:
        end_time = int(datetime.now(timezone.utc).timestamp() * 1000)

    duration_seconds = (end_time - start_time) / 1000

    if duration_seconds < 60:
        return f"{duration_seconds:.0f} sec"

    minutes = duration_seconds / 60

    if minutes < 60:
        return f"{minutes:.1f} min"

    hours = minutes / 60

    return f"{hours:.1f} hr"


def get_state(run):
    """Return readable run status."""

    if not run.state:
        return "UNKNOWN"

    result_state = run.state.result_state

    if result_state:
        return str(result_state.value)

    lifecycle_state = run.state.life_cycle_state

    if lifecycle_state:
        return str(lifecycle_state.value)

    return "UNKNOWN"


def get_status_icon(status):
    """Return icon for status."""

    status = status.upper()

    if status in ["SUCCESS", "SUCCEEDED"]:
        return "🟢"

    if status in ["FAILED", "ERROR", "TIMED_OUT"]:
        return "🔴"

    if status in ["RUNNING", "PENDING", "QUEUED"]:
        return "🟡"

    if status in ["CANCELED", "CANCELLED", "SKIPPED"]:
        return "⚪"

    return "🔵"


# ---------------------------------------------------------
# Get jobs
# ---------------------------------------------------------

@st.cache_data(ttl=60)
def get_jobs():

    jobs = []

    try:

        for job in w.jobs.list():

            if job.job_id is not None:

                jobs.append(
                    {
                        "job_id": job.job_id,
                        "job_name": job.settings.name
                        if job.settings and job.settings.name
                        else f"Job {job.job_id}"
                    }
                )

    except Exception as e:

        st.error("Unable to retrieve Databricks jobs.")

        st.exception(e)

    return jobs


# ---------------------------------------------------------
# Get job runs
# ---------------------------------------------------------

@st.cache_data(ttl=30)
def get_job_runs(job_id, limit=50):

    runs = []

    try:

        response = w.jobs.list_runs(
            job_id=job_id,
            limit=limit
        )

        for run in response:

            status = get_state(run)

            runs.append(
                {
                    "run_id": run.run_id,
                    "run_name": run.run_name or "-",
                    "status": status,
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "duration": calculate_duration(
                        run.start_time,
                        run.end_time
                    ),
                    "trigger": (
                        run.trigger.value
                        if run.trigger
                        else "-"
                    ),
                    "run_page_url": run.run_page_url or "-",
                    "run": run,
                }
            )

    except Exception as e:

        st.error("Unable to retrieve job runs.")

        st.exception(e)

    return runs


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.title("📊 Databricks Job Monitor")

st.caption(
    "Monitor Databricks jobs, recent runs, status, duration, "
    "and task-level execution details."
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

st.sidebar.header("Job Configuration")

jobs = get_jobs()

if not jobs:

    st.warning(
        "No Databricks jobs were found. "
        "Check your App permissions and workspace configuration."
    )

    st.stop()


job_options = {
    f"{job['job_name']} (ID: {job['job_id']})": job["job_id"]
    for job in jobs
}

selected_job_name = st.sidebar.selectbox(
    "Select Job",
    options=list(job_options.keys())
)

selected_job_id = job_options[selected_job_name]


run_limit = st.sidebar.selectbox(
    "Number of Runs",
    options=[10, 25, 50, 100],
    index=1
)


status_filter = st.sidebar.multiselect(
    "Status Filter",
    options=[
        "SUCCESS",
        "FAILED",
        "RUNNING",
        "PENDING",
        "CANCELED",
        "SKIPPED",
        "UNKNOWN",
    ],
    default=[]
)


if st.sidebar.button("🔄 Refresh"):

    st.cache_data.clear()

    st.rerun()


# ---------------------------------------------------------
# Get runs
# ---------------------------------------------------------

runs = get_job_runs(
    selected_job_id,
    run_limit
)


# ---------------------------------------------------------
# Apply status filter
# ---------------------------------------------------------

filtered_runs = runs

if status_filter:

    filtered_runs = [
        run
        for run in runs
        if run["status"] in status_filter
    ]


# ---------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------

total_runs = len(filtered_runs)

successful_runs = sum(
    1
    for run in filtered_runs
    if run["status"] in ["SUCCESS", "SUCCEEDED"]
)

failed_runs = sum(
    1
    for run in filtered_runs
    if run["status"] in [
        "FAILED",
        "ERROR",
        "TIMED_OUT"
    ]
)

running_runs = sum(
    1
    for run in filtered_runs
    if run["status"] in [
        "RUNNING",
        "PENDING",
        "QUEUED"
    ]
)


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Runs",
        total_runs
    )

with col2:
    st.metric(
        "Successful",
        successful_runs
    )

with col3:
    st.metric(
        "Failed",
        failed_runs
    )

with col4:
    st.metric(
        "Running",
        running_runs
    )


st.divider()


# ---------------------------------------------------------
# Run table
# ---------------------------------------------------------

st.subheader("Recent Job Runs")


if not filtered_runs:

    st.info("No runs found for the selected filters.")

else:

    table_data = []

    for run in filtered_runs:

        status = run["status"]

        table_data.append(
            {
                "Run ID": run["run_id"],
                "Run Name": run["run_name"],
                "Status": f"{get_status_icon(status)} {status}",
                "Start Time": format_timestamp(
                    run["start_time"]
                ),
                "End Time": format_timestamp(
                    run["end_time"]
                ),
                "Duration": run["duration"],
                "Trigger": run["trigger"],
            }
        )

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# Run details
# ---------------------------------------------------------

st.divider()

st.subheader("🔎 Run Details")


run_options = {
    f"Run {run['run_id']} - {run['status']}": run["run_id"]
    for run in filtered_runs
}


if run_options:

    selected_run_label = st.selectbox(
        "Select a run to view details",
        options=list(run_options.keys())
    )

    selected_run_id = run_options[selected_run_label]

    selected_run = next(
        (
            run
            for run in filtered_runs
            if run["run_id"] == selected_run_id
        ),
        None
    )

    if selected_run:

        run = selected_run["run"]

        col1, col2, col3 = st.columns(3)

        with col1:

            st.write("**Run ID**")

            st.write(run.run_id)

            st.write("**Run Name**")

            st.write(run.run_name or "-")


        with col2:

            st.write("**Status**")

            status = get_state(run)

            st.write(
                f"{get_status_icon(status)} {status}"
            )

            st.write("**Trigger**")

            st.write(
                run.trigger.value
                if run.trigger
                else "-"
            )


        with col3:

            st.write("**Start Time**")

            st.write(
                format_timestamp(run.start_time)
            )

            st.write("**End Time**")

            st.write(
                format_timestamp(run.end_time)
            )


        st.write("**Duration**")

        st.write(
            calculate_duration(
                run.start_time,
                run.end_time
            )
        )


        if run.run_page_url:

            st.link_button(
                "🔗 Open Run in Databricks",
                run.run_page_url
            )


        # -------------------------------------------------
        # Task details
        # -------------------------------------------------

        st.divider()

        st.subheader("Task Details")


        tasks = run.tasks


        if not tasks:

            st.info(
                "No task-level information is available "
                "for this run."
            )

        else:

            task_data = []

            for task in tasks:

                task_status = "UNKNOWN"

                if task.state:

                    if task.state.result_state:

                        task_status = (
                            task.state.result_state.value
                        )

                    elif task.state.life_cycle_state:

                        task_status = (
                            task.state.life_cycle_state.value
                        )


                task_data.append(
                    {
                        "Task Key": task.task_key,
                        "Status": (
                            f"{get_status_icon(task_status)} "
                            f"{task_status}"
                        ),
                        "Start Time": format_timestamp(
                            task.start_time
                        ),
                        "End Time": format_timestamp(
                            task.end_time
                        ),
                        "Duration": calculate_duration(
                            task.start_time,
                            task.end_time
                        ),
                    }
                )


            st.dataframe(
                task_data,
                use_container_width=True,
                hide_index=True,
            )


        # -------------------------------------------------
        # Error information
        # -------------------------------------------------

        if run.state:

            if run.state.state_message:

                st.divider()

                st.subheader("State Message")

                st.code(
                    run.state.state_message
                )


st.divider()

st.caption(
    "Databricks Job Monitor • Powered by Databricks SDK"
)