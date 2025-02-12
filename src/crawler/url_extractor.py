from typing import Set, List
import re
from urllib.parse import urljoin, urlparse

class UrlExtractor:
    """Extract and filter URLs from HTML content."""
    
    def __init__(self, base_url: str, allowed_domains: List[str] = None):
        """Initialize URL extractor.
        
        Args:
            base_url: Base URL for resolving relative URLs
            allowed_domains: List of allowed domains. If None, only URLs from the same domain as base_url are allowed.
        """
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        
        if allowed_domains:
            self.allowed_domains = set(allowed_domains)
        else:
            self.allowed_domains = {self.base_domain}
        
        # Common patterns for API documentation links
        self.api_patterns = [
            r'api|docs?|reference|manual|guide|tutorial|sdk',  # Common terms
            r'v\d+|version',  # Version indicators
            r'function|method|class|module|namespace',  # Code structure
            r'get|post|put|delete|patch',  # HTTP methods
            r'endpoint|route|path',  # API endpoints
        ]
        
        self.api_pattern = re.compile('|'.join(self.api_patterns), re.IGNORECASE)
        
        # Patterns to exclude
        self.exclude_patterns = [
            r'logout|signout|sign-out',  # Authentication
            r'download|asset|image|img|css|js|font',  # Assets
            r'print|pdf|epub|zip',  # Downloads
            r'blog|news|article',  # Non-documentation
            r'profile|account|settings',  # User pages
        ]
        
        self.exclude_pattern = re.compile('|'.join(self.exclude_patterns), re.IGNORECASE)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and allowed."""
        try:
            parsed = urlparse(url)
            
            # Must be http(s)
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Check domain
            if parsed.netloc not in self.allowed_domains:
                return False
            
            # Check exclusion patterns
            if self.exclude_pattern.search(parsed.path):
                return False
            
            # Prefer API/documentation URLs
            if not self.api_pattern.search(parsed.path):
                return False
            
            return True
            
        except Exception:
            return False
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by resolving relative URLs and removing fragments."""
        # Resolve relative URLs
        normalized = urljoin(self.base_url, url)
        
        # Remove fragments
        parsed = urlparse(normalized)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    def extract_urls(self, html_content: str) -> Set[str]:
        """Extract valid URLs from HTML content."""
        # Simple regex for href extraction
        urls = set()
        for match in re.finditer(r'href=[\'"]?([^\'" >]+)', html_content):
            url = match.group(1)
            
            # Normalize URL
            normalized_url = self.normalize_url(url)
            
            # Add if valid
            if self.is_valid_url(normalized_url):
                urls.add(normalized_url)
        
        return urls
