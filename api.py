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
from mobile_audio_handler import mobile_session_manager, MobileAudioSession
import base64

# Import the necessary components
from welness_agent_live import UserContext, HealthSnapshot, WellnessAgentLive
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


class ChatUserContextIn(BaseModel):
    name: str
    mood: Optional[str] = None
    health: Optional[HealthSnapshotIn] = None
    conversation_summary: Optional[str] = None
    goals: Optional[str] = None


class WellnessChatRequest(BaseModel):
    message: str
    context: Optional[ChatUserContextIn] = None


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

@app.post("/wellness-chat")
async def wellness_chat(req: WellnessChatRequest):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    agent_live = WellnessAgentLive(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
    if agent_live is None:
        raise HTTPException(status_code=500, detail="Wellness agent not initialized")

    user_ctx: Optional[UserContext] = None
    if req.context is not None:
        health_ctx = None
        if req.context.health is not None:
            health_ctx = HealthSnapshot(
                steps_today=req.context.health.steps_today,
                sleep_hours_last_night=req.context.health.sleep_hours_last_night,
            )

        user_ctx = UserContext(
            name=req.context.name,
            mood=req.context.mood,
            health=health_ctx,
            conversation_summary=req.context.conversation_summary,
            goals=req.context.goals,
        )

    reply = await agent_live.chat(
        user_message=req.message,
        user_context=user_ctx,
    )

    return {"reply": reply}


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


@app.websocket("/ws/audio/{session_id}")
async def mobile_audio_websocket(session_id: str, websocket: WebSocket):
    """
    WebSocket endpoint for mobile audio streaming.

    Protocol:
    Client -> Server:
        - {"type": "audio", "data": "<base64_audio>"}  # Send audio chunk
        - {"type": "start_speaking"}  # User started speaking
        - {"type": "stop_speaking"}   # User stopped speaking
        - {"type": "end_session"}     # Request to end session

    Server -> Client:
        - {"type": "audio", "data": "<base64_audio>"}  # AI audio response
        - {"type": "agent_transcript", "text": "..."}  # AI's spoken text
        - {"type": "turn_complete"}                    # AI finished speaking
        - {"type": "live_analysis", ...}               # Real-time analysis
        - {"type": "session_ending", ...}              # Session is ending
        - {"type": "session_ended", ...}               # Session ended
        - {"type": "error", "message": "..."}          # Error occurred
    """

    # Validate session exists
    if session_id not in active_sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    print(f"[Mobile Audio] Client connected to session {session_id}")

    session_info = active_sessions[session_id]
    audio_session: Optional[MobileAudioSession] = None

    try:
        # Wait for initial configuration from client
        data = await websocket.receive_json()

        if data.get("type") != "start_audio_session":
            await websocket.close(code=4000, reason="Expected start_audio_session message")
            return

        # Get system prompt and context from the completed orchestration
        # These should have been generated during the initial /start-session call
        system_prompt = session_info.get('system_prompt', WELLNESS_SYSTEM_PROMPT)
        initial_context = session_info.get('initial_context', '')

        # Create user context for audio session
        user_context = {
            'name': session_info['user_name'],
            'health_data': session_info.get('health_data', {})
        }

        # Get API key
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            await websocket.send_json({
                "type": "error",
                "message": "Server API key not configured"
            })
            await websocket.close()
            return

        # Create and start audio session
        audio_session = await mobile_session_manager.create_session(
            session_id=session_id,
            user_context=user_context,
            api_key=api_key,
            websocket=websocket,
            initial_system_prompt=system_prompt,
            initial_context=initial_context
        )

        # Send confirmation
        await websocket.send_json({
            "type": "audio_session_started",
            "session_id": session_id
        })

        # Handle incoming messages from client
        while audio_session.is_active:
            try:
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=0.1
                )

                # Handle different message types
                if message['type'] == 'websocket.receive':
                    if 'text' in message:
                        data = json.loads(message['text'])

                        if data['type'] == 'audio':
                            # Decode base64 audio and send to Gemini
                            audio_bytes = base64.b64decode(data['data'])
                            await audio_session.process_audio_from_client(audio_bytes)

                        elif data['type'] == 'end_session':
                            print(f"[Mobile Audio] Client requested session end")
                            await audio_session.end_session("client_requested")
                            break

                        elif data['type'] == 'user_transcript':
                            # Client is sending their own transcript
                            if audio_session.live_coordinator:
                                await audio_session.live_coordinator.add_transcript(
                                    "user",
                                    data.get('text', '')
                                )

                elif message['type'] == 'websocket.disconnect':
                    print(f"[Mobile Audio] Client disconnected")
                    break

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[Mobile Audio] Error receiving message: {e}")
                break

    except Exception as e:
        print(f"[Mobile Audio] Session error: {e}")
        import traceback
        traceback.print_exc()

        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

    finally:
        print(f"[Mobile Audio] Cleaning up session {session_id}")

        # Clean up audio session
        if audio_session:
            await audio_session.end_session("connection_closed")

        # Update session state
        if session_id in active_sessions:
            active_sessions[session_id].update({
                "status": "ended",
                "ended": True,
                "ended_at": datetime.now().isoformat()
            })

        try:
            await websocket.close()
        except:
            pass


