import sqlite3
import re
import os
from datetime import datetime
import config

class BHAIMemoryEngine:
    def __init__(self, db_path: str = "weights/bhai_brain.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initializes tables and configures SQLite for automatic space reclamation."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # EDGE CASE 1 FIX: Turn on incremental autovacuuming BEFORE building tables
        # This forces the filesystem to reclaim free pages immediately upon deletion passes
        cursor.execute("PRAGMA auto_vacuum = INCREMENTAL;")
        cursor.execute("PRAGMA journal_mode = WAL;") # Write-Ahead Logging for non-blocking operations
        
        # 1. Chronological Time-Series Table (Short/Medium Conversation context)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                speaker TEXT,
                text_content TEXT
            )
        """)
        
        # 2. Directed Semantic Entity Graph Table (Long-term personalized facts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_graph (
                entity_key TEXT,
                associated_fact TEXT,
                access_count INTEGER DEFAULT 1,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entity_key, associated_fact)
            )
        """)
        conn.commit()
        conn.close()

    def log_turn(self, speaker: str, text: str):
        """Chronicles a conversational turn into the time-series log."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_history (speaker, text_content) VALUES (?, ?)",
            (speaker, text)
        )
        conn.commit()
        conn.close()

    def extract_and_store_entities(self, user_text: str):
        """
        Passive background relation extraction. Scans the text for key structural definitions
        like project details, variables, or environment specs and binds them to nodes.
        """
        # Look for assignment patterns like "X is Y" or "backend for X is Y"
        match = re.search(r'(?:backend for|subdomain for|project|app)?\s*([a-zA-Z0-9_-]+)\s+(?:is|runs on|set to)\s+([a-zA-Z0-9_./:-]+)', user_text, re.IGNORECASE)
        if match:
            entity = match.group(1).strip().upper()
            fact = f"{match.group(1).strip()} is associated with {match.group(2).strip()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memory_graph (entity_key, associated_fact, last_accessed)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(entity_key, associated_fact) DO UPDATE SET
                    access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
            """, (entity, fact))
            conn.commit()
            conn.close()

    def retrieve_context(self, user_input: str) -> str:
        """
        Vectorless Hybrid Context Fetch. Matches tokens against the text-graph indices 
        and extracts chronological logs under 0.5ms.
        """
        # Tokenize words, filtering out common short words/stopwords
        words = [w.strip("?,.!:\"'").upper() for w in user_input.split() if len(w) > 3]
        if not words:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT speaker, text_content FROM conversation_history 
                ORDER BY id DESC LIMIT 3
            """)
            history = [f"{row[0].upper()}: {row[1]}" for row in reversed(cursor.fetchall())]
            conn.close()
            
            context_payload = ""
            if history:
                context_payload += "\n[RECENT CONVERSATION]:\n" + "\n".join(history)
            return context_payload
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Traversal: Fetch long-term graph connections matching the active keywords
        placeholders = ",".join(["?"] * len(words))
        cursor.execute(f"""
            SELECT associated_fact FROM memory_graph 
            WHERE UPPER(entity_key) IN ({placeholders})
            ORDER BY access_count DESC, last_accessed DESC LIMIT 3
        """, words)
        facts = [row[0] for row in cursor.fetchall()]
        
        # 2. Recency: Pull the immediate last 3 turns from the history log
        cursor.execute("""
            SELECT speaker, text_content FROM conversation_history 
            ORDER BY id DESC LIMIT 3
        """)
        history = [f"{row[0].upper()}: {row[1]}" for row in reversed(cursor.fetchall())]
        conn.close()
        
        # Stitches information cleanly into localized payload contexts
        context_payload = ""
        if facts:
            context_payload += "\n[PERSONAL PROFILE CONTEXT]:\n" + "\n".join(f"- {f}" for f in facts)
        if history:
            context_payload += "\n[RECENT CONVERSATION]:\n" + "\n".join(history)
            
        return context_payload

    # =========================================================================
    #                    DATA EVICTION & CLEANUP ENGINE
    # =========================================================================

    def clear_stale_context(self, maximum_days: int = 14):
        """
        EDGE CASE 2 FIX: Enforces a strict time-to-live (TTL) on conversational turns.
        Keeps logs from expanding indefinitely while retaining your baseline graph facts.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Delete conversational entries older than the target timeframe
            cursor.execute(
                "DELETE FROM conversation_history WHERE timestamp < datetime('now', ?)",
                (f"-{maximum_days} days",)
            )
            
            # Prune forgotten graph relations that haven't been accessed or referenced in 60 days
            cursor.execute(
                "DELETE FROM memory_graph WHERE last_accessed < datetime('now', '-60 days')"
            )
            
            conn.commit()
            
            # Incremental Page Reclamation Pass
            cursor.execute("PRAGMA incremental_vacuum(50);") # Reclaim up to 50 empty pages at a time safely
        except Exception as e:
            print(f"❌ Storage compaction routine encountered an issue: {e}")
        finally:
            conn.close()

    def delete_explicit_entity(self, key_token: str):
        """
        Explicit memory pruning handler. If you pivot away from a project, you can pass 
        its node label (e.g. 'BHEJNA') to drop all related associations cleanly.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        target = key_token.strip().upper()
        
        cursor.execute("DELETE FROM memory_graph WHERE entity_key = ?", (target,))
        cursor.execute("DELETE FROM conversation_history WHERE UPPER(text_content) LIKE ?", (f"%{target}%",))
        
        conn.commit()
        cursor.execute("PRAGMA incremental_vacuum(20);")
        conn.close()
        print(f"🧹 Memory sanitized. All references to node [{target}] have been purged.")
