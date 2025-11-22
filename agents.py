# agents.py
import os
import sqlite3
import json
import asyncio
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from google import genai
from google.genai import types
from datetime import datetime

# --- Configuration ---
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("WARNING: GEMINI_API_KEY environment variable not set in agents.py.")

# Initialize the Gemini Client
CLIENT = genai.Client(api_key=API_KEY) if API_KEY else None

DB_FILE = "user_data.db"
CONVERSATION_DIR = "conversations"


# --- Tools for Social Agent ---

def get_user_interests(user_name: str) -> str:
    """Gets the user's interests from the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT interests FROM user_interests WHERE user_name = ?", (user_name,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        return f"No specific interests found for {user_name}. Using default interests: wellness, outdoor activities, social events."
    except Exception as e:
        print(f"Error getting user interests: {e}")
        return "wellness, outdoor activities, social events"


def find_social_events(interests: str) -> List[dict]:
    """Finds social events based on a list of user interests."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        interest_list = [i.strip().lower() for i in interests.split(',')]

        found_events = []
        for interest in interest_list:
            cursor.execute(
                "SELECT event_name, date, location FROM social_events WHERE interest_tag = ? AND date > ?",
                (interest, datetime.now().strftime('%Y-%m-%d'))
            )
            for event in cursor.fetchall():
                found_events.append({
                    "interest": interest,
                    "name": event[0],
                    "date": event[1],
                    "location": event[2],
                })

        conn.close()

        # If no events found, return some default suggestions
        if not found_events:
            return [{
                "interest": "general",
                "name": "Local community meetup",
                "date": "Check local community boards",
                "location": "Your area"
            }]

        return found_events
    except Exception as e:
        print(f"Error finding social events: {e}")
        return [{
            "interest": "general",
            "name": "Local community activities",
            "date": "Various dates",
            "location": "Check local resources"
        }]


# --- State for LangGraph ---

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], lambda x, y: x + y]
    user_name: str
    initial_mood: str
    initial_health_data: dict
    mood_score: int
    mood_analysis: str
    social_suggestion: str
    health_score: int
    health_suggestion: str
    final_context_prompt: str


# --- Base Agent Class ---

class BaseAgent:
    """Base class for all specialized agents."""

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.model = 'gemini-2.0-flash-exp'

    def _format_messages(self, state: AgentState) -> List[AnyMessage]:
        """Prepares messages for the model (as LangChain messages for state history)."""
        initial_context = f"User Name: {state['user_name']}. Initial Mood: {state['initial_mood']}. Initial Health: {state['initial_health_data']}."

        return [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=initial_context)
        ]

    def _create_gemini_content(self, state: AgentState) -> List[types.Content]:
        """Creates the native Gemini Content object for the API call."""
        initial_context_str = f"User Name: {state['user_name']}. Initial Mood: {state['initial_mood']}. Initial Health: {state['initial_health_data']}."

        full_message = f"{self.system_prompt}\n\n[CONTEXT]: {initial_context_str}"

        return [
            types.Content(
                role="user",
                parts=[types.Part(text=full_message)]
            )
        ]

    async def __call__(self, state: AgentState):
        """Runs the agent and returns a dictionary update for the state."""

        messages_lc = self._format_messages(state)

        if not CLIENT:
            print(f"WARNING: {self.__class__.__name__} skipped - no API key")
            return {
                "messages": messages_lc + [SystemMessage(content="Agent skipped due to missing API key.")]
            }

        messages_gemini = self._create_gemini_content(state)

        try:
            # Run synchronous API call in thread pool
            response = await asyncio.to_thread(
                CLIENT.models.generate_content_stream,
                model=self.model,
                contents=messages_gemini
            )

            full_response = ""
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text

            return {
                "messages": messages_lc + [SystemMessage(content=f"Agent response: {full_response}")]
            }
        except Exception as e:
            print(f"Error in {self.__class__.__name__}: {e}")
            return {
                "messages": messages_lc + [SystemMessage(content=f"Agent error: {str(e)}")]
            }


