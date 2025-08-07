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
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=api_key, temperature=0)


if "factcheck_feedback_text" not in st.session_state:
    st.session_state.factcheck_feedback_text = ""

if "tonality_feedback_text" not in st.session_state:
    st.session_state.tonality_feedback_text = ""

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
        border-radius: 0.625rem;
        border: 0.063rem solid #e08e79;
        max-height: 53.125rem;          /* adjust height as needed */
        overflow-y: auto;
        }

        .custom-article-box::-webkit-scrollbar {
        display: none;  /* hide scrollbar */
        }
        
         h1, h3 {
            padding-top: 1rem;
            margin_top: 0;
        }
    </style>
""",
    unsafe_allow_html=True,
)


# Back button
top_col1, _, _ = st.columns([0.1, 0.8, 0.1])
with top_col1:
    if st.button("Back"):
        for key in [
            "factcheck_results",
            "factcheck_feedback_text",
            "tonality_feedback_text",
            "factcheck_rendered",
            "tonality_blocks",
            "show_full_text",
        ]:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("home_page.py")


st.markdown(
    '<h1 style="text-align: center;"> ProofReader </h1>', unsafe_allow_html=True
)

st.markdown(
    '<h3 style="text-align: center;"> Den digitala korrekturläsaren </h3>',
    unsafe_allow_html=True,
)

st.markdown("<br><br>", unsafe_allow_html=True)


@st.cache_data(show_spinner="Söker och hämtar relaterade källor...")
def get_claim_search_output(text):
    claim_extr_prompt = PromptTemplate.from_template("""
            Du är en redaktörsassistent som arbetar med faktagranskning.

            Gå igenom följande text och extrahera endast de meningar eller stycken som innehåller sakliga påståenden - alltså fakta som skulle kunna kontrolleras genom en internetsökning.

            Gör följande:
            1. Identifiera varje faktapåstående och kopiera det ordagrant.
                - Faktapåståendena ska vara självständiga, fullständiga (dvs. inga syftningar som "båda", "de", "han", "detta"), och konkreta (innehåller namn på t.ex. plats, person, art, organisation, årtal etc.)
                - Uteslut allt som är subjektivt, spekulativt, innehåller värderingar, eller inte går att verifiera via internet.
                - Uteslut påståenden med oklara syftningar (t.ex. "båda arterna", "den här lagen", "det", "jag").
                - Uteslut påståenden som innehåller personnamn.
                - Uteslut påståenden som saknar specifika uppgifter som plats, tid, kvantitet, namn eller händelse.
                - Uteslut påståenden som är allmänt hållet och inte går att kontrollera med en tydlig faktasökning (t.ex. "Men klimatförändringarna och förlusterna av djur och natur pågår samtidigt, hela tiden.").
            6. För varje påstående, formulera en naturlig frågeformulering (t.ex. en Googlesökning) som är så informativ som möjligt. Undvik sökfraser med bara namn eller siffror. Tänk: "Hur hög är...", "Vad innebär det att...", "När grundades..." etc.
            7. Lista resultatet i detta format:

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


@st.cache_data(show_spinner=False)
def get_evidence_summary(content, claim):
    create_content_chain = summarize_prompt | llm | StrOutputParser()
    return create_content_chain.invoke({"content": content, "claim": claim})


@st.cache_data(show_spinner=False)
def get_fact_check_judgment(claim, evidence):
    extract_sources_chain = fact_check_prompt | llm | StrOutputParser()
    return extract_sources_chain.invoke({"claim": claim, "evidence": evidence})


