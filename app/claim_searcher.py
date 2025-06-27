from langchain_tavily import TavilySearch
import os
from dotenv import load_dotenv

load_dotenv()


tavily_key = os.getenv("TAVILY_API_KEY")

search_tool = TavilySearch(
    max_results=3,
)


def search_claims(claims_list=list, search_tool=search_tool) -> list:
    result_list = []

    for claim_dict in claims_list:
        claim = claim_dict["påstående"]
        query = claim_dict["sökfråga"]

        search = search_tool.invoke({"query": query})
        search_results = search["results"]

        result_list.append({"claim": claim, "results": search_results})

    return result_list
