import streamlit as st
from auth import authenticator
import pandas as pd
import re

authenticator.login()
if st.session_state["authentication_status"]:
    # Title
    st.title("Using Set A to Answer Question Set B")


    def parse_answer(answer):
        ans = re.findall(r"(?<![A-Za-z0-9])([ABC])(?:\.\s*)?(?=\s|:|,|$|\n.*)", answer)
        if len(ans) == 0:
            ans = re.findall(r"^([ABC])\s*", answer)
        return ans[0] if len(ans) > 0 else None
    
    def create_column(col1, col2):
        col1_val = parse_answer(col1)
        col2_val = parse_answer(col2)
        print(col1_val,col2_val)
        res = None
        if col1_val and col2_val:
            res = "\u2705" if col1_val == col2_val else "\u274C"
        return res
    file_path = "./scripts/data/report_part_3.csv"
    df = pd.read_csv(file_path)
    df['Result'] = df.apply(lambda row: create_column(row['true_ans'], row['generated_ans']), axis=1)
    accuracy = ((df['Result'] == "\u2705").sum() / len(df)) * 100

    st.divider()
    st.subheader(f"Accuracy : {round(accuracy, 2)} %")

    filtered_df = df[df['Result'].notna()]
    filtered_df = filtered_df.drop(['relativity'], axis=1)
    filtered_df = filtered_df.rename(columns={'id': 'ID', 'question': 'Question', 'true_ans': 'Correct Answer', 'generated_ans': 'Generated Answer'})
    filtered_df = filtered_df.set_index(filtered_df.columns[0])

    st.table(filtered_df)
    