# Det är viktigt att du inte börjar outputen med exempelvis "Här är en justering av texten, steg för steg:".
# som har en avsändare som vill informera om natur, miljö och klimat på ett lättsamt men trovärdigt sätt
@st.cache_data(show_spinner="Genererar tonalitetsfeedback...")
def get_tonality_feedback(text):
    prompt = f"""Jag vill att du hjälper mig att justera tonaliteten i en text. Målet är att få texten att låta mer naturlig, utan att ändra dess innebörd eller fakta. 
        **Viktigt:** Börja **direkt** med första identifierade formuleringen. **Skriv inte någon inledande kommentar, sammanfattning eller förklaring**. Det gäller även fraser som "Här är..." eller "Nedan följer...".  
        Följ dessa steg:

        -  Identifiera formuleringar som behöver förtydligas, samt formuleringar som har ett dåligt flyt eller är inkonsekventa i jämförelse med resten av texten. 
        -  Om formuleringana innehåller subjektiva värderingar är det tillåtet, så länge det passar i sammanhanget.
        -  Kommentera ifall påståendet innehåller ord eller beskrivningar som kan ses som överdrifter.
        -  Lämna inga kommentarer till formuleringar med citatstreck. 
        -  Förklara kort varför varje uttryck du identifierar är otydligt, har en konstig grammatisk uppbyggnad eller har dåligt flyt.
        -  Föreslå en omskrivning som är bättre formulerad utifrån din kommentar. Innehållet och betydelsen ska behållas.
        -  Presentera varje fall i exakt detta format:

        **Original**: [originalformulering] \n
        **Kommentar**: [kort förklaring till vad som kan förbättras med formuleringen] \n
        **Omskrivning**: [förbättrad formulering] \n
            
        Det är viktigt att ha med ett radbyte mellan varje del.
                    
        Här är texten: {text}"""

    response = llm.invoke(prompt)
    return response.content


# def show_more():
#     st.session_state.show_full_text = True


# def show_less():
#     st.session_state.show_full_text = False


col1, col2 = st.columns([2, 1])

