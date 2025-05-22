import re
from typing import Dict, Set, Optional
from fuzzywuzzy import fuzz, process

class ContentMatcher:
    def __init__(self):
        self.min_word_length = 4  # Define this FIRST
        self.min_match_threshold = 2
        self.fuzzy_threshold = 75
        self.chapter_map = self._build_chapter_map()
        
    def _build_chapter_map(self) -> Dict[str, str]:
        """Create a mapping of all chapter keywords to subjects"""
        chapter_map = {}
        for subject, chapters in CHAPTER_DATA.items():
            for chapter in chapters:
                words = self._extract_keywords(chapter)
                for word in words:
                    chapter_map[word] = subject
        return chapter_map
        
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text"""
        words = set(re.findall(r'\w{'+str(self.min_word_length)+r',}', text.lower()))
        return words
        
    def find_subject(self, text: str) -> Optional[str]:
        """Find the best matching subject using multiple matching strategies"""
        if not text:
            return None
            
        text_lower = text.lower()
        text_words = self._extract_keywords(text_lower)
        
        # Strategy 1: Exact multi-word matching
        for subject, chapters in CHAPTER_DATA.items():
            for chapter in chapters:
                if len(chapter.split()) > 1 and chapter.lower() in text_lower:
                    return subject
        
        # Strategy 2: Multiple keyword matching
        subject_scores = {}
        for word in text_words:
            if word in self.chapter_map:
                subject = self.chapter_map[word]
                subject_scores[subject] = subject_scores.get(subject, 0) + 1
                
        if subject_scores:
            best_subject = max(subject_scores.items(), key=lambda x: x[1])[0]
            if subject_scores[best_subject] >= self.min_match_threshold:
                return best_subject
                
        # Strategy 3: Fuzzy matching as fallback
        all_chapters = []
        for subject, chapters in CHAPTER_DATA.items():
            all_chapters.extend((chap, subject) for chap in chapters)
            
        best_match = process.extractOne(
            text_lower, 
            [chap[0] for chap in all_chapters], 
            scorer=fuzz.token_set_ratio
        )
        
        if best_match and best_match[1] >= self.fuzzy_threshold:
            for chap, subject in all_chapters:
                if chap == best_match[0]:
                    return subject
                    
        return None

# Initialize the matcher
matcher = ContentMatcher()
