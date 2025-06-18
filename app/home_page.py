import streamlit as st

# Main page content
st.markdown("# Upload file")
st.sidebar.markdown("# Upload file")

st.file_uploader("Upload a Word document", type =["docx"])