# Modified start-session endpoint to prepare for mobile audio
@app.post("/start-session-mobile", response_model=SessionResponse)
async def start_session_mobile(
        req: StartSessionRequest,
        background_tasks: BackgroundTasks
):
    """
    Starts the orchestration for mobile clients.
    After this completes, client should connect to /ws/audio/{session_id}
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

    # Run initial orchestration to get context
    background_tasks.add_task(run_mobile_orchestration, req, session_id)

    return SessionResponse(
        status="orchestration_started",
        message=f"Initial analysis started. Wait for 'orchestration_complete' status, then connect to /ws/audio/{session_id}",
        user_name=req.name,
        session_id=session_id
    )


async def run_mobile_orchestration(req: StartSessionRequest, session_id: str):
    """
    Run the initial orchestration without starting voice session.
    Prepares the session for mobile audio streaming.
    """
    try:
        start_time = datetime.now()

        # Initialize session state
        active_sessions[session_id] = {
            "status": "orchestrating",
            "user_name": req.name,
            "ended": False,
            "reason": None,
            "started_at": start_time.isoformat(),
            "ended_at": None,
            "duration_seconds": None,
            "health_data": {
                "steps_today": req.health.steps_today if req.health else 0,
                "sleep_hours_last_night": req.health.sleep_hours_last_night if req.health else 0.0,
            }
        }

        # Broadcast orchestration started
        await manager.broadcast(session_id, {
            "type": "orchestration_started",
            "user_name": req.name,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })

        # Run initial agent orchestration
        from agents import SentimentAgent, SocialAgent, HealthAgent, AgentState, generate_final_prompt
        from wellness_orchestrator_live import app as graph_app

        initial_state = AgentState(
            messages=[],
            user_name=req.name,
            initial_mood=req.mood or "neutral",
            initial_health_data={
                "steps_today": req.health.steps_today if req.health else 0,
                "sleep_hours_last_night": req.health.sleep_hours_last_night if req.health else 0.0,
            },
            mood_score=5,
            mood_analysis="",
            social_suggestion="",
            health_score=50,
            health_suggestion="",
            final_context_prompt="",
        )

        print(f"[Mobile Session {session_id}] Running initial orchestration...")
        final_state = await graph_app.ainvoke(initial_state, config={"recursion_limit": 10})

        # Store results in session
        final_prompt = final_state.get('final_context_prompt', '')

        active_sessions[session_id].update({
            "status": "orchestration_complete",
            "system_prompt": WELLNESS_SYSTEM_PROMPT,
            "initial_context": final_prompt,
            "mood_score": final_state.get('mood_score'),
            "health_score": final_state.get('health_score'),
            "mood_analysis": final_state.get('mood_analysis'),
            "social_suggestion": final_state.get('social_suggestion'),
            "health_suggestion": final_state.get('health_suggestion')
        })

        # Notify client that orchestration is complete
        await manager.broadcast(session_id, {
            "type": "orchestration_complete",
            "session_id": session_id,
            "message": "Ready for audio streaming. Connect to /ws/audio/{session_id}",
            "timestamp": datetime.now().isoformat(),
            "initial_analysis": {
                "mood_score": final_state.get('mood_score'),
                "health_score": final_state.get('health_score')
            }
        })

        print(f"[Mobile Session {session_id}] Orchestration complete, ready for audio")

    except Exception as e:
        print(f"[Mobile Session {session_id}] Orchestration error: {e}")
        import traceback
        traceback.print_exc()

        active_sessions[session_id].update({
            "status": "error",
            "ended": True,
            "reason": f"orchestration_error: {str(e)}",
            "error_details": str(e)
        })

        await manager.broadcast(session_id, {
            "type": "orchestration_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


# Add endpoint to check if session is ready for audio
@app.get("/session/{session_id}/ready")
async def check_audio_ready(session_id: str):
    """Check if session orchestration is complete and ready for audio streaming."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session_info = active_sessions[session_id]
    status = session_info.get("status")

    return {
        "session_id": session_id,
        "status": status,
        "ready": status == "orchestration_complete",
        "initial_analysis": {
            "mood_score": session_info.get("mood_score"),
            "health_score": session_info.get("health_score"),
            "mood_analysis": session_info.get("mood_analysis"),
            "social_suggestion": session_info.get("social_suggestion"),
            "health_suggestion": session_info.get("health_suggestion")
        } if status == "orchestration_complete" else None
    }

