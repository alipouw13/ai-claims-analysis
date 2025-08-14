"""
Bing Search Tool for Azure AI Foundry Agents

This tool provides Bing Search functionality to agents for web grounding,
allowing them to search the web for current information and verify facts.
"""

import logging
import json
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class BingSearchTool:
    """
    Bing Search tool for Azure AI Foundry agents
    
    This tool can be attached to agents to provide:
    - Web search capabilities
    - Current information retrieval
    - Fact verification
    - News and market data
    """
    
    def __init__(self, subscription_key: str = None, endpoint: str = None):
        self.subscription_key = subscription_key or settings.BING_SEARCH_SUBSCRIPTION_KEY
        self.endpoint = endpoint or settings.BING_SEARCH_ENDPOINT
        self._initialized = False
        
    async def initialize(self):
        """Initialize the Bing Search tool"""
        try:
            if not self.subscription_key:
                logger.warning("Bing Search subscription key not configured")
                return
                
            if not self.endpoint:
                logger.warning("Bing Search endpoint not configured")
                return
                
            self._initialized = True
            logger.info("Bing Search tool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Bing Search tool: {e}")
            raise
    
    async def search_web(
        self, 
        query: str, 
        count: int = 10,
        offset: int = 0,
        mkt: str = "en-US",
        safe_search: str = "Moderate"
    ) -> Dict[str, Any]:
        """
        Search the web using Bing Search API
        
        Args:
            query: Search query
            count: Number of results to return (max 50)
            offset: Number of results to skip
            mkt: Market/locale (e.g., "en-US")
            safe_search: Safe search level ("Off", "Moderate", "Strict")
            
        Returns:
            Search results with web pages and metadata
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            if not self.subscription_key or not self.endpoint:
                return {
                    "error": "Bing Search not configured",
                    "query": query,
                    "results": [],
                    "total_results": 0
                }
            
            # Prepare headers
            headers = {
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "Accept": "application/json"
            }
            
            # Prepare parameters
            params = {
                "q": query,
                "count": min(count, 50),  # Bing API limit
                "offset": offset,
                "mkt": mkt,
                "safesearch": safe_search,
                "responseFilter": "Webpages,News",
                "textFormat": "Raw"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/v7.0/search",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract web results
                        web_results = []
                        if "webPages" in data and "value" in data["webPages"]:
                            for result in data["webPages"]["value"]:
                                web_results.append({
                                    "title": result.get("name", ""),
                                    "url": result.get("url", ""),
                                    "snippet": result.get("snippet", ""),
                                    "date_last_crawled": result.get("dateLastCrawled", ""),
                                    "language": result.get("language", ""),
                                    "is_navigation": result.get("isNavigational", False)
                                })
                        
                        # Extract news results
                        news_results = []
                        if "news" in data and "value" in data["news"]:
                            for result in data["news"]["value"]:
                                news_results.append({
                                    "title": result.get("name", ""),
                                    "url": result.get("url", ""),
                                    "description": result.get("description", ""),
                                    "date_published": result.get("datePublished", ""),
                                    "provider": result.get("provider", [{}])[0].get("name", "") if result.get("provider") else "",
                                    "category": result.get("category", "")
                                })
                        
                        return {
                            "query": query,
                            "total_results": data.get("webPages", {}).get("totalEstimatedMatches", 0),
                            "web_results": web_results,
                            "news_results": news_results,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Bing Search API error: {response.status} - {error_text}")
                        return {
                            "error": f"Bing Search API error: {response.status}",
                            "query": query,
                            "results": [],
                            "total_results": 0
                        }
                        
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "results": [],
                "total_results": 0
            }
    
    async def search_news(
        self, 
        query: str, 
        count: int = 10,
        offset: int = 0,
        mkt: str = "en-US",
        freshness: str = "Day"
    ) -> Dict[str, Any]:
        """
        Search for news using Bing News Search API
        
        Args:
            query: News search query
            count: Number of results to return
            offset: Number of results to skip
            mkt: Market/locale
            freshness: Freshness filter ("Day", "Week", "Month")
            
        Returns:
            News search results
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            if not self.subscription_key or not self.endpoint:
                return {
                    "error": "Bing Search not configured",
                    "query": query,
                    "results": [],
                    "total_results": 0
                }
            
            # Prepare headers
            headers = {
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "Accept": "application/json"
            }
            
            # Prepare parameters
            params = {
                "q": query,
                "count": min(count, 50),
                "offset": offset,
                "mkt": mkt,
                "freshness": freshness,
                "textFormat": "Raw"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/v7.0/news/search",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        news_results = []
                        if "value" in data:
                            for result in data["value"]:
                                news_results.append({
                                    "title": result.get("name", ""),
                                    "url": result.get("url", ""),
                                    "description": result.get("description", ""),
                                    "date_published": result.get("datePublished", ""),
                                    "provider": result.get("provider", [{}])[0].get("name", "") if result.get("provider") else "",
                                    "category": result.get("category", ""),
                                    "image_url": result.get("image", {}).get("thumbnail", {}).get("contentUrl", "") if result.get("image") else ""
                                })
                        
                        return {
                            "query": query,
                            "total_results": len(news_results),
                            "news_results": news_results,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Bing News API error: {response.status} - {error_text}")
                        return {
                            "error": f"Bing News API error: {response.status}",
                            "query": query,
                            "results": [],
                            "total_results": 0
                        }
                        
        except Exception as e:
            logger.error(f"Bing news search failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "results": [],
                "total_results": 0
            }
    
    async def verify_facts(
        self, 
        statements: List[str],
        context: str = None
    ) -> Dict[str, Any]:
        """
        Verify facts by searching for supporting or contradicting information
        
        Args:
            statements: List of statements to verify
            context: Additional context for verification
            
        Returns:
            Fact verification results
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            verification_results = []
            
            for i, statement in enumerate(statements):
                # Create search query for fact verification
                search_query = f'"{statement}"'
                if context:
                    search_query += f" {context}"
                
                # Search for supporting evidence
                search_results = await self.search_web(search_query, count=5)
                
                # Analyze results for verification
                supporting_sources = []
                contradicting_sources = []
                
                if "web_results" in search_results:
                    for result in search_results["web_results"]:
                        # Simple keyword matching for verification
                        # In a real implementation, you'd use more sophisticated NLP
                        title_lower = result["title"].lower()
                        snippet_lower = result["snippet"].lower()
                        statement_lower = statement.lower()
                        
                        # Check for supporting evidence
                        if any(keyword in title_lower or keyword in snippet_lower 
                               for keyword in statement_lower.split()[:3]):
                            supporting_sources.append({
                                "url": result["url"],
                                "title": result["title"],
                                "snippet": result["snippet"]
                            })
                        else:
                            contradicting_sources.append({
                                "url": result["url"],
                                "title": result["title"],
                                "snippet": result["snippet"]
                            })
                
                verification_results.append({
                    "statement": statement,
                    "statement_id": i,
                    "supporting_sources": supporting_sources,
                    "contradicting_sources": contradicting_sources,
                    "verification_score": len(supporting_sources) / max(len(supporting_sources) + len(contradicting_sources), 1),
                    "total_sources": len(supporting_sources) + len(contradicting_sources)
                })
            
            return {
                "statements": statements,
                "verification_results": verification_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Fact verification failed: {e}")
            return {
                "error": str(e),
                "statements": statements,
                "verification_results": []
            }
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """Get the tool schema for Azure AI Foundry agent configuration"""
        return {
            "name": "bing_search_tool",
            "description": "Search the web and verify facts using Bing Search API",
            "type": "web_search",
            "capabilities": [
                "search_web",
                "search_news",
                "verify_facts"
            ],
            "supported_markets": ["en-US", "en-GB", "en-CA"],
            "safe_search_levels": ["Off", "Moderate", "Strict"],
            "freshness_options": ["Day", "Week", "Month"]
        }
