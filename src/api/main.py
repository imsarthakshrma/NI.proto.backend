"""
Native IQ REST API - Backend for Frontend UI
Connects your existing bot system to your web frontend
"""

# import os
import sys
# import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add project paths
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in [str(SRC), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import your existing bot system
from integration.telegram.hybrid_native_bot import HybridNativeAI

# Import API routes
from api.memory_api import router as memory_router
from api.auth_api import router as auth_router
from api.group_chat_api import router as group_chat_router

app = FastAPI(
    title="Native IQ API",
    description="Backend API for Native IQ Frontend",
    version="0.1.0-beta"
)

# Include API routes
app.include_router(memory_router)
app.include_router(auth_router)
app.include_router(group_chat_router)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # configure for your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your existing bot system
native_bot = HybridNativeAI()

# Pydantic models for API
class ChatMessage(BaseModel):
    content: str
    user_id: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    requires_permission: bool = False
    pending_action: Optional[Dict[str, Any]] = None
    timestamp: str

class DashboardData(BaseModel):
    opportunities: List[Dict[str, Any]]
    contacts: Dict[str, Any]
    recent_actions: List[Dict[str, Any]]
    conversation_history: List[Dict[str, Any]]

class UserApproval(BaseModel):
    user_id: str
    approved: bool
    action_token: Optional[str] = None

# WebSocket connections for real-time chat
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Native IQ API is running", "version": "0.1.0-beta"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """
    Main chat endpoint - connects to your existing bot system
    """
    try:
        # Use your existing bot system
        response = await native_bot.process_message(
            user_id=message.user_id,
            message=message.content,
            context={"source": "web_frontend", "session_id": message.session_id}
        )
        
        # Check if permission is required
        requires_permission = False
        pending_action = None
        
        if message.user_id in native_bot.pending_actions:
            requires_permission = True
            pending_action = native_bot.pending_actions[message.user_id]
        
        return ChatResponse(
            response=response,
            requires_permission=requires_permission,
            pending_action=pending_action,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

@app.post("/api/approve")
async def approve_action(approval: UserApproval):
    """
    Handle user approval/denial of pending actions
    """
    try:
        if approval.approved:
            # Simulate "Yes" response to trigger your existing approval logic
            response = await native_bot.process_message(
                user_id=approval.user_id,
                message="Yes",
                context={"source": "web_frontend", "approval": True}
            )
        else:
            # Simulate "No" response
            response = await native_bot.process_message(
                user_id=approval.user_id,
                message="No",
                context={"source": "web_frontend", "approval": False}
            )
        
        return {"status": "success", "response": response}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval processing error: {str(e)}")

@app.get("/api/dashboard/{user_id}", response_model=DashboardData)
async def get_dashboard_data(user_id: str):
    """
    Get dashboard data for user - observations, contacts, history
    """
    try:
        # Get data from your existing session context
        session_data = native_bot.session_context.get(user_id, {})
        
        # Extract opportunities (extend this based on your observation logic)
        opportunities = []
        if "last_meeting" in session_data:
            opportunities.append({
                "type": "meeting_scheduled",
                "description": f"Meeting: {session_data['last_meeting'].get('title', 'Untitled')}",
                "timestamp": session_data['last_meeting'].get('timestamp', ''),
                "status": "completed"
            })
        
        if "last_email_status" in session_data:
            opportunities.append({
                "type": "email_sent",
                "description": f"Email: {session_data['last_email_status'].get('subject', 'Untitled')}",
                "timestamp": session_data['last_email_status'].get('timestamp', ''),
                "status": "completed"
            })
        
        # Get contacts
        contacts = session_data.get("contacts", {})
        
        # Get recent actions (you can extend this)
        recent_actions = []
        
        # Load conversation history from your existing JSON file
        conversation_history = []
        try:
            history_file = ROOT / "data" / "conversation_memory.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    if user_id in data:
                        conversation_history = data[user_id].get("messages", [])[-10:]  # Last 10 messages
        except Exception:
            pass  # Graceful fallback
        
        return DashboardData(
            opportunities=opportunities,
            contacts=contacts,
            recent_actions=recent_actions,
            conversation_history=conversation_history
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard data error: {str(e)}")

@app.get("/api/contacts/{user_id}")
async def get_contacts(user_id: str):
    """
    Get user's contact list
    """
    try:
        session_data = native_bot.session_context.get(user_id, {})
        contacts = session_data.get("contacts", {})
        return {"contacts": contacts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contacts error: {str(e)}")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket for real-time chat updates
    """
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Listen for messages from frontend
            data = await websocket.receive_json()
            
            # Process through your bot system
            response = await native_bot.process_message(
                user_id=user_id,
                message=data.get("message", ""),
                context={"source": "websocket"}
            )
            
            # Send response back
            await manager.send_message(user_id, {
                "type": "chat_response",
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_status": "active" if native_bot else "inactive"
    }

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
