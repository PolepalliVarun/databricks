import streamlit as st

st.set_page_config(
    page_title="Job Monitor",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Job Monitor")

st.success("Job Monitor page is loading successfully.")

st.write("If you can see this message, Streamlit page navigation is working.")

st.info(
    "The Databricks Jobs API code has intentionally been removed "
    "from this test. We will add it after confirming the page loads."
)