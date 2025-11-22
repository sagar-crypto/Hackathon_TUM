import asyncio
import pyaudio
import os
import sys
import traceback
from google import genai
from google.genai import types
from websockets.exceptions import ConnectionClosedError
from typing import Optional
from dataclasses import dataclass



#system prompt

WELLNESS_SYSTEM_PROMPT = """
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


@dataclass
class HealthSnapshot:
    steps_today: Optional[int] = None
    sleep_hours_last_night: Optional[float] = None

@dataclass
class UserContext:
    name: str
    mood: Optional[str] = None
    health: Optional[HealthSnapshot] = None
    conversation_summary: Optional[str] = None
    goals: Optional[str] = None  # e.g. "sleep better", "exercise more"

# (optional) dynamic context helper
def build_wellness_context(ctx: UserContext) -> str:
    parts = []
    parts.append(f"The user's name is {ctx.name}.")
    if ctx.mood:
        parts.append(f"They currently feel {ctx.mood}.")
    if ctx.health:
        if ctx.health.steps_today is not None:
            parts.append(f"Today they have walked about {ctx.health.steps_today} steps.")
        if ctx.health.sleep_hours_last_night is not None:
            parts.append(f"Last night they slept about {ctx.health.sleep_hours_last_night:.1f} hours.")
    if ctx.conversation_summary:
        parts.append(f"In the previous conversation, they said: {ctx.conversation_summary}")
    if ctx.goals:
        parts.append(f"Their current wellbeing goals are: {ctx.goals}.")
    parts.append(
        "Start by gently acknowledging anything notable (like low activity or poor sleep), "
        "then ask how they are feeling about their day. Keep the tone warm and non-judgmental."
    )
    return " ".join(parts)


# --- Configuration ---
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_ID = "gemini-live-2.5-flash-preview"

# Audio Configuration
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHUNK_SIZE = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1

# Speaker Safety Buffer
# We wait this many seconds after the AI finishes before unmuting the mic.
# This prevents the mic from hearing the last echo of the AI's voice.
ECHO_DELAY = 0.3


class AudioHandler:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None

    def start_input_stream(self):
        if self.input_stream: return
        self.input_stream = self.p.open(
            format=FORMAT, channels=CHANNELS, rate=INPUT_SAMPLE_RATE,
            input=True, frames_per_buffer=CHUNK_SIZE
        )

    def start_output_stream(self):
        if self.output_stream: return
        self.output_stream = self.p.open(
            format=FORMAT, channels=CHANNELS, rate=OUTPUT_SAMPLE_RATE,
            output=True, frames_per_buffer=CHUNK_SIZE
        )

    def read_input(self):
        if self.input_stream and self.input_stream.is_active():
            return self.input_stream.read(CHUNK_SIZE, exception_on_overflow=False)
        return None

    def write_output(self, audio_data):
        if self.output_stream and self.output_stream.is_active():
            self.output_stream.write(audio_data)

    def close(self):
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.p.terminate()


# --- Session State for Echo Prevention ---
class SessionState:
    def __init__(self):
        self.is_ai_speaking = False


async def audio_input_loop(session, audio_handler, state):
    """
    Sends audio ONLY when the AI is NOT speaking.
    """
    print(f"--- 🎤 Listening ({INPUT_SAMPLE_RATE}Hz)... ---")
    try:
        while True:
            # Always read the mic to clear the buffer
            audio_data = await asyncio.to_thread(audio_handler.read_input)

            if audio_data:
                # ECHO CANCELLATION CHECK:
                # Only send audio if the AI is NOT speaking
                if not state.is_ai_speaking:
                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=audio_data,
                            mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}"
                        )
                    )

            await asyncio.sleep(0.00)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Input loop error: {e}")


async def audio_output_loop(session, audio_handler, state):
    print(f"--- 🔊 Ready for Audio ({OUTPUT_SAMPLE_RATE}Hz) ---")

    while True:  # Keep reconnecting to the receive loop
        try:
            async for response in session.receive():
                server_content = response.server_content
                if server_content:

                    # 1. Handle Audio Data
                    if server_content.model_turn:
                        # If we receive audio, lock the mic immediately
                        state.is_ai_speaking = True

                        for part in server_content.model_turn.parts:
                            if part.inline_data:
                                await asyncio.to_thread(audio_handler.write_output, part.inline_data.data)

                    # 2. Handle Turn Completion
                    if server_content.turn_complete:
                        # AI is done. Wait a tiny bit for the sound to clear from speakers.
                        await asyncio.sleep(ECHO_DELAY)
                        state.is_ai_speaking = False
                        print(".", end="", flush=True)

        except asyncio.CancelledError:
            break
        except ConnectionClosedError:
            print("\nConnection closed.")
            break
        except Exception as e:
            print(f"Output loop error: {e}")
            traceback.print_exc()
            break


class WellnessAgent:
    def __init__(self, api_key: str, model_id: str = MODEL_ID):
        self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
        self.model_id = model_id

    async def start_voice_session(
        self,
        user_context: Optional[UserContext] = None,
    ):
        audio_handler = AudioHandler()

        async def _run():
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Zephyr"
                        )
                    )
                ),
                system_instruction=WELLNESS_SYSTEM_PROMPT,
            )

            async with self.client.aio.live.connect(
                model=self.model_id,
                config=config
            ) as session:
                audio_handler.start_input_stream()
                audio_handler.start_output_stream()

                state = SessionState()

                # 🔹 Dynamic initial context based on health + history
                if user_context is not None:
                    context_text = build_wellness_context(user_context)
                    await session.send_client_content(
                        turns=types.Content(
                            role="user",
                            parts=[types.Part(text=context_text)],
                        ),
                        turn_complete=True,
                    )

                input_task = asyncio.create_task(audio_input_loop(session, audio_handler, state))
                output_task = asyncio.create_task(audio_output_loop(session, audio_handler, state))

                done, pending = await asyncio.wait(
                    [input_task, output_task],
                    return_when=asyncio.FIRST_EXCEPTION
                )

                for task in pending:
                    task.cancel()

        try:
            await _run()
        finally:
            audio_handler.close()



# --- main / entrypoint ---
async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set.")
        return

    agent = WellnessAgent(api_key=api_key)

    # Mocked context for now – later this comes from iOS Health + history
    ctx = UserContext(
        name="Sagar",
        mood="a bit low on energy",
        health=HealthSnapshot(
            steps_today=2000,
            sleep_hours_last_night=5.0,
        ),
        conversation_summary="They felt stressed about work and wanted to improve their sleep habits.",
        goals="sleep better and be more active",
    )

    try:
        await agent.start_voice_session(user_context=ctx)
    except Exception as e:
        print(f"Session Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
