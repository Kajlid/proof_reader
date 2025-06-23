import streamlit as st
import docx

st.set_page_config(layout="centered")

# Main page content
st.markdown("# Upload file")
st.sidebar.markdown("# Upload file")

data = st.file_uploader("Upload a Word document", type =["docx"])

if data:
    doc = docx.Document(data)
    full_text = "\n".join([para.text for para in doc.paragraphs])

    st.session_state["doc_text"]= full_text

    
    st.switch_page("page_2.py")
