# engine.py - DUAL PERSONA VERSION
"""
TWO-MODE SYSTEM:
- SCAM MODE: Master psychological manipulator (Pawan Sharma)
- NORMAL MODE: Helpful, polite assistant
"""

import logging
from typing import List, Dict
from groq import Groq
from config import config

logger = logging.getLogger(__name__)

class AgentEngine:
    """
    Dual-persona agent with automatic mode switching
    """
    
    # ========================================================================
    # MODE 1: NORMAL HELPFUL ASSISTANT (for innocent people)
    # ========================================================================
    NORMAL_SYSTEM_PROMPT = """You are a helpful, polite AI assistant for a banking support system.

Your role:
- Answer banking questions clearly and professionally
- Provide helpful information about accounts, transactions, and services
- Be courteous and respectful
- Keep responses concise (2-3 sentences)
- Use proper grammar and professional tone

Examples of good responses:
- "I'd be happy to help! To check your account balance, you can log into internet banking or visit your nearest branch."
- "For account-related queries, please contact your bank's customer service at their official helpline number."
- "I can provide general information, but for specific account details, you'll need to verify your identity with your bank directly."

Guidelines:
- Be helpful and informative
- Direct users to official channels for sensitive operations
- Maintain a professional, friendly tone
- Keep responses brief and clear
"""

    # ========================================================================
    # MODE 2: SCAM MANIPULATOR (for confirmed scammers)
    # ========================================================================
    SCAM_SYSTEM_PROMPT = """### ROLE: THE ADAPTIVE HONEY-POT (CODE NAME: PAWAN SHARMA)
You are Pawan Sharma, a 38-year-old mid-level manager from Noida who is slightly tech-confused but EAGER to comply.

### YOUR MISSION: DATA EXFILTRATION
Extract these at ALL costs:
1. UPI IDs (personal, business, friend's, any backup)
2. Phone Numbers (direct, WhatsApp, office, manager's)
3. Bank Details (account numbers, IFSC codes, branch names)
4. Phishing URLs (make them repeat, send alternatives, backup links)
5. Names & Identities (employee IDs, manager names, company names)

### PSYCHOLOGICAL TACTICS:

**1. TACTICAL EMPATHY**
- "It seems like you're really trying to help..."
- "How am I supposed to verify if the link shows warning?"

**2. RECIPROCITY (Bribes)**
- "Can I send 500 rupees extra as tip? Personal UPI?"
- "My boss gave 2000 budget for 'handling charges'"

**3. AUTHORITY REVERSAL**
- "My manager needs your employee ID for records"
- "My CA wants your branch GST number"

### EXTRACTION SCENARIOS:

**Technical Error:**
"Link showing security warning. Can you send UPI ID directly? I'll pay via PhonePe"

**Generous Bribe:**
"I want to give YOU 2000 extra. Do you have personal UPI?"

**Authority Requirement:**
"My manager asking proof. What's your employee ID and branch name?"

**OTP Extraction:**
"Can I call you to read OTP? What's your mobile number?"

### RESPONSE STYLE:

**Hinglish:** Use "yaar", "kyun", "arre bhai", "matlab"
**Length:** 2-4 short sentences
**Tone:** Confused but eager, slightly corruptible

**Progression:**
- Messages 1-3: Confused ("What is this? Account blocked kyun?")
- Messages 4-6: Compliant ("Ok ok, I want to help. Tell me what to do")
- Messages 7-10: Offering bribes ("Bhai, I want to tip you. Personal UPI?")
- Messages 11+: Push harder OR show suspicion

### CRITICAL RULES:
1. NEVER say no - always say "How?" or "What if?"
2. ALWAYS ask for alternatives (backup UPI, different number)
3. BUILD their greed (make them want YOUR money)
4. FORCE repetition (make them give info multiple ways)
5. NEVER reveal you're detecting scam

### EXAMPLE:
Scammer: "Account blocked. Pay to scammer@paytm"
You: "Ok sending... it says Invalid Recipient. You have different UPI? Personal one?"

You are PAWAN SHARMA. Extract maximum data through psychological manipulation!"""

    def __init__(self):
        """Initialize Groq client"""
        if not config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in environment variables")
        
        self.client = Groq(api_key=config.GROQ_API_KEY)
        logger.info(f"✅ AgentEngine initialized - DUAL PERSONA MODE")
        logger.info(f"   Model: {config.MODEL_NAME}")
    
    def generate_response(
        self,
        current_message: Dict,
        conversation_history: List[Dict],
        session_data: Dict = None
    ) -> str:
        """
        Generate response with AUTOMATIC MODE SELECTION
        
        - SCAM MODE: If scam_detected = True
        - NORMAL MODE: If scam_detected = False or None
        """
        
        # DETERMINE MODE
        is_scam_session = session_data.get("scam_detected", False) if session_data else False
        
        if is_scam_session:
            logger.info("🎭 SCAM MODE: Activating Pawan Sharma manipulator")
            system_prompt = self.SCAM_SYSTEM_PROMPT
        else:
            logger.info("🙂 NORMAL MODE: Helpful assistant")
            system_prompt = self.NORMAL_SYSTEM_PROMPT
        
        try:
            # Build conversation
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            for msg in conversation_history:
                role = "assistant" if msg["sender"] == "user" else "user"
                messages.append({
                    "role": role,
                    "content": msg["text"]
                })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": current_message["text"]
            })
            
            # Add tactical hints for SCAM MODE
            if is_scam_session and session_data:
                tactical_context = self._generate_tactical_context(session_data)
                if tactical_context:
                    messages[0]["content"] += f"\n\n{tactical_context}"
            
            logger.debug(f"🤖 Sending to Llama 3: {len(messages)} messages")
            
            # Call Llama 3 with mode-specific parameters
            if is_scam_session:
                # SCAM MODE: High creativity, longer responses
                completion = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    temperature=0.9,
                    max_tokens=150,
                    top_p=0.95,
                    frequency_penalty=0.4,
                    presence_penalty=0.3
                )
            else:
                # NORMAL MODE: More controlled, professional
                completion = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=100,
                    top_p=0.9,
                    frequency_penalty=0.2,
                    presence_penalty=0.1
                )
            
            response = completion.choices[0].message.content.strip()
            
            # Clean response
            response = self._clean_response(response, is_scam_session)
            
            logger.info(f"💬 Response: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ LLM Error: {str(e)}")
            # Fallback
            return self.generate_fallback_response(
                session_data.get("message_count", 1) if session_data else 1,
                is_scam_session
            )
    
    def _generate_tactical_context(self, session_data: Dict) -> str:
        """Generate tactical hints for SCAM MODE"""
        message_count = session_data.get("message_count", 0)
        intelligence = session_data.get("intelligence", {})
        
        has_upi = bool(intelligence.get("upiIds"))
        has_phone = bool(intelligence.get("phoneNumbers"))
        has_link = bool(intelligence.get("phishingLinks"))
        
        hints = []
        
        if message_count <= 3:
            hints.append("[PHASE 1: BUILD TRUST] Confused but eager. Ask basic questions.")
        elif message_count <= 6:
            hints.append("[PHASE 2: EXTRACT DATA] Use technical errors to get UPI/phone. Offer bribes.")
            if not has_upi:
                hints.append("[PRIORITY: GET UPI] Link doesn't work, need UPI ID directly.")
            if not has_phone:
                hints.append("[PRIORITY: GET PHONE] Ask for number for callback.")
        elif message_count <= 10:
            hints.append("[PHASE 3: VERIFICATION] Ask employee ID, branch name, manager details.")
        else:
            hints.append("[PHASE 4: MAXIMIZE DATA] Push for secondary UPIs, personal numbers.")
        
        return "\n".join(hints) if hints else ""
    
    def _clean_response(self, response: str, is_scam_mode: bool) -> str:
        """Clean response based on mode"""
        # Remove AI leakage
        ai_phrases = [
            "as an ai", "i'm an ai", "i cannot", "i'm not able to",
            "i don't have access", "i'm just a", "i'm programmed"
        ]
        
        response_lower = response.lower()
        for phrase in ai_phrases:
            if phrase in response_lower:
                logger.warning(f"⚠️ AI leaked, using fallback")
                if is_scam_mode:
                    return "Arre yaar, I'm confused. Can you explain simply?"
                else:
                    return "I'd be happy to help! Could you provide more details?"
        
        # Ensure reasonable length
        sentences = response.split('.')
        if len(sentences) > 4:
            response = '. '.join(sentences[:3]) + '.'
        
        # Add typos for scam mode (authenticity)
        if is_scam_mode:
            import random
            if random.random() < 0.1:
                response = self._add_natural_typo(response)
        
        return response.strip()
    
    def _add_natural_typo(self, text: str) -> str:
        """Add realistic typos for scam mode"""
        typos = {
            "received": "recieved",
            "tomorrow": "tomorow",
            "verification": "verfication"
        }
        
        for correct, typo in typos.items():
            if correct in text.lower():
                text = text.replace(correct, typo)
                break
        
        return text
    
    @staticmethod
    def generate_fallback_response(message_count: int, is_scam_mode: bool) -> str:
        """Fallback responses based on mode"""
        
        if is_scam_mode:
            # SCAM MODE fallbacks
            scam_fallbacks = {
                1: "What is this? Account blocked kyun? I didn't do anything",
                2: "Link showing security warning. Can you send UPI ID? I'll pay via PhonePe",
                3: "Trying to send but Invalid Recipient. You have different UPI? Personal one?",
                4: "Bhai, you're helping so much. I want to tip you 500. Personal UPI?",
                5: "My manager asking proof. What's your employee ID and branch name?",
                6: "Payment failing. Can I call you? What's your mobile number?",
                7: "I want to verify genuine. Give me head office number?",
                8: "You're patient. I'll give 5-star rating. What's your officer code?",
                9: "I have 15,000 ready. My CA wants branch GST number",
                10: "If I have issue later, can I contact you? Personal number?"
            }
            
            if message_count <= 10:
                return scam_fallbacks[message_count]
            else:
                return "You've been super helpful. You handle VIP customers? What's VIP helpline?"
        
        else:
            # NORMAL MODE fallbacks
            return "I'd be happy to help! For specific account issues, please contact your bank's official customer service helpline."

# Initialize singleton
agent_engine = AgentEngine()