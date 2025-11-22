# live_transcript_handler.py
"""
Handles live transcript processing and coordination between agents.
Provides real-time analysis and suggestions during voice conversations.
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import traceback
from collections import deque

from agents import SentimentAgent, SocialAgent, HealthAgent, AgentState
from langchain_core.messages import HumanMessage, SystemMessage


@dataclass
class TranscriptSegment:
    """Represents a segment of conversation transcript."""
    timestamp: datetime
    speaker: str  # "user" or "agent"
    text: str
    sentiment_score: Optional[int] = None
    detected_topics: List[str] = field(default_factory=list)


@dataclass
class LiveAnalysisResult:
    """Results from real-time agent analysis."""
    mood_score: int
    mood_trend: str  # "improving", "declining", "stable"
    mood_context: str
    social_suggestions: List[str]
    health_insights: str
    recommended_topics: List[str]
    urgency_level: str  # "low", "medium", "high"


class TranscriptBuffer:
    """Manages a sliding window of conversation transcript."""

    def __init__(self, max_segments: int = 20, analysis_window: int = 5):
        self.segments: deque[TranscriptSegment] = deque(maxlen=max_segments)
        self.analysis_window = analysis_window
        self._lock = asyncio.Lock()

    async def add_segment(self, segment: TranscriptSegment):
        """Add a new transcript segment."""
        async with self._lock:
            self.segments.append(segment)

    async def get_recent_user_text(self, num_segments: Optional[int] = None) -> str:
        """Get recent user utterances as a single string."""
        async with self._lock:
            n = num_segments or self.analysis_window
            user_segments = [s for s in list(self.segments)[-n:] if s.speaker == "user"]
            return " ".join([s.text for s in user_segments])

    async def get_full_conversation(self) -> str:
        """Get the entire conversation history."""
        async with self._lock:
            return "\n".join([
                f"{s.speaker.upper()}: {s.text}"
                for s in self.segments
            ])


class LiveAgentCoordinator:
    """
    Coordinates real-time analysis from multiple agents during conversation.
    Provides continuous insights to the wellness agent.
    """

    def __init__(self, user_name: str, initial_context: Dict):
        self.user_name = user_name
        self.initial_context = initial_context

        # Initialize agents
        self.sentiment_agent = SentimentAgent()
        self.social_agent = SocialAgent()
        self.health_agent = HealthAgent()

        # Transcript management
        self.transcript_buffer = TranscriptBuffer()

        # Analysis state
        self.last_analysis: Optional[LiveAnalysisResult] = None
        self.mood_history: deque[int] = deque(maxlen=10)
        self.analysis_count = 0

        # Callbacks for real-time updates
        self.on_analysis_complete: Optional[Callable] = None

        # Control flags
        self._running = False
        self._analysis_task: Optional[asyncio.Task] = None

    async def start(self, on_analysis_complete: Optional[Callable] = None):
        """Start the live coordinator."""
        self._running = True
        self.on_analysis_complete = on_analysis_complete

        # Start periodic analysis task
        self._analysis_task = asyncio.create_task(self._periodic_analysis_loop())
        print("🔄 Live Agent Coordinator started")

    async def stop(self):
        """Stop the live coordinator."""
        self._running = False
        if self._analysis_task:
            self._analysis_task.cancel()
            try:
                await self._analysis_task
            except asyncio.CancelledError:
                pass
        print("⏹️  Live Agent Coordinator stopped")

    async def add_transcript(self, speaker: str, text: str):
        """Add a new transcript segment from the conversation."""
        segment = TranscriptSegment(
            timestamp=datetime.now(),
            speaker=speaker,
            text=text
        )
        await self.transcript_buffer.add_segment(segment)

        # Log transcript addition
        speaker_emoji = "👤" if speaker == "user" else "🤖"
        print(f"\n{speaker_emoji} [Transcript] {speaker.upper()}: {text[:100]}{'...' if len(text) > 100 else ''}")

        # Trigger immediate analysis if this is a user utterance
        if speaker == "user" and len(text.split()) > 5:
            print(f"🔔 Triggering immediate analysis (user spoke {len(text.split())} words)")
            asyncio.create_task(self._analyze_now())

    async def _periodic_analysis_loop(self):
        """Runs periodic analysis every 30 seconds."""
        try:
            while self._running:
                await asyncio.sleep(30)
                if self._running:
                    await self._analyze_now()
        except asyncio.CancelledError:
            pass

    async def _analyze_now(self):
        """Run immediate analysis with all agents."""
        try:
            recent_text = await self.transcript_buffer.get_recent_user_text()

            # Skip if no recent text
            if not recent_text or len(recent_text.strip()) < 10:
                return

            full_conversation = await self.transcript_buffer.get_full_conversation()

            print(f"\n{'─' * 60}")
            print(f"🔍 LIVE ANALYSIS TRIGGERED #{self.analysis_count + 1}")
            print(f"{'─' * 60}")
            print(f"📝 Analyzing recent text: '{recent_text[:100]}...'")
            print(f"{'─' * 60}\n")

            # Build agent state
            state = AgentState(
                messages=[],
                user_name=self.user_name,
                initial_mood=recent_text,  # Use recent text as "mood"
                initial_health_data=self.initial_context.get('health_data', {}),
                mood_score=5,
                mood_analysis="",
                social_suggestion="",
                health_score=50,
                health_suggestion="",
                final_context_prompt=""
            )

            # Run agents in parallel with logging
            print("⚡ Starting parallel agent execution...")
            print("   🎭 Sentiment Agent analyzing mood...")
            print("   👥 Social Agent finding suggestions...")
            print("   💪 Health Agent evaluating wellness...\n")

            sentiment_task = asyncio.create_task(self._analyze_sentiment(state, recent_text))
            social_task = asyncio.create_task(self._analyze_social(state, recent_text))
            health_task = asyncio.create_task(self._analyze_health(state))

            # Wait for all analyses
            sentiment_result, social_result, health_result = await asyncio.gather(
                sentiment_task, social_task, health_task,
                return_exceptions=True
            )

            print("✅ All agents completed analysis\n")

            # Process results
            analysis = await self._build_analysis_result(
                sentiment_result, social_result, health_result
            )

            self.last_analysis = analysis
            self.analysis_count += 1

            # Detailed logging of results
            print(f"{'═' * 60}")
            print(f"📊 LIVE ANALYSIS RESULTS #{self.analysis_count}")
            print(f"{'═' * 60}")
            print(f"🎭 Sentiment Agent:")
            print(f"   • Mood Score: {analysis.mood_score}/10")
            print(f"   • Trend: {analysis.mood_trend.upper()}")
            print(f"   • Context: {analysis.mood_context[:80]}...")
            print(f"\n👥 Social Agent:")
            if analysis.social_suggestions:
                for i, suggestion in enumerate(analysis.social_suggestions[:3], 1):
                    print(f"   {i}. {suggestion[:70]}...")
            else:
                print(f"   • No new suggestions")
            print(f"\n💪 Health Agent:")
            print(f"   • Insight: {analysis.health_insights[:80]}...")
            print(f"\n🚨 Overall:")
            print(f"   • Urgency Level: {analysis.urgency_level.upper()}")
            print(f"   • Recommended Topics: {', '.join(analysis.recommended_topics[:3])}")
            print(f"{'═' * 60}\n")

            # Notify callback
            if self.on_analysis_complete:
                await self.on_analysis_complete(analysis)

        except Exception as e:
            print(f"❌ Error in live analysis: {e}")
            traceback.print_exc()

    async def _analyze_sentiment(self, state: AgentState, recent_text: str) -> Dict:
        """Run sentiment analysis on recent text."""
        try:
            print("   🎭 [Sentiment Agent] Starting mood analysis...")
            # Create a focused state for sentiment
            sentiment_state = AgentState(
                messages=[HumanMessage(content=f"Analyze the mood in this text: '{recent_text}'")],
                user_name=state['user_name'],
                initial_mood=recent_text,
                initial_health_data=state['initial_health_data'],
                mood_score=5,
                mood_analysis="",
                social_suggestion="",
                health_score=50,
                health_suggestion="",
                final_context_prompt=""
            )

            result = await self.sentiment_agent(sentiment_state)

            # Track mood history
            mood_score = result.get('mood_score', 5)
            self.mood_history.append(mood_score)

            print(f"   🎭 [Sentiment Agent] Complete → Mood: {mood_score}/10")

            return result
        except Exception as e:
            print(f"   ❌ [Sentiment Agent] Error: {e}")
            return {'mood_score': 5, 'mood_analysis': 'Unable to analyze mood'}

    async def _analyze_social(self, state: AgentState, recent_text: str) -> Dict:
        """Run social suggestion analysis."""
        try:
            print("   👥 [Social Agent] Finding social activities...")
            social_state = AgentState(
                messages=[HumanMessage(
                    content=f"Based on this conversation: '{recent_text}', suggest relevant social activities.")],
                user_name=state['user_name'],
                initial_mood=recent_text,
                initial_health_data=state['initial_health_data'],
                mood_score=5,
                mood_analysis="",
                social_suggestion="",
                health_score=50,
                health_suggestion="",
                final_context_prompt=""
            )

            result = await self.social_agent(social_state)
            suggestion_preview = result.get('social_suggestion', '')[:50]
            print(f"   👥 [Social Agent] Complete → '{suggestion_preview}...'")
            return result
        except Exception as e:
            print(f"   ❌ [Social Agent] Error: {e}")
            return {'social_suggestion': 'Consider local community activities'}

    async def _analyze_health(self, state: AgentState) -> Dict:
        """Run health analysis."""
        try:
            print("   💪 [Health Agent] Analyzing wellness metrics...")
            result = await self.health_agent(state)
            health_score = result.get('health_score', 50)
            print(f"   💪 [Health Agent] Complete → Health Score: {health_score}/100")
            return result
        except Exception as e:
            print(f"   ❌ [Health Agent] Error: {e}")
            return {'health_score': 50, 'health_suggestion': 'Maintain healthy habits'}

    async def _build_analysis_result(
            self,
            sentiment_result: Dict,
            social_result: Dict,
            health_result: Dict
    ) -> LiveAnalysisResult:
        """Combine agent results into a coherent analysis."""

        # Determine mood trend
        mood_score = sentiment_result.get('mood_score', 5)
        mood_trend = self._calculate_mood_trend()

        # Determine urgency
        urgency = self._calculate_urgency(mood_score, mood_trend)

        # Extract social suggestions
        social_text = social_result.get('social_suggestion', '')
        social_suggestions = [s.strip() for s in social_text.split('.') if s.strip()]

        # Build recommended topics
        topics = []
        if mood_score < 4:
            topics.extend(["coping strategies", "self-care", "emotional support"])
        if urgency == "high":
            topics.append("immediate wellness techniques")
        topics.extend(["social connection", "healthy activities"])

        return LiveAnalysisResult(
            mood_score=mood_score,
            mood_trend=mood_trend,
            mood_context=sentiment_result.get('mood_analysis', ''),
            social_suggestions=social_suggestions[:3],  # Top 3
            health_insights=health_result.get('health_suggestion', ''),
            recommended_topics=topics,
            urgency_level=urgency
        )

    def _calculate_mood_trend(self) -> str:
        """Calculate mood trend from history."""
        if len(self.mood_history) < 3:
            return "stable"

        recent = list(self.mood_history)[-3:]
        if recent[-1] > recent[0] + 1:
            return "improving"
        elif recent[-1] < recent[0] - 1:
            return "declining"
        return "stable"

    def _calculate_urgency(self, mood_score: int, trend: str) -> str:
        """Determine urgency level."""
        if mood_score <= 3 or (mood_score <= 4 and trend == "declining"):
            return "high"
        elif mood_score <= 5 or trend == "declining":
            return "medium"
        return "low"

    async def get_current_suggestions(self) -> Optional[LiveAnalysisResult]:
        """Get the most recent analysis results."""
        return self.last_analysis

    async def get_context_for_agent(self) -> str:
        """Generate a context string for the wellness agent."""
        if not self.last_analysis:
            return ""

        analysis = self.last_analysis

        context_parts = [
            f"\n[REAL-TIME CONTEXT UPDATE]",
            f"Current Mood: {analysis.mood_score}/10 (trend: {analysis.mood_trend})",
            f"Urgency: {analysis.urgency_level.upper()}"
        ]

        if analysis.mood_context:
            context_parts.append(f"Context: {analysis.mood_context}")

        if analysis.social_suggestions:
            context_parts.append(f"Social Suggestions: {'; '.join(analysis.social_suggestions)}")

        if analysis.health_insights:
            context_parts.append(f"Health Note: {analysis.health_insights}")

        if analysis.recommended_topics:
            context_parts.append(f"Consider discussing: {', '.join(analysis.recommended_topics[:3])}")

        context_parts.append("[END CONTEXT UPDATE]\n")

        return "\n".join(context_parts)