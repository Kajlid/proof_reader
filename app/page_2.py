import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_core.output_parsers.json import JsonOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from claim_searcher import search_claims

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-lite")
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", api_key=api_key)

st.set_page_config(layout="wide")

check1, check2 = st.columns([0.005, 0.04], gap="small")
with check1:
    fact_check = st.checkbox("Faktakontroll")
with check2:
    tone_check = st.checkbox("Tonalitet")



col1, col2 = st.columns([2, 1])

with col1:
    with st.container(border=True):
        if "doc_text" in st.session_state:
            st.text(st.session_state["doc_text"])


with col2:
    text = st.session_state["doc_text"]
    feedback_text = ""

    if fact_check:
        st.markdown("### **Faktakontroll**")
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

            st.markdown("### Relaterade källor:")
            for source in search_results:
                title = source["title"]
                url = source["url"]
                content = source["content"]
                evidence += content

                # Display title with a hyperlink to the URL
                st.markdown(f"[🔗 {title}]({url})", unsafe_allow_html=True)

                st.markdown(content)

                feedback_text += f"Källor: {title}\n{url}\n{content}\n\n"

            feedback_text += "\n"

            fact_check_prompt = PromptTemplate.from_template(
                """Här är ett påstående som ska kontrolleras: {claim}. 
                Stämmer påståendet utifrån den här informationen (från sökresultat) som ska användas som underlag: {evidence}? 
                
                Din uppgift är att bedöma om påståendet:
                - **Stöds av källor***
                - **Motsägs av källor**
                - **Osäkert, kan behövas undersökas närmare** (t.ex. om källorna är motstridiga eller inte direkt stödjer påståendet)
                
                Ange din slutsats med ett av dessa tre alternativ, följt av en kort motivering på högst en mening. Exempel:

                Stöds av källor  \n
                Motivering: Påståendet bekräftas direkt av en eller fler källor."""
            )

            extract_sources_chain = fact_check_prompt | llm | StrOutputParser()
            response = extract_sources_chain.invoke(
                {"claim": claim, "evidence": evidence}
            )
            st.markdown(f"### Slutsats:\n{response}")
            feedback_text += f"AI-slutsats:\n{response}"

    if tone_check:
        st.markdown("### **Tonalitetskontroll**")
        prompt = f"""Jag vill att du hjälper mig att justera tonaliteten i en text. Målet är att göra texten mer neutral, objektiv och saklig, utan att ändra dess innebörd eller fakta. Följ de här fyra stegen:

        1.Identifiera formuleringar som är subjektiva eller värderande. Leta efter ord eller uttryck som innehåller åsikter, känslor, överdrifter eller personliga värderingar.
        2.Förklara kort varför varje uttryck du identifierar är subjektivt.
        3.Föreslå en omskrivning som gör uttrycket mer neutralt och objektivt. Innehållet och betydelsen ska behållas.
        4.Presentera varje fall i exakt detta format, med en radbrytning mellan varje nytt exempel:

        **Original**: [originalformulering] \n
        **Kommentar**: [kort förklaring till varför det är subjektivt] \n
        **Omskrivning**: [neutral version] \n\n
        
                    
        Här är texten: {text}"""

        response = model.generate_content(prompt)
        st.markdown(response.text)
        feedback_text += "### Tonalitetskontroll\n" + response.text + "\n\n"

    # Downloading the result file
    st.download_button("Ladda ned feedback", feedback_text, file_name="feedback.txt")
