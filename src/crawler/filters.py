from abc import ABC, abstractmethod
from typing import List, Dict, Set
import re
from collections import Counter
import math

class BaseFilter(ABC):
    """Base class for content filters."""
    
    @abstractmethod
    def filter(self, content: str) -> str:
        """Filter the content and return processed result."""
        pass

class PruningContentFilter(BaseFilter):
    """Filter that removes redundant and irrelevant content."""
    
    def __init__(self):
        self.redundant_patterns = [
            r'<script.*?</script>',  # JavaScript
            r'<style.*?</style>',    # CSS
            r'<!--.*?-->',           # Comments
            r'<nav.*?</nav>',        # Navigation
            r'<footer.*?</footer>',  # Footer
            r'<header.*?</header>'   # Header
        ]
    
    def filter(self, content: str) -> str:
        """Remove redundant content using regex patterns."""
        filtered = content
        for pattern in self.redundant_patterns:
            filtered = re.sub(pattern, '', filtered, flags=re.DOTALL)
        return filtered.strip()

class BM25ContentFilter(BaseFilter):
    """Filter content using BM25 relevance scoring."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # term frequency saturation parameter
        self.b = b    # length normalization parameter
        self.avg_doc_length = 0
        self.doc_freqs = Counter()
        self.num_docs = 0
        
    def _tokenize(self, text: str) -> List[str]:
        """Convert text to tokens."""
        # Remove HTML tags and tokenize
        text = re.sub(r'<[^>]+>', '', text)
        return re.findall(r'\w+', text.lower())
    
    def _compute_idf(self, term: str) -> float:
        """Compute Inverse Document Frequency."""
        if term not in self.doc_freqs or self.num_docs == 0:
            return 0
        return math.log((self.num_docs - self.doc_freqs[term] + 0.5) / 
                       (self.doc_freqs[term] + 0.5) + 1)
    
    def train(self, documents: List[str]):
        """Train the filter on a corpus of documents."""
        self.doc_freqs.clear()
        total_length = 0
        doc_terms: Set[str] = set()
        
        for doc in documents:
            tokens = self._tokenize(doc)
            total_length += len(tokens)
            doc_terms.clear()
            
            # Count document frequency
            for token in tokens:
                doc_terms.add(token)
            for term in doc_terms:
                self.doc_freqs[term] += 1
        
        self.num_docs = len(documents)
        self.avg_doc_length = total_length / max(1, self.num_docs)
    
    def filter(self, content: str) -> str:
        """Filter content by keeping most relevant parts based on BM25 scores."""
        if self.num_docs == 0:
            return content
            
        # Split content into paragraphs
        paragraphs = re.split(r'\n\s*\n', content)
        if len(paragraphs) <= 1:
            return content
            
        # Score each paragraph
        scores = []
        for para in paragraphs:
            tokens = self._tokenize(para)
            if not tokens:
                scores.append(0)
                continue
                
            score = 0
            term_freqs = Counter(tokens)
            
            for term, freq in term_freqs.items():
                idf = self._compute_idf(term)
                term_score = (freq * (self.k1 + 1)) / (freq + self.k1 * (
                    1 - self.b + self.b * len(tokens) / self.avg_doc_length))
                score += idf * term_score
                
            scores.append(score)
        
        # Keep paragraphs with scores above mean
        mean_score = sum(scores) / len(scores)
        filtered_paras = [para for para, score in zip(paragraphs, scores) 
                         if score >= mean_score]
        
        return '\n\n'.join(filtered_paras)

class FilterPipeline:
    """Pipeline for applying multiple filters in sequence."""
    
    def __init__(self, filters: List[BaseFilter]):
        self.filters = filters
    
    def process(self, content: str) -> str:
        """Apply all filters in sequence."""
        result = content
        for filter_obj in self.filters:
            result = filter_obj.filter(result)
        return result
