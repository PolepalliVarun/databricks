import os
import json
import streamlit as st
import pandas as pd

from databricks.sdk import WorkspaceClient
from datetime import datetime, timezone, timedelta


# =========================================================
# PAGE CONFIG
# =========================================================

st.title("🤖 AI Job Analysis")

st.caption(
    "Ask questions about your Databricks jobs, job runs, "
    "DBU usage, and overall job health."
)


# =========================================================
# DATE RANGE
# =========================================================

USAGE_END_DATE = datetime.now(
    timezone.utc
).date()

USAGE_START_DATE = (
    USAGE_END_DATE - timedelta(days=30)
)


# =========================================================
# AI ENDPOINT CONFIGURATION
# =========================================================

DEFAULT_ENDPOINT = os.getenv(
    "AI_ENDPOINT_NAME",
    ""
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
# HELPER FUNCTIONS
# =========================================================

def format_timestamp(timestamp):

    if timestamp is None:
        return "-"

    try:

        return datetime.fromtimestamp(
            timestamp / 1000,
            tz=timezone.utc
        ).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

    except Exception:

        return "-"


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


def get_job_creator(job):

    try:

        if job.creator_user_name:
            return job.creator_user_name

    except Exception:
        pass

    return "-"


def get_run_result_state(run):

    try:

        if (
            run.state
            and run.state.result_state
        ):

            return (
                run.state
                .result_state
                .value
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
                    "job_id":
                        str(job.job_id),

                    "job_name":
                        get_job_name(job),

                    "created_time":
                        format_timestamp(
                            getattr(
                                job,
                                "created_time",
                                None
                            )
                        ),

                    "updated_time":
                        format_timestamp(
                            getattr(
                                job,
                                "updated_time",
                                None
                            )
                        ),

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
            job_id=int(job_id),
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

        # Prefer RUNNING warehouse

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

        # Otherwise first warehouse

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
        return empty_df

    query = f"""
SELECT
    CAST(usage_metadata.job_id AS STRING) AS job_id,
    SUM(usage_quantity) AS dbu_usage
FROM system.billing.usage
WHERE usage_date >= DATE('{USAGE_START_DATE}')
  AND usage_date <= DATE('{USAGE_END_DATE}')
  AND usage_unit = 'DBU'
  AND usage_metadata.job_id IS NOT NULL
GROUP BY
    CAST(usage_metadata.job_id AS STRING)
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

        if (
            response.status.state.value
            != "SUCCEEDED"
        ):
            return empty_df

        result = response.result

        if result is None:
            return empty_df

        rows = []

        if result.data_array:

            for row in result.data_array:

                if len(row) < 2:
                    continue

                if row[0] is None:
                    continue

                try:

                    dbu_value = float(
                        row[1]
                    )

                except Exception:

                    dbu_value = 0.0

                rows.append(
                    {
                        "job_id":
                            str(row[0]).strip(),

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

        df["dbu_usage"] = pd.to_numeric(
            df["dbu_usage"],
            errors="coerce"
        ).fillna(0.0)

        df = (
            df.groupby(
                "job_id",
                as_index=False
            )["dbu_usage"]
            .sum()
        )

        return df

    except Exception:

        return empty_df


# =========================================================
# BUILD AI DATA
# =========================================================

@st.cache_data(ttl=60)
def build_analysis_data():

    jobs_result = get_jobs()

    if isinstance(
        jobs_result,
        dict
    ):

        return {
            "error":
                jobs_result.get(
                    "error",
                    "Unable to retrieve jobs."
                )
        }

    jobs = jobs_result

    dbu_df = get_job_dbu_usage()

    dbu_lookup = {}

    if not dbu_df.empty:

        for _, row in dbu_df.iterrows():

            try:

                dbu_lookup[
                    str(
                        row["job_id"]
                    ).strip()
                ] = float(
                    row["dbu_usage"]
                )

            except Exception:

                continue

    analysis_rows = []

    for job in jobs:

        job_id = str(
            job["job_id"]
        ).strip()

        runs = get_job_runs(
            job_id
        )

        total_runs = len(
            runs
        )

        success_runs = 0
        failed_runs = 0

        for run in runs:

            status = (
                get_run_result_state(
                    run
                )
                .upper()
            )

            if status in [
                "SUCCESS",
                "SUCCEEDED"
            ]:

                success_runs += 1

            elif status in [
                "FAILED",
                "ERROR",
                "TIMED_OUT"
            ]:

                failed_runs += 1

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

            success_ratio = 0.0

        analysis_rows.append(
            {
                "job_id":
                    job_id,

                "job_name":
                    job["job_name"],

                "created_by":
                    job["created_by"],

                "created_time":
                    job["created_time"],

                "updated_time":
                    job["updated_time"],

                "total_runs":
                    total_runs,

                "success_runs":
                    success_runs,

                "failed_runs":
                    failed_runs,

                "success_ratio":
                    round(
                        success_ratio,
                        2
                    ),

                "dbu_usage":
                    round(
                        dbu_lookup.get(
                            job_id,
                            0.0
                        ),
                        4
                    )
            }
        )

    return analysis_rows


# =========================================================
# LOAD DATA
# =========================================================

with st.spinner(
    "Loading job data for AI analysis..."
):

    analysis_data = (
        build_analysis_data()
    )


if isinstance(
    analysis_data,
    dict
):

    st.error(
        analysis_data.get(
            "error",
            "Unable to load job data."
        )
    )

    st.stop()


if not analysis_data:

    st.warning(
        "No job data is available for analysis."
    )

    st.stop()


# =========================================================
# DATA PREVIEW
# =========================================================

with st.expander(
    "📋 View data available to AI"
):

    preview_df = pd.DataFrame(
        analysis_data
    )

    st.dataframe(
        preview_df,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# AI ENDPOINT
# =========================================================

st.subheader(
    "⚙️ AI Configuration"
)

endpoint_name = st.text_input(
    "Databricks Model Serving Endpoint",
    value=DEFAULT_ENDPOINT,
    placeholder="Enter serving endpoint name"
)

st.caption(
    "The endpoint must be available to this "
    "Databricks App with query permission."
)


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are a Databricks Job Operations Analyst.

Analyze only the Databricks job monitoring data
provided by the application.

The available fields are:

- Job ID
- Job name
- Created by
- Created time
- Updated time
- Total runs
- Successful runs
- Failed runs
- Success ratio
- DBU usage

Rules:

1. Use only the supplied data.
2. Never invent job names, IDs, DBU values, or run counts.
3. If information is unavailable, clearly say so.
4. Identify jobs with failures.
5. Identify jobs with high DBU usage.
6. Identify jobs with low success ratios.
7. Compare jobs when requested.
8. Give practical operational recommendations.
9. Clearly separate facts from recommendations.
10. Cost information is not available.
11. Do not estimate cost.
12. Be concise and practical.
"""


# =========================================================
# CHAT SESSION
# =========================================================

if "ai_messages" not in st.session_state:

    st.session_state.ai_messages = []


# =========================================================
# QUICK QUESTIONS
# =========================================================

st.subheader(
    "💡 Quick Questions"
)

quick1, quick2, quick3, quick4 = st.columns(4)

quick_question = None


with quick1:

    if st.button(
        "Highest DBU jobs"
    ):

        quick_question = (
            "Which jobs have the highest DBU "
            "usage? Show the top 5 and explain "
            "which ones should be investigated."
        )


with quick2:

    if st.button(
        "Failed jobs"
    ):

        quick_question = (
            "Which jobs are failing most often? "
            "Analyze failed runs and success ratios."
        )


with quick3:

    if st.button(
        "Job health"
    ):

        quick_question = (
            "Give me an overall health analysis "
            "of the Databricks jobs and identify "
            "the jobs that need attention."
        )


with quick4:

    if st.button(
        "Recommendations"
    ):

        quick_question = (
            "Give me the top operational recommendations "
            "based on the current job and DBU data."
        )


# =========================================================
# DISPLAY CHAT HISTORY
# =========================================================

for message in st.session_state.ai_messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# CHAT INPUT
# =========================================================

user_question = st.chat_input(
    "Ask a question about your Databricks jobs..."
)


if quick_question:

    user_question = quick_question


# =========================================================
# PROCESS QUESTION
# =========================================================

if user_question:

    if not endpoint_name.strip():

        st.error(
            "Please enter your Databricks Model Serving "
            "endpoint name first."
        )

        st.stop()


    # -----------------------------------------------------
    # SAVE USER QUESTION
    # -----------------------------------------------------

    st.session_state.ai_messages.append(
        {
            "role": "user",
            "content": user_question
        }
    )


    with st.chat_message(
        "user"
    ):

        st.markdown(
            user_question
        )


    # -----------------------------------------------------
    # PREPARE DATA
    # -----------------------------------------------------

    data_context = json.dumps(
        analysis_data,
        indent=2,
        default=str
    )


    # Keep prompt at reasonable size

    max_context_chars = 50000

    if len(data_context) > max_context_chars:

        data_context = (
            data_context[:max_context_chars]
            + "\n...[data truncated]"
        )


    # -----------------------------------------------------
    # BUILD PROMPT
    # -----------------------------------------------------

    user_prompt = (
        "Here is the current Databricks job "
        "monitoring data:\n\n"
        "```json\n"
        + data_context
        + "\n```\n\n"
        "DBU usage period: "
        + str(USAGE_START_DATE)
        + " to "
        + str(USAGE_END_DATE)
        + "\n\n"
        "User question:\n"
        + user_question
        + "\n\n"
        "Analyze the supplied data and answer "
        "the user's question."
    )


    # -----------------------------------------------------
    # CALL MODEL SERVING
    # -----------------------------------------------------

    with st.chat_message(
        "assistant"
    ):

        with st.spinner(
            "Analyzing job data..."
        ):

            try:

                response = (
                    w
                    .serving_endpoints_data_plane
                    .query(
                        name=endpoint_name.strip(),

                        messages=[
                            {
                                "role":
                                    "system",

                                "content":
                                    SYSTEM_PROMPT
                            },
                            {
                                "role":
                                    "user",

                                "content":
                                    user_prompt
                            }
                        ],

                        temperature=0.2,

                        max_tokens=1200
                    )
                )


                # -----------------------------------------
                # READ RESPONSE
                # -----------------------------------------

                answer = None


                try:

                    if (
                        response
                        and response.choices
                    ):

                        choice = (
                            response.choices[0]
                        )


                        if (
                            choice.message
                            and
                            choice.message.content
                        ):

                            answer = (
                                choice
                                .message
                                .content
                            )

                except Exception:

                    answer = None


                # -----------------------------------------
                # FALLBACK
                # -----------------------------------------

                if not answer:

                    try:

                        response_dict = (
                            response.as_dict()
                        )

                        choices = (
                            response_dict.get(
                                "choices",
                                []
                            )
                        )

                        if choices:

                            answer = (
                                choices[0]
                                .get(
                                    "message",
                                    {}
                                )
                                .get(
                                    "content"
                                )
                            )

                    except Exception:

                        answer = None


                # -----------------------------------------
                # FINAL RESPONSE
                # -----------------------------------------

                if not answer:

                    answer = (
                        "The AI endpoint returned a response, "
                        "but the response format could not "
                        "be read."
                    )


                st.markdown(
                    answer
                )


                # -----------------------------------------
                # SAVE RESPONSE
                # -----------------------------------------

                st.session_state.ai_messages.append(
                    {
                        "role":
                            "assistant",

                        "content":
                            answer
                    }
                )


            except Exception as e:

                error_message = (
                    "Unable to query the Databricks "
                    "AI serving endpoint.\n\n"
                    "Error: `"
                    + str(e)
                    + "`"
                )


                st.error(
                    error_message
                )


                st.info(
                    """
Check the following:

1. The serving endpoint name is correct.
2. The Databricks App has Can Query permission
   on the serving endpoint.
3. The endpoint is available.
4. The endpoint supports chat messages.
"""
                )


# =========================================================
# CLEAR CHAT
# =========================================================

if st.session_state.ai_messages:

    st.divider()

    if st.button(
        "🗑️ Clear Chat"
    ):

        st.session_state.ai_messages = []

        st.rerun()