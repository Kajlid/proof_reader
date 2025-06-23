import streamlit as st


# TODO: Add functionality to this page

st.set_page_config(layout="wide")
col1, col2, col3 = st.columns([3, 2, 1])

with col1:
    with st.container(border=True):
        if "doc_text" in st.session_state:
            st.text(st.session_state["doc_text"])


with col2:
    # Choice of suggestions
    st.checkbox("Spell check")
    st.checkbox("Fact check")


with col3:
    # Downloading the result file 
    text = "blablabla"
    st.download_button("Download file", text, file_name="file.txt")
