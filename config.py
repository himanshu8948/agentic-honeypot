# config.py
import os
import sys
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Setup basic logging for config validation
logger = logging.getLogger(__name__)

class Config:
    """
    Centralized configuration management
    
    Reads from environment variables with sensible defaults.
    CRITICAL: Never hardcode sensitive keys in this file!
    """
    
    # ========================================================================
    # API Security
    # ========================================================================
    API_KEY = os.getenv("API_KEY", "himanshu_agentic_honeypot")
    PORT = int(os.getenv("PORT", 8000))
    
    # ========================================================================
    # LLM Configuration (Groq)
    # ========================================================================
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    MODEL_NAME = "llama-3.3-70b-versatile"  # Best Llama 3 model on Groq
    
    # ========================================================================
    # Callback Configuration
    # ========================================================================
    CALLBACK_URL = os.getenv(
        "CALLBACK_URL", 
        "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    )
    CALLBACK_TIMEOUT = int(os.getenv("CALLBACK_TIMEOUT", 22))
    
    # ========================================================================
    # Agent Behavior
    # ========================================================================
    MAX_MESSAGES_BEFORE_CALLBACK = int(os.getenv("MAX_MESSAGES_BEFORE_CALLBACK", 15))
    MIN_MESSAGES_BEFORE_CALLBACK = int(os.getenv("MIN_MESSAGES_BEFORE_CALLBACK", 5))
    
    # ========================================================================
    # Scam Detection Thresholds
    # ========================================================================
    SCAM_KEYWORD_THRESHOLD = 3
    CRITICAL_INTEL_WEIGHT = 10
    
    # ========================================================================
    # Validation (runs on import)
    # ========================================================================
    @classmethod
    def validate(cls):
        """
        Validate critical configuration values
        Warns if required keys are missing but doesn't crash
        """
        warnings = []
        
        # Check API Key
        if not cls.API_KEY or cls.API_KEY == "your_secret_api_key_here":
            warnings.append("⚠️  API_KEY not set or using default - please set in .env")
        
        # Check Groq API Key
        if not cls.GROQ_API_KEY:
            warnings.append("⚠️  GROQ_API_KEY not set - LLM responses will fail")
        
        # Check Callback URL
        if not cls.CALLBACK_URL or "example.com" in cls.CALLBACK_URL:
            warnings.append("⚠️  CALLBACK_URL not properly configured")
        
        # Log warnings
        if warnings:
            logger.warning("=" * 80)
            logger.warning("CONFIGURATION WARNINGS:")
            for warning in warnings:
                logger.warning(f"  {warning}")
            logger.warning("=" * 80)
        
        return len(warnings) == 0
    
    @classmethod
    def display(cls):
        """Display current configuration (hiding sensitive values)"""
        print("=" * 80)
        print("CURRENT CONFIGURATION:")
        print("=" * 80)
        print(f"  API_KEY: {'*' * 8}{cls.API_KEY[-4:] if cls.API_KEY else 'NOT SET'}")
        print(f"  PORT: {cls.PORT}")
        print(f"  GROQ_API_KEY: {'*' * 8}{cls.GROQ_API_KEY[-4:] if cls.GROQ_API_KEY else 'NOT SET'}")
        print(f"  MODEL_NAME: {cls.MODEL_NAME}")
        print(f"  CALLBACK_URL: {cls.CALLBACK_URL}")
        print(f"  CALLBACK_TIMEOUT: {cls.CALLBACK_TIMEOUT}s")
        print(f"  MAX_MESSAGES_BEFORE_CALLBACK: {cls.MAX_MESSAGES_BEFORE_CALLBACK}")
        print(f"  MIN_MESSAGES_BEFORE_CALLBACK: {cls.MIN_MESSAGES_BEFORE_CALLBACK}")
        print("=" * 80)

# ============================================================================
# CRITICAL: Export singleton instance (not the class)
# This allows imports like: from config import config
# ============================================================================
config = Config()

# Validate configuration on import
config.validate()

# Optional: Display config if running this file directly
if __name__ == "__main__":
    config.display()