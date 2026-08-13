import streamlit as st


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="App Context",
    page_icon="📘",
    layout="wide"
)


# =========================================================
# PAGE HEADER
# =========================================================

st.title("📘 Databricks Job Monitoring Application")

st.markdown(
    """
    This application provides a centralized view of
    Databricks job information, job execution activity,
    and DBU usage.
    """
)


# =========================================================
# 1. APPLICATION OVERVIEW
# =========================================================

st.header("1. Application Overview")

st.markdown(
    """
    The Databricks Job Monitoring Application is designed
    to provide an easy-to-use interface for monitoring and
    understanding Databricks jobs.

    Instead of manually checking individual jobs and their
    execution details, the application brings important
    job information into a single dashboard.

    The application currently focuses on two primary
    scenarios:

    - **Job Monitoring** – View and monitor Databricks jobs
      and their execution information.

    - **DBU Usage Monitoring** – View DBU consumption
      associated with individual Databricks jobs.
    """
)


# =========================================================
# 2. PURPOSE OF THE APPLICATION
# =========================================================

st.header("2. Purpose")

st.markdown(
    """
    The main purpose of the application is to simplify
    Databricks job monitoring and provide operational
    visibility.

    It helps users quickly identify:

    - Available Databricks jobs
    - Job names and Job IDs
    - Job creation information
    - Job update information
    - Job owners/creators
    - Job execution statistics
    - Successful and failed runs
    - DBU consumption by job
    """
)


# =========================================================
# 3. APPLICATION SCENARIOS
# =========================================================

st.header("3. Application Scenarios")


with st.expander(
    "📊 Scenario 1 – Job Monitoring",
    expanded=True
):

    st.markdown(
        """
        The Job Monitoring scenario provides information
        about Databricks jobs available in the connected
        workspace.

        Users can:

        - View all available jobs
        - Search/filter jobs by name
        - Filter jobs based on the creator
        - View Job IDs
        - View job creation dates
        - View last update information
        - Review job execution statistics
        - View successful and failed runs
        - Review job success ratios
        """
    )


with st.expander(
    "📈 Scenario 2 – DBU Usage"
):

    st.markdown(
        """
        The DBU Usage scenario provides visibility into
        Databricks Unit (DBU) consumption.

        DBU usage is retrieved from the Databricks
        `system.billing.usage` table.

        Job-level DBU usage is associated with the
        corresponding Databricks Job ID using:

        `usage_metadata.job_id`

        The application aggregates DBU consumption for
        the configured usage period and maps the result
        back to the corresponding Databricks jobs.

        This allows users to understand which jobs are
        consuming DBUs and how much DBU usage is associated
        with each job.
        """
    )


# =========================================================
# 4. DATA SOURCES
# =========================================================

st.header("4. Data Sources")

st.markdown(
    """
    The application uses Databricks APIs and system tables
    to retrieve the required information.
    """
)


st.subheader("Databricks Jobs API")

st.markdown(
    """
    The Databricks SDK is used to retrieve job information,
    including:

    - Job ID
    - Job name
    - Created date
    - Last update date
    - Job creator
    - Job runs
    """
)


st.subheader("Databricks System Billing")

st.markdown(
    """
    DBU usage is retrieved from:

    `system.billing.usage`

    The application uses the following information:

    - `usage_date`
    - `usage_unit`
    - `usage_quantity`
    - `usage_metadata.job_id`

    DBU records are grouped by Job ID to calculate
    job-level DBU usage.
    """
)


# =========================================================
# 5. DATA FLOW
# =========================================================

st.header("5. Application Data Flow")

st.code(
    """
Databricks Workspace
        |
        |
        +----------------------+
        |                      |
        v                      v
 Databricks Jobs API     system.billing.usage
        |                      |
        |                      |
        v                      v
   Job Details             DBU Usage
        |                      |
        |                 usage_metadata
        |                    .job_id
        |                      |
        +----------+-----------+
                   |
                   v
             Job ID Mapping
                   |
                   v
          Streamlit Dashboard
                   |
          +--------+--------+
          |                 |
          v                 v
     Job Monitor        DBU Usage
    """
)


