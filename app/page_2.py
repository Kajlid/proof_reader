import streamlit as st

# TODO: Add functionality to this page

col1, col2 = st.columns([3, 1])

with col1:
    # Choice of suggestions
    st.checkbox("Spell check")
    st.checkbox("Fact check")


with col2:
    # Downloading the result file 
    text = "blablabla"
    st.download_button("Download file", text, file_name="file.txt")
