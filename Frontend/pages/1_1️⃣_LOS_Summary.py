import streamlit as st
from auth import authenticator

authenticator.login()
if st.session_state["authentication_status"]:
    # Title
    st.title("View LOS Summary")

    # select topic
    option = st.selectbox('Choose a CFA Topic:', ('Residual Income Valuation',  'Equity Valuation Applications and Processes',  'Free Cash Flow Valuation'))

    website = {}
    website['Residual Income Valuation'] = "https://www.cfainstitute.org/membership/professional-development/refresher-readings/residual-income-valuation"
    website['Equity Valuation Applications and Processes'] = "https://www.cfainstitute.org/membership/professional-development/refresher-readings/equity-valuation-applications-processes"
    website['Free Cash Flow Valuation'] = "https://www.cfainstitute.org/membership/professional-development/refresher-readings/equity-valuation-applications-processes"

    # Function to load markdown
    def load_markdown(file_path):
        with open(file_path, 'r') as file:
            return file.read()
        
    markdown_text = load_markdown(f'./scripts/data/{option}LOS_Summary.md')
    st.write("CFA Website [Link](%s): " % website[option])
    st.subheader("Markdown Summary generated using OpenAI:")
    st.markdown(markdown_text, unsafe_allow_html=True)

