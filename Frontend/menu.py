import streamlit as st


def menu():
    st.sidebar.page_link("main.py", label="Home", icon="🏠")
    # st.sidebar.page_link("pages/page_1.py", label="Upload PDF", icon="1️⃣")
    # st.sidebar.page_link("pages/page_2.py", label="Trigger Airflow", icon="2️⃣")
    # st.sidebar.page_link("pages/page_3.py", label="Query Snowflake", icon="3️⃣")
