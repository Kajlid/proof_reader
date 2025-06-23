import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai

# TODO: Add functionality to this page

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(layout="wide")
col1, col2, col3 = st.columns([3, 1, 2])

with col1:
    with st.container(border=True):
        if "doc_text" in st.session_state:
            st.text(st.session_state["doc_text"])


with col2:
    # Choice of suggestions
    st.checkbox("Stavningskontroll")
    st.checkbox("Faktakontroll")
    st.checkbox("Tonalitet")


with col3:
    # Downloading the result file
    text = st.session_state["doc_text"]
    response = model.generate_content(f"Ge språklig feedback på den här texten: {text}")
    st.text(response.text) 
    st.download_button("Ladda ned feedback", response.text, file_name="feedback.txt")
