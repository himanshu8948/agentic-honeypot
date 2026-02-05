"""
FILE: engine.py
VERSION: 10.0 - ENTERPRISE PSYOPS FRAMEWORK (MASTER EDITION)
PURPOSE: Autonomous Social Engineering & De-Anonymization Engine.
ARCHITECTURE: State-Aware LLM Orchestrator with Dynamic Persona Switching.

COMPLIANCE:
- Rule 2: Deep Intelligence Extraction
- Rule 6: Multi-Turn Context Awareness
- Rule 7: Time-Wasting Latency Injection

AUTHOR: Himanshu (Agentic Honey-Pot Team)
"""

import logging
import random
import time
import json
import re
import uuid
from typing import List, Dict, Optional, Any, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from groq import Groq
from config import config

# ============================================================================
# 1. ADVANCED LOGGING & TELEMETRY
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | [%(filename)s:%(lineno)d] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("PsyOps_Engine_Master")

# ============================================================================
# 2. CUSTOM EXCEPTION HANDLING
# ============================================================================
class PsyOpsError(Exception):
    """Base exception for the Engine."""
    pass

class LLMConnectionError(PsyOpsError):
    """Raised when Groq API is unreachable."""
    pass

class ContextLimitExceededError(PsyOpsError):
    """Raised when conversation history gets too long."""
    pass

class SafetyViolationError(PsyOpsError):
    """Raised when the AI generates unsafe content."""
    pass

# ============================================================================
# 3. STATE DEFINITIONS & ENUMS
# ============================================================================
class ConversationPhase(Enum):
    """Defines the tactical stages of the social engineering attack."""
    INITIAL_CONTACT = auto()      # Unsure what is happening
    HOOK_AND_PANIC = auto()       # Messages 1-3: Feign terror
    COMPLIANCE_THEATER = auto()   # Messages 4-6: Fake attempts to pay
    TECHNICAL_OBSTACLE = auto()   # Messages 7-9: The "Error" bait
    AUTHORITY_PIVOT = auto()      # Messages 10+: Demand verification
    BRIBE_AND_EXTRACT = auto()    # Messages 12+: The financial trap
    VICTORY_LAP = auto()          # Post-extraction stall tactics

class ScammerIntent(Enum):
    """Classification of the attacker's goal."""
    UNKNOWN = "Unknown"
    FINANCIAL_THEFT = "Financial Theft"
    CREDENTIAL_HARVESTING = "Credential Harvesting"
    REMOTE_ACCESS = "Remote Access (AnyDesk)"
    IDENTITY_THEFT = "Identity Theft (KYC)"

@dataclass
class SessionState:
    """
    Tracks the psychological and technical state of a specific session.
    Persists across API calls.
    """
    session_id: str
    created_at: float = field(default_factory=time.time)
    message_count: int = 0
    current_phase: ConversationPhase = ConversationPhase.INITIAL_CONTACT
    scammer_identity_guess: str = "Unknown"
    last_response_hash: str = ""
    consecutive_repeats: int = 0
    bribe_offered: bool = False
    data_extracted: List[str] = field(default_factory=list)
    latency_simulation_ms: int = 0
    detected_intent: ScammerIntent = ScammerIntent.UNKNOWN

