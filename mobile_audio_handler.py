# mobile_audio_handler.py
"""
Handles audio streaming for mobile clients via WebSocket.
Replaces server-side PyAudio with client-side audio streaming.
"""

import asyncio
import json
import base64
from typing import Optional, Dict, Set
from datetime import datetime
from google import genai
from google.genai import types
import os

from live_transcript_handler import LiveAgentCoordinator, LiveAnalysisResult


class MobileAudioSession:
    """Manages a single mobile audio session with Gemini Live API."""

    def __init__(self, session_id: str, user_context: dict, api_key: str):
        self.session_id = session_id
        self.user_context = user_context
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
        self.model_id = os.environ.get("MODEL", "gemini-2.0-flash-exp")

        # Session state
        self.is_active = False
        self.should_end = False
        self.end_session_requested = False
        self.gemini_session = None

        # Live agent coordinator
        self.live_coordinator: Optional[LiveAgentCoordinator] = None

        # WebSocket connection
        self.websocket = None

        # Tasks
        self.gemini_receive_task = None
        self.context_injection_task = None

    async def start(self, websocket, initial_system_prompt: str, initial_context: str):
        """Start the audio session with Gemini Live API."""
        self.websocket = websocket
        self.is_active = True

        # Initialize live agent coordinator
        initial_ctx = {
            'health_data': self.user_context.get('health_data', {})
        }

        self.live_coordinator = LiveAgentCoordinator(
            self.user_context.get('name', 'User'),
            initial_ctx
        )

        async def on_analysis_complete(analysis: LiveAnalysisResult):
            """Send analysis updates to mobile client."""
            await self.send_to_client({
                "type": "live_analysis",
                "mood_score": analysis.mood_score,
                "mood_trend": analysis.mood_trend,
                "urgency": analysis.urgency_level,
                "social_suggestions": analysis.social_suggestions,
                "health_insights": analysis.health_insights
            })

        await self.live_coordinator.start(on_analysis_complete=on_analysis_complete)

        # Configure Gemini Live
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Zephyr"
                    )
                )
            ),
            system_instruction=initial_system_prompt,
            tools=[self._end_session_tool],
        )

        # Connect to Gemini Live
        self.gemini_session = await self.client.aio.live.connect(
            model=self.model_id,
            config=config
        ).__aenter__()

        # Send initial context
        if initial_context:
            await self.gemini_session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=initial_context)],
                ),
                turn_complete=True,
            )

        # Start background tasks
        self.gemini_receive_task = asyncio.create_task(self._receive_from_gemini())
        self.context_injection_task = asyncio.create_task(self._context_injection_loop())

        print(f"[Session {self.session_id}] Started successfully")

    def _end_session_tool(self):
        """Tool for Gemini to end the session."""
        return {"status": "session_ended"}

    async def process_audio_from_client(self, audio_data: bytes):
        """Process audio received from mobile client."""
        if not self.is_active or self.end_session_requested:
            return

        try:
            # Send audio to Gemini
            await self.gemini_session.send_realtime_input(
                audio=types.Blob(
                    data=audio_data,
                    mime_type="audio/pcm;rate=16000"  # Adjust based on client format
                )
            )
        except Exception as e:
            print(f"[Session {self.session_id}] Error processing audio: {e}")
            await self.send_to_client({
                "type": "error",
                "message": f"Audio processing error: {str(e)}"
            })

    async def _receive_from_gemini(self):
        """Receive responses from Gemini and forward to client."""
        try:
            async for response in self.gemini_session.receive():
                if self.should_end:
                    break

                # Handle tool calls
                if hasattr(response, 'tool_call') and response.tool_call:
                    await self._handle_tool_call(response.tool_call)

                # Handle server content
                server_content = response.server_content
                if server_content:
                    if server_content.model_turn:
                        await self._handle_model_turn(server_content.model_turn)

                    if server_content.turn_complete:
                        await self.send_to_client({
                            "type": "turn_complete"
                        })

                        # Check if session should end after turn completes
                        if self.end_session_requested:
                            print(f"[Session {self.session_id}] Ending after final response")
                            await asyncio.sleep(1.0)  # Give client time to play audio
                            await self.end_session("ai_initiated")

        except Exception as e:
            print(f"[Session {self.session_id}] Error in Gemini receive: {e}")
            await self.send_to_client({
                "type": "error",
                "message": f"Gemini error: {str(e)}"
            })

    async def _handle_tool_call(self, tool_call):
        """Handle tool calls from Gemini."""
        if hasattr(tool_call, 'function_calls') and tool_call.function_calls:
            for fc in tool_call.function_calls:
                function_name = getattr(fc, 'name', None)
                function_id = getattr(fc, 'id', None)

                if function_name == 'end_session_tool':
                    print(f"[Session {self.session_id}] End session tool called")
                    self.end_session_requested = True

                    # Send tool response back to Gemini
                    await self.gemini_session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                id=function_id,
                                name=function_name,
                                response={"status": "session_ended"}
                            )
                        ]
                    )

                    # Notify client
                    await self.send_to_client({
                        "type": "session_ending",
                        "message": "AI is ending the session"
                    })

    async def _handle_model_turn(self, model_turn):
        """Handle model turn with audio and text."""
        audio_chunks = []
        text_parts = []

        for part in model_turn.parts:
            # Extract audio
            if part.inline_data:
                audio_chunks.append(part.inline_data.data)

            # Extract text
            if hasattr(part, 'text') and part.text:
                text_parts.append(part.text)

        # Send audio to client
        if audio_chunks:
            for chunk in audio_chunks:
                await self.send_to_client({
                    "type": "audio",
                    "data": base64.b64encode(chunk).decode('utf-8')
                })

        # Send transcript to client and live coordinator
        if text_parts:
            full_text = " ".join(text_parts)
            await self.send_to_client({
                "type": "agent_transcript",
                "text": full_text
            })

            if self.live_coordinator:
                await self.live_coordinator.add_transcript("agent", full_text)

    async def _context_injection_loop(self):
        """Periodically inject context from live agents."""
        try:
            last_context = ""
            while not self.should_end:
                await asyncio.sleep(45)

                if self.live_coordinator and not self.end_session_requested:
                    context = await self.live_coordinator.get_context_for_agent()

                    if context and context != last_context:
                        last_context = context

                        # Send to Gemini
                        await self.gemini_session.send_client_content(
                            turns=types.Content(
                                role="user",
                                parts=[types.Part(text=context)],
                            ),
                            turn_complete=True,
                        )

                        # Notify client
                        await self.send_to_client({
                            "type": "context_update",
                            "context": context
                        })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Session {self.session_id}] Context injection error: {e}")

    async def send_to_client(self, message: dict):
        """Send message to mobile client."""
        if self.websocket:
            try:
                await self.websocket.send_json(message)
            except Exception as e:
                print(f"[Session {self.session_id}] Error sending to client: {e}")

    async def end_session(self, reason: str):
        """End the session gracefully."""
        if self.should_end:
            return

        self.should_end = True
        self.is_active = False

        print(f"[Session {self.session_id}] Ending: {reason}")

        # Notify client
        await self.send_to_client({
            "type": "session_ended",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

        # Cancel tasks
        if self.gemini_receive_task:
            self.gemini_receive_task.cancel()
        if self.context_injection_task:
            self.context_injection_task.cancel()

        # Stop coordinator
        if self.live_coordinator:
            await self.live_coordinator.stop()

        # Close Gemini session
        if self.gemini_session:
            try:
                await self.gemini_session.__aexit__(None, None, None)
            except Exception as e:
                print(f"[Session {self.session_id}] Error closing Gemini: {e}")


class MobileAudioSessionManager:
    """Manages multiple mobile audio sessions."""

    def __init__(self):
        self.sessions: Dict[str, MobileAudioSession] = {}

    async def create_session(
            self,
            session_id: str,
            user_context: dict,
            api_key: str,
            websocket,
            initial_system_prompt: str,
            initial_context: str
    ) -> MobileAudioSession:
        """Create and start a new mobile audio session."""

        session = MobileAudioSession(session_id, user_context, api_key)
        self.sessions[session_id] = session

        await session.start(websocket, initial_system_prompt, initial_context)

        return session

    async def get_session(self, session_id: str) -> Optional[MobileAudioSession]:
        """Get an existing session."""
        return self.sessions.get(session_id)

    async def end_session(self, session_id: str, reason: str = "closed"):
        """End a session."""
        session = self.sessions.get(session_id)
        if session:
            await session.end_session(reason)
            del self.sessions[session_id]

    async def cleanup_inactive_sessions(self):
        """Clean up inactive sessions."""
        to_remove = [
            sid for sid, session in self.sessions.items()
            if not session.is_active
        ]
        for sid in to_remove:
            await self.end_session(sid, "inactive")


# Global session manager
mobile_session_manager = MobileAudioSessionManager()