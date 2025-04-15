"""
Search service for the Just Ask AI Telegram bot.
"""
from typing import Dict, List, Optional

from serpapi import GoogleSearch

from src.config.settings import get_settings
from src.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SearchService:
    """Search service using SerpAPI."""

    def __init__(self):
        """Initialize search service."""
        self.api_key = settings.SERPAPI_KEY
        logger.info("Initialized search service")

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search the web.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results
        """
        try:
            if not self.api_key:
                logger.error("SerpAPI key not found")
                return []

            # Set up search parameters
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": num_results,
            }

            # Perform search
            search = GoogleSearch(params)
            results = search.get_dict()

            # Extract organic results
            organic_results = results.get("organic_results", [])

            # Format results
            formatted_results = []
            for result in organic_results[:num_results]:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": "Google Search",
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []

    def format_results_for_prompt(self, results: List[Dict]) -> str:
        """Format search results for use in a prompt.

        Args:
            results: Search results

        Returns:
            Formatted search results
        """
        if not results:
            return "No search results found."

        formatted_text = "Search Results:\n\n"

        for i, result in enumerate(results, 1):
            # Clean and format the title
            title = result['title'].strip()

            # Clean and format the snippet
            snippet = result['snippet'].strip()
            # Ensure snippet is not too long
            if len(snippet) > 300:
                snippet = snippet[:297] + "..."

            # Format the result
            formatted_text += f"{i}. {title}\n"
            formatted_text += f"   {snippet}\n"
            formatted_text += f"   Source: {result['link']}\n\n"

        return formatted_text


# Create a singleton instance
search_service = SearchService()


def get_search_service() -> SearchService:
    """Get search service instance.

    Returns:
        Search service instance
    """
    return search_service
