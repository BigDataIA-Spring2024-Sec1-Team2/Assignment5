import streamlit as st
from auth import authenticator
import pandas as pd
import re

authenticator.login()
if st.session_state["authentication_status"]:
    # Title
    st.title("Using Knowledge Base to Answer Question Set B")


    def parse_answer(answer):
        # print(answer)
        ans = re.findall(r"(?<![A-Za-z0-9])([ABC])\.(?=\s)", answer)
        if len(ans) == 0:
            ans = re.findall(r"^([ABC])\s*", answer)
        # print("Parsed answer")
        # print(ans)
        return ans[0] if len(ans) > 0 else None
    
    def create_column(col1, col2):
        col1_val = parse_answer(col1)
        col2_val = parse_answer(col2)
        res = None
        if col1_val and col2_val:
            res = "✅" if col1_val == col2_val else "❌"
        return res

    file_path = "../scripts/use_case_2/data/report_part_4.csv"
    df = pd.read_csv(file_path)
    
    df['Result'] = df.apply(lambda row: create_column(row['true_ans'], row['generated_ans']), axis=1)
    print(len(df))
    # print(df['Result'])
    accuracy = ((df['Result'] == "✅").sum() / len(df)) * 100

    st.divider()
    st.subheader(f"Accuracy : {round(accuracy, 2)} %")

    filtered_df = df[df['Result'].notna()]
    filtered_df = filtered_df.drop(['relativity'], axis=1)
    filtered_df = filtered_df.rename(columns={'id': 'ID', 'question': 'Question', 'true_ans': 'Correct Answer', 'generated_ans': 'Generated Answer'})
    filtered_df = filtered_df.set_index(filtered_df.columns[0])
    print(filtered_df)

    st.table(filtered_df)
    
    # col1, col2, col3, col4 = st.columns(4)
    # with col1:
    #     st.write(f"**Question (from Set B)**")
    # with col2:
    #     st.write(f"**Correct Answer**")
    # with col3:
    #     st.write(f"**Generated Answer**")
    # with col4:
    #     st.write(f"**Same?**")
    # st.divider()
    # for idx, row in df.iterrows():
    #     col1, col2, col3, col4 = st.columns(4)
    #     if row[4] != None:
    #         with col1:
    #             st.write(f"{row[0]}: {row[1]}")
    #         with col2:
    #             st.write(row[2])
    #         with col3:
    #             st.write(row[3])
    #         with col4:
    #             st.write(row[5])
    #         st.divider()
