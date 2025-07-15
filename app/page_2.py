import streamlit as st
import os
from dotenv import load_dotenv
import re
import google.generativeai as genai
from langchain_core.output_parsers.json import JsonOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from claim_searcher import search_claims

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", api_key=api_key)


st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3rem;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# Back button
top_col1, _, _ = st.columns([0.1, 0.8, 0.1])
with top_col1:
    if st.button("Back"):
        st.switch_page("home_page.py")


st.markdown(
    '<h1 style="text-align: center;"> Textgranskare </h1>', unsafe_allow_html=True
)


col1, col2 = st.columns([0.05, 0.04], gap="small")
with col1:
    selected_option = st.radio(
        "Välj granskningstyp",
        ["Faktakontroll", "Tonalitet"],
        horizontal=True,
        label_visibility="collapsed",
    )


@st.cache_data(show_spinner="Söker och hämtar relaterade källor...")
def get_claim_search_output():
    claim_extr_prompt = PromptTemplate.from_template("""
            Du är en redaktörsassistent som arbetar med faktagranskning.

            Gå igenom följande text och extrahera endast de meningar eller stycken som innehåller sakliga påståenden - alltså fakta som skulle kunna kontrolleras genom en internetsökning.

            Gör följande:
            1. Identifiera varje faktapåstående och kopiera det ordagrant.
            2. Uteslut allt som är subjektivt, spekulativt, innehåller värderingar, eller inte går att verifiera via internet.
            3. För varje påstående, formulera en fokuserad sökfråga (till exempel en Google-sökning) som kan användas för att kontrollera sanningshalten.
            4. Lista resultatet i detta format:

            [
            {{
                "påstående": "WWF bildades 1961 i Schweiz.",
                "sökfråga": "WWF bildades 1961 Schweiz"
            }}
            ]

            Text att analysera:
            \"\"\"
            {input_text}
            \"\"\"
            """)
    extract_sources_chain = claim_extr_prompt | llm | JsonOutputParser()
    response = extract_sources_chain.invoke({"input_text": text})

    result_list = search_claims(response)

    return result_list


@st.cache_data(show_spinner="Genererar tonalitetsfeedback...")
def get_tonality_feedback(text):
    prompt = f"""Jag vill att du hjälper mig att justera tonaliteten i en text. Målet är att få texten att låta mer trovärdig och naturlig, utan att ändra dess innebörd eller fakta. Följ de här fyra stegen:

    1.Identifiera formuleringar som behöver förtydligas, samt formuleringar som har ett dåligt flyt eller en för slapp ton. Leta efter ord eller uttryck som innehåller överdrifter eller personliga värderingar.
    2.Förklara kort varför varje uttryck du identifierar är otydligt eller har dåligt flyt.
    3.Föreslå en omskrivning som gör uttrycket mer sammanhängande eller trovärdigt. Innehållet och betydelsen ska behållas.
    4.Presentera varje fall i exakt detta format:

    **Original**: [originalformulering] \n
    **Kommentar**: [kort förklaring till varför det är subjektivt] \n
    **Omskrivning**: [neutral version] \n
        
                    
    Här är texten: {text}"""

    response = llm.invoke(prompt)
    return response.content


col1, col2 = st.columns([2, 1])

feedback_text = ""

with col1:
    with st.container(border=True):
        if "doc_text" in st.session_state:
            st.markdown(st.session_state["doc_text"])


