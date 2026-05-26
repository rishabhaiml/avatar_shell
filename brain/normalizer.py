import re

class LinguisticNormalizer:
    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        
        # Stage 0: Cleanse Visual Markdown Emphasis (Fixes the "Asterisk" Bug)
        text = re.sub(r'[*_~`]+', '', text)
        
        # Stage 1: Explicit Email Addresses (e.g., support@bhejna.com)
        email_pattern = r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        def expand_email(match):
            user = match.group(1).replace('.', ' dot ')
            domain = match.group(2).replace('.', ' dot ')
            return f"{user} at {domain}"
        text = re.sub(email_pattern, expand_email, text)
        
        # Stage 2: Explicit URL Domains / Subdomains (e.g., api.bhejna.tech)
        url_pattern = r'(?<=[a-zA-Z0-9])\.(?=[a-zA-Z0-9])'
        def expand_period(match):
            start_idx = match.start()
            full_text = match.string
            if start_idx > 0 and start_idx < len(full_text) - 1:
                if full_text[start_idx-1].isdigit() and full_text[start_idx+1].isdigit():
                    return " point "
            return " dot "
        text = re.sub(url_pattern, expand_period, text)
        
        # Stage 3: Map isolated special symbols cleanly
        special_char_map = {
            " #": " hashtag ",
            " / ": " slash ",
            " _ ": " underscore ",
            " & ": " and ",
            " @ ": " at "
        }
        for char, phonetic in special_char_map.items():
            text = text.replace(char, phonetic)
            
        # Standardize multiple consecutive spaces to a single clean space
        text = re.sub(r'\s+', ' ', text).strip()
        return text

class StreamSentenceSplitter:
    def __init__(self):
        self.buffer = ""
        # Match sentence endings: . ? ! followed by a space, newline, or end-of-string
        self.sentence_end = re.compile(r'([^.!?]+[.!?]+)(?=\s|$)')

    def process_chunk(self, text_fragment: str):
        self.buffer += text_fragment
        normalized_buffer = LinguisticNormalizer.normalize_text(self.buffer)
        
        sentences = []
        last_idx = 0
        
        for match in self.sentence_end.finditer(normalized_buffer):
            sentences.append(match.group(1).strip())
            last_idx = match.end()
            
        if last_idx > 0:
            # Reconstruct remaining un-split content back to string memory cache
            self.buffer = normalized_buffer[last_idx:]
        else:
            self.buffer = normalized_buffer
            
        return sentences

    def flush(self):
        remainder = LinguisticNormalizer.normalize_text(self.buffer).strip()
        self.buffer = ""
        return [remainder] if remainder else []


class StreamClauseSplitter:
    def __init__(self):
        self.buffer = ""
        self.words = []

    def process_chunk(self, text_fragment: str) -> list[str]:
        self.buffer += text_fragment
        
        # Find the last whitespace to ensure we don't slice a word in half
        last_space_idx = max(self.buffer.rfind(" "), self.buffer.rfind("\n"), self.buffer.rfind("\t"))
        if last_space_idx == -1:
            return []
            
        process_text = self.buffer[:last_space_idx]
        self.buffer = self.buffer[last_space_idx:]
        
        clauses = []
        raw_words = process_text.split()
        for w in raw_words:
            if not w:
                continue
            self.words.append(w)
            
            # Strip trailing quotes, brackets, and markdown notation for punctuation checks
            clean_w = w.rstrip('"\')]}*_~`')
            
            is_breath_mark = any(clean_w.endswith(m) for m in [",", ":", ";", "—"])
            is_terminal_mark = any(clean_w.endswith(m) for m in [".", "?", "!"])
            
            should_slice = False
            if is_terminal_mark:
                should_slice = True
            elif is_breath_mark and len(self.words) >= 4:
                should_slice = True
            elif len(self.words) >= 7:
                should_slice = True  # Force-slice high ceiling
                
            if should_slice:
                completed = " ".join(self.words).strip()
                normalized = LinguisticNormalizer.normalize_text(completed)
                if normalized:
                    clauses.append(normalized)
                self.words = []
                
        return clauses

    def flush(self) -> list[str]:
        remainder_words = list(self.words)
        if self.buffer.strip():
            remainder_words.extend(self.buffer.split())
        self.buffer = ""
        self.words = []
        
        clauses = []
        if remainder_words:
            completed = " ".join(remainder_words).strip()
            normalized = LinguisticNormalizer.normalize_text(completed)
            if normalized:
                clauses.append(normalized)
        return clauses

