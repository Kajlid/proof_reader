# ProofReader

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-%E2%9C%94%EF%B8%8F-brightgreen)](https://streamlit.io/)

## Project Description

ProofReader aims to optimize the editorial process of WWF's magazine, by offering fact-checking and suggestions on tonality improvements. This project was made by a student team collaborating with WWF for AI Sweden's Public Innovation Summer Program 2025. 


## Prerequisites 
- Python 3.12 or higher
- `uv` package installer

## Environment Setup
```bash
source .venv/bin/activate
uv sync
```

Create a `.env` file in the root directory with the following API keys:

```bash
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
```


## Running the Application
```bash
streamlit run app/app.py
```

## Managing Dependencies
Adding new dependency:

```bash
uv add <dependency>
```

## Development
This project uses:
- Streamlit as the build tool and frontend framework
- Google Gemini API for language model interaction
- Tavily Search API for retrieving web content
- LangChain for chaining prompts

## Project Structure

```
app/
├── app.py             # main app file
├── claim_searcher.py  # script for search logic for claims
├── home_page.py       # script for uploading and processing file (landing page)
├── page_2.py          # script for fact-checking and tonality check functionalities
```

## Authors 
The team consists of Ebba Leppänen Gröndal, Isabella Fu and Kajsa Lidin.