# --- Agent 1: Sentiment Agent ---

class SentimentAgent(BaseAgent):
    def __init__(self):
        system_prompt = (
            "You are a specialized **Mood/Sentiment Analysis Agent**. "
            "Your task is to analyze the provided initial context (user name, mood, health data) "
            "and produce a mood score and a short analysis. "
            "Output *only* a JSON object with the following schema: "
            "{'mood_score': int (1-10, 1=very low, 10=very high), 'mood_analysis': str (a short, one-sentence justification)}."
        )
        super().__init__(system_prompt)

    async def __call__(self, state: AgentState):
        result = await super().__call__(state)

        full_response = result['messages'][-1].content.replace("Agent response: ", "")

        try:
            json_str = full_response.strip().replace("```json", "").replace("```", "")
            data = json.loads(json_str)

            return {
                "mood_score": data.get("mood_score", 5),
                "mood_analysis": data.get("mood_analysis", "Mood analyzed based on initial context."),
                "messages": result["messages"]
            }
        except Exception as e:
            if 'skipped' in full_response.lower():
                return {
                    "mood_score": 5,
                    "mood_analysis": full_response,
                    "messages": result["messages"]
                }
            print(f"Error parsing Sentiment Agent output: {e}")
            return {
                "mood_score": 5,
                "mood_analysis": f"Based on feeling '{state['initial_mood']}', mood appears moderate.",
                "messages": result["messages"]
            }


# --- Agent 2: Social Agent ---

class SocialAgent(BaseAgent):
    def __init__(self):
        self.tool_functions = [get_user_interests, find_social_events]
        self.tool_map = {tool.__name__: tool for tool in self.tool_functions}

        system_prompt = (
            "You are a specialized **Social Event Agent**. "
            "Your task is to use the `get_user_interests` tool for the user name provided in the context. "
            "Then, use the `find_social_events` tool with the retrieved interests to find relevant, upcoming events. "
            "Finally, suggest one or two specific, compelling events to the user based on the tool results. "
            "Your final output should be a single string for the 'social_suggestion' field, "
            "starting with 'Based on your interests in X, you might enjoy Y on Z at P.'"
        )
        super().__init__(system_prompt)

    async def __call__(self, state: AgentState):
        messages_lc = self._format_messages(state)

        if not CLIENT:
            return {
                "social_suggestion": "Consider checking local community boards for events that match your interests.",
                "messages": messages_lc
            }

        messages_gemini = self._create_gemini_content(state)

        try:
            max_iterations = 5
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                response = await asyncio.to_thread(
                    CLIENT.models.generate_content,
                    model=self.model,
                    contents=messages_gemini,
                    config=types.GenerateContentConfig(tools=self.tool_functions)
                )

                if response.candidates and response.candidates[0].content.parts:
                    parts = response.candidates[0].content.parts

                    # Check for function calls
                    function_calls = [p for p in parts if hasattr(p, 'function_call') and p.function_call]

                    if function_calls:
                        tool_output_parts = []

                        for part in function_calls:
                            call = part.function_call
                            tool_func = self.tool_map.get(call.name)

                            if not tool_func:
                                raise ValueError(f"Unknown tool: {call.name}")

                            # Execute the tool
                            tool_result = await asyncio.to_thread(tool_func, **dict(call.args))

                            tool_output_parts.append(
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=call.name,
                                        response={"result": tool_result}
                                    )
                                )
                            )

                        # Append model's call and tool results
                        messages_gemini.append(types.Content(role="model", parts=parts))
                        messages_gemini.append(types.Content(role="user", parts=tool_output_parts))
                        continue

                    # Check for text response
                    text_parts = [p for p in parts if hasattr(p, 'text') and p.text]
                    if text_parts:
                        suggestion = " ".join([p.text for p in text_parts]).strip()
                        lc_messages = messages_lc + [SystemMessage(content=f"Social Agent Suggestion: {suggestion}")]
                        return {
                            "social_suggestion": suggestion,
                            "messages": lc_messages
                        }

                # If we get here without function calls or text, break
                break

            # Fallback if max iterations reached
            return {
                "social_suggestion": "Consider exploring local community events that align with your wellness goals.",
                "messages": messages_lc
            }

        except Exception as e:
            print(f"Error in Social Agent: {e}")
            return {
                "social_suggestion": "Consider checking local community resources for social activities.",
                "messages": messages_lc
            }


