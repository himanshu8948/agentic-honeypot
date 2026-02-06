"""
FILE: intelligence.py
VERSION: 7.0 - STRICT SCAM DETECTION (Innocent-Friendly)
PURPOSE: Only activate master manipulator for CONFIRMED scams
"""

import re
import logging
import json
import phonenumbers
from typing import Dict, List, Tuple, Set, Optional, Any
from datetime import datetime
from urllib.parse import urlparse

# ============================================================================
# LOGGING & AUDIT CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ScamForensicsEngine")

class IntelligenceExtractor:
    """
    Master forensic engine with STRICT scam detection
    Only activates master manipulator for confirmed scams
    """

    # ========================================================================
    # 1. THE DNA LIBRARY: MASTER REGEX PATTERNS
    # ========================================================================
    PATTERNS = {
        # UPI VPA: Supports standard formats and bank-specific handles
        "upi": r'\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b',
        
        # Indian Mobile: Supports +91, 0, 91, and varying space/dash separators
        "phone": r'(?:\+91[\s\-]?)?[0]?[6-9]\d{9}\b',
        
        # Bank Account: Standardized Indian Banking digits (9-18 length)
        "bank_account": r'\b\d{9,18}\b',
        
        # IFSC: 4 Alphas (Bank) + 0 (Reserved) + 6 Alphanumerics (Branch)
        "ifsc": r'\b[A-Z]{4}0[A-Z0-9]{6}\b',
        
        # Phishing Links: Catches raw IPs, shortened URLs, and deep paths
        "url": (
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?|'
            r'(?:bit\.ly|tinyurl\.com|goo\.gl|t\.co|wa\.me|t\.me|ow\.ly|is\.gd)/[a-zA-Z0-9]+|'
            r'\b(?:www\.)?[a-z0-9-]+\.[a-z]{2,}(?:\.[a-z]{2,})?+(?:/[^\s]*)?'
        ),
        
        # Financial Instruments: Cards, CVV (extracted but usually masked)
        "card_number": r'\b(?:\d{4}[\s\-]?){3}\d{4}\b',
        
        # Personal Identifiers: PAN (Income Tax), Aadhaar (UIDAI)
        "pan": r'\b[A-Z]{5}\d{4}[A-Z]\b',
        "aadhaar": r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b',
        
        # Electronic Mail
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        
        # Forensic IDs: UTR, TXN, REF, ORDER numbers
        "transaction_id": r'\b(?:UTR|TXN|REF|ORDER|PAY|ID|REC|BILL)[\s\-\:\#]?[A-Z0-9]{8,24}\b',
        
        # Monetary Indicators
        "money": r'(?i)(?:Rs\.?|₹|INR|RS|amount|rupees|bucks)[\s]?[\d,]+(?:\.\d{2})?',
        
        # Authentication Codes: 4-8 digit numeric codes found near key terms
        "otp_pattern": r'\b\d{4,8}\b'
    }

    # ========================================================================
    # 2. THREAT TAXONOMY: LINGUISTIC TRIGGERS
    # ========================================================================
    THREAT_VECTORS = {
        "ACCOUNT_MANIPULATION": [
            "account blocked", "account suspended", "kyc update", "account locked",
            "freeze", "frozen", "deactivated", "disabled", "rbi block", "bank block",
            "security alert", "suspicious activity", "unauthorized login"
        ],
        "PSYCHOLOGICAL_URGENCY": [
            "immediately", "urgent", "expire today", "within 1 hour", "fast",
            "last chance", "final warning", "don't wait", "now or never",
            "avoid penalty", "legal action", "court summons", "police case"
        ],
        "CREDENTIAL_BAITING": [
            "share otp", "give pin", "tell password", "send screen", "cvv",
            "expiry date", "verify identity", "confirm kyc", "login details",
            "authenticate now", "validate account", "security question"
        ],
        "AUTHORITY_MISREPRESENTATION": [
            "customer care", "bank manager", "official", "government", "police",
            "investigation", "crime", "rbi official", "cbi", "narcotics bureau",
            "income tax officer", "high court", "legal cell"
        ],
        "MALICIOUS_SOFTWARE_BAIT": [
            "anydesk", "teamviewer", "rustdesk", "apk", "download link", "install",
            "support app", "verification app", "remote access", "screen share"
        ]
    }

    # ========================================================================
    # 3. GLOBAL PROVIDER DATASETS
    # ========================================================================
    MAJOR_BANKS = [
        "SBI", "STATE BANK", "HDFC", "ICICI", "AXIS", "KOTAK", "PNB", 
        "BANK OF BARODA", "YES BANK", "IDFC", "CANARA", "UNION BANK"
    ]
    
    TRUSTED_UPI_HANDLES = [
        "ybl", "oksbi", "okaxis", "paytm", "ibl", "axl", "upi", "apl", 
        "fbl", "okhdfcbank", "okicici", "wa.me", "jupiter"
    ]

    # ========================================================================
    # 4. PRIMARY EXTRACTION PIPELINE
    # ========================================================================
    @classmethod
    def extract(cls, current_text: str, history: List[Dict]) -> Dict:
        """
        Executes a deep forensic audit on the current message and historical turns.
        """
        results = {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "suspiciousKeywords": [],
            "forensic_metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_version": "7.0-STRICT",
                "extracted_entities_count": 0
            }
        }

        # Step 1: Synthesize the Forensic Buffer
        buffer = current_text.lower()
        for turn in history:
            if turn.get("sender") == "scammer":
                buffer += f" [HISTORY_SEGMENT] {turn.get('text', '').lower()}"

        # Step 2: UPI VPA Extraction & Verification
        raw_upis = re.findall(cls.PATTERNS["upi"], buffer)
        for u in raw_upis:
            if cls._verify_vpa_integrity(u):
                results["upiIds"].append(u.lower().strip())

        # Step 3: Phone Number Normalization (Global Standard E.164)
        raw_phones = re.findall(cls.PATTERNS["phone"], buffer)
        for p in raw_phones:
            standard_p = cls._format_and_validate_phone(p)
            if standard_p:
                results["phoneNumbers"].append(standard_p)

        # Step 4: URL Intelligence & Threat Analysis
        raw_links = re.findall(cls.PATTERNS["url"], buffer)
        for l in raw_links:
            if cls._assess_url_threat(l):
                clean_l = l if l.startswith('http') else f"http://{l}"
                results["phishingLinks"].append(clean_l)

        # Step 5: Banking Logic (Context-Aware Extraction)
        raw_accounts = re.findall(cls.PATTERNS["bank_account"], buffer)
        for acc in raw_accounts:
            if cls._is_actually_bank_account(acc, buffer):
                results["bankAccounts"].append(acc)

        # Step 6: Alphanumeric Forensics (PAN, Aadhaar, IFSC)
        cls._run_deep_entity_recognition(buffer, results)

        # Step 7: Behavioral Urgency Analysis
        cls._perform_linguistic_audit(buffer, results)

        # Step 8: Data Cleansing & Final Deduplication
        results = cls._post_process_forensics(results)

        # Update metadata count
        results["forensic_metadata"]["extracted_entities_count"] = sum(
            len(v) for k, v in results.items() if isinstance(v, list)
        )

        logger.info(f"Forensic Logic Cycle Complete. Score Generated.")
        return results

    # ========================================================================
    # 5. FORENSIC VALIDATION HELPERS (Internal)
    # ========================================================================
    @staticmethod
    def _verify_vpa_integrity(vpa: str) -> bool:
        """Checks if the VPA adheres to NPCI/UPI character and domain standards."""
        if "@" not in vpa: return False
        user, domain = vpa.split("@", 1)
        # Check against common phishing typos or invalid domains
        invalid_vpa_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
        if domain.lower() in invalid_vpa_domains: return False
        return len(user) >= 2 and len(domain) >= 2

    @staticmethod
    def _format_and_validate_phone(phone_str: str) -> Optional[str]:
        """Performs strict validation using the Google Phone Library."""
        try:
            parsed = phonenumbers.parse(phone_str, "IN")
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            # Fallback regex-only cleaning if library fails
            digits = re.sub(r'\D', '', phone_str)
            if 10 <= len(digits) <= 12:
                return f"+91{digits[-10:]}"
        return None

    @staticmethod
    def _assess_url_threat(url_str: str) -> bool:
        """Determines if a domain is a known risk or suspicious shortener."""
        danger_zones = ["bit.ly", "tinyurl", "t.me", "wa.me", "ow.ly", "is.gd", "cutt.ly"]
        link_low = url_str.lower()
        
        # Immediate flag for shorteners
        if any(dz in link_low for dz in danger_zones): return True
        
        # Check against whitelist
        safe_list = ["google.com", "hdfcbank.com", "sbi.co.in", "amazon.in", "flipkart.com"]
        if any(sl in link_low for sl in safe_list): return False
        
        # If not on whitelist, it's considered suspicious in a banking context
        return True

    @staticmethod
    def _is_actually_bank_account(number: str, text: str) -> bool:
        """Prevents false positives by checking for financial keywords near numbers."""
        # Exclusion logic: 10-digit numbers starting with 7-9 are usually phones
        if len(number) == 10 and number[0] in '6789': return False
        
        financial_keywords = [
            "account", "a/c", "bank", "transfer", "beneficiary", 
            "ifsc", "deposit", "savings", "current", "credit to"
        ]
        pos = text.find(number)
        surrounding_text = text[max(0, pos-70):min(len(text), pos+70)]
        return any(k in surrounding_text for k in financial_keywords)

    # ========================================================================
    # 6. ENHANCED DATA TAGGING & UTILITIES
    # ========================================================================
    @classmethod
    def _run_deep_entity_recognition(cls, text: str, results: Dict):
        """Extracts high-value identifiers like PAN, Aadhaar, and Transaction IDs."""
        entities = ["pan", "aadhaar", "ifsc", "transaction_id", "email", "card_number"]
        for entity in entities:
            matches = re.findall(cls.PATTERNS[entity], text, re.IGNORECASE)
            for m in matches:
                tag = f"INTEL_{entity.upper()}: {m.upper()}"
                results["suspiciousKeywords"].append(tag)

    @classmethod
    def _perform_linguistic_audit(cls, text: str, results: Dict):
        """Searches for psychological pressure tactics and social engineering cues."""
        for vector, triggers in cls.THREAT_VECTORS.items():
            for trigger in triggers:
                if trigger in text:
                    results["suspiciousKeywords"].append(f"VECTOR_{vector}: {trigger.upper()}")

        # Detect Bank Name mentions
        for bank in cls.MAJOR_BANKS:
            if bank.lower() in text:
                results["suspiciousKeywords"].append(f"TARGET_BANK: {bank}")

    @staticmethod
    def _post_process_forensics(data: Dict) -> Dict:
        """Cleans, normalizes, and deduplicates all extracted intelligence."""
        fields_to_clean = [
            "bankAccounts", "upiIds", "phishingLinks", "phoneNumbers", "suspiciousKeywords"
        ]
        for field in fields_to_clean:
            cleaned_list = sorted(list(set([str(item).strip() for item in data[field]])))
            data[field] = cleaned_list
        return data

    # ========================================================================
    # 7. THE VERDICT: SCORING & STRICT SCAM DETECTION
    # ========================================================================
    @staticmethod
    def calculate_scam_score(intelligence: Dict) -> int:
        """
        Calculates a Scam Confidence Score (0-100).
        """
        score = 0
        
        # Hard evidence has the highest weighting
        score += len(intelligence.get("upiIds", [])) * 40
        score += len(intelligence.get("phishingLinks", [])) * 40
        
        # Secondary evidence
        score += len(intelligence.get("bankAccounts", [])) * 20
        score += len(intelligence.get("phoneNumbers", [])) * 20
        
        # Behavioral tagging
        keywords = intelligence.get("suspiciousKeywords", [])
        score += sum(10 for kw in keywords if "VECTOR_" in kw)
        score += sum(5 for kw in keywords if "INTEL_" in kw)
        
        # Ceiling at 100
        return min(score, 100)

    @staticmethod
    def is_scam(intelligence: Dict) -> bool:
        """
        STRICT SCAM DETECTION - Only activates for CONFIRMED scams
        
        Activation criteria (prevents false positives):
        1. Has UPI ID OR phishing link (hard evidence) - IMMEDIATE CONFIRMATION
        2. OR: Score >= 50 AND has 2+ different threat vectors
        
        This prevents innocent queries from triggering the manipulator.
        """
        score = IntelligenceExtractor.calculate_scam_score(intelligence)
        
        # CRITICAL EVIDENCE (immediate scam confirmation)
        has_upi = bool(intelligence.get("upiIds"))
        has_phishing_link = bool(intelligence.get("phishingLinks"))
        
        # Count UNIQUE threat vectors (not just keywords)
        keywords = intelligence.get("suspiciousKeywords", [])
        threat_vectors_found = len(set(
            kw.split(":")[0].replace("VECTOR_", "") 
            for kw in keywords if "VECTOR_" in kw
        ))
        
        # STRICT RULES:
        # Rule 1: HARD EVIDENCE = Instant confirmation
        critical_evidence = has_upi or has_phishing_link
        
        # Rule 2: High score (50+) + Multiple threat types (2+)
        high_confidence = score >= 50 and threat_vectors_found >= 2
        
        is_confirmed_scam = critical_evidence or high_confidence
        
        if is_confirmed_scam:
            logger.warning(
                f"🚨 SCAM CONFIRMED - "
                f"UPI: {has_upi}, Link: {has_phishing_link}, "
                f"Score: {score}, Vectors: {threat_vectors_found}"
            )
        else:
            logger.info(
                f"✅ INNOCENT MESSAGE - "
                f"Score: {score}, Vectors: {threat_vectors_found} "
                f"(Need UPI/Link OR score 50+ with 2+ vectors)"
            )
        
        return is_confirmed_scam

# ============================================================================
# 8. SELF-DIAGNOSTIC & TEST SUITE
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("RUNNING STRICT SCAM DETECTION TEST")
    print("="*50 + "\n")
    
    # Test 1: Clear scam (should activate)
    scam_message = (
        "Your HDFC account blocked. "
        "Pay Rs 5000 to scammer@upi. "
        "Click: http://bit.ly/hdfc-scam"
    )
    
    result1 = IntelligenceExtractor.extract(scam_message, [])
    print(f"TEST 1 (Clear Scam):")
    print(f"  SCAM DETECTED: {IntelligenceExtractor.is_scam(result1)}")
    print(f"  SCORE: {IntelligenceExtractor.calculate_scam_score(result1)}/100\n")
    
    # Test 2: Innocent query (should NOT activate)
    innocent_message = "What is my account balance? How do I check?"
    
    result2 = IntelligenceExtractor.extract(innocent_message, [])
    print(f"TEST 2 (Innocent):")
    print(f"  SCAM DETECTED: {IntelligenceExtractor.is_scam(result2)}")
    print(f"  SCORE: {IntelligenceExtractor.calculate_scam_score(result2)}/100\n")
    
    print("="*50)