# =========================================================
# 6. JOB MONITORING FLOW
# =========================================================

st.header("6. Job Monitoring Flow")

st.markdown(
    """
    The Job Monitoring page follows this process:

    **Step 1 – Retrieve Jobs**

    The application connects to the Databricks workspace
    and retrieves available jobs using the Databricks SDK.

    **Step 2 – Display Job Information**

    Job details such as Job Name, Job ID, Created Date,
    Last Update Date, and Created By are displayed.

    **Step 3 – Retrieve Job Runs**

    The application retrieves recent runs for each job.

    **Step 4 – Analyze Run Status**

    Runs are categorized based on their execution status.

    **Step 5 – Display Monitoring Information**

    The dashboard presents total runs, successful runs,
    failed runs, and success ratios.
    """
)


# =========================================================
# 7. DBU USAGE FLOW
# =========================================================

st.header("7. DBU Usage Flow")

st.markdown(
    """
    The DBU Usage page follows this process:

    **Step 1 – Query Billing Data**

    The application queries the Databricks
    `system.billing.usage` table.

    **Step 2 – Identify Job-Level Usage**

    Records containing:

    `usage_metadata.job_id`

    are used to associate DBU usage with Databricks jobs.

    **Step 3 – Aggregate DBU**

    DBU consumption is calculated using:

    `SUM(usage_quantity)`

    grouped by Job ID.

    **Step 4 – Map DBU to Jobs**

    The calculated DBU values are matched with the
    corresponding Job IDs retrieved from the Jobs API.

    **Step 5 – Display Results**

    The DBU usage is displayed alongside the relevant
    Databricks job information.
    """
)


# =========================================================
# 8. FILTERING
# =========================================================

st.header("8. Filtering and Navigation")

st.markdown(
    """
    The application provides filters to help users focus
    on specific jobs.

    Available filters include:

    - **Workspace**
    - **Job Name**
    - **Created By**

    These filters allow users to narrow the displayed
    information without changing the underlying data.
    """
)


# =========================================================
# 9. DBU USAGE PERIOD
# =========================================================

st.header("9. DBU Usage Period")

st.markdown(
    """
    DBU usage is currently calculated for a rolling
    30-day period.

    The period is automatically calculated based on the
    current date.

    This means the application does not require users to
    manually enter a DBU date range.
    """
)


# =========================================================
# 10. TECHNOLOGIES USED
# =========================================================

st.header("10. Technologies Used")

technologies = {
    "Frontend / Dashboard":
        "Streamlit",

    "Cloud Platform":
        "Microsoft Azure / Databricks",

    "Databricks Integration":
        "Databricks SDK for Python",

    "Job Information":
        "Databricks Jobs API",

    "Billing / DBU Information":
        "Databricks System Tables",

    "Billing Table":
        "system.billing.usage",

    "Programming Language":
        "Python",

    "Data Processing":
        "Pandas"
}


st.table(
    pd.DataFrame(
        list(
            technologies.items()
        ),
        columns=[
            "Component",
            "Technology"
        ]
    )
)


# =========================================================
# 11. BENEFITS
# =========================================================

st.header("11. Benefits")

st.markdown(
    """
    The application provides the following benefits:

    - Centralized visibility into Databricks jobs
    - Simplified job monitoring
    - Faster identification of failed executions
    - Job-level DBU visibility
    - Reduced need for manual queries
    - Easy filtering and navigation
    - Operational monitoring through a single interface
    - Foundation for future cost and usage analysis
    """
)


# =========================================================
# 12. FUTURE ENHANCEMENTS
# =========================================================

st.header("12. Future Enhancements")

st.markdown(
    """
    The application can be extended with additional
    capabilities such as:

    - Job cost calculation
    - Custom DBU date-range selection
    - Historical DBU trends
    - Job performance dashboards
    - Automated alerts for failed jobs
    - High DBU usage alerts
    - Job execution duration analysis
    - Workspace-level usage comparison
    - Export of job and usage reports
    - Additional Databricks system-table integrations
    """
)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Databricks Job Monitoring Application"
)

st.caption(
    "Application Context and Documentation"
)