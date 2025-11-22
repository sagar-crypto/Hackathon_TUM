# api.py - Updated with WebSocket support
import os
import uvicorn
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Set
import json
from get_data import fetch_ticketmaster_events, TicketmasterError
from db_client import fetch_social_events_by_name, DatabaseError
from datetime import datetime

# Import the necessary components
from welness_agent_live import UserContext, HealthSnapshot
from wellness_orchestrator_live import run_orchestration_with_callback

# Global dictionary to track session states
active_sessions: Dict[str, Dict] = {}
session_websockets: Dict[str, Set[WebSocket]] = {}


# ---- Pydantic models (HTTP layer) ----

class HealthSnapshotIn(BaseModel):
    steps_today: Optional[int] = None
    sleep_hours_last_night: Optional[float] = None


class EventsQuery(BaseModel):
    lat: float
    lon: float
    radius_km: float = 20.0
    keyword: Optional[str] = None
    size: int = 20


class StartSessionRequest(BaseModel):
    name: str
    mood: Optional[str] = None
    health: Optional[HealthSnapshotIn] = None
    conversation_summary: Optional[str] = None
    goals: Optional[str] = None


class SessionResponse(BaseModel):
    status: str
    message: str
    user_name: str
    session_id: Optional[str] = None


class SessionEndResponse(BaseModel):
    session_id: str
    user_name: str
    ended: bool
    reason: str
    timestamp: str


class SocialEventQuery(BaseModel):
    event_name: str


# ---- FastAPI app with CORS ----

