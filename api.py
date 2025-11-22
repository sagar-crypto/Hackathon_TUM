# api.py
import os
import asyncio
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from welness_agent import WellnessAgent, UserContext, HealthSnapshot  # import from your existing file

# ---- Pydantic models (HTTP layer) ----

class HealthSnapshotIn(BaseModel):
    steps_today: Optional[int] = None
    sleep_hours_last_night: Optional[float] = None

class StartSessionRequest(BaseModel):
    name: str
    mood: Optional[str] = None
    health: Optional[HealthSnapshotIn] = None
    conversation_summary: Optional[str] = None
    goals: Optional[str] = None

# ---- FastAPI app ----

app = FastAPI(title="Wellness Agent API")

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("WARNING: GEMINI_API_KEY is not set. Remember to export it before running the server.")

# Create a single global agent instance
agent = WellnessAgent(api_key=API_KEY) if API_KEY else None

# Helper to start session as a background task
async def run_voice_session(ctx: UserContext):
    if agent is None:
        print("WellnessAgent is not initialized (missing API key).")
        return
    await agent.start_voice_session(user_context=ctx)

@app.post("/start-session")
async def start_session(req: StartSessionRequest, background_tasks: BackgroundTasks):
    """
    Start a wellness voice session based on dynamic context (health + history).
    The audio will run on the backend machine (mic+speakers).
    """
    if agent is None:
        return {"status": "error", "message": "Server not configured with GEMINI_API_KEY"}

    # Map Pydantic input -> your internal UserContext dataclass
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

    # Run the voice session in the background so HTTP returns immediately
    background_tasks.add_task(run_voice_session, user_ctx)

    return {
        "status": "ok",
        "message": "Voice session started on backend",
        "user": req.name,
    }


if __name__ == "__main__":
    # Run dev server
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
