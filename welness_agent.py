import asyncio
import pyaudio
import os
import sys
import traceback
from google import genai
from google.genai import types
from websockets.exceptions import ConnectionClosedError
from typing import Optional, List
from dataclasses import dataclass


# Define the end_session tool for the LLM
def end_session_tool():
    """
    Call this function when the user wants to end the conversation.
    Use this when the user says goodbye, mentions they need to leave,
    or indicates they're finished with the conversation.
    """
    return {"status": "session_ended"}


# System prompt
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

Session Management:
- If the user indicates they want to end the conversation (saying goodbye, mentioning they need to leave, expressing they're done talking, etc.), acknowledge their goodbye warmly and briefly.
- After acknowledging their goodbye, you MUST call the end_session tool to properly close the conversation.
- Do not try to extend the conversation once the user has indicated they want to leave.
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
    goals: Optional[str] = None


def build_wellness_context(ctx: UserContext) -> str:
    """Build context string from user context."""
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


# Configuration
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_ID = os.environ.get("MODEL")

# Audio Configuration
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHUNK_SIZE = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
ECHO_DELAY = 0.3


class AudioHandler:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None

    def start_input_stream(self):
        if self.input_stream:
            return
        self.input_stream = self.p.open(
            format=FORMAT, channels=CHANNELS, rate=INPUT_SAMPLE_RATE,
            input=True, frames_per_buffer=CHUNK_SIZE
        )

    def start_output_stream(self):
        if self.output_stream:
            return
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


class SessionState:
    def __init__(self):
        self.is_ai_speaking = False
        self.should_end_session = False
        self.last_user_text = ""
        self.session_ended_callback = None  # Callback to notify when session ends


async def audio_input_loop(session, audio_handler, state):
    """Sends audio ONLY when the AI is NOT speaking."""
    print(f"--- 🎤 Listening ({INPUT_SAMPLE_RATE}Hz)... ---")
    try:
        while True:
            audio_data = await asyncio.to_thread(audio_handler.read_input)
            if audio_data and not state.is_ai_speaking:
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
    """Handles audio output and turn management."""
    print(f"--- 🔊 Ready for Audio ({OUTPUT_SAMPLE_RATE}Hz) ---")

    while True:
        try:
            async for response in session.receive():
                server_content = response.server_content
                if server_content:
                    # Handle audio output
                    if server_content.model_turn:
                        state.is_ai_speaking = True
                        for part in server_content.model_turn.parts:
                            # Play audio
                            if part.inline_data:
                                await asyncio.to_thread(audio_handler.write_output, part.inline_data.data)

                            # Check for function call to end session
                            if hasattr(part, 'function_call') and part.function_call:
                                func_call = part.function_call
                                # Check if it's the end_session_tool
                                if hasattr(func_call, 'name') and func_call.name == 'end_session_tool':
                                    print(f"\n\n👋 AI assistant decided to end the session")
                                    print("Ending session gracefully...")
                                    state.should_end_session = True
                                    # Notify callback if set
                                    await asyncio.sleep(5.0)
                                    if state.session_ended_callback:
                                        await state.session_ended_callback("ai_initiated")
                                    # Let the goodbye audio finish playing

                                    return
                                elif hasattr(func_call, 'id') and 'end_session' in str(func_call):
                                    print(f"\n\n👋 AI assistant decided to end the session")
                                    print("Ending session gracefully...")
                                    await asyncio.sleep(5.0)
                                    state.should_end_session = True
                                    if state.session_ended_callback:
                                        await state.session_ended_callback("ai_initiated")
                                    await asyncio.sleep(5.0)

                                    return

                    # Handle turn completion
                    if server_content.turn_complete:
                        await asyncio.sleep(ECHO_DELAY)
                        state.is_ai_speaking = False
                        print(".", end="", flush=True)

                # Check for tool calls at response level
                if hasattr(response, 'tool_call') and response.tool_call:
                    tool_call = response.tool_call
                    # Try different ways to access the tool name
                    tool_name = None
                    if hasattr(tool_call, 'function_calls') and tool_call.function_calls:
                        for fc in tool_call.function_calls:
                            if hasattr(fc, 'name'):
                                tool_name = fc.name
                            elif hasattr(fc, 'id') and 'end_session' in str(fc):
                                tool_name = 'end_session_tool'

                    if tool_name == 'end_session_tool':
                        print(f"\n\n👋 AI assistant decided to end the session")
                        print("Ending session gracefully...")
                        await asyncio.sleep(5.0)
                        state.should_end_session = True

                        if state.session_ended_callback:
                            await state.session_ended_callback("ai_initiated")

                        await asyncio.sleep(5.0)
                        return

        except asyncio.CancelledError:
            break
        except ConnectionClosedError:
            print("\nConnection closed.")
            if state.session_ended_callback:
                try:
                    await state.session_ended_callback("connection_closed")
                except Exception:
                    pass
            break
        except AttributeError as e:
            # Debug: print the structure of the tool call
            print(f"\nDebug - AttributeError: {e}")
            if hasattr(response, 'tool_call'):
                print(f"Tool call structure: {response.tool_call}")
                print(f"Tool call type: {type(response.tool_call)}")
                print(f"Tool call attributes: {dir(response.tool_call)}")
            continue
        except Exception as e:
            print(f"Output loop error: {e}")
            traceback.print_exc()
            break


class WellnessAgent:
    def __init__(self, api_key: str, model_id: str = MODEL_ID):
        self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
        self.model_id = model_id

    async def start_voice_session(self, user_context: Optional[UserContext] = None, on_session_end=None):
        """Start voice session with basic context.

        Args:
            user_context: User context information
            on_session_end: Optional async callback function(reason: str) called when session ends
        """
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
                tools=[end_session_tool],  # Register the end_session tool
            )

            async with self.client.aio.live.connect(model=self.model_id, config=config) as session:
                audio_handler.start_input_stream()
                audio_handler.start_output_stream()
                state = SessionState()

                # Set the callback
                state.session_ended_callback = on_session_end

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

                # Monitor for session end signal
                while not state.should_end_session:
                    done, pending = await asyncio.wait(
                        [input_task, output_task],
                        timeout=0.1,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Check if any task raised an exception
                    for task in done:
                        if task.exception():
                            print(f"\nTask error: {task.exception()}")
                            state.should_end_session = True
                            break

                # Cancel remaining tasks
                for task in [input_task, output_task]:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                print("\n✅ Session ended successfully.")

                # Notify callback of normal completion if not already notified
                if not state.should_end_session and on_session_end:
                    await on_session_end("manual_completion")

        try:
            await _run()
        except KeyboardInterrupt:
            print("\n\n⚠️ Session interrupted by user")
            if on_session_end:
                await on_session_end("user_interrupted")
        finally:
            audio_handler.close()

    async def start_voice_session_with_context(
            self,
            user_context: UserContext,
            initial_history: Optional[List] = None,
            on_session_end=None
    ):
        """
        Start voice session with pre-generated context from orchestrator.
        Accepts a conversation history including the generated prompt.

        Args:
            user_context: User context information
            initial_history: Optional conversation history
            on_session_end: Optional async callback function(reason: str) called when session ends
        """
        audio_handler = AudioHandler()

        async def _run():
            # Extract context from history
            context_text = ""
            system_prompt = WELLNESS_SYSTEM_PROMPT

            if initial_history:
                for msg in initial_history:
                    if hasattr(msg, 'content'):
                        if 'wellness companion' in msg.content.lower():
                            system_prompt = msg.content
                        elif 'FINAL CONTEXT FOR WELLNESS AGENT' in msg.content:
                            context_text = msg.content

            if not context_text:
                context_text = build_wellness_context(user_context)

            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Zephyr"
                        )
                    )
                ),
                system_instruction=system_prompt,
                tools=[end_session_tool],  # Register the end_session tool
            )

            async with self.client.aio.live.connect(model=self.model_id, config=config) as session:
                audio_handler.start_input_stream()
                audio_handler.start_output_stream()
                state = SessionState()

                # Set the callback
                state.session_ended_callback = on_session_end

                print(f"\n--- Sending Generated Context to Voice Agent ---")
                await session.send_client_content(
                    turns=types.Content(
                        role="user",
                        parts=[types.Part(text=context_text)],
                    ),
                    turn_complete=True,
                )

                input_task = asyncio.create_task(audio_input_loop(session, audio_handler, state))
                output_task = asyncio.create_task(audio_output_loop(session, audio_handler, state))

                # Monitor for session end signal
                while not state.should_end_session:
                    done, pending = await asyncio.wait(
                        [input_task, output_task],
                        timeout=0.1,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Check if any task raised an exception
                    for task in done:
                        if task.exception():
                            print(f"\nTask error: {task.exception()}")
                            state.should_end_session = True
                            break

                # Cancel remaining tasks
                for task in [input_task, output_task]:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                print("\n✅ Session ended successfully.")

                # Notify callback of normal completion if not already notified
                if not state.should_end_session and on_session_end:
                    await on_session_end("manual_completion")

        try:
            await _run()
        except KeyboardInterrupt:
            print("\n\n⚠️ Session interrupted by user")
            if on_session_end:
                await on_session_end("user_interrupted")
        finally:
            audio_handler.close()


async def main():
    """Standalone test of wellness agent."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set.")
        return

    agent = WellnessAgent(api_key=api_key)

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