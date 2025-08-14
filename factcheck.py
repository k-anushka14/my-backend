import asyncio
import re
import json
from typing import Dict, List, Optional, Any
import httpx
from bs4 import BeautifulSoup
from config import settings
from cache import cache

class FactCheckService:
    """Fact-checking service using Google Fact Check Tools API and Politifact fallback."""
    
    def __init__(self):
        self.google_api_key = settings.GOOGLE_FACT_CHECK_API_KEY
        self.google_base_url = "https://factchecktools.googleapis.com/v1alpha1"
        self.politifact_base_url = "https://www.politifact.com"
        self.http_client = None
        self._session_lock = asyncio.Lock()
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with timeout."""
        if not self.http_client:
            async with self._session_lock:
                if not self.http_client:
                    self.http_client = httpx.AsyncClient(
                        timeout=settings.REQUEST_TIMEOUT_SECONDS,
                        headers={
                            'User-Agent': 'FakeNewsDetector/1.0 (Chrome Extension)',
                            'Accept': 'application/json, text/html'
                        }
                    )
        return self.http_client
    
    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize search query for safety."""
        if not query or not isinstance(query, str):
            return ""
        
        # Remove potentially dangerous characters
        query = re.sub(r'[<>"\']', '', query)
        query = re.sub(r'javascript:', '', query, flags=re.IGNORECASE)
        query = re.sub(r'data:', '', query, flags=re.IGNORECASE)
        
        # Limit length
        query = query[:500].strip()
        
        return query
    
    async def fact_check(self, query: str) -> Dict[str, Any]:
        """Perform fact-checking on a query."""
        # Sanitize input
        sanitized_query = self._sanitize_query(query)
        if not sanitized_query:
            return {
                "error": "Invalid or empty query",
                "claims": [],
                "source": "none"
            }
        
        # Check cache first
        cached_result = await cache.get_api_response("factcheck", sanitized_query)
        if cached_result:
            return cached_result
        
        try:
            # Try Google Fact Check API first
            if self.google_api_key:
                result = await self._google_fact_check(sanitized_query)
                if result and result.get("claims"):
                    # Cache successful result
                    await cache.set_api_response("factcheck", sanitized_query, result)
                    return result
            
            # Fallback to Politifact scraping
            result = await self._politifact_fact_check(sanitized_query)
            if result:
                # Cache result
                await cache.set_api_response("factcheck", sanitized_query, result)
                return result
            
            # No results found
            return {
                "claims": [],
                "source": "none",
                "message": "No fact-checking results found"
            }
            
        except Exception as e:
            print(f"Fact-checking error: {e}")
            return {
                "error": f"Fact-checking service error: {str(e)}",
                "claims": [],
                "source": "error"
            }
    
    async def _google_fact_check(self, query: str) -> Optional[Dict[str, Any]]:
        """Use Google Fact Check Tools API."""
        try:
            client = await self._get_http_client()
            
            params = {
                'key': self.google_api_key,
                'query': query,
                'maxAgeDays': 365,  # Look back 1 year
                'pageSize': 10
            }
            
            response = await client.get(f"{self.google_base_url}/claims:search", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('claims'):
                return None
            
            claims = []
            for claim in data['claims']:
                claim_info = {
                    'text': claim.get('text', ''),
                    'claimant': claim.get('claimant', 'Unknown'),
                    'claimDate': claim.get('claimDate', ''),
                    'reviewDate': claim.get('reviewDate', ''),
                    'rating': self._normalize_google_rating(claim.get('textualRating', '')),
                    'url': claim.get('claimReview', [{}])[0].get('url', '') if claim.get('claimReview') else '',
                    'reviewer': claim.get('claimReview', [{}])[0].get('publisher', {}).get('name', '') if claim.get('claimReview') else '',
                    'source': 'google_fact_check'
                }
                claims.append(claim_info)
            
            return {
                "claims": claims,
                "source": "google_fact_check",
                "total_results": len(claims)
            }
            
        except Exception as e:
            print(f"Google Fact Check API error: {e}")
            return None
    
    def _normalize_google_rating(self, rating: str) -> str:
        """Normalize Google's rating to standard format."""
        rating_lower = rating.lower()
        
        if any(word in rating_lower for word in ['false', 'pants', 'lie']):
            return "False"
        elif any(word in rating_lower for word in ['true', 'true']):
            return "True"
        elif any(word in rating_lower for word in ['mostly', 'mostly']):
            return "Mostly False"
        elif any(word in rating_lower for word in ['half', 'half']):
            return "Half True"
        elif any(word in rating_lower for word in ['unproven', 'unverified']):
            return "Unproven"
        else:
            return rating.title()
    
    async def _politifact_fact_check(self, query: str) -> Optional[Dict[str, Any]]:
        """Scrape Politifact for fact-checking results."""
        try:
            client = await self._get_http_client()
            
            # Search Politifact
            search_url = f"{self.politifact_base_url}/search/?q={httpx.quote(query)}"
            response = await client.get(search_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find fact-check articles
            articles = soup.find_all('article', class_='m-teaser')
            
            if not articles:
                return None
            
            claims = []
            for article in articles[:5]:  # Limit to 5 results
                try:
                    # Extract article link
                    link_elem = article.find('a', href=True)
                    if not link_elem:
                        continue
                    
                    article_url = link_elem['href']
                    if not article_url.startswith('http'):
                        article_url = f"{self.politifact_base_url}{article_url}"
                    
                    # Extract rating
                    rating_elem = article.find('img', alt=True)
                    rating = "Unknown"
                    if rating_elem and rating_elem.get('alt'):
                        rating = rating_elem['alt'].replace('PolitiFact ruling ', '')
                    
                    # Extract title/text
                    title_elem = article.find('h3') or article.find('h2')
                    title = title_elem.get_text(strip=True) if title_elem else "No title"
                    
                    # Extract date
                    date_elem = article.find('time')
                    date = date_elem.get_text(strip=True) if date_elem else "Unknown date"
                    
                    claim_info = {
                        'text': title,
                        'rating': rating,
                        'url': article_url,
                        'date': date,
                        'reviewer': 'PolitiFact',
                        'source': 'politifact_scraping'
                    }
                    claims.append(claim_info)
                    
                except Exception as e:
                    print(f"Error parsing Politifact article: {e}")
                    continue
            
            return {
                "claims": claims,
                "source": "politifact_scraping",
                "total_results": len(claims)
            }
            
        except Exception as e:
            print(f"Politifact scraping error: {e}")
            return None
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of fact-checking services."""
        status = {
            "google_fact_check": {
                "available": bool(self.google_api_key),
                "api_key_configured": bool(self.google_api_key)
            },
            "politifact_fallback": {
                "available": True,
                "base_url": self.politifact_base_url
            },
            "cache_enabled": True,
            "timeout_seconds": settings.REQUEST_TIMEOUT_SECONDS
        }
        
        # Test Google API if available
        if self.google_api_key:
            try:
                client = await self._get_http_client()
                test_response = await client.get(
                    f"{self.google_base_url}/claims:search",
                    params={'key': self.google_api_key, 'query': 'test', 'pageSize': 1}
                )
                status["google_fact_check"]["working"] = test_response.status_code == 200
            except:
                status["google_fact_check"]["working"] = False
        
        return status

# Global fact-check service instance
fact_check_service = FactCheckService()
