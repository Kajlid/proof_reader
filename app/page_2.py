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
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key)

if "feedback_text" not in st.session_state:
    st.session_state.feedback_text = ""

if "factcheck_rendered" not in st.session_state:
    st.session_state.factcheck_rendered = False

st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3rem;
        }

        .custom-article-box {
        background-color: #fffdfd;  /* tropical yellow */
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e08e79;
        max-height: 850px;          /* adjust height as needed */
        overflow-y: auto;
        }

        .custom-article-box::-webkit-scrollbar {
        display: none;  /* hide scrollbar */
        }
    </style>
""", unsafe_allow_html=True,
)


# Back button
top_col1, _, _ = st.columns([0.1, 0.8, 0.1])
with top_col1:
    if st.button("Back"):
        st.switch_page("home_page.py")


st.markdown(
    '<h1 style="text-align: center;"> Textgranskare </h1>', unsafe_allow_html=True
)


@st.cache_data(show_spinner="Söker och hämtar relaterade källor...")
def get_claim_search_output(text):
    claim_extr_prompt = PromptTemplate.from_template("""
            Du är en redaktörsassistent som arbetar med faktagranskning.

            Gå igenom följande text och extrahera endast de meningar eller stycken som innehåller sakliga påståenden - alltså fakta som skulle kunna kontrolleras genom en internetsökning.

            Gör följande:
            1. Identifiera två faktapåståenden och kopiera det ordagrant.
            2. Uteslut allt som är subjektivt, spekulativt, innehåller värderingar, eller inte går att verifiera via internet.
            3. Uteslut påståenden som innehåller personnamn.
            4. För varje påstående, formulera en fokuserad sökfråga (till exempel en Google-sökning) som kan användas för att kontrollera sanningshalten.
            5. Lista resultatet i detta format:

            [
            {{
                "påstående": "WWF bildades 1961 i Schweiz.",
                "sökfråga": "WWF bildades 1961 Schweiz"
            }}
            ]

            Text att analysera:
            \"\"\"
            {text}
            \"\"\"
            """)
    extract_sources_chain = claim_extr_prompt | llm | JsonOutputParser()
    response = extract_sources_chain.invoke({"text": text})

    result_list = search_claims(response)

    return result_list


@st.cache_data(show_spinner="Genererar tonalitetsfeedback...")
def get_tonality_feedback(text):
    prompt = f"""Jag vill att du hjälper mig att justera tonaliteten i en text. Målet är att få texten att låta mer trovärdig och naturlig, utan att ändra dess innebörd eller fakta. 
    Det är viktigt att du inte börjar outputen med exempelvis "Här är en justering av texten, steg för steg:". Följ de här fyra stegen:

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


def show_more():
    st.session_state.show_full_text = True


def show_less():
    st.session_state.show_full_text = False


col1, col2 = st.columns([2, 1])

with col1:
    selected_option = st.radio(
        "Välj granskningstyp",
        ["Faktakontroll", "Tonalitet"],
        horizontal=True,
        label_visibility="collapsed",
    )
    
    st.markdown(
        f"""
        <div class="custom-article-box">
            {st.session_state["doc_text"]}
        </div>
        """,
        unsafe_allow_html=True
    )


