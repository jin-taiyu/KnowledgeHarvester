from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict
import asyncio
import logging
from collections import deque
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .url_extractor import UrlExtractor

@dataclass
class CrawlerConfig:
    """Configuration for the crawler."""
    enable_javascript: bool = False
    wait_time: int = 5  # seconds to wait for dynamic content
    headers: dict = None
    proxy: str = None
    max_depth: int = 3  # maximum recursion depth
    max_pages: int = 100  # maximum number of pages to crawl
    allowed_domains: List[str] = field(default_factory=list)  # allowed domains for recursion
    enable_recursion: bool = False  # whether to enable recursive crawling

@dataclass
class CrawlResult:
    """Result of a crawl operation."""
    url: str
    content: str
    metadata: dict
    child_urls: Set[str] = field(default_factory=set)  # URLs found in this page
    status: str = "success"
    error: Optional[str] = None
    crawl_time: str = field(default_factory=lambda: datetime.now().isoformat())

class BaseCrawler:
    """Base crawler class with support for both static and dynamic pages."""
    
    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.logger = logging.getLogger(__name__)
        self._driver = None
        self._crawled_urls: Set[str] = set()
        self._url_queue: deque = deque()
        self._current_depth: Dict[str, int] = {}
    
    async def crawl(self, url: str):
        """Crawl the specified URL and its linked pages if recursion is enabled.
        
        This is an async generator that yields CrawlResult objects as they are crawled.
        """
        if not self.config.enable_recursion:
            # Single page crawl
            result = await self._crawl_single_url(url)
            if result:
                yield result
            return
        
        # Initialize recursive crawl
        self._crawled_urls.clear()
        self._url_queue.clear()
        self._current_depth.clear()
        
        self.url_extractor = UrlExtractor(url, self.config.allowed_domains)
        
        self._url_queue.append(url)
        self._current_depth[url] = 0
        
        while self._url_queue and len(self._crawled_urls) < self.config.max_pages:
            current_url = self._url_queue.popleft()
            current_depth = self._current_depth[current_url]
            
            if current_url in self._crawled_urls or current_depth >= self.config.max_depth:
                continue
            
            result = await self._crawl_single_url(current_url)
            if not result:
                continue
            
            self._crawled_urls.add(current_url)
            yield result
            
            # Extract and queue child URLs
            if current_depth < self.config.max_depth:
                child_urls = self.url_extractor.extract_urls(result.content)
                result.child_urls = child_urls
                
                for child_url in child_urls:
                    if child_url not in self._crawled_urls and child_url not in self._current_depth:
                        self._url_queue.append(child_url)
                        self._current_depth[child_url] = current_depth + 1
    
    async def _crawl_single_url(self, url: str) -> Optional[CrawlResult]:
        """Crawl a single URL."""
        try:
            if self.config.enable_javascript:
                return await self._crawl_with_javascript(url)
            return await self._crawl_static(url)
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {str(e)}")
            return CrawlResult(
                url=url,
                content="",
                metadata={},
                status="error",
                error=str(e)
            )
    
    async def _crawl_static(self, url: str) -> CrawlResult:
        """Crawl static content using requests."""
        headers = self.config.headers or {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, proxies={'http': self.config.proxy, 'https': self.config.proxy} if self.config.proxy else None)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return CrawlResult(
            url=url,
            content=str(soup),
            metadata={
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'encoding': response.encoding
            }
        )
    
    async def _crawl_with_javascript(self, url: str) -> CrawlResult:
        """Crawl dynamic content using Selenium."""
        if not self._driver:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            if self.config.proxy:
                chrome_options.add_argument(f'--proxy-server={self.config.proxy}')
            self._driver = webdriver.Chrome(options=chrome_options)
        
        try:
            self._driver.get(url)
            WebDriverWait(self._driver, self.config.wait_time).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            
            return CrawlResult(
                url=url,
                content=self._driver.page_source,
                metadata={
                    'title': self._driver.title,
                    'current_url': self._driver.current_url
                }
            )
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None

    def __del__(self):
        """Cleanup resources."""
        if self._driver:
            self._driver.quit()