with col1:
    selected_option = st.radio(
        "Välj granskningstyp",
        ["Faktakontroll", "Tonalitetsfeedback"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown(
        f"""
        <div class="custom-article-box">
            {st.session_state["doc_text"]}
        </div>
        """,
        unsafe_allow_html=True,
    )


with col2:
    download_button_placeholder = st.empty()

    text = st.session_state["doc_text"]

    # FAKTAKOLL
    if selected_option == "Faktakontroll":
        st.markdown("## **Faktakontroll**")

        if "factcheck_results" not in st.session_state:
            st.session_state.factcheck_results = get_claim_search_output(text)
            st.session_state.factcheck_feedback_text = (
                ""  # Skriv bara över vid första körning
            )

        if not st.session_state.factcheck_rendered:
            with st.container(border=False, height=900):
                for claim_with_source in st.session_state.factcheck_results:
                    claim = claim_with_source["claim"]

                    st.markdown(f"#### Påstående:\n{claim}")
                    st.session_state.factcheck_feedback_text += (
                        f"#### Påstående:\n{claim}\n\n"
                    )

                    search_results = claim_with_source["results"]

                    evidence = ""

                    # - Skriv meningarna utan citattecken.
                    summarize_prompt = PromptTemplate.from_template(
                        """Här är ett text: {content} och ett påstående: {claim}
                        
                        Din uppgift är att plocka ut 2 hela meningar från denna texten.
                        
                        Regler:
                        - Utgå ifrån de delar av texten som aktivt svarar på påståendet, så andra orelaterade delar av texten bör ignoreras.
                        - Ta inte med någon ytterligare förklaring utan skriv bara ut meningarna som de är.
                        - Om du hittar en exakt eller väldigt lik formulering i källan som matchar påståendet bör denna tas med.
                        - Om direkta siffror nämns så bör du försöka hitta de exakta siffrorna i texten som hör ihop med formuleringen i påståendet.
                        - Generera inte nytt innehåll, utan plocka ut meningar i texten som överensstämmer mest med ämnet.
                        - Skriv ihop det som ett sammanhängande stycke i flytande text, och sätt citattecken (" ") runtom hela texten (alltså inte endast för varje mening för sig). 
                        - Skriv *INTE* ut resultatet som en punktlista.
                        - Skriv *INTE* ut det returnerade resultatet som numrerade listor. 
                        - Om du inte kan extrahera meningar, lämna då svaret som en tom sträng, utan kommentar och utan citattecken ("").
                        - En annan källa som nämns i texten räknas inte som relevant text.
                        """
                    )

                    st.markdown("#### Relaterade källor:")
                    st.session_state.factcheck_feedback_text += (
                        "#### Relaterade källor:\n\n"
                    )
                    for source in search_results:
                        title = source["title"]
                        url = source["url"]
                        content = source["content"]

                        st.markdown(f"[🔗 {title}]({url})", unsafe_allow_html=True)

                        create_content_chain = (
                            summarize_prompt | llm | StrOutputParser()
                        )

                        output = (
                            st.empty()
                        )  # Create an empty placeholder for streamed output

                        # tokens = create_content_chain.invoke(  # Replace with stream for streamed text generation
                        #     {"content": content, "claim": claim}
                        # )

                        tokens = get_evidence_summary(content, claim)
                        output.markdown(tokens)
                        new_content = tokens
                        evidence += new_content

                        st.session_state.factcheck_feedback_text += (
                            f"[🔗 {title}]({url})\n\n"
                        )
                        st.session_state.factcheck_feedback_text += f"{tokens}\n\n"

                    st.session_state.factcheck_feedback_text += "\n"

                    fact_check_prompt = PromptTemplate.from_template(
                        """Här är ett påstående som ska kontrolleras: {claim}. 
                        Stämmer påståendet utifrån den här informationen (från sökresultat) som ska användas som underlag: {evidence}? 
                        
                        Din uppgift är att bedöma om påståendet:
                        - **Påståendet stöds av källor***
                        - **Påståendet motsägs av källor**
                        - **Osäkert, kan behövas undersökas närmare** (t.ex. om källorna är motstridiga eller inte direkt stödjer påståendet)
                        
                        Ange din slutsats med ett av dessa tre alternativ, följt av en kort motivering på högst en mening. Exempel:

                        Påståendet stöds av källor  \n
                        Motivering: Påståendet bekräftas direkt av en eller fler källor.

                        Det är viktigt att om ingen information kan extraheras från någon av källorna, skriv då "Ingen information hittades i källorna.", och absolut inget mer än det.
                        """
                    )

                    extract_sources_chain = fact_check_prompt | llm | StrOutputParser()
                    # response = extract_sources_chain.invoke(
                    #     {"claim": claim, "evidence": evidence}
                    # )

                    response = get_fact_check_judgment(claim, evidence)

                    st.markdown(f"#### Slutsats:\n{response}")
                    st.markdown("---")
                    st.session_state.factcheck_feedback_text += (
                        f"#### Slutsats:\n{response}\n\n====================\n\n"
                    )

            st.session_state.factcheck_rendered = True
        else:
            # Just show previously generated feedback
            st.markdown(st.session_state.factcheck_feedback_text)

        download_button_placeholder.download_button(
            "Ladda ned feedback",
            "FAKTAKONTROLL\n\n" + st.session_state.factcheck_feedback_text,
            file_name="faktakontroll.txt",
            key="save_fact_check",
        )

    # TONALITETSKOLL
    elif selected_option == "Tonalitetsfeedback":
        st.markdown("## **Tonalitetsfeedback**")

        st.session_state.tonality_feedback_text = ""

        full_text = get_tonality_feedback(text)

        # st.session_state.feedback_text += "Tonalitetskontroll\n" + full_text + "\n\n"

        if "tonality_blocks" not in st.session_state:
            raw_blocks = re.split(r"\n(?=\*\*Original\*\*:)", full_text.strip())
            st.session_state.tonality_blocks = raw_blocks
            st.session_state.show_full_text = False

        # Skriv varje block med tydlig separator i .txt-filen
        st.session_state.tonality_feedback_text += "Tonalitetsfeedback\n\n"
        for block in st.session_state.tonality_blocks:
            st.session_state.tonality_feedback_text += (
                block.strip() + "\n\n====================\n\n"
            )

        download_button_placeholder.download_button(
            "Ladda ned feedback",
            st.session_state.tonality_feedback_text,
            file_name="tonalitetsfeedback.txt",
            key="save_tone_check",
        )

        with st.container(border=False, height=900):  # Anpassa höjden efter behov
            for block in st.session_state.tonality_blocks:
                st.markdown(block.strip())
                st.markdown("---")
