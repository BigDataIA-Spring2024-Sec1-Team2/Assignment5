import streamlit as st
from auth import authenticator
import pandas as pd

authenticator.login()
if st.session_state["authentication_status"]:
    # Title
    st.title("Knowledge Base (Q/A)")
    st.subheader("Question Set A")

    file_path = "../scripts/use_case_2/data/set_a.csv"
    df = pd.read_csv(file_path)
    
    for idx, row in df.iterrows():
        st.write(f"**Question {row[0]}:** {row[1]}")
        st.write(f"**Answer:** {row[2]}")
        st.divider()
