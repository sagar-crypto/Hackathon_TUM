import asyncio
import pyaudio
import os
import sys
import traceback
from google import genai
from google.genai import types
from websockets.exceptions import ConnectionClosedError
from typing import Dict, List, Optional
from dataclasses import dataclass

from live_transcript_handler import LiveAgentCoordinator, LiveAnalysisResult


def end_session_tool():
    """Call this function when the user wants to end the conversation."""
    return {"status": "session_ended"}


WELLNESS_SYSTEM_PROMPT = """
You are a warm, calm, and empathetic wellness companion.

Goals:
- Check in on how the user is feeling emotionally and mentally.
- Ask gentle, open questions. Listen more than you speak.
- Offer simple coping strategies (breathing, journaling, short breaks).
- Encourage self-compassion and normalize common struggles.

REAL-TIME GUIDANCE:
- You receive periodic context updates with mood analysis and suggestions.
- Use these insights to guide your responses naturally without explicitly mentioning them.
- If mood is declining, be extra gentle and offer immediate coping techniques.
- If social suggestions are provided, weave them into conversation naturally.
- Prioritize urgent topics when urgency is high.

Boundaries:
- You are NOT a therapist and cannot give medical or legal advice.
- If the user mentions self-harm, suicide, or being in danger, tell them clearly
  to immediately contact local emergency services or a trusted person and seek
  professional help.

Style:
- Speak slowly and clearly, in short sentences.
- Avoid jargon. Be kind, non-judgmental, and validating.

Session Management:
- If the user indicates they want to end the conversation, acknowledge warmly and briefly.
- After acknowledging their goodbye, you MUST call the end_session tool.
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
    """
    Build a short text summary of the user's state for the wellness agent.
    Used for both voice (initial context) and text chat.
    """
    parts = []
    parts.append(f"The user's name is {ctx.name}.")
    if ctx.mood:
        parts.append(f"They currently feel {ctx.mood}.")
    if ctx.health:
        if ctx.health.steps_today is not None:
            parts.append(f"Today they have walked about {ctx.health.steps_today} steps.")
        if ctx.health.sleep_hours_last_night is not None:
            parts.append(
                f"Last night they slept about {ctx.health.sleep_hours_last_night:.1f} hours."
            )
    if ctx.conversation_summary:
        parts.append(
            f"In the previous conversation, they said: {ctx.conversation_summary}"
        )
    if ctx.goals:
        parts.append(f"Their current wellbeing goals are: {ctx.goals}.")
    parts.append(
        "Start by gently asking how they are feeling about their day. "
        "Keep the tone warm, supportive, and non-judgmental."
    )
    return " ".join(parts)


# Audio Configuration
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHUNK_SIZE = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
ECHO_DELAY = 0.3
FINAL_AUDIO_WAIT = 2.0  # Give 2 seconds for final audio to play


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
        self.end_session_requested = False  # NEW: Track when end is requested
        self.last_user_text = ""
        self.last_agent_text = ""
        self.session_ended_callback = None
        self.live_coordinator: Optional[LiveAgentCoordinator] = None
        self.last_context_update = ""


async def audio_input_loop(session, audio_handler, state):
    """Sends audio ONLY when the AI is NOT speaking."""
    print(f"--- 🎤 Listening ({INPUT_SAMPLE_RATE}Hz)... ---")
    try:
        while not state.should_end_session:
            audio_data = await asyncio.to_thread(audio_handler.read_input)
            if audio_data and not state.is_ai_speaking and not state.end_session_requested:
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
    """Handles audio output, transcription, and turn management with live agent coordination."""
    print(f"--- 🔊 Ready for Audio ({OUTPUT_SAMPLE_RATE}Hz) ---")

    try:
        while not state.should_end_session:
            try:
                async for response in session.receive():
                    # Check for tool calls first
                    if hasattr(response, 'tool_call') and response.tool_call:
                        tool_call = response.tool_call
                        print(f"\n🔧 Tool call detected: {tool_call}")

                        # Check if it's the end_session_tool
                        if hasattr(tool_call, 'function_calls') and tool_call.function_calls:
                            for fc in tool_call.function_calls:
                                function_name = getattr(fc, 'name', None)
                                function_id = getattr(fc, 'id', None)

                                print(f"   Function name: {function_name}, ID: {function_id}")

                                if function_name == 'end_session_tool':
                                    print("\n👋 End session tool called")
                                    state.end_session_requested = True

                                    # Send tool response
                                    print("   Sending tool response...")
                                    await session.send_tool_response(
                                        function_responses=[
                                            types.FunctionResponse(
                                                id=function_id,
                                                name=function_name,
                                                response={"status": "session_ended"}
                                            )
                                        ]
                                    )
                                    print("   Tool response sent, waiting for AI's final message...")

                                    # DON'T end here - continue to receive the final audio response

                    server_content = response.server_content
                    if server_content:
                        # Handle audio output and transcription
                        if server_content.model_turn:
                            state.is_ai_speaking = True
                            current_text_parts = []

                            for part in server_content.model_turn.parts:
                                # Play audio
                                if part.inline_data:
                                    await asyncio.to_thread(audio_handler.write_output, part.inline_data.data)

                                # Collect text for transcription
                                if hasattr(part, 'text') and part.text:
                                    current_text_parts.append(part.text)

                            # Store agent's text and send to coordinator
                            if current_text_parts:
                                state.last_agent_text = " ".join(current_text_parts)
                                if state.live_coordinator:
                                    await state.live_coordinator.add_transcript("agent", state.last_agent_text)
                                    print(f"\n🤖 Agent: {state.last_agent_text[:80]}...")

                        # Handle turn completion
                        if server_content.turn_complete:
                            await asyncio.sleep(ECHO_DELAY)
                            state.is_ai_speaking = False
                            print(".", end="", flush=True)

                            # If we're in the process of ending, now we can actually end
                            if state.end_session_requested:
                                print("\n\n👋 AI has finished speaking, ending session gracefully...")
                                # Give a bit more time for audio buffer to clear
                                await asyncio.sleep(FINAL_AUDIO_WAIT)
                                state.should_end_session = True
                                if state.session_ended_callback:
                                    await state.session_ended_callback("ai_initiated")
                                return

            except asyncio.CancelledError:
                print("\n[Output Loop] Cancelled")
                break
            except ConnectionClosedError:
                print("\n[Output Loop] Connection closed.")
                state.should_end_session = True
                if state.session_ended_callback:
                    try:
                        await state.session_ended_callback("connection_closed")
                    except Exception:
                        pass
                break
            except Exception as e:
                print(f"[Output Loop] Error: {e}")
                traceback.print_exc()
                continue

    finally:
        print("[Output Loop] Exiting...")


async def context_injection_loop(session, state):
    """
    Periodically injects live agent analysis into the conversation.
    This provides the wellness agent with real-time insights.
    """
    try:
        while not state.should_end_session:
            await asyncio.sleep(45)  # Update every 45 seconds

            if state.live_coordinator and not state.end_session_requested:
                context = await state.live_coordinator.get_context_for_agent()

                if context and context != state.last_context_update:
                    state.last_context_update = context

                    print(f"\n{'─' * 60}")
                    print(f"💡 [Context Injector] Sending live insights to wellness agent...")
                    print(f"{'─' * 60}")
                    print(context)
                    print(f"{'─' * 60}\n")

                    await session.send_client_content(
                        turns=types.Content(
                            role="user",
                            parts=[types.Part(text=context)],
                        ),
                        turn_complete=True,
                    )
                    print("✅ [Context Injector] Context successfully injected\n")
    except asyncio.CancelledError:
        print("⏹️  [Context Injector] Stopped")
        pass
    except Exception as e:
        print(f"❌ [Context Injector] Error: {e}")


class WellnessAgentLive:
    def __init__(self, api_key: str, model_id: str = os.environ.get("MODEL")):
        self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
        self.model_id = model_id

    async def start_voice_session_with_live_agents(
            self,
            user_context: UserContext,
            initial_history: Optional[List] = None,
            on_session_end=None
    ):
        """
        Start voice session with live agent coordination.
        Agents continuously analyze the conversation and provide real-time insights.
        """
        audio_handler = AudioHandler()

        # Initialize live agent coordinator
        initial_ctx = {
            'health_data': {
                'steps_today': user_context.health.steps_today if user_context.health else 0,
                'sleep_hours_last_night': user_context.health.sleep_hours_last_night if user_context.health else 0.0,
            }
        }

        live_coordinator = LiveAgentCoordinator(user_context.name, initial_ctx)

        async def on_analysis_complete(analysis: LiveAnalysisResult):
            """Callback when live analysis completes."""
            print(f"\n📈 Live Analysis Complete:")
            print(f"   Mood: {analysis.mood_score}/10 ({analysis.mood_trend})")
            print(f"   Urgency: {analysis.urgency_level}")
            if analysis.social_suggestions:
                print(f"   Top Suggestion: {analysis.social_suggestions[0][:60]}...")

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
                tools=[end_session_tool],
            )

            async with self.client.aio.live.connect(model=self.model_id, config=config) as session:
                audio_handler.start_input_stream()
                audio_handler.start_output_stream()
                state = SessionState()
                state.session_ended_callback = on_session_end
                state.live_coordinator = live_coordinator

                # Start live agent coordinator
                await live_coordinator.start(on_analysis_complete=on_analysis_complete)
                print(f"{'═' * 60}")
                print("🔄 Live Agent Coordinator: ACTIVE")
                print(f"{'═' * 60}\n")

                # Send initial context
                if context_text:
                    print(f"{'─' * 60}")
                    print(f"📤 [Initial Context] Sending to wellness agent...")
                    print(f"{'─' * 60}")
                    await session.send_client_content(
                        turns=types.Content(
                            role="user",
                            parts=[types.Part(text=context_text)],
                        ),
                        turn_complete=True,
                    )
                    print("✅ [Initial Context] Sent successfully\n")

                # Start all loops
                print(f"{'─' * 60}")
                print("🚀 Starting voice session loops...")
                print(f"{'─' * 60}")
                print("   🎤 Audio Input Loop: Starting...")
                input_task = asyncio.create_task(audio_input_loop(session, audio_handler, state))
                print("   🔊 Audio Output Loop: Starting...")
                output_task = asyncio.create_task(audio_output_loop(session, audio_handler, state))
                print("   💡 Context Injection Loop: Starting...")
                context_task = asyncio.create_task(context_injection_loop(session, state))
                print(f"{'─' * 60}\n")
                print("✅ All systems active - conversation ready!\n")

                # Monitor for session end
                print("\n[Main] Waiting for session to end...")
                while not state.should_end_session:
                    done, pending = await asyncio.wait(
                        [input_task, output_task, context_task],
                        timeout=0.1,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in done:
                        if task.exception():
                            print(f"\n[Main] Task error: {task.exception()}")
                            state.should_end_session = True
                            break

                print("\n[Main] Session end signal received, cleaning up...")

                # Wait for output task to complete (it handles final audio)
                print("[Main] Waiting for output task...")
                try:
                    await asyncio.wait_for(output_task, timeout=5.0)
                    print("[Main] Output task completed")
                except asyncio.TimeoutError:
                    print("[Main] Output task timeout, forcing cancel")
                    if not output_task.done():
                        output_task.cancel()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"[Main] Output task error: {e}")

                # Cancel remaining tasks
                print("[Main] Cancelling remaining tasks...")
                for task in [input_task, context_task]:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass

                # Stop coordinator
                print("[Main] Stopping coordinator...")
                await live_coordinator.stop()

                print("\n✅ Session ended successfully.")

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

    from typing import Dict  # add to your imports at the top: Optional, List, Dict

    async def chat(
        self,
        user_message: str,
        user_context: Optional[UserContext] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Text-only wellness chat using the SAME live model.
        Opens a short-lived live session with response_modalities=['TEXT'].

        `history` is a list of dicts:
          [{ "role": "user"|"assistant", "text": "..." }, ...]
        """
        config = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            system_instruction=WELLNESS_SYSTEM_PROMPT,
        )

        async with self.client.aio.live.connect(
            model=self.model_id,
            config=config,
        ) as session:
            # 0) Re-send conversation history (only user turns)
            if history:
                for turn in history:
                    if turn["role"] != "user":
                        continue  # skip assistant/model turns

                    await session.send_client_content(
                        turns=types.Content(
                            role="user",
                            parts=[types.Part(text=turn["text"])],
                        ),
                        turn_complete=True,
                    )

            # 1) Optional dynamic context message (e.g. only on first turn)
            if user_context is not None:
                context_text = build_wellness_context(user_context)
                await session.send_client_content(
                    turns=types.Content(
                        role="user",
                        parts=[types.Part(text=context_text)],
                    ),
                    turn_complete=True,
                )

            # 2) Actual user message
            await session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=user_message)],
                ),
                turn_complete=True,
            )

            # 3) Collect streamed text reply
            reply_chunks: List[str] = []

            async for response in session.receive():
                server_content = response.server_content
                if not server_content:
                    continue

                if server_content.model_turn:
                    for part in server_content.model_turn.parts:
                        if hasattr(part, "text") and part.text:
                            reply_chunks.append(part.text)

                if server_content.turn_complete:
                    break

            if not reply_chunks:
                return "I'm sorry, I’m having trouble responding right now."

            return "".join(reply_chunks).strip()



async def main():
    """Standalone test of live wellness agent."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set.")
        return

    agent = WellnessAgentLive(api_key=api_key)

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
        await agent.start_voice_session_with_live_agents(user_context=ctx)
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
