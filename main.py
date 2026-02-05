# main.py
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
import logging
from datetime import datetime

# Corrected Imports
from config import config
from db import session_manager  # Importing the object, not the class
from engine import agent_engine
from intelligence import IntelligenceExtractor
from callback import callback_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Agentic Honey-Pot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class MessageData(BaseModel):
    sender: str
    text: str
    timestamp: int

class AnalyzeRequest(BaseModel):
    sessionId: str
    message: MessageData
    conversationHistory: List[Dict] = Field(default_factory=list)
    metadata: Optional[Dict] = None

class AnalyzeResponse(BaseModel):
    status: str
    reply: str

@app.get("/")
async def health_check():
    return {"status": "online", "model": config.MODEL_NAME}

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request_data: AnalyzeRequest, x_api_key: str = Header(None, alias="x-api-key")):
    if not x_api_key or x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_id = request_data.sessionId
    msg = request_data.message
    
    try:
        # 1. Session tracking
        session = session_manager.get_or_create(session_id)
        session_manager.increment_message_count(session_id)
        
        # 2. Extract intelligence
        intel = IntelligenceExtractor.extract(msg.text, request_data.conversationHistory)
        session_manager.update_intelligence(session_id, intel)
        
        # 3. AI Reply
        try:
            reply = agent_engine.generate_response(
                current_message=msg.model_dump(),
                conversation_history=request_data.conversationHistory,
                session_data=session
            )
        except Exception:
            reply = "I'm not sure I understand, can you explain?"

        # 4. Callback logic
        if callback_manager.should_trigger_callback(session, session["intelligence"], session["message_count"]):
            callback_manager.send_final_result(
                session_id=session_id,
                scam_detected=session["scam_detected"],
                total_messages=session["message_count"],
                extracted_intelligence=session["intelligence"],
                agent_notes="Automated extraction complete."
            )
            session_manager.mark_callback_sent(session_id)

        return AnalyzeResponse(status="success", reply=reply)

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)