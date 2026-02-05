# engine.py
import logging
from typing import List, Dict
from groq import Groq
from config import config

logger = logging.getLogger(__name__)

class AgentEngine:
    """
    Handles Rule 7: Agent Behavior.
    Uses Llama 3 via Groq for natural, adaptive responses.
    """
    
    SYSTEM_PROMPT = """You are a regular Indian person who has received a suspicious message. You are cautious but curious.

CRITICAL RULES:
1. **Stay in character**: You are NOT an AI. You are a real person named Raj or Priya.
2. **Be naturally suspicious**: Ask questions a real person would ask when something feels off.
3. **Never reveal you're a honeypot**: The scammer must believe you're a potential victim.
4. **Engage strategically**: Extract info (bank details, UPI IDs, links) by seeming interested but cautious.
5. **Use natural Indian English**: Mix of formal and casual, occasional typos are okay (e.g., "yaar", "wait what?").
6. **Show emotions**: Confusion, worry, skepticism.
7. **Ask clarifying questions**: "Which bank?", "What is your employee ID?", "Can you call me instead?"
8. **Stall for time**: "I'm at work right now", "Let me check with my bank first".

RESPONSE STYLE:
- Keep responses SHORT (1-3 sentences).
- Use questions to keep them talking.
- Mix proper grammar with casual chat style."""

    def __init__(self):
        if not config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in environment variables")
        
        self.client = Groq(api_key=config.GROQ_API_KEY)
        logger.info(f"✅ AgentEngine initialized with model: {config.MODEL_NAME}")
    
    def generate_response(
        self,
        current_message: Dict,
        conversation_history: List[Dict],
        session_data: Dict = None
    ) -> str:
        try:
            # Build conversation context
            sys_msg = self.SYSTEM_PROMPT
            
            # Context injection based on Rule 7 (adaptation)
            if session_data:
                count = session_data.get("message_count", 0)
                if count >= 8:
                    sys_msg += "\n\nCONTEXT: You've been talking for a while. Start pushing harder for specific details like UPI IDs or express strong skepticism to see how they react."

            messages = [{"role": "system", "content": sys_msg}]
            
            # Map history to LLM roles correctly
            for msg in conversation_history:
                # In a honeypot, the AGENT (user) is the 'assistant'
                # and the SCAMMER is the 'user'
                role = "assistant" if msg.get("sender") == "user" else "user"
                messages.append({"role": role, "content": msg.get("text", "")})
            
            # Add the final incoming scammer message
            messages.append({"role": "user", "content": current_message.get("text", "")})
            
            completion = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages,
                temperature=0.8,
                max_tokens=150,
                top_p=0.9
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Groq Error: {str(e)}")
            count = session_data.get("message_count", 1) if session_data else 1
            return self.generate_fallback_response(count)
    
    @staticmethod
    def generate_fallback_response(message_count: int) -> str:
        fallbacks = {
            1: "Wait, why will my account be blocked? I just used it yesterday.",
            2: "Which bank branch is this? I will go there directly.",
            3: "Can you send me your employee ID or an official email first?",
            4: "I'm travelling right now, network is bad. Can you send the link again?",
            5: "I am really confused. Is there any other way to verify this?"
        }
        return fallbacks.get(min(message_count, 5), "I need to check this with my family first.")

agent_engine = AgentEngine()