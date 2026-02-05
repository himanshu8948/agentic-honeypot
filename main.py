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
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
import logging
from datetime import datetime

# Import your custom modules
from config import config
from db import session_manager  # FIXED: Import the instance, not the class
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

# CORS Configuration (allow GUVI platform to call your API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to GUVI domains
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
    
    @field_validator('sender')
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
    """
    CRITICAL: This MUST match GUVI platform's exact request format
    Reference: Problem Statement Section 6
    """
    sessionId: str
    message: MessageData
    conversationHistory: List[Dict] = Field(default_factory=list)
    metadata: Optional[Metadata] = None
    
    model_config = {  # FIXED: Updated for Pydantic v2
        "json_schema_extra": {
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
    }

class AnalyzeResponse(BaseModel):
    """
    CRITICAL: This MUST match GUVI platform's exact response format
    Reference: Problem Statement Section 8
    """
    status: str  # Must be "success"
    reply: str   # Agent's response
    
    model_config = {  # FIXED: Updated for Pydantic v2
        "json_schema_extra": {
            "example": {
                "status": "success",
                "reply": "Why is my account being suspended?"
            }
        }
    }

# ============================================================================
# HEALTH CHECK ENDPOINT (TESTER REQUIREMENT)
# ============================================================================

@app.get("/")
async def health_check():
    """
    CRITICAL: Endpoint tester checks if API is online
    Must return clear online status
    """
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
# MAIN ANALYSIS ENDPOINT (EXACT PATH: /analyze)
# ============================================================================

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request_data: AnalyzeRequest,
    x_api_key: str = Header(None, alias="x-api-key")
):
    """
    CRITICAL ENDPOINT: This is what GUVI platform calls
    
    Compliance Requirements:
    - Rule 4: x-api-key authentication
    - Rule 6: Handle conversationHistory correctly
    - Rule 7: Generate adaptive agent responses
    - Rule 8: Return exact format {"status": "success", "reply": "..."}
    - Rule 12: Trigger callback when conditions met
    
    Args:
        request_data: Request body matching GUVI schema
        x_api_key: API key from header
    
    Returns:
        AnalyzeResponse with status and reply
    """
    
    # ========================================================================
    # RULE 4: AUTHENTICATION (CRITICAL - INSTANT FAIL IF WRONG)
    # ========================================================================
    if not x_api_key:
        logger.warning("❌ Missing API key in request")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing x-api-key header"
        )
    
    if x_api_key != config.API_KEY:
        logger.warning(f"❌ Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid API key"
        )
    
    # Extract request data
    session_id = request_data.sessionId
    message = request_data.message
    history = request_data.conversationHistory
    metadata = request_data.metadata
    
    logger.info(f"📨 INCOMING REQUEST - Session: {session_id}")
    logger.info(f"   Message: {message.text[:100]}...")
    logger.info(f"   History length: {len(history)}")
    
    try:
        # ====================================================================
        # SESSION MANAGEMENT
        # ====================================================================
        session = session_manager.get_or_create(session_id)
        session_manager.increment_message_count(session_id)
        
        # ====================================================================
        # INTELLIGENCE EXTRACTION (Rule 2)
        # ====================================================================
        intelligence = IntelligenceExtractor.extract(message.text, history)
        session_manager.update_intelligence(session_id, intelligence)
        
        # Calculate scam score
        scam_score = IntelligenceExtractor.calculate_scam_score(
            session["intelligence"]
        )
        
        logger.info(f"🔍 Intelligence extracted - Score: {scam_score}/100")
        logger.debug(f"   Intel: {intelligence}")
        
        # ====================================================================
        # SCAM DETECTION
        # ====================================================================
        if IntelligenceExtractor.is_scam(session["intelligence"]):
            session_manager.mark_scam_detected(session_id, scam_score)
            logger.warning(f"🚨 SCAM CONFIRMED - Session: {session_id}")
        
        # ====================================================================
        # AGENT RESPONSE GENERATION (Rule 7)
        # ====================================================================
        try:
            agent_reply = agent_engine.generate_response(
                current_message=message.model_dump(),  # FIXED: model_dump() for Pydantic v2
                conversation_history=history,
                session_data=session
            )
            logger.info(f"💬 Agent response: {agent_reply}")
            
        except Exception as llm_error:
            logger.error(f"❌ LLM error: {str(llm_error)}")
            # Fallback to rule-based response
            agent_reply = agent_engine.generate_fallback_response(
                session["message_count"]
            )
            logger.info(f"🔄 Using fallback response: {agent_reply}")
        
        # ====================================================================
        # CALLBACK TRIGGER CHECK (Rule 12 - CRITICAL)
        # ====================================================================
        if callback_manager.should_trigger_callback(
            session_data=session,
            intelligence=session["intelligence"],
            message_count=session["message_count"]
        ):
            logger.info(f"🎯 CALLBACK TRIGGER CONDITIONS MET - Session: {session_id}")
            
            # Generate agent notes
            agent_notes = callback_manager.generate_agent_notes(
                conversation_history=history,
                intelligence=session["intelligence"],
                scam_score=scam_score
            )
            
            # Send mandatory callback
            callback_success = callback_manager.send_final_result(
                session_id=session_id,
                scam_detected=session["scam_detected"],
                total_messages=session["message_count"],
                extracted_intelligence=session["intelligence"],
                agent_notes=agent_notes
            )
            
            if callback_success:
                session_manager.mark_callback_sent(session_id)
                logger.info(f"✅ CALLBACK SENT SUCCESSFULLY - Session: {session_id}")
            else:
                logger.error(f"❌ CALLBACK FAILED - Session: {session_id}")
        
        # ====================================================================
        # RULE 8: RETURN EXACT RESPONSE FORMAT (CRITICAL)
        # ====================================================================
        response = AnalyzeResponse(
            status="success",
            reply=agent_reply
        )
        
        logger.info(f"✅ REQUEST COMPLETED - Session: {session_id}")
        return response
    
    except KeyError as e:
        logger.error(f"💥 Missing required field: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Bad Request: Missing required field {str(e)}"
        )
    
    except ValueError as e:
        logger.error(f"💥 Invalid value: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Bad Request: Invalid value {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

# ============================================================================
# ADDITIONAL UTILITY ENDPOINTS
# ============================================================================

@app.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    x_api_key: str = Header(None, alias="x-api-key")
):
    """Get session details (for debugging)"""
    if x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert datetime to string for JSON serialization
    if "created_at" in session:
        session["created_at"] = session["created_at"].isoformat()
    
    return session

@app.get("/sessions")
async def list_sessions(
    x_api_key: str = Header(None, alias="x-api-key")
):
    """List all active sessions (for debugging)"""
    if x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "total_sessions": len(session_manager.sessions),
        "sessions": list(session_manager.sessions.keys())
    }

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"💥 Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": "Internal server error"}
    )

# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 80)
    logger.info("🚀 AGENTIC HONEY-POT API STARTING")
    logger.info("=" * 80)
    logger.info(f"   Model: {config.MODEL_NAME}")
    logger.info(f"   API Key configured: {'Yes' if config.API_KEY else 'No'}")
    logger.info(f"   Groq API configured: {'Yes' if config.GROQ_API_KEY else 'No'}")
    logger.info(f"   Callback URL: {config.CALLBACK_URL}")
    logger.info("=" * 80)

@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information"""
    logger.info("🛑 AGENTIC HONEY-POT API SHUTTING DOWN")
    logger.info(f"   Total sessions handled: {len(session_manager.sessions)}")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Agentic Honey-Pot API")
    logger.info(f"   Port: {config.PORT}")
    logger.info(f"   Model: {config.MODEL_NAME}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.PORT,
        reload=False,  # Set to True for development
        log_level="info",
        access_log=True
    )