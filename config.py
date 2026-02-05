# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Centralized configuration management"""
    
    # API Security
    API_KEY = os.getenv("API_KEY", "default_secret_key")
    PORT = int(os.getenv("PORT", 8000))
    
    # LLM Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    MODEL_NAME = "llama-3.3-70b-versatile"  # Best Llama 3 model on Groq
    
    # Callback Configuration
    CALLBACK_URL = os.getenv("CALLBACK_URL", "https://hackathon.guvi.in/api/updateHoneyPotFinalResult")
    CALLBACK_TIMEOUT = int(os.getenv("CALLBACK_TIMEOUT", 5))
    
    # Agent Behavior
    MAX_MESSAGES_BEFORE_CALLBACK = int(os.getenv("MAX_MESSAGES_BEFORE_CALLBACK", 15))
    MIN_MESSAGES_BEFORE_CALLBACK = int(os.getenv("MIN_MESSAGES_BEFORE_CALLBACK", 5))
    
    # Scam Detection Thresholds
    SCAM_KEYWORD_THRESHOLD = 3
    CRITICAL_INTEL_WEIGHT = 10  # UPI, bank accounts, phishing links

config = Config()