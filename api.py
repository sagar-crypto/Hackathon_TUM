# api.py
import os
import uvicorn
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
from get_data import fetch_ticketmaster_events, TicketmasterError
from db_client import fetch_social_events_by_name, DatabaseError

# Import the necessary components
from welness_agent import UserContext, HealthSnapshot
from wellness_orchestrator import run_orchestration

# Global dictionary to track session states
active_sessions = {}


# ---- Pydantic models (HTTP layer) ----

class HealthSnapshotIn(BaseModel):
    steps_today: Optional[int] = None
    sleep_hours_last_night: Optional[float] = None


class EventsQuery(BaseModel):
    lat: float          # device GPS latitude
    lon: float          # device GPS longitude
    radius_km: float = 20.0
    keyword: Optional[str] = None  # e.g. "social", "music", "fitness"
    size: int = 20


class StartSessionRequest(BaseModel):
    """The input payload from the frontend to kick off the agent run."""
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


# ---- FastAPI app ----

app = FastAPI(
    title="Wellness Agent Orchestration API",
    description="Triggers the LangGraph multi-agent workflow to prepare context for the Wellness Agent.",
    version="1.0.0"
)


# Helper function to run the full orchestration and session
async def run_full_workflow(req: StartSessionRequest, session_id: str):
    """
    Converts the API request into the internal UserContext and runs the LangGraph.
    """
    try:
        # Initialize session state
        active_sessions[session_id] = {
            "status": "running",
            "user_name": req.name,
            "ended": False,
            "reason": None
        }

        # Define callback for when session ends
        async def on_session_end(reason: str):
            print(f"\n📞 Session {session_id} ended: {reason}")
            from datetime import datetime
            active_sessions[session_id] = {
                "status": "ended",
                "user_name": req.name,
                "ended": True,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }

        # 1. Map Pydantic input -> internal UserContext dataclass
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

        print(f"\n🔄 Processing request for user: {req.name} (Session: {session_id})")

        # 2. Run the orchestration with callback
        from wellness_orchestrator import run_orchestration_with_callback
        await run_orchestration_with_callback(user_ctx, on_session_end)

        print(f"✓ Workflow completed for {req.name}\n")

    except Exception as e:
        print(f"❌ Error in workflow for {req.name}: {e}")
        from datetime import datetime
        active_sessions[session_id] = {
            "status": "error",
            "user_name": req.name,
            "ended": True,
            "reason": f"error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        import traceback
        traceback.print_exc()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Wellness Agent Orchestration API",
        "version": "1.0.0"
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
    """
    Starts the full multi-agent orchestration and the voice session in the background.
    Returns a session_id that can be used to check session status.

    Note: The voice session requires microphone/speaker access on the server.
    For production web/mobile apps, consider using WebSocket streaming instead.
    """

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
        message=f"Multi-agent context generation and voice session for {req.name} started. Use session_id to check status.",
        user_name=req.name,
        session_id=session_id
    )


@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Check the status of a voice session.
    Returns whether the session has ended and the reason.
    """
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
        "timestamp": session_info.get("timestamp")
    }


@app.get("/session/{session_id}/wait")
async def wait_for_session_end(session_id: str):
    """
    Long-polling endpoint that waits for the session to end.
    Returns immediately if session is already ended, otherwise waits.
    """
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    # Poll until session ends (with timeout)
    max_wait = 3600  # 1 hour max
    poll_interval = 1  # Check every second
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

    # Timeout
    return {
        "session_id": session_id,
        "ended": False,
        "status": "timeout",
        "message": "Wait timeout reached"
    }


@app.post("/start-context-and-session", response_model=SessionResponse)
async def start_context_and_session(
        req: StartSessionRequest,
        background_tasks: BackgroundTasks
):
    """
    Alias for start-session endpoint (backwards compatibility).
    """
    return await start_session(req, background_tasks)



@app.post("/events-near-me")
async def events_near_me(query: EventsQuery):
    """
    Return a list of events near the given lat/lon using Ticketmaster Discovery API.
    """
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
        # ticketmaster_client-specific error
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # generic fallback
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.post("/social-events")
async def social_events(query: SocialEventQuery):
    """
    Return all social_events rows matching the given event_name (partial match).
    """
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

    await run_full_workflow(test_request)


if __name__ == "__main__":
    import sys

    # Check if running in test mode
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Running in test mode...")
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(test_workflow())
    else:
        # Start the API server
        print("Starting Wellness Agent API server...")
        print("API will be available at: http://localhost:8000")
        print("API docs at: http://localhost:8000/docs")
        uvicorn.run(app, host="0.0.0.0", port=8000)
