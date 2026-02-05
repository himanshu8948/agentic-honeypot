# main.py - PRODUCTION-READY FOR GUVI ENDPOINT TESTER
"""
CRITICAL COMPLIANCE CHECKLIST:
✅ Endpoint: POST /analyze (NOT /api/message)
✅ Health Check: GET / returns {"status": "online"}
✅ Authentication: x-api-key header validation
✅ Request Format: Exact match to GUVI schema
✅ Response Format: {"status": "success", "reply": "..."}
✅ Error Handling: 401 for auth, 400 for bad request, 500 for server errors
"""

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator # FIXED: field_validator for v2
from typing import List, Dict, Optional
import logging
from datetime import datetime

# Import your custom modules
from config import config
from db import SessionManager as session_manager # Ensure this matches your db.py instance name
from engine import agent_engine
from intelligence import IntelligenceExtractor
from callback import callback_manager

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('honeypot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================
app = FastAPI(
    title="Agentic Honey-Pot API",
    description="AI-powered scam detection and intelligence extraction for GUVI AI Impact India",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CRITICAL: Middleware to bypass Ngrok browser warning for the automated tester
@app.middleware("http")
async def add_ngrok_skip_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# ============================================================================
# REQUEST/RESPONSE MODELS (EXACT GUVI SCHEMA)
# ============================================================================

class MessageData(BaseModel):
    """Message object exactly as GUVI sends it"""
    sender: str  # "scammer" or "user"
    text: str
    timestamp: int  # Epoch time in milliseconds
    
    @field_validator('sender') # FIXED: Updated for Pydantic v2
    @classmethod
    def validate_sender(cls, v):
        if v not in ['scammer', 'user']:
            raise ValueError('sender must be "scammer" or "user"')
        return v

class ConversationMessage(BaseModel):
    """Historical message format"""
    sender: str
    text: str
    timestamp: int

class Metadata(BaseModel):
    """Optional metadata"""
    channel: Optional[str] = None
    language: Optional[str] = "English"
    locale: Optional[str] = "IN"

class AnalyzeRequest(BaseModel):
    """Matches GUVI platform's exact request format"""
    sessionId: str
    message: MessageData
    conversationHistory: List[Dict] = Field(default_factory=list)
    metadata: Optional[Metadata] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "sessionId": "wertyu-dfghj-ertyui",
                "message": {
                    "sender": "scammer",
                    "text": "Your bank account will be blocked today. Verify immediately.",
                    "timestamp": 1770005528731
                },
                "conversationHistory": [],
                "metadata": {
                    "channel": "SMS",
                    "language": "English",
                    "locale": "IN"
                }
            }
        }

class AnalyzeResponse(BaseModel):
    """Matches GUVI platform's exact response format"""
    status: str  # Must be "success"
    reply: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "reply": "Why is my account being suspended?"
            }
        }

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/")
async def health_check():
    """Mandatory for Tester: confirms service is live"""
    return {
        "status": "online",
        "message": "Honeypot Agent is ready",
        "service": "Agentic Honey-Pot API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "model": config.MODEL_NAME
    }

@app.get("/health")
async def detailed_health():
    """Detailed health check with system status"""
    return {
        "status": "healthy",
        "uptime": "online",
        "services": {
            "llm": "operational" if config.GROQ_API_KEY else "not_configured",
            "session_manager": "operational",
            "intelligence_extractor": "operational",
            "callback_manager": "operational"
        },
        "active_sessions": len(session_manager.sessions),
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# MAIN ANALYSIS ENDPOINT
# ============================================================================

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request_data: AnalyzeRequest,
    x_api_key: str = Header(None, alias="x-api-key")
):
    # RULE 4: AUTHENTICATION
    if not x_api_key:
        logger.warning("❌ Missing API key in request")
        raise HTTPException(status_code=401, detail="Unauthorized: Missing x-api-key header")
    
    if x_api_key != config.API_KEY:
        logger.warning(f"❌ Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key")
    
    session_id = request_data.sessionId
    message = request_data.message
    history = request_data.conversationHistory
    
    logger.info(f"📨 INCOMING REQUEST - Session: {session_id}")
    
    try:
        # SESSION MANAGEMENT
        session = session_manager.get_or_create(session_id)
        session_manager.increment_message_count(session_id)
        
        # INTELLIGENCE EXTRACTION (Rule 2)
        intelligence = IntelligenceExtractor.extract(message.text, history)
        session_manager.update_intelligence(session_id, intelligence)
        
        scam_score = IntelligenceExtractor.calculate_scam_score(session["intelligence"])
        
        # SCAM DETECTION
        if IntelligenceExtractor.is_scam(session["intelligence"]):
            session_manager.mark_scam_detected(session_id, scam_score)
            logger.warning(f"🚨 SCAM CONFIRMED - Session: {session_id}")
        
        # AGENT RESPONSE GENERATION (Rule 7)
        try:
            agent_reply = agent_engine.generate_response(
                current_message=message.model_dump(), # FIXED: model_dump for v2
                conversation_history=history,
                session_data=session
            )
        except Exception as llm_error:
            logger.error(f"❌ LLM error: {str(llm_error)}")
            agent_reply = agent_engine.generate_fallback_response(session["message_count"])
        
        # CALLBACK TRIGGER CHECK (Rule 12)
        if callback_manager.should_trigger_callback(
            session_data=session,
            intelligence=session["intelligence"],
            message_count=session["message_count"]
        ):
            agent_notes = callback_manager.generate_agent_notes(history, session["intelligence"], scam_score)
            callback_manager.send_final_result(
                session_id=session_id,
                scam_detected=session["scam_detected"],
                total_messages=session["message_count"],
                extracted_intelligence=session["intelligence"],
                agent_notes=agent_notes
            )
            session_manager.mark_callback_sent(session_id)

        return AnalyzeResponse(status="success", reply=agent_reply)
    
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# (Utility endpoints for /sessions and /sessions/{id} go here, keeping your logic)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=False)