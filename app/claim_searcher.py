from langchain_tavily import TavilySearch
from langchain_tavily import TavilyExtract
import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()


tavily_key = os.getenv("TAVILY_API_KEY")

search_tool = TavilySearch(
    max_results=2,
    # Uncomment the row below to limit the search results to only a few selected domains:
    # include_domains=["wwf.se", "worldwildlife.org", "britannica.com", "nature.com", "https://artfakta.se/", "naturvardsverket.se", "slu.se", "nationalgeographic.com"],
)


def search_and_extract(query, search_tool, extract_tool):
    """Search for sources and extract text from url:s for one claim.

    Args:
        query (string): search query connected to a specific claim
        search_tool (TavilySearch): An instance of the TavilySearch tool.
        extract_tool (TavilyExtract): An instance of the TavilyExtract tool.

    Returns:
        List[dict]: list with dictionaries containing title, url and content for each source.
    """
    search = search_tool.invoke({"query": query})

    search_results = search["results"]
    refined_results = []

    for res in search_results:
        url = res["url"]
        extraction = extract_tool.invoke({"urls": [url]})
        if isinstance(extraction, dict) and "results" in extraction:
            raw_content = extraction["results"][0]["raw_content"]
        else:
            raw_content = str(extraction)

        refined_results.append(
            {"title": res["title"], "url": url, "content": raw_content}
        )
    return refined_results


def search_claims(claims_list, search_tool=search_tool, extract_tool=TavilyExtract()):
    """Function to search claims / queries in parallel.

    Args:
        claims_list (list): List of claims to search.
        search_tool (TavilySearch): An instance of the TavilySearch tool.
        extract_tool (TavilyExtract): An instance of the TavilyExtract tool.

    Returns:
        List[dict]: list with dictionaries containing each claim and result.
    """
    result_list = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for claim_dict in claims_list:
            query = claim_dict["sökfråga"]
            futures.append(
                executor.submit(search_and_extract, query, search_tool, extract_tool)
            )
        for claim_dict, future in zip(claims_list, futures):
            refined_results = future.result()
            result_list.append(
                {"claim": claim_dict["påstående"], "results": refined_results}
            )
    return result_list
