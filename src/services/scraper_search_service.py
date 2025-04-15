"""
Web scraper search service for the Just Ask AI Telegram bot.
"""
import re
import urllib.parse
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from src.config.settings import get_settings
from src.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ScraperSearchService:
    """Search service using web scraping."""

    def __init__(self):
        """Initialize scraper search service."""
        # User agent to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        logger.info("Initialized scraper search service")

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search the web using scraping.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results
        """
        try:
            # Try to use DuckDuckGo Lite (text-only version)
            results = self._search_duckduckgo_lite(query, num_results)

            # If DuckDuckGo fails or returns no results, try Bing
            if not results:
                results = self._search_bing(query, num_results)

            return results[:num_results]

        except Exception as e:
            logger.error(f"Error searching with scraper: {e}")
            return []

    def _search_duckduckgo_lite(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search using DuckDuckGo Lite.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results
        """
        try:
            # Encode the query for URL
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"

            # Send request
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')

            # Extract results
            results = []
            for tr in soup.select('tr.result-link, tr.result-snippet'):
                # Check if it's a link row
                if 'result-link' in tr.get('class', []):
                    a_tag = tr.find('a')
                    if a_tag:
                        link = a_tag.get('href', '')
                        title = a_tag.get_text(strip=True)
                        current_result = {
                            'title': title, 'link': link, 'snippet': '', 'source': 'DuckDuckGo'}
                        results.append(current_result)
                # Check if it's a snippet row
                elif 'result-snippet' in tr.get('class', []) and results:
                    snippet = tr.get_text(strip=True)
                    results[-1]['snippet'] = snippet

            return results[:num_results]

        except Exception as e:
            logger.error(f"Error searching DuckDuckGo Lite: {e}")
            return []

    def _search_bing(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search using Bing.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results
        """
        try:
            # Encode the query for URL
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://www.bing.com/search?q={encoded_query}"

            # Send request
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')

            # Extract results
            results = []
            for result in soup.select('.b_algo'):
                # Extract title and link
                title_elem = result.select_one('h2 a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')

                # Extract snippet
                snippet_elem = result.select_one('.b_caption p')
                snippet = snippet_elem.get_text(
                    strip=True) if snippet_elem else ''

                results.append({
                    'title': title,
                    'link': link,
                    'snippet': snippet,
                    'source': 'Bing',
                })

                if len(results) >= num_results:
                    break

            return results

        except Exception as e:
            logger.error(f"Error searching Bing: {e}")
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
scraper_search_service = ScraperSearchService()


def get_scraper_search_service() -> ScraperSearchService:
    """Get scraper search service instance.

    Returns:
        Scraper search service instance
    """
    return scraper_search_service