app = FastAPI(
    title="Wellness Agent Orchestration API",
    description="Multi-agent wellness orchestration with WebSocket support",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- WebSocket Manager ----

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        print(f"[WS] Client connected to session {session_id}")

    async def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        print(f"[WS] Client disconnected from session {session_id}")

    async def broadcast(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"[WS] Broadcast error: {e}")
                    disconnected.add(connection)

            for connection in disconnected:
                await self.disconnect(session_id, connection)


manager = ConnectionManager()


# ---- Helper function to run the full workflow ----

async def run_full_workflow(req: StartSessionRequest, session_id: str):
    """Runs the orchestration and coordinates with WebSocket clients."""
    try:
        # Initialize session state
        active_sessions[session_id] = {
            "status": "running",
            "user_name": req.name,
            "ended": False,
            "reason": None,
            "started_at": datetime.now().isoformat()
        }

        # Broadcast to all connected clients
        await manager.broadcast(session_id, {
            "type": "session_started",
            "user_name": req.name,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })

        async def on_session_end(reason: str):
            """Callback when the session ends."""
            print(f"\n👋 Session {session_id} ended: {reason}")
            active_sessions[session_id] = {
                "status": "ended",
                "user_name": req.name,
                "ended": True,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }

            # Broadcast session end to all clients
            await manager.broadcast(session_id, {
                "type": "session_ended",
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            })

        # Convert Pydantic input to internal UserContext
        health_ctx = None
        if req.health is not None:
            health_ctx = HealthSnapshot(
                steps_today=req.health.steps_today,
                sleep_hours_last_night=req.health.sleep_hours_last_night,
            )

        user_ctx = UserContext(
            name=req.name,
            mood=req.mood,
            health=health_ctx,
            conversation_summary=req.conversation_summary,
            goals=req.goals,
        )

        print(f"\n📝 Processing request for user: {req.name} (Session: {session_id})")

        # Run the orchestration with callback
        from wellness_orchestrator_live import run_orchestration_with_callback
        await run_orchestration_with_callback(user_ctx, on_session_end)

        print(f"✅ Workflow completed for {req.name}\n")

    except Exception as e:
        print(f"❌ Error in workflow for {req.name}: {e}")
        import traceback
        traceback.print_exc()

        active_sessions[session_id] = {
            "status": "error",
            "user_name": req.name,
            "ended": True,
            "reason": f"error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

        await manager.broadcast(session_id, {
            "type": "session_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


# ---- REST Endpoints ----

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Wellness Agent Orchestration API",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    api_key = os.environ.get("GEMINI_API_KEY")
    return {
        "status": "healthy",
        "api_key_configured": bool(api_key)
    }


@app.post("/start-session", response_model=SessionResponse)
async def start_session(
        req: StartSessionRequest,
        background_tasks: BackgroundTasks
):
    """Starts the full multi-agent orchestration in the background."""

    # Validate API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured on server"
        )

    # Validate input
    if not req.name or len(req.name.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="User name is required"
        )

    # Generate session ID
    import uuid
    session_id = f"session_{uuid.uuid4().hex[:8]}"

    # Run the full workflow in the background
    background_tasks.add_task(run_full_workflow, req, session_id)

    return SessionResponse(
        status="processing_started",
        message=f"Session started. Connect via WebSocket or use /session/{session_id}/status to monitor.",
        user_name=req.name,
        session_id=session_id
    )


@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Check the status of a voice session."""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    session_info = active_sessions[session_id]

    return {
        "session_id": session_id,
        "user_name": session_info["user_name"],
        "status": session_info["status"],
        "ended": session_info["ended"],
        "reason": session_info.get("reason"),
        "timestamp": session_info.get("timestamp"),
        "started_at": session_info.get("started_at")
    }


@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(session_id: str, websocket: WebSocket):
    """WebSocket endpoint for real-time session updates."""

    # Validate session exists
    if session_id not in active_sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await manager.connect(session_id, websocket)

    # Send current session status
    session_info = active_sessions[session_id]
    await websocket.send_json({
        "type": "session_status",
        "status": session_info["status"],
        "ended": session_info["ended"],
        "user_name": session_info["user_name"]
    })

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()

            # Handle client messages (e.g., ping/pong)
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "get_status":
                session_info = active_sessions.get(session_id, {})
                await websocket.send_json({
                    "type": "session_status",
                    "status": session_info.get("status"),
                    "ended": session_info.get("ended")
                })

    except WebSocketDisconnect:
        await manager.disconnect(session_id, websocket)


@app.get("/session/{session_id}/wait")
async def wait_for_session_end(session_id: str):
    """Long-polling endpoint that waits for the session to end."""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    max_wait = 3600
    poll_interval = 1
    waited = 0

    while waited < max_wait:
        session_info = active_sessions[session_id]
        if session_info["ended"]:
            return {
                "session_id": session_id,
                "user_name": session_info["user_name"],
                "status": session_info["status"],
                "ended": True,
                "reason": session_info.get("reason"),
                "timestamp": session_info.get("timestamp")
            }

        await asyncio.sleep(poll_interval)
        waited += poll_interval

    return {
        "session_id": session_id,
        "ended": False,
        "status": "timeout"
    }


@app.post("/events-near-me")
async def events_near_me(query: EventsQuery):
    """Return events near given coordinates."""
    try:
        events = await fetch_ticketmaster_events(
            lat=query.lat,
            lon=query.lon,
            radius_km=query.radius_km,
            keyword=query.keyword,
            size=query.size,
        )
        return {"events": events, "count": len(events)}
    except TicketmasterError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/social-events")
async def social_events(query: SocialEventQuery):
    """Return social events matching the query."""
    try:
        events = fetch_social_events_by_name(query.event_name)
        return {"events": events, "count": len(events)}
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# ---- For local testing ----

async def test_workflow():
    """Test the workflow with sample data."""
    test_request = StartSessionRequest(
        name="Sagar",
        mood="a bit low on energy",
        health=HealthSnapshotIn(
            steps_today=2000,
            sleep_hours_last_night=5.0
        ),
        conversation_summary="They felt stressed about work and wanted to improve their sleep habits.",
        goals="sleep better and be more active"
    )

    await run_full_workflow(test_request, "test_session")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Running in test mode...")
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(test_workflow())
    else:
        print("Starting Wellness Agent API server...")
        print("API docs at: http://localhost:8000/docs")
        print("Frontend: Open wellness_frontend.html in your browser")
        uvicorn.run(app, host="0.0.0.0", port=8000)