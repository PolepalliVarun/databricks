import streamlit as st

st.set_page_config(
    page_title="Databricks Operations",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Databricks Operations Dashboard")

st.success("Main application is running successfully.")

st.markdown("""
Use the **Pages** menu on the left to open:

- 📊 Job Monitor
- 📘 App Context
""")