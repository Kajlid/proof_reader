import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_core.output_parsers.json import JsonOutputParser
from langchain_core.runnables import Runnable
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from claim_searcher import search_claims

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-lite")
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", api_key=api_key)


class GeminiRunnable(Runnable):
    def invoke(self, input_str, config=None):
        return model.generate_content(input_str).text


st.set_page_config(layout="wide")
col1, col2, col3 = st.columns([3, 1, 2])

with col1:
    with st.container(border=True):
        if "doc_text" in st.session_state:
            st.text(st.session_state["doc_text"])


with col2:
    # Choice of suggestions
    spell_check = st.checkbox("Stavningskontroll")
    fact_check = st.checkbox("Faktakontroll")
    tone_check = st.checkbox("Tonalitet")


with col3:
    text = st.session_state["doc_text"]
    feedback_text = ""

    if spell_check:
        st.markdown("### **Stavningskontroll**")
        prompt = f"Du är en språkgranskare med fokus på svensk stavning och grammatik. Läs igenom följande text och identifiera eventuella stavfel eller grammatiska fel. Identifiera endast faktiska stavfel eller grammatiska fel enligt vedertagen svensk språkstandard (till exempel enligt SAOL och Svenska skrivregler). Gör inte ändringar i egennamn, facktermer eller etablerade främmande ord om de är korrekta i sitt sammanhang. Ge en kort, tydlig och saklig kommentar (högst en mening) för varje fel du hittar. Om texten är korrekt, skriv ingenting. Ge bara feedback om du är helt säker. Tonen på feedbacken ska hållas vänlig, respektfull och saklig: {text}"

        response = model.generate_content(prompt)
        st.markdown(response.text)
        feedback_text += "### Stavningskontroll\n" + response.text + "\n\n"

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
        }},
        {{
            "påstående": "Marie Curie upptäckte radium 1898.",
            "sökfråga": "Marie Curie radium upptäckt 1898"
        }}
        ]

        Text att analysera:
        \"\"\"
        {input_text}
        \"\"\"
        """)

        chain = claim_extr_prompt | llm | JsonOutputParser()
        response = chain.invoke({"input_text": text})
        print("Type: ", type(response))

        # response = model.generate_content(claim_extr_prompt)

        result_list = search_claims(response)

        for result in result_list:
            claim = result["claim"]

            st.markdown(f"### Påstående:\n{claim}")
            feedback_text += f"{claim}\n"

            search_results = result["results"]

            evidence = ""

            st.markdown("### Källor:")
            for source in search_results:
                title = source["title"]
                url = source["url"]
                content = source["content"]
                evidence += content

                st.page_link(url, label=title)

                st.markdown(content)

                feedback_text += f"{title}\n{url}\n{content}\n\n"

            feedback_text += "\n"

            fact_check_prompt = f"Här är ett påstående som ska kontrolleras: {claim}. Stämmer påståendet utifrån den här informationen: {evidence}? Svara med högst en mening"

            response = model.generate_content(fact_check_prompt)
            st.markdown(f"### Slutsats:\n{response.text}")
            st.markdown(response.text)

            # feedback_text += "### Faktakontroll\n" + response.text + "\n\n"

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
