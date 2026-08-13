import os
import streamlit as st

st.title("Databricks App Debug")

st.write("Current directory:")
st.code(os.getcwd())

st.write("Files in current directory:")
st.write(os.listdir("."))

st.write("Pages directory exists:")
st.write(os.path.exists("pages"))

if os.path.exists("pages"):
    st.write("Files inside pages:")
    st.write(os.listdir("pages"))