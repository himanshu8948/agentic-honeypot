# db.py
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """
    In-memory session storage for conversation tracking
    Handles Rule 6.2: Multi-turn conversation history
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def get_or_create(self, session_id: str) -> Dict:
        """
        Get existing session or create new one
        
        Returns session with structure:
        {
            "session_id": str,
            "created_at": datetime,
            "message_count": int,
            "scam_detected": bool,
            "callback_sent": bool,
            "intelligence": {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": []
            },
            "scam_score": int
        }
        """
        if session_id not in self.sessions:
            logger.info(f"📝 Creating new session: {session_id}")
            self.sessions[session_id] = {
                "session_id": session_id,
                "created_at": datetime.now(),
                "message_count": 0,
                "scam_detected": False,
                "callback_sent": False,
                "intelligence": {
                    "bankAccounts": [],
                    "upiIds": [],
                    "phishingLinks": [],
                    "phoneNumbers": [],
                    "suspiciousKeywords": []
                },
                "scam_score": 0
            }
        return self.sessions[session_id]
    
    def update_intelligence(self, session_id: str, new_intelligence: Dict):
        """Merge new intelligence into existing session"""
        session = self.get_or_create(session_id)
        
        for key in ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers", "suspiciousKeywords"]:
            if key in new_intelligence:
                # Add new items, avoiding duplicates
                existing = set(session["intelligence"][key])
                new_items = set(new_intelligence[key])
                session["intelligence"][key] = list(existing | new_items)
        
        logger.debug(f"Updated intelligence for {session_id}: {session['intelligence']}")
    
    def increment_message_count(self, session_id: str):
        """Increment message counter"""
        session = self.get_or_create(session_id)
        session["message_count"] += 1
    
    def mark_scam_detected(self, session_id: str, score: int):
        """Mark session as confirmed scam"""
        session = self.get_or_create(session_id)
        session["scam_detected"] = True
        session["scam_score"] = max(session["scam_score"], score)
        logger.warning(f"🚨 Scam detected in session {session_id} (score: {score})")
    
    def mark_callback_sent(self, session_id: str):
        """Mark callback as successfully sent"""
        session = self.get_or_create(session_id)
        session["callback_sent"] = True
        logger.info(f"✅ Callback marked as sent for {session_id}")
    
    def get_session(self, session_id: str) -> Dict:
        """Safely get session (returns empty dict if not found)"""
        return self.sessions.get(session_id, {})

# ============================================================================
# CRITICAL: Export singleton instance (not the class)
# This allows main.py to import: from db import session_manager
# ============================================================================
session_manager = SessionManager()