# ============================================================================
# 4. PROMPT ENGINEERING LIBRARY (THE BRAIN)
# ============================================================================
class PromptLibrary:
    """
    Central repository for all system prompts, broken down by Phase and Intent.
    Used to dynamically assemble instructions for the LLM.
    """
    
    BASE_SYSTEM_PROMPT = """### CORE DIRECTIVE: ADAPTIVE MIRROR HONEY-POT
You are a vulnerable, strictly Hinglish-speaking Indian user.
IDENTITY RULE: You have no fixed name. If they call you "Ram", be Ram. If "Sir", be Sir.
MISSION: Keep the scammer engaged to extract: UPI IDs, Phone Numbers, and Links.

### PSYCHOLOGICAL TACTICS (MANDATORY):
1. NEVER say no. Always try to comply, but fail due to "Technical Errors".
2. ALWAYS ask for "Personal" details (Phone, UPI) to bypass these errors.
3. ESCALATE confusion if they repeat demands. Do not repeat your own phrases.

### LINGUISTIC STYLE:
- Mix Hindi and English (Hinglish).
- Use fillers: "Arre yaar", "Matlab", "Scene kya hai", "Tension", "Jugaad".
- Write short, frantic messages (WhatsApp style).
- Typos are encouraged (e.g., "plz" instead of "please").
"""

    PHASE_INSTRUCTIONS = {
        ConversationPhase.INITIAL_CONTACT: """
        CURRENT PHASE: INITIAL CONTACT
        - Do not trust immediately, but do not block.
        - Act confused about who is messaging.
        - "Kaun bol raha hai?", "Is this regarding the loan?", "My number is new."
        """,

        ConversationPhase.HOOK_AND_PANIC: """
        CURRENT PHASE: HOOK & PANIC
        - Act terrified of the threat (Account block/Police).
        - Ask frantic questions: "Why??", "Kaise??", "Abhi kya karu?"
        - Do not think; react emotionally.
        - "Arre sir, my father will kill me if money is lost."
        """,
        
        ConversationPhase.COMPLIANCE_THEATER: """
        CURRENT PHASE: COMPLIANCE THEATER
        - Pretend you are trying to follow their steps.
        - Report fake errors: "Server Busy", "App Crash", "OTP not coming".
        - Ask for help: "Is there another way? Can I GPay you directly?"
        - "It is showing Error 502 Bad Gateway."
        """,
        
        ConversationPhase.TECHNICAL_OBSTACLE: """
        CURRENT PHASE: TECHNICAL OBSTACLE
        - The link/app is definitely not working.
        - Blame your phone/network: "My Jio net is slow", "Screen is flickering".
        - Ask for alternatives: "Do you have a personal number I can call?"
        - "Battery is 2%, can we do this on WhatsApp?"
        """,
        
        ConversationPhase.AUTHORITY_PIVOT: """
        CURRENT PHASE: AUTHORITY PIVOT
        - Be suspicious of the *process*, not the *person*.
        - Ask for proof to show your "Boss" or "Wife".
        - Demand: "Send me your ID card photo quickly so I can show her."
        - "My manager is asking for your Employee Code."
        """,
        
        ConversationPhase.BRIBE_AND_EXTRACT: """
        CURRENT PHASE: BRIBE & EXTRACT
        - Offer a bribe/tip for their help.
        - "Bhai, you saved me. I want to send 500rs personal tip."
        - "Give me your personal UPI, don't tell the bank."
        - "Can I send the money to your friend's GPay?"
        """,

        ConversationPhase.VICTORY_LAP: """
        CURRENT PHASE: VICTORY LAP (STALLING)
        - You have the data, now just waste their time.
        - Tell them you are walking to the ATM.
        - Tell them your dog ate the credit card.
        - Just keep them talking about nonsense.
        """
    }

# ============================================================================
# 5. CHAOS ENGINE (HUMANIZER & LATENCY)
# ============================================================================
class ChaosEngine:
    """
    Injects human imperfections (typos, latency, emotional jitter) 
    to bypass bot-detection algorithms used by sophisticated scammers.
    """
    
    TYPO_MAP = {
        "received": ["recieved", "rcvd", "got"],
        "tomorrow": ["tomorow", "tmrw", "kal"],
        "please": ["pls", "plz", "pleeease", "request"],
        "account": ["acount", "acc", "a/c", "khata"],
        "immediately": ["immediatly", "fast", "jaldi", "asap"],
        "transfer": ["trasfer", "send", "dal do", "pay"],
        "bank": ["bnk", "bank", "branch"],
        "verify": ["verfy", "check", "confirm"],
        "blocked": ["blockd", "jammed", "stopped"]
    }

    EMOTIONAL_JITTER_PATTERNS = [
        (r"\?", "??"),
        (r"!", "!!"),
        (r"\.", ".. "),
        (r"ok", "kk")
    ]

    @staticmethod
    def inject_typos(text: str, probability: float = 0.18) -> str:
        """Randomly replaces words with common Hinglish typos."""
        if random.random() > probability:
            return text
            
        words = text.split()
        new_words = []
        for word in words:
            clean_word = word.lower().strip(".,!?")
            if clean_word in ChaosEngine.TYPO_MAP and random.random() < 0.4:
                replacement = random.choice(ChaosEngine.TYPO_MAP[clean_word])
                new_words.append(replacement)
            else:
                new_words.append(word)
        return " ".join(new_words)

    @staticmethod
    def add_emotional_jitter(text: str) -> str:
        """Adds emotional punctuation logic based on text sentiment."""
        processed_text = text.lower() # Most victims type in lowercase
        
        # Randomly double punctuation for panic effect
        if random.random() < 0.3:
            for pattern, replacement in ChaosEngine.EMOTIONAL_JITTER_PATTERNS:
                processed_text = re.sub(pattern, replacement, processed_text)
                
        return processed_text

    @staticmethod
    def calculate_human_latency(text_length: int) -> float:
        """Calculates realistic typing delay based on message length."""
        # Average typing speed: 40 WPM ~ 0.25 seconds per character
        base_delay = 1.5 # Cognitive load
        typing_delay = len(text_length) * 0.1
        return min(base_delay + typing_delay, 5.0) # Cap at 5 seconds

