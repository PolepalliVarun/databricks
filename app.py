import streamlit as st
from databricks.sdk import WorkspaceClient

st.set_page_config(
    page_title="Databricks Job Monitor",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Databricks Job Monitor")

# ---------------------------------------------------------
# Create Databricks client
# ---------------------------------------------------------

try:
    w = WorkspaceClient()

    st.success("Databricks client created successfully.")

except Exception as e:

    st.error("Failed to create Databricks client.")

    st.exception(e)

    st.stop()


# ---------------------------------------------------------
# Check authentication
# ---------------------------------------------------------

try:

    current_user = w.current_user.me()

    st.success("Authentication: SUCCESS")

    st.info(
        f"Authenticated as: {current_user.user_name}"
    )

except Exception as e:

    st.error("Authentication: FAILED")

    st.exception(e)

    st.stop()


# ---------------------------------------------------------
# Check Jobs API
# ---------------------------------------------------------

st.subheader("Jobs API Test")

try:

    jobs = list(w.jobs.list())

    st.success("Jobs API: SUCCESS")

    st.write(
        f"Number of jobs found: **{len(jobs)}**"
    )

    if jobs:

        job_data = []

        for job in jobs:

            job_name = (
                job.settings.name
                if job.settings and job.settings.name
                else "Unnamed Job"
            )

            job_data.append(
                {
                    "Job ID": job.job_id,
                    "Job Name": job_name,
                }
            )

        st.dataframe(
            job_data,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.warning(
            "Authentication succeeded, but no jobs were returned."
        )

except Exception as e:

    st.error("Jobs API: FAILED")

    st.error(
        f"Error Type: {type(e).__name__}"
    )

    st.exception(e)