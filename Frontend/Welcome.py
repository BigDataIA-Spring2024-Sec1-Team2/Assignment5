import streamlit as st
import time
import streamlit_authenticator as stauth

import streamlit.components.v1 as components

import yaml
from yaml.loader import SafeLoader
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

st.set_page_config(
        page_title="Team 2: PDF Extracton",
        page_icon=":handshake",
        layout="wide"
    )


# # Streamlit app to display Airflow health check
# def streamlit_airflow_health_monitor(airflow_url):
#     # Streamlit widget to start/stop monitoring
#     start_button = st.button('check Health ')

#     monitoring = False
#     # Placeholder for displaying the health check status
#     status_placeholder = st.empty()
#     run_placeholder = st.text(f"Monitoring... : {monitoring}")
#     # Initialize the monitoring status

#     # run_placeholder = status_placeholder.text(f"Monitoring... : {monitoring}")

#     if start_button:
#         monitoring = True

#         run_placeholder = run_placeholder.text(f"Monitoring... : {monitoring}")
        
        

#     if monitoring:

#         run_placeholder = run_placeholder.text(f"Monitoring... : {monitoring}")
#         # Perform the health check
#         health_status = check_airflow_health(airflow_url)
#         # Display the health status
        
#         status_placeholder.text(f"Airflow Health Status: {health_status}")
#         # Wait for 1 second before the next check
#         time.sleep(1)







authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
)

authenticator.login()
if st.session_state["authentication_status"]:
    authenticator.logout()

    st.title("Finance Professional Development Resources")
    st.subheader("Team 2")
    st.subheader("Sayali Dalvi | Soeb Hussain | Ameya Apte")
    st.markdown("""#### Overview:
Welcome to the Development of a Structured Database and Text Extraction System for Finance Professional Development Resources! In this assignment, we are exploring the application of Models as a Service APIs to build intelligent systems for knowledge retrieval and Q/A tasks.

Throughout this assignment, we will utilize Pinecone and OpenAI APIs for the following purposes:
1. **Creating Knowledge Summaries:** Utilizing OpenAI's GPT to generate concise summaries of complex financial concepts.
2. **Generating a Knowledge Base (Q/A):** Building a comprehensive knowledge base that provides context-rich question and answer pairs.
3. **Vector Database Utilization:** Leveraging vector databases to efficiently find and answer questions from the knowledge base.
4. **Utilizing Knowledge Summaries:** Using the generated knowledge summaries to provide answers to questions.
""")
   
elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')