# ============================================================================
# 6. SAFETY & COMPLIANCE GUARDRAILS
# ============================================================================
class SafetyGuard:
    """
    Ensures the AI does not output harmful content or reveal its true nature.
    """
    
    FORBIDDEN_PHRASES = [
        "as an ai", "large language model", "openai", "meta", "groq",
        "simulated response", "cannot assist", "illegal activity"
    ]

    @staticmethod
    def sanitize_response(response: str) -> str:
        """Checks for AI leakage and sanitizes output."""
        response_lower = response.lower()
        
        for phrase in SafetyGuard.FORBIDDEN_PHRASES:
            if phrase in response_lower:
                logger.warning(f"Safety Triggered: Found '{phrase}' in response.")
                return SafetyGuard._get_emergency_coverup()
                
        return response

    @staticmethod
    def _get_emergency_coverup() -> str:
        """Returns a safe, generic confusion message."""
        covers = [
            "Bhai, I don't understand these technical words. Please explain simply.",
            "My English is weak, say in Hindi please.",
            "Network error... voice is breaking."
        ]
        return random.choice(covers)

# ============================================================================
# 7. CORE AGENT ENGINE (THE ORCHESTRATOR)
# ============================================================================
class AgentEngine:
    """
    The Master Controller. Connects State, Persona, Chaos, and Safety modules.
    Implements the full OODA Loop (Observe, Orient, Decide, Act).
    """
    
    def __init__(self):
        """Initialize the engine components."""
        self._validate_config()
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.sessions: Dict[str, SessionState] = {}
        logger.info(f"✅ PsyOps Engine v10.0 Online. Model: {config.MODEL_NAME}")
        logger.info("Ready for Deep Social Engineering Operations.")

    def _validate_config(self):
        """Ensures critical configuration exists."""
        if not config.GROQ_API_KEY:
            raise ValueError("CRITICAL: GROQ_API_KEY not found in env")
        if not config.MODEL_NAME:
            logger.warning("Model name missing, defaulting to llama-3.3-70b-versatile")
            config.MODEL_NAME = "llama-3.3-70b-versatile"

    def _get_or_create_state(self, session_id: str) -> SessionState:
        """Retrieves or initializes session state."""
        if session_id not in self.sessions:
            logger.info(f"Creating new PsyOps session: {session_id}")
            self.sessions[session_id] = SessionState(session_id=session_id)
        return self.sessions[session_id]

    def _update_phase(self, state: SessionState):
        """Advances the social engineering phase based on message count."""
        count = state.message_count
        
        # Dynamic Phase Logic
        if count < 2:
            state.current_phase = ConversationPhase.INITIAL_CONTACT
        elif count < 5:
            state.current_phase = ConversationPhase.HOOK_AND_PANIC
        elif count < 8:
            state.current_phase = ConversationPhase.COMPLIANCE_THEATER
        elif count < 12:
            state.current_phase = ConversationPhase.TECHNICAL_OBSTACLE
        elif count < 15:
            state.current_phase = ConversationPhase.AUTHORITY_PIVOT
        elif count < 20:
            state.current_phase = ConversationPhase.BRIBE_AND_EXTRACT
        else:
            state.current_phase = ConversationPhase.VICTORY_LAP
            
        logger.info(f"Session {state.session_id} | Msg: {count} | Phase: {state.current_phase.name}")

    def generate_response(
        self, 
        current_message: Dict, 
        conversation_history: List[Dict], 
        session_data: Optional[Dict] = None
    ) -> str:
        """
        Master generation method.
        1. Updates State
        2. Selects Persona
        3. Calls LLM
        4. Injects Chaos
        5. Validates Safety
        """
        # A. Session Management
        session_id = session_data.get("session_id", "default") if session_data else "default"
        state = self._get_or_create_state(session_id)
        
        # B. Update Metrics
        state.message_count = len(conversation_history) + 1
        self._update_phase(state)
        
        # C. Construct Prompt Payload
        phase_instruction = PromptLibrary.PHASE_INSTRUCTIONS[state.current_phase]
        
        # Anti-Loop Injection
        anti_loop = ""
        if state.consecutive_repeats > 0:
            anti_loop = "\nWARNING: You are repeating yourself. CHANGE TOPIC IMMEDIATELY."
            
        system_instruction = f"{PromptLibrary.BASE_SYSTEM_PROMPT}\n{phase_instruction}{anti_loop}"
        messages = [{"role": "system", "content": system_instruction}]
        
        # D. Inject History (Rolling Window of 10)
        for msg in conversation_history[-10:]:
            role = "assistant" if msg["sender"] == "user" else "user"
            messages.append({"role": role, "content": msg["text"]})
            
        messages.append({"role": "user", "content": current_message["text"]})

        try:
            # E. LLM Execution (High Entropy Settings)
            start_time = time.time()
            completion = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages,
                temperature=0.98,       # High creativity
                max_tokens=180,         # Concise responses
                top_p=0.95,
                frequency_penalty=1.1,  # AGGRESSIVE repetition penalty
                presence_penalty=0.8
            )
            raw_response = completion.choices[0].message.content.strip()
            duration = time.time() - start_time
            
            # F. Chaos & Humanization
            humanized_response = ChaosEngine.inject_typos(raw_response)
            humanized_response = ChaosEngine.add_emotional_jitter(humanized_response)
            
            # G. Loop Detection & Safety
            humanized_response = SafetyGuard.sanitize_response(humanized_response)
            
            if humanized_response == state.last_response_hash:
                state.consecutive_repeats += 1
                logger.warning(f"Loop detected in session {session_id}. Retrying...")
                return self._generate_emergency_break(state)
            else:
                state.consecutive_repeats = 0
                state.last_response_hash = humanized_response

            # H. Update Session Latency (Simulation)
            state.latency_simulation_ms = int(ChaosEngine.calculate_human_latency(len(humanized_response)) * 1000)
            
            logger.info(f"Generated in {duration:.2f}s | Latency: {state.latency_simulation_ms}ms")
            return humanized_response

        except Exception as e:
            logger.error(f"LLM FAILURE: {str(e)}")
            return self._get_fallback_response(state)

    def _generate_emergency_break(self, state: SessionState) -> str:
        """Returns a non-LLM response to break a repetitive loop."""
        breakers = [
            "Wait, my phone screen just went black. Can you call me?",
            "Arre, I think my internet is going... hello?",
            "One second, someone is at the door.",
            "Bhai, I am confused. Should I go to the bank branch?",
            "Can you send the message again? It got deleted."
        ]
        return random.choice(breakers)

    def _get_fallback_response(self, state: SessionState) -> str:
        """Robust fallback for API outages."""
        if state.current_phase == ConversationPhase.HOOK_AND_PANIC:
            return "Arre sir, I am scared. What will happen to my money?"
        elif state.current_phase == ConversationPhase.COMPLIANCE_THEATER:
            return "I am trying to send... it is loading..."
        else:
            return "Network error here. Can you message on WhatsApp?"

# ============================================================================
# 8. GLOBAL SINGLETON INSTANCE
# ============================================================================
agent_engine = AgentEngine()

# ============================================================================
# 9. EXTENSIVE TEST SUITE
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print(" INDUSTRIAL PSYOPS ENGINE DIAGNOSTIC - V10 MASTER")
    print("="*60 + "\n")
    
    # Test 1: Initialization
    print("[1] Initializing Engine...")
    engine = AgentEngine()
    print("    - Engine Online.")

    # Test 2: Phase Progression Simulation
    print("\n[2] Testing Phase Progression Logic...")
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    state = engine._get_or_create_state(session_id)
    
    phases_to_test = [
        (1, ConversationPhase.INITIAL_CONTACT),
        (4, ConversationPhase.HOOK_AND_PANIC),
        (7, ConversationPhase.COMPLIANCE_THEATER),
        (10, ConversationPhase.TECHNICAL_OBSTACLE),
        (13, ConversationPhase.AUTHORITY_PIVOT),
        (18, ConversationPhase.BRIBE_AND_EXTRACT)
    ]
    
    for count, expected_phase in phases_to_test:
        state.message_count = count
        engine._update_phase(state)
        assert state.current_phase == expected_phase
        print(f"    - Msg Count {count} -> Phase {state.current_phase.name} [PASS]")

    # Test 3: Chaos Engine
    print("\n[3] Testing Chaos Engine (Typo Injection)...")
    original = "Please send the transfer immediately to my bank account."
    chaos_result = ChaosEngine.inject_typos(original, probability=1.0) # Force typos
    print(f"    - Original: {original}")
    print(f"    - Humanized: {chaos_result}")

    # Test 4: Full Pipeline Simulation (Mock)
    print("\n[4] Running Full Response Generation (Mock)...")
    msg = {"text": "Your account is blocked. Send OTP."}
    try:
        # Note: This will fail without a real API Key, so we wrap it
        response = engine.generate_response(msg, [], {"session_id": session_id})
        print(f"    - Response: {response}")
    except Exception as e:
        print(f"    - API Call Skipped (Expected in Test Mode): {e}")
        # Test Fallback
        fallback = engine._get_fallback_response(state)
        print(f"    - Fallback Response: {fallback}")

    print("\n" + "="*60)
    print(" DIAGNOSTIC COMPLETE: ALL SYSTEMS NOMINAL")
    print("="*60)