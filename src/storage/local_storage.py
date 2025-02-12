"""Local file system storage implementation."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import os
import re

from ..crawler.formatters import FormattedContent

@dataclass
class StorageConfig:
    """Configuration for storage operations."""
    base_path: Path
    create_domain_dirs: bool = True
    create_date_dirs: bool = True
    file_prefix: str = ""
    file_suffix: str = ""

class LocalStorage:
    """Handles storage of crawled content to local file system."""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self._ensure_base_path()
    
    def _ensure_base_path(self):
        """Create base storage directory if it doesn't exist."""
        self.config.base_path.mkdir(parents=True, exist_ok=True)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        domain_match = re.match(r'https?://([^/]+)', url)
        if domain_match:
            return domain_match.group(1).replace(':', '_').replace('.', '_')
        return 'unknown_domain'
    
    def _create_storage_path(self, url: str) -> Path:
        """Create and return the full storage path for the content."""
        parts = []
        
        if self.config.create_domain_dirs:
            parts.append(self._extract_domain(url))
            
        if self.config.create_date_dirs:
            date_str = datetime.now().strftime('%Y-%m-%d')
            parts.append(date_str)
        
        # Create the directory path
        dir_path = self.config.base_path.joinpath(*parts)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return dir_path
    
    def _generate_filename(self, url: str, format_type: str) -> str:
        """Generate a filename for the content."""
        # Create base filename from URL
        base_name = re.sub(r'[^\w\-_.]', '_', url.split('/')[-1] or 'index')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Combine parts with prefix and suffix
        filename_parts = []
        if self.config.file_prefix:
            filename_parts.append(self.config.file_prefix)
        filename_parts.append(base_name)
        filename_parts.append(timestamp)
        if self.config.file_suffix:
            filename_parts.append(self.config.file_suffix)
        
        # Add appropriate extension
        extension = '.md' if format_type == 'markdown' else '.json'
        
        return '_'.join(filename_parts) + extension
    
    def save(self, content: FormattedContent, url: str) -> Optional[Path]:
        """Save formatted content to local storage."""
        try:
            storage_path = self._create_storage_path(url)
            filename = self._generate_filename(url, content.format_type)
            file_path = storage_path / filename
            
            # Save content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content.content)
            
            # Save metadata separately
            if content.metadata:
                metadata_path = file_path.with_suffix('.meta.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(content.metadata, f, ensure_ascii=False, indent=2)
            
            return file_path
            
        except Exception as e:
            print(f"Error saving content: {str(e)}")
            return None
    
    def load(self, file_path: Path) -> Optional[FormattedContent]:
        """Load saved content from local storage."""
        try:
            if not file_path.exists():
                return None
            
            # Read content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to load metadata if it exists
            metadata = {}
            metadata_path = file_path.with_suffix('.meta.json')
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # Determine format type from extension
            format_type = 'markdown' if file_path.suffix == '.md' else 'json'
            
            return FormattedContent(
                content=content,
                metadata=metadata,
                format_type=format_type
            )
            
        except Exception as e:
            print(f"Error loading content: {str(e)}")
            return None
    
    def list_files(self, domain: str = None, date: str = None) -> list[Path]:
        """List saved files, optionally filtered by domain and/or date."""
        files = []
        base_path = self.config.base_path
        
        if domain and self.config.create_domain_dirs:
            base_path = base_path / domain
        
        if date and self.config.create_date_dirs:
            base_path = base_path / date
        
        if base_path.exists():
            for ext in ['.md', '.json']:
                files.extend(base_path.rglob(f'*{ext}'))
        
        return sorted(files)
