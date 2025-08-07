import streamlit as st

# Define the pages
home_page = st.Page("home_page.py", title="Home Page")
overview_page = st.Page("overview_page.py", title="Overview Page")

# Set up navigation
pg = st.navigation([home_page, overview_page])

pg.run()
