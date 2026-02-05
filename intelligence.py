# intelligence.py
import re
import logging
from typing import Dict, List, Tuple
import phonenumbers

logger = logging.getLogger(__name__)

class IntelligenceExtractor:
    """
    Handles Rules 2 & 3: Extract scam intelligence
    Uses regex patterns and NLP to identify:
    - Bank accounts
    - UPI IDs
    - Phishing links
    - Phone numbers
    - Suspicious keywords
    """
    
    # Regex patterns for Indian financial data
    PATTERNS = {
        "upi": r'\b[\w\.-]+@[\w\.-]+\b',  # username@bank
        "bank_account": r'\b\d{9,18}\b',  # 9-18 digit account numbers
        "ifsc": r'\b[A-Z]{4}0[A-Z0-9]{6}\b',  # IFSC codes
        "phone": r'\+?91[-\s]?\d{10}|\b\d{10}\b',  # Indian phone numbers
        "url": r'https?://[^\s]+|www\.[^\s]+|\b[a-z0-9]+\.(com|in|net|org|xyz|click|tk)[^\s]*'
    }
    
    # Scam keywords (weighted by severity)
    SCAM_KEYWORDS = {
        "critical": [
            "account blocked", "suspended", "verify immediately", "update kyc",
            "refund pending", "prize won", "lottery", "tax refund",
            "otp", "cvv", "pin", "password", "atm card blocked"
        ],
        "high": [
            "urgent", "verify", "confirm", "update", "click here",
            "expire", "limited time", "act now", "immediate action"
        ],
        "medium": [
            "bank", "payment", "transfer", "account", "upi",
            "paytm", "phonepe", "gpay", "link", "secure"
        ]
    }
    
    @staticmethod
    def extract(message_text: str, conversation_history: List[Dict]) -> Dict[str, List[str]]:
        """
        Extract intelligence from message and conversation history
        
        Returns:
            Dict with keys: bankAccounts, upiIds, phishingLinks, phoneNumbers, suspiciousKeywords
        """
        intelligence = {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "suspiciousKeywords": []
        }
        
        # Combine current message with history for context
        all_text = message_text.lower()
        for msg in conversation_history:
            if msg.get("sender") == "scammer":
                all_text += " " + msg.get("text", "").lower()
        
        # Extract UPI IDs
        upi_matches = re.findall(IntelligenceExtractor.PATTERNS["upi"], all_text)
        for upi in upi_matches:
            # Filter out emails and keep only UPI-like patterns
            if any(bank in upi.lower() for bank in ["@paytm", "@ybl", "@oksbi", "@axl", "@icici", "@hdfcbank", "@upi"]):
                intelligence["upiIds"].append(upi)
        
        # Extract bank accounts
        account_matches = re.findall(IntelligenceExtractor.PATTERNS["bank_account"], all_text)
        intelligence["bankAccounts"].extend(account_matches)
        
        # Extract phone numbers
        phone_matches = re.findall(IntelligenceExtractor.PATTERNS["phone"], all_text)
        for phone in phone_matches:
            try:
                parsed = phonenumbers.parse(phone, "IN")
                if phonenumbers.is_valid_number(parsed):
                    intelligence["phoneNumbers"].append(phonenumbers.format_number(
                        parsed, phonenumbers.PhoneNumberFormat.E164
                    ))
            except:
                # If parsing fails, keep raw format
                intelligence["phoneNumbers"].append(phone)
        
        # Extract URLs (potential phishing links)
        url_matches = re.findall(IntelligenceExtractor.PATTERNS["url"], all_text)
        for url in url_matches:
            # Filter out legitimate domains
            if not any(safe in url.lower() for safe in ["google.com", "gov.in", "wikipedia.org"]):
                intelligence["phishingLinks"].append(url)
        
        # Extract suspicious keywords
        for severity, keywords in IntelligenceExtractor.SCAM_KEYWORDS.items():
            for keyword in keywords:
                if keyword in all_text:
                    intelligence["suspiciousKeywords"].append(keyword)
        
        # Remove duplicates
        for key in intelligence:
            intelligence[key] = list(set(intelligence[key]))
        
        logger.debug(f"Extracted intelligence: {intelligence}")
        return intelligence
    
    @staticmethod
    def calculate_scam_score(intelligence: Dict[str, List[str]]) -> int:
        """
        Calculate scam confidence score (0-100)
        
        Scoring:
        - UPI ID: +30 points
        - Bank account: +25 points
        - Phishing link: +20 points
        - Phone number: +10 points
        - Critical keyword: +5 points each
        - High keyword: +3 points each
        - Medium keyword: +1 point each
        """
        score = 0
        
        # Critical intelligence (high weight)
        score += len(intelligence.get("upiIds", [])) * 30
        score += len(intelligence.get("bankAccounts", [])) * 25
        score += len(intelligence.get("phishingLinks", [])) * 20
        score += len(intelligence.get("phoneNumbers", [])) * 10
        
        # Keyword-based scoring
        keywords = intelligence.get("suspiciousKeywords", [])
        for keyword in keywords:
            if any(k in keyword for k in IntelligenceExtractor.SCAM_KEYWORDS["critical"]):
                score += 5
            elif any(k in keyword for k in IntelligenceExtractor.SCAM_KEYWORDS["high"]):
                score += 3
            else:
                score += 1
        
        return min(score, 100)  # Cap at 100
    
    @staticmethod
    def is_scam(intelligence: Dict[str, List[str]]) -> bool:
        """
        Determine if intelligence indicates confirmed scam
        
        Criteria:
        - Has critical intel (UPI, bank, phishing) OR
        - Scam score >= 30
        """
        has_critical = any([
            intelligence.get("upiIds"),
            intelligence.get("bankAccounts"),
            intelligence.get("phishingLinks")
        ])
        
        score = IntelligenceExtractor.calculate_scam_score(intelligence)
        
        return has_critical or score >= 30