from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass

@dataclass
class FormattedContent:
    """Container for formatted content."""
    content: str
    metadata: Dict[str, Any]
    format_type: str

class BaseFormatter(ABC):
    """Base class for content formatters."""
    
    @abstractmethod
    def format(self, content: str, metadata: Dict[str, Any] = None) -> FormattedContent:
        """Format the content and return the result."""
        pass

class MarkdownFormatter(BaseFormatter):
    """Convert HTML content to Markdown format."""
    
    def __init__(self):
        self.heading_pattern = re.compile(r'h[1-6]')
        self.list_tags = {'ul', 'ol'}
        self.code_tags = {'pre', 'code'}
    
    def _convert_heading(self, tag) -> str:
        """Convert HTML heading to Markdown heading."""
        level = int(tag.name[1])
        return f"{'#' * level} {tag.get_text().strip()}\n\n"
    
    def _convert_paragraph(self, tag) -> str:
        """Convert HTML paragraph to Markdown paragraph."""
        return f"{tag.get_text().strip()}\n\n"
    
    def _convert_list(self, tag, indent: int = 0) -> str:
        """Convert HTML list to Markdown list."""
        result = []
        for item in tag.find_all('li', recursive=False):
            prefix = '  ' * indent + ('* ' if tag.name == 'ul' else '1. ')
            content = item.get_text().strip()
            result.append(f"{prefix}{content}")
            
            # Handle nested lists
            nested_lists = item.find_all(['ul', 'ol'], recursive=False)
            for nested in nested_lists:
                result.append(self._convert_list(nested, indent + 1))
        
        return '\n'.join(result) + '\n\n'
    
    def _convert_code(self, tag) -> str:
        """Convert HTML code block to Markdown code block."""
        language = tag.get('class', [''])[0] or ''
        if 'language-' in language:
            language = language.split('language-')[1]
        return f"```{language}\n{tag.get_text().strip()}\n```\n\n"
    
    def _convert_table(self, tag) -> str:
        """Convert HTML table to Markdown table."""
        result = []
        
        # Extract headers
        headers = []
        for th in tag.find_all('th'):
            headers.append(th.get_text().strip())
        
        if not headers:
            # If no headers found, use first row as header
            first_row = tag.find('tr')
            if first_row:
                headers = [td.get_text().strip() for td in first_row.find_all('td')]
        
        if not headers:
            return ''
        
        # Create header row
        result.append('| ' + ' | '.join(headers) + ' |')
        result.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        
        for row in tag.find_all('tr')[1:] if tag.find('th') else tag.find_all('tr')[1:]:
            cells = [td.get_text().strip() for td in row.find_all('td')]
            if cells:
                result.append('| ' + ' | '.join(cells) + ' |')
        
        return '\n'.join(result) + '\n\n'
    
    def format(self, content: str, metadata: Dict[str, Any] = None) -> FormattedContent:
        """Convert HTML content to Markdown format."""
        soup = BeautifulSoup(content, 'html.parser')
        result = []
        
        for tag in soup.find_all(True):
            if self.heading_pattern.match(tag.name):
                result.append(self._convert_heading(tag))
            elif tag.name == 'p':
                result.append(self._convert_paragraph(tag))
            elif tag.name in self.list_tags:
                result.append(self._convert_list(tag))
            elif tag.name in self.code_tags:
                result.append(self._convert_code(tag))
            elif tag.name == 'table':
                result.append(self._convert_table(tag))
        
        return FormattedContent(
            content=''.join(result).strip(),
            metadata=metadata or {},
            format_type='markdown'
        )

class JsonFormatter(BaseFormatter):
    """Convert HTML content to structured JSON format."""
    
    def _extract_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured data from HTML content."""
        result = {
            'title': '',
            'headings': [],
            'sections': [],
            'code_blocks': [],
            'tables': []
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            result['title'] = title_tag.get_text().strip()
        
        # Extract headings and create sections
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_data = {
                'level': int(heading.name[1]),
                'text': heading.get_text().strip()
            }
            result['headings'].append(heading_data)
            
            # Create section (heading + following content until next heading)
            section_content = []
            for sibling in heading.find_next_siblings():
                if sibling.name and sibling.name.startswith('h'):
                    break
                if sibling.name == 'p':
                    section_content.append(sibling.get_text().strip())
            
            if section_content:
                result['sections'].append({
                    'heading': heading_data,
                    'content': '\n'.join(section_content)
                })
        
        # Extract code blocks
        for code in soup.find_all(['pre', 'code']):
            language = code.get('class', [''])[0] or ''
            if 'language-' in language:
                language = language.split('language-')[1]
            result['code_blocks'].append({
                'language': language,
                'code': code.get_text().strip()
            })
        
        # Extract tables
        for table in soup.find_all('table'):
            table_data = {
                'headers': [],
                'rows': []
            }
            
            # Extract headers
            headers = table.find_all('th')
            if headers:
                table_data['headers'] = [th.get_text().strip() for th in headers]
            
            # Extract rows
            for row in table.find_all('tr')[1:] if headers else table.find_all('tr'):
                cells = [td.get_text().strip() for td in row.find_all('td')]
                if cells:
                    table_data['rows'].append(cells)
            
            result['tables'].append(table_data)
        
        return result
    
    def format(self, content: str, metadata: Dict[str, Any] = None) -> FormattedContent:
        """Convert HTML content to JSON format."""
        soup = BeautifulSoup(content, 'html.parser')
        structure = self._extract_structure(soup)
        
        if metadata:
            structure['metadata'] = metadata
        
        return FormattedContent(
            content=json.dumps(structure, ensure_ascii=False, indent=2),
            metadata=metadata or {},
            format_type='json'
        )