# --- Agent 3: Health Agent ---

class HealthAgent(BaseAgent):
    def __init__(self):
        system_prompt = (
            "You are a specialized **Health and Fitness Agent**. "
            "Analyze the provided `initial_health_data` (steps, sleep). "
            "Calculate a **Health Score** (1-100, where 100 is excellent). "
            "Provide a one-sentence health suggestion based on the data. "
            "Output *only* a JSON object with the following schema: "
            "{'health_score': int, 'health_suggestion': str}."
        )
        super().__init__(system_prompt)

    async def __call__(self, state: AgentState):
        health_data = state['initial_health_data']
        steps = health_data.get('steps_today', 0)
        sleep = health_data.get('sleep_hours_last_night', 0)

        # Deterministic score calculation
        score = min(steps / 10000 * 50, 50) + min(sleep / 8 * 50, 50)
        score = round(score)

        suggestion = ""
        if sleep < 7.0 and steps < 5000:
            suggestion = "You were low on both sleep and activity. Prioritize an early bedtime and a 30-minute walk."
        elif sleep < 7.0:
            suggestion = "Your sleep was low. Try to reduce screen time an hour before bed."
        elif steps < 5000:
            suggestion = "Your steps are low. Incorporate a short walk during lunch today."
        else:
            suggestion = "Your health metrics look good! Keep up the great work."

        result = await super().__call__(state)

        return {
            "health_score": score,
            "health_suggestion": suggestion,
            "messages": result["messages"] + [
                SystemMessage(content=f"Health Agent Analysis: Score={score}, Suggestion='{suggestion}'")
            ]
        }


# --- Final Prompt Generator ---

async def generate_final_prompt(state: AgentState) -> dict:
    """
    Combines the outputs of all specialized agents into a single, cohesive prompt
    for the conversational Wellness Agent.
    """
    user_name = state['user_name']
    initial_mood = state['initial_mood']
    steps = state['initial_health_data'].get('steps_today', 'N/A')
    sleep = state['initial_health_data'].get('sleep_hours_last_night', 'N/A')

    mood_analysis = state.get('mood_analysis', 'No mood analysis available.')
    social_suggestion = state.get('social_suggestion', 'No social suggestions available.')
    health_suggestion = state.get('health_suggestion', 'No health suggestions available.')
    health_score = state.get('health_score', 'N/A')

    prompt = f"""
*** FINAL CONTEXT FOR WELLNESS AGENT ***

The user is {user_name}.

Initial State:
- User reported feeling: '{initial_mood}'
- Steps today: {steps}
- Sleep last night: {sleep} hours

Agent-Generated Analysis:
1. **Mood**: {mood_analysis} 
2. **Health Score ({health_score}/100)**: {health_suggestion}
3. **Social Suggestion**: {social_suggestion}

**Instructions for Wellness Agent:**

1. **Personalized Greeting**: Start the conversation warmly, using the user's name.
2. **Acknowledge Data**: Gently acknowledge the most notable piece of data (e.g., low sleep or low steps).
3. **Integrate Suggestions**: Weave in the health and social suggestions naturally as conversation points, but do NOT present them as a list of facts. 
4. **Focus**: Immediately shift the conversation to an empathetic check-in, keeping the Wellness Agent's original goals and boundaries in mind.

Start your final response with the actual conversational text the Wellness Agent should say to the user.
"""

    # Save conversation if database is available
    try:
        from setup_database import save_conversation
        await asyncio.to_thread(save_conversation, user_name, prompt)
    except ImportError:
        print("WARNING: Could not import save_conversation. Skipping database save.")
    except Exception as e:
        print(f"WARNING: Could not save conversation: {e}")

    return {"final_context_prompt": prompt}

