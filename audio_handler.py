# audio_handler.py
"""
Handles audio streaming with Gemini Live API.
Integrates client audio input directly with Gemini's real-time processing.
"""

import asyncio
import base64
import io
from typing import Optional, AsyncGenerator
from google import genai
from google.genai import types
import os


class GeminiLiveAudioHandler:
    """Manages audio streaming with Gemini Live API."""

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
        self.model_id = os.environ.get("MODEL", "gemini-2.0-flash-exp")
        self.active_sessions = {}

    async def create_audio_session(self, session_id: str, user_name: str) -> str:
        """Create a new Gemini Live session for audio streaming."""

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Zephyr"
                    )
                )
            ),
            system_instruction=self._get_wellness_prompt(),
        )

        # Store session info for later use
        self.active_sessions[session_id] = {
            "user_name": user_name,
            "config": config,
            "session": None
        }

        print(f"[Gemini Live] Created audio session for {user_name} ({session_id})")
        return session_id

    def _get_wellness_prompt(self) -> str:
        """Get the wellness system prompt."""
        return """
You are a warm, calm, and empathetic wellness companion.

Goals:
- Check in on how the user is feeling emotionally and mentally.
- Ask gentle, open questions. Listen more than you speak.
- Offer simple coping strategies (breathing, journaling, short breaks).
- Encourage self-compassion and normalize common struggles.

Boundaries:
- You are NOT a therapist and cannot give medical or legal advice.
- If the user mentions self-harm, suicide, or being in danger, tell them clearly
  to immediately contact local emergency services or a trusted person and seek
  professional help.

Style:
- Speak slowly and clearly, in short sentences.
- Avoid jargon. Be kind, non-judgmental, and validating.
"""

    async def process_audio_stream(
            self,
            session_id: str,
            audio_bytes: bytes
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream audio to Gemini Live API and yield response audio chunks.

        Args:
            session_id: Session identifier
            audio_bytes: Raw audio data from client (WebM/WAV)

        Yields:
            Audio response chunks from Gemini
        """

        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session_info = self.active_sessions[session_id]

        try:
            # Create or reuse Gemini Live connection
            async with self.client.aio.live.connect(
                    model=self.model_id,
                    config=session_info["config"]
            ) as live_session:

                # Send audio to Gemini
                print(f"[Gemini Live] Sending audio ({len(audio_bytes)} bytes) to Gemini...")
                await live_session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_bytes,
                        mime_type="audio/webm"  # or "audio/wav" depending on client
                    )
                )

                # Receive and yield response audio
                response_audio_chunks = []
                async for response in live_session.receive():
                    server_content = response.server_content

                    if server_content and server_content.model_turn:
                        for part in server_content.model_turn.parts:
                            # Yield audio data if present
                            if part.inline_data:
                                chunk = part.inline_data.data
                                response_audio_chunks.append(chunk)
                                yield chunk
                                print(f"[Gemini Live] Yielding {len(chunk)} bytes")

                    # Stop when turn is complete
                    if server_content and server_content.turn_complete:
                        print(
                            f"[Gemini Live] Turn complete, total response: {sum(len(c) for c in response_audio_chunks)} bytes")
                        break

        except Exception as e:
            print(f"[Gemini Live] Error: {e}")
            raise

    async def get_text_response(
            self,
            session_id: str,
            audio_bytes: bytes
    ) -> tuple[str, bytes]:
        """
        Send audio to Gemini and get both text transcription and audio response.

        Returns:
            Tuple of (transcribed_text, response_audio_bytes)
        """

        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session_info = self.active_sessions[session_id]
        transcribed_text = ""
        response_audio = b""

        try:
            async with self.client.aio.live.connect(
                    model=self.model_id,
                    config=session_info["config"]
            ) as live_session:

                print(f"[Gemini Live] Processing audio for transcription and response...")

                # Send audio input
                await live_session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_bytes,
                        mime_type="audio/webm"
                    )
                )

                # Receive responses
                async for response in live_session.receive():
                    server_content = response.server_content

                    if server_content:
                        # Extract text (user's transcribed speech)
                        if hasattr(server_content, 'interrupted') and server_content.interrupted:
                            print(f"[Gemini Live] User interrupted")

                        # Get model's response
                        if server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                # Extract audio response
                                if part.inline_data:
                                    response_audio += part.inline_data.data

                                # Extract text response
                                if hasattr(part, 'text') and part.text:
                                    transcribed_text += part.text

                        # Stop when turn is complete
                        if server_content.turn_complete:
                            print(f"[Gemini Live] Received {len(response_audio)} bytes of audio response")
                            print(f"[Gemini Live] Response text: {transcribed_text[:100]}...")
                            break

            return transcribed_text, response_audio

        except Exception as e:
            print(f"[Gemini Live] Error in get_text_response: {e}")
            raise

    async def close_session(self, session_id: str):
        """Close a session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            print(f"[Gemini Live] Closed session {session_id}")


# Global instance
gemini_audio_handler = GeminiLiveAudioHandler()