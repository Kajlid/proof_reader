import streamlit as st
import docx

st.set_page_config(layout="centered")

# Main page content

st.markdown(
    '<h1 style="text-align: center;"> ProofReader </h1>', unsafe_allow_html=True
)

st.markdown(
    '<h3 style="text-align: center;"> Den digitala korrekturläsaren </h3>',
    unsafe_allow_html=True,
)

st.markdown("<br><br><br><br>", unsafe_allow_html=True)


data = st.file_uploader("Ladda upp ett dokument i Word-format", type=["docx"])

if data:
    doc = docx.Document(data)

    full_text = ""

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style = para.style.name

        # checking if Word's Heading style is used
        if style.startswith("Heading"):
            level = style.replace("Heading ", "")
            if level.isdigit():
                full_text += f"\n\n## {'#' * int(level)} {text}"
                continue

        # If not, checking for manually styled heading
        is_bold = all(run.bold for run in para.runs if run.text.strip())
        is_large = any(
            run.font.size and run.font.size.pt >= 16
            for run in para.runs
            if run.text.strip()
        )
        is_large_middle = any(
            run.font.size and 14 <= run.font.size.pt < 16
            for run in para.runs
            if run.text.strip()
        )

        if is_bold and is_large:
            full_text += f"\n\n## {text}"
        elif is_bold and is_large_middle:
            full_text += f"\n\n### {text}"
        elif is_bold:
            full_text += f"\n\n**{text}**"
        elif is_large:
            full_text += f"\n\n### {text}"  # Very big but not bold
        elif is_large_middle:
            full_text += f"\n\n#### {text}"  # Large but not bold
        else:
            full_text += f"\n\n{text}"

    st.session_state["doc_text"] = full_text

    st.switch_page("page_2.py")