# Add this to your api.py

# Update the run_full_workflow function to store more detailed end information
async def run_full_workflow(req: StartSessionRequest, session_id: str):
    """Runs the orchestration and coordinates with WebSocket clients."""
    try:
        # Initialize session state
        active_sessions[session_id] = {
            "status": "running",
            "user_name": req.name,
            "ended": False,
            "reason": None,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "duration_seconds": None
        }

        start_time = datetime.now()

        # Broadcast to all connected clients
        await manager.broadcast(session_id, {
            "type": "session_started",
            "user_name": req.name,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })

        async def on_session_end(reason: str):
            """Callback when the session ends."""
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print(f"\n👋 Session {session_id} ended: {reason}")

            session_data = {
                "status": "ended",
                "user_name": req.name,
                "ended": True,
                "reason": reason,
                "timestamp": end_time.isoformat(),
                "started_at": start_time.isoformat(),
                "ended_at": end_time.isoformat(),
                "duration_seconds": duration
            }

            active_sessions[session_id] = session_data

            # Broadcast session end to all clients with full details
            await manager.broadcast(session_id, {
                "type": "session_ended",
                "reason": reason,
                "timestamp": end_time.isoformat(),
                "duration_seconds": duration,
                "session_data": session_data
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
            "timestamp": datetime.now().isoformat(),
            "error_details": str(e)
        }

        await manager.broadcast(session_id, {
            "type": "session_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


# Enhanced status endpoint with more details
@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Check the status of a voice session with full details."""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    session_info = active_sessions[session_id]

    response = {
        "session_id": session_id,
        "user_name": session_info["user_name"],
        "status": session_info["status"],
        "ended": session_info["ended"],
        "started_at": session_info.get("started_at")
    }

    # Add end details if session has ended
    if session_info["ended"]:
        response.update({
            "reason": session_info.get("reason"),
            "ended_at": session_info.get("ended_at"),
            "timestamp": session_info.get("timestamp"),
            "duration_seconds": session_info.get("duration_seconds"),
        })

    # Add error details if present
    if "error_details" in session_info:
        response["error_details"] = session_info["error_details"]

    return response


# New endpoint: Wait for session end with full details
@app.get("/session/{session_id}/result")
async def wait_for_session_result(session_id: str):
    """
    Long-polling endpoint that waits for the session to end and returns complete results.
    This is useful for clients that want to get the final outcome without WebSockets.
    """
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    max_wait = 3600  # 1 hour max
    poll_interval = 0.5
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
                "started_at": session_info.get("started_at"),
                "ended_at": session_info.get("ended_at"),
                "timestamp": session_info.get("timestamp"),
                "duration_seconds": session_info.get("duration_seconds"),
                "error_details": session_info.get("error_details")
            }

        await asyncio.sleep(poll_interval)
        waited += poll_interval

    # Timeout reached
    return {
        "session_id": session_id,
        "ended": False,
        "status": "timeout",
        "waited_seconds": waited
    }


# Enhanced WebSocket endpoint with better messaging
@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(session_id: str, websocket: WebSocket):
    """WebSocket endpoint for real-time session updates with full details."""

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
        "user_name": session_info["user_name"],
        "started_at": session_info.get("started_at")
    })

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()

            # Handle client messages
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "get_status":
                session_info = active_sessions.get(session_id, {})
                response = {
                    "type": "session_status",
                    "status": session_info.get("status"),
                    "ended": session_info.get("ended")
                }

                # Include end details if available
                if session_info.get("ended"):
                    response.update({
                        "reason": session_info.get("reason"),
                        "ended_at": session_info.get("ended_at"),
                        "duration_seconds": session_info.get("duration_seconds")
                    })

                await websocket.send_json(response)

    except WebSocketDisconnect:
        await manager.disconnect(session_id, websocket)

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