with col2:
    download_button_placeholder = st.empty()

    text = st.session_state["doc_text"]

    # FAKTAKOLL
    if selected_option == "Faktakontroll":
        st.markdown("## **Faktakontroll**")

        if "factcheck_results" not in st.session_state:
            st.session_state.factcheck_results = get_claim_search_output(text)
            st.session_state.feedback_text = ""  # Skriv bara över vid första körning

        if not st.session_state.factcheck_rendered:

            with st.container(border=False, height=900):
                #for idx, claim_with_source in enumerate(st.session_state.factcheck_results):
                #for idx, claim_with_source in enumerate(result_list):
                for claim_with_source in st.session_state.factcheck_results:
                    claim = claim_with_source["claim"]

                    st.markdown(f"#### Påstående:\n{claim}")
                    st.session_state.feedback_text += f"#### Påstående:\n{claim}\n\n"

                    search_results = claim_with_source["results"]

                    evidence = ""

                    summarize_prompt = PromptTemplate.from_template(
                        """Här är ett text: {content} och ett påstående: {claim}
                        
                        Din uppgift är att plocka ut 2-3 hela meningar från denna texten. 
                        
                        Regler:
                        - Utgå ifrån de delar av texten som aktivt svarar på påståendet, så andra orelaterade delar av texten bör ignoreras.
                        - Ta inte med någon ytterligare förklaring utan skriv bara ut meningarna som de är.
                        - Om du hittar en exakt eller väldigt lik formulering som påståendet bör denna tas med.
                        - Om direkta siffror nämns så bör du försöka hitta de exakta siffrorna i texten som hör ihop med formuleringen i påståendet.
                        - Generera inte nytt innehåll, utan plocka ut meningar i texten som överensstämmer mest med ämnet.
                        - Skriv ihop det som ett sammanhängande stycke i flytande text. 
                        - Skriv *INTE* ut resultatet som en punktlista.
                        - Skriv *INTE* ut det returnerade resultatet som numrerade listor. 
                        - Skriv meningarna utan citattecken. 
                        - Om du inte kan extrahera meningar, lämna då svaret som en tom sträng, utan kommentar.
                        """
                    )

                    st.markdown("#### Relaterade källor:")
                    st.session_state.feedback_text += "#### Relaterade källor:\n\n"
                    for source in search_results:
                        title = source["title"]
                        url = source["url"]
                        content = source["content"]

                        # Display title with a hyperlink to the URL
                        st.markdown(f"[🔗 {title}]({url})", unsafe_allow_html=True)

                        create_content_chain = summarize_prompt | llm | StrOutputParser()

                        output = (
                            st.empty()
                        )  # Create an empty placeholder for streamed output

                        tokens = create_content_chain.invoke(  # Replace with stream for streamed text generation
                            {"content": content, "claim": claim}
                        )
                        output.markdown(tokens)
                        new_content = tokens
                        evidence += new_content

                        st.session_state.feedback_text += f"[🔗 {title}]({url})\n\n"
                        st.session_state.feedback_text += f"{tokens}\n\n"

                    st.session_state.feedback_text += "\n"

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

                    st.markdown(f"#### Slutsats:\n{response}")
                    st.markdown("---")
                    st.session_state.feedback_text += f"#### Slutsats:\n{response}\n\n"

            st.session_state.factcheck_rendered = True
        else:
            # Just show previously generated feedback
            st.markdown(st.session_state.feedback_text)

        download_button_placeholder.download_button(
            "Ladda ned feedback",
            st.session_state.feedback_text,
            file_name="faktakontroll.txt",
            key="save_fact_check",
        )

    # TONALITETSKOLL
    elif selected_option == "Tonalitet":
        st.markdown("## **Tonalitetskontroll**")

        st.session_state.feedback_text = ""

        full_text = get_tonality_feedback(text)

        st.session_state.feedback_text += "Tonalitetskontroll\n" + full_text + "\n\n"

        download_button_placeholder.download_button(
            "Ladda ned feedback",
            st.session_state.feedback_text,
            file_name="tonalitetsfeedback.txt",
            key="save_tone_check",
        )

        if "tonality_blocks" not in st.session_state:
            raw_blocks = re.split(r"\n(?=\*\*Original\*\*:)", full_text.strip())
            st.session_state.tonality_blocks = raw_blocks
            st.session_state.show_full_text = False

        block_limit_tone = 2

        # Display either preview or full output
        if st.session_state.show_full_text:
            for block in st.session_state.tonality_blocks:
                st.markdown(block.strip())
                st.markdown("---")
            st.button("Visa mindre", on_click=show_less)
        else:
            for block in st.session_state.tonality_blocks[:block_limit_tone]:
                st.markdown(block.strip())
                st.markdown("---")
            st.button("Visa mer", on_click=show_more)