with col2:
    text = st.session_state["doc_text"]

    # FAKTAKOLL
    if selected_option == "Faktakontroll":
        st.download_button(
            "Ladda ned feedback", feedback_text, file_name="feedback.txt"
        )
        st.markdown("### **Faktakontroll**")

        with st.spinner("Söker och hämtar relaterade källor..."):
            claim_extr_prompt = PromptTemplate.from_template("""
            Du är en redaktörsassistent som arbetar med faktagranskning.

            Gå igenom följande text och extrahera endast de meningar eller stycken som innehåller sakliga påståenden - alltså fakta som skulle kunna kontrolleras genom en internetsökning.

            Gör följande:
            1. Identifiera varje faktapåstående och kopiera det ordagrant.
            2. Uteslut allt som är subjektivt, spekulativt, innehåller värderingar, eller inte går att verifiera via internet.
            3. För varje påstående, formulera en fokuserad sökfråga (till exempel en Google-sökning) som kan användas för att kontrollera sanningshalten.
            4. Lista resultatet i detta format:

            [
            {{
                "påstående": "WWF bildades 1961 i Schweiz.",
                "sökfråga": "WWF bildades 1961 Schweiz"
            }}
            ]

            Text att analysera:
            \"\"\"
            {input_text}
            \"\"\"
            """)

            extract_sources_chain = claim_extr_prompt | llm | JsonOutputParser()
            response = extract_sources_chain.invoke({"input_text": text})

            result_list = search_claims(response)

        for claim_with_source in result_list:
            claim = claim_with_source["claim"]

            st.markdown(f"### Påstående:\n{claim}")
            feedback_text += f"Påstående:\n{claim}\n"

            search_results = claim_with_source["results"]

            evidence = ""

            summarize_prompt = PromptTemplate.from_template(
                """Plocka ut 2-3 hela meningar från denna text: {content}. 
                Utgå ifrån de delar av texten som aktivt svarar på detta påstående: {claim}, så andra orelaterade delar av texten bör ignoreras.
                Om du hittar en exakt eller väldigt lik formulering som påståendet bör denna tas med.
                Om direkta siffror nämns så bör du försöka hitta de exakta siffrorna i texten som hör ihop med formuleringen i påståendet.
                Generera inte nytt innehåll, utan plocka ut de sammanhängande meningarna i texten som överensstämmer mest med ämnet. 
                Skapa ingen punktlista, utan skriv bara meningarna efter varandra, utan citattecken. Ta inte med någon ytterligare förklaring utan skriv bara ut meningarna som de är.
                Om du inte kan extrahera meningar, lämna då svaret som en tom sträng, utan kommentar.
                """
            )

            st.markdown("### Relaterade källor:")
            for source in search_results:
                title = source["title"]
                url = source["url"]
                content = source["content"]

                # Display title with a hyperlink to the URL
                st.markdown(f"[🔗 {title}]({url})", unsafe_allow_html=True)

                create_content_chain = summarize_prompt | llm | StrOutputParser()

                # new_content = create_content_chain.invoke(        # invoke
                # {"content": content, "claim": claim}
                # )

                response_stream = create_content_chain.stream(
                    {"content": content, "claim": claim}
                )

                # evidence += new_content

                output = st.empty()  # Create an empty placeholder
                tokens = ""

                for chunk in response_stream:
                    tokens += chunk
                    output.markdown(tokens)

                new_content = tokens
                evidence += new_content

                # st.markdown(new_content)

                feedback_text += f"Källor: {title}\n{url}\n{content}\n\n"

            feedback_text += "\n"

            fact_check_prompt = PromptTemplate.from_template(
                """Här är ett påstående som ska kontrolleras: {claim}. 
                Stämmer påståendet utifrån den här informationen (från sökresultat) som ska användas som underlag: {evidence}? 
                
                Din uppgift är att bedöma om påståendet:
                - **Påståendet stöds av källor***
                - **Påståendet motsägs av källor**
                - **Osäkert, kan behövas undersökas närmare** (t.ex. om källorna är motstridiga eller inte direkt stödjer påståendet)
                
                Ange din slutsats med ett av dessa tre alternativ, följt av en kort motivering på högst en mening. Exempel:

                Påståendet stöds av källor  \n
                Motivering: Påståendet bekräftas direkt av en eller fler källor."""
            )

            extract_sources_chain = fact_check_prompt | llm | StrOutputParser()
            response = extract_sources_chain.invoke(
                {"claim": claim, "evidence": evidence}
            )
            st.markdown(f"### Slutsats:\n{response}")
            feedback_text += f"AI-slutsats:\n{response}"

    # TONALITETSKOLL
    elif selected_option == "Tonalitet":
        st.download_button(
            "Ladda ned feedback", feedback_text, file_name="feedback.txt"
        )
        st.markdown("### **Tonalitetskontroll**")

        full_text = get_tonality_feedback(text)

        feedback_text += "### Tonalitetskontroll\n" + full_text + "\n\n"

        if "tonality_blocks" not in st.session_state:
            raw_blocks = re.split(r"\n(?=\*\*Original\*\*:)", full_text.strip())
            st.session_state.tonality_blocks = raw_blocks
            st.session_state.show_full_text = False

        block_limit = 4

        def show_more():
            st.session_state.show_full_text = True

        def show_less():
            st.session_state.show_full_text = False

        # Display either preview or full output
        if st.session_state.show_full_text:
            for block in st.session_state.tonality_blocks:
                st.markdown(block.strip())
                st.markdown("---")
            st.button("Visa mindre", on_click=show_less)
        else:
            for block in st.session_state.tonality_blocks[:block_limit]:
                st.markdown(block.strip())
                st.markdown("---")
            st.button("Visa mer", on_click=show_more)
