# callback.py
import requests
import logging
from typing import Dict, List
from config import config

logger = logging.getLogger(__name__)

class CallbackManager:
    """
    Handles Rule 12: Mandatory Final Result Callback
    This is THE MOST CRITICAL component for evaluation
    """
    
    @staticmethod
    def should_trigger_callback(
        session_data: Dict,
        intelligence: Dict,
        message_count: int
    ) -> bool:
        """
        Determine if callback should be triggered NOW
        
        Trigger Logic (ANY condition met):
        1. Critical intelligence found (UPI/bank/phishing)
        2. Message count >= MAX_MESSAGES (prevent infinite loops)
        3. High scam score + sufficient engagement (score >= 50 and count >= MIN_MESSAGES)
        4. Multiple intelligence types extracted
        
        Returns:
            bool: True if callback should be sent
        """
        
        # Don't retrigger if already sent
        if session_data.get("callback_sent", False):
            return False
        
        # Must have scam detected
        if not session_data.get("scam_detected", False):
            return False
        
        # Condition 1: Critical intelligence (highest priority)
        has_critical_intel = any([
            intelligence.get("bankAccounts"),
            intelligence.get("upiIds"),
            intelligence.get("phishingLinks")
        ])
        
        # Condition 2: Max messages reached (safety valve)
        max_messages_reached = message_count >= config.MAX_MESSAGES_BEFORE_CALLBACK
        
        # Condition 3: High confidence + sufficient engagement
        high_confidence = (
            session_data.get("scam_score", 0) >= 50 and
            message_count >= config.MIN_MESSAGES_BEFORE_CALLBACK
        )
        
        # Condition 4: Multiple intelligence types (quality extraction)
        intel_types_found = sum([
            bool(intelligence.get("bankAccounts")),
            bool(intelligence.get("upiIds")),
            bool(intelligence.get("phishingLinks")),
            bool(intelligence.get("phoneNumbers")),
            len(intelligence.get("suspiciousKeywords", [])) >= 3
        ])
        comprehensive_intel = intel_types_found >= 3 and message_count >= config.MIN_MESSAGES_BEFORE_CALLBACK
        
        # Decision logic
        should_trigger = any([
            has_critical_intel,
            max_messages_reached,
            high_confidence,
            comprehensive_intel
        ])
        
        if should_trigger:
            logger.info(f"🎯 Callback trigger conditions met for session {session_data.get('session_id')}")
            logger.info(f"   - Critical intel: {has_critical_intel}")
            logger.info(f"   - Max messages: {max_messages_reached}")
            logger.info(f"   - High confidence: {high_confidence}")
            logger.info(f"   - Comprehensive: {comprehensive_intel}")
        
        return should_trigger
    
    @staticmethod
    def send_final_result(
        session_id: str,
        scam_detected: bool,
        total_messages: int,
        extracted_intelligence: Dict[str, List[str]],
        agent_notes: str
    ) -> bool:
        """
        Send mandatory callback to GUVI evaluation endpoint
        
        EXACTLY matches Rule 12 payload format
        
        Returns:
            bool: True if callback succeeded
        """
        
        # Construct payload EXACTLY per Rule 12
        payload = {
            "sessionId": session_id,
            "scamDetected": scam_detected,
            "totalMessagesExchanged": total_messages,
            "extractedIntelligence": {
                "bankAccounts": extracted_intelligence.get("bankAccounts", []),
                "upiIds": extracted_intelligence.get("upiIds", []),
                "phishingLinks": extracted_intelligence.get("phishingLinks", []),
                "phoneNumbers": extracted_intelligence.get("phoneNumbers", []),
                "suspiciousKeywords": extracted_intelligence.get("suspiciousKeywords", [])
            },
            "agentNotes": agent_notes
        }
        
        try:
            logger.info(f"🚀 SENDING FINAL CALLBACK for session {session_id}")
            logger.info(f"   URL: {config.CALLBACK_URL}")
            logger.debug(f"   Payload: {payload}")
            
            response = requests.post(
                config.CALLBACK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=config.CALLBACK_TIMEOUT
            )
            
            if response.status_code == 200:
                logger.info(f"✅ CALLBACK SUCCESSFUL for session {session_id}")
                logger.info(f"   Response: {response.text}")
                return True
            else:
                logger.error(f"❌ Callback failed: HTTP {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except requests.Timeout:
            logger.error(f"⏱️ Callback timeout after {config.CALLBACK_TIMEOUT}s for session {session_id}")
            return False
        except requests.RequestException as e:
            logger.error(f"💥 Network error during callback: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"💥 Unexpected callback error: {str(e)}")
            return False
    
    @staticmethod
    def generate_agent_notes(
        conversation_history: List[Dict],
        intelligence: Dict,
        scam_score: int
    ) -> str:
        """
        Generate human-readable summary of scammer behavior
        
        Analyzes tactics used and intelligence gathered
        """
        tactics = []
        
        # Analyze keywords for tactics
        keywords = intelligence.get("suspiciousKeywords", [])
        
        if any(k in keywords for k in ["urgent", "immediately", "now", "expire"]):
            tactics.append("urgency tactics")
        
        if any(k in keywords for k in ["verify", "confirm", "update", "kyc"]):
            tactics.append("verification pressure")
        
        if any(k in keywords for k in ["account blocked", "suspended", "locked"]):
            tactics.append("account threat")
        
        if intelligence.get("phishingLinks"):
            tactics.append("phishing link redirection")
        
        if intelligence.get("upiIds") or intelligence.get("bankAccounts"):
            tactics.append("payment information extraction")
        
        if any(k in keywords for k in ["prize", "lottery", "refund", "won"]):
            tactics.append("fake reward lure")
        
        if intelligence.get("phoneNumbers"):
            tactics.append("contact information harvesting")
        
        # Construct notes
        if tactics:
            tactics_str = ", ".join(tactics)
            notes = f"Scammer used {tactics_str}. "
        else:
            notes = "Scammer attempted generic social engineering. "
        
        # Add intelligence summary
        intel_summary = []
        if intelligence.get("upiIds"):
            intel_summary.append(f"{len(intelligence['upiIds'])} UPI IDs")
        if intelligence.get("bankAccounts"):
            intel_summary.append(f"{len(intelligence['bankAccounts'])} bank accounts")
        if intelligence.get("phishingLinks"):
            intel_summary.append(f"{len(intelligence['phishingLinks'])} phishing links")
        
        if intel_summary:
            notes += f"Extracted: {', '.join(intel_summary)}. "
        
        notes += f"Confidence score: {scam_score}/100"
        
        return notes

# Initialize singleton
callback_manager = CallbackManager()