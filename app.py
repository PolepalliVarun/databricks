import streamlit as st
from databricks.sdk import WorkspaceClient

st.set_page_config(
    page_title="Databricks Run Test",
    layout="wide"
)

st.title("Databricks Job Run Test")

w = WorkspaceClient()


# ---------------------------------------------------------
# Identity
# ---------------------------------------------------------

try:

    user = w.current_user.me()

    st.success(
        f"Authenticated as: {user.user_name}"
    )

except Exception as e:

    st.error("Authentication failed")
    st.exception(e)
    st.stop()


# ---------------------------------------------------------
# Test Job
# ---------------------------------------------------------

job_id = 271000619686762

st.write(
    f"Testing Job ID: `{job_id}`"
)


# ---------------------------------------------------------
# Job
# ---------------------------------------------------------

try:

    job = w.jobs.get(
        job_id=job_id
    )

    st.success("Job API: SUCCESS")

    st.write(
        f"Job Name: **{job.settings.name}**"
    )

except Exception as e:

    st.error("Job API: FAILED")
    st.exception(e)


# ---------------------------------------------------------
# Runs
# ---------------------------------------------------------

try:

    response = w.jobs.list_runs(
        job_id=job_id,
        limit=10
    )

    runs = list(response)

    st.success(
        f"Runs returned: {len(runs)}"
    )


    for run in runs:

        st.divider()

        status = "UNKNOWN"

        if run.state:

            if run.state.result_state:
                status = run.state.result_state.value

            elif run.state.life_cycle_state:
                status = run.state.life_cycle_state.value


        st.write(
            f"**Run ID:** {run.run_id}"
        )

        st.write(
            f"**Status:** {status}"
        )

        st.write(
            f"**Start Time:** {run.start_time}"
        )

        st.write(
            f"**End Time:** {run.end_time}"
        )

        if run.run_page_url:

            st.link_button(
                "Open Run",
                run.run_page_url
            )


except Exception as e:

    st.error("Run API: FAILED")
    st.exception(e)