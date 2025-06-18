import streamlit as st
import pandas as pd
import numpy as np


# Define the pages
home_page = st.Page("home_page.py", title="Home Page")
page_2 = st.Page("page_2.py", title="Page 2")

# Set up navigation
pg = st.navigation([home_page, page_2])

pg.run()
