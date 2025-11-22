# client_examples.py - Example clients for the enhanced API

import asyncio
import aiohttp
import json
from typing import Optional


# ============================================================================
# Example 1: Simple HTTP Polling Client
# ============================================================================

class PollingClient:
    """
    Simple client that starts a session and polls for status updates.
    Good for: Simple integrations, serverless functions, basic scripts
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id: Optional[str] = None

    async def start_session(self, name: str, mood: str = None, **kwargs):
        """Start a new wellness session."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "name": name,
                "mood": mood,
                **kwargs
            }

            async with session.post(f"{self.base_url}/start-session", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.session_id = data["session_id"]
                    print(f"✅ Session started: {self.session_id}")
                    return data
                else:
                    raise Exception(f"Failed to start session: {resp.status}")

    async def check_status(self):
        """Check if the session has ended."""
        if not self.session_id:
            raise Exception("No active session")

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/session/{self.session_id}/status") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    raise Exception(f"Failed to check status: {resp.status}")

    async def wait_for_session_end(self, poll_interval: float = 2.0):
        """
        Poll the API until the session ends.
        Returns the final session data when complete.
        """
        print(f"⏳ Waiting for session to end (polling every {poll_interval}s)...")

        while True:
            status = await self.check_status()

            if status["ended"]:
                print(f"\n✅ Session ended!")
                print(f"   Reason: {status.get('reason')}")
                print(f"   Duration: {status.get('duration_seconds', 0):.1f}s")
                return status

            print(f"   Status: {status['status']} (still running...)")
            await asyncio.sleep(poll_interval)

    async def end_session(self, reason: str = "client_requested"):
        """Manually end the session."""
        if not self.session_id:
            raise Exception("No active session")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"{self.base_url}/session/{self.session_id}/end",
                    json={"reason": reason}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Session ended manually: {reason}")
                    return data
                else:
                    raise Exception(f"Failed to end session: {resp.status}")


# ============================================================================
# Example 2: WebSocket Client (Real-time)
# ============================================================================

class WebSocketClient:
    """
    WebSocket client for real-time session updates.
    Good for: Interactive applications, dashboards, mobile apps
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.session_id: Optional[str] = None
        self.ws = None

    async def start_session(self, name: str, mood: str = None, **kwargs):
        """Start a new wellness session."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "name": name,
                "mood": mood,
                **kwargs
            }

            async with session.post(f"{self.base_url}/start-session", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.session_id = data["session_id"]
                    print(f"✅ Session started: {self.session_id}")
                    return data
                else:
                    raise Exception(f"Failed to start session: {resp.status}")

    async def connect_websocket(self):
        """Connect to WebSocket for real-time updates."""
        if not self.session_id:
            raise Exception("No active session")

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                    f"{self.ws_url}/ws/session/{self.session_id}"
            ) as ws:
                self.ws = ws
                print(f"🔌 Connected to WebSocket")

                # Listen for messages
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        await self.handle_message(data)

                        # Exit when session ends
                        if data.get("type") == "session_ended":
                            print(f"\n✅ Session ended via WebSocket!")
                            print(f"   Reason: {data.get('reason')}")
                            print(f"   Duration: {data.get('duration_seconds', 0):.1f}s")
                            break

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"❌ WebSocket error: {ws.exception()}")
                        break

    async def handle_message(self, data: dict):
        """Handle incoming WebSocket messages."""
        msg_type = data.get("type")

        if msg_type == "connected":
            print(f"✅ WebSocket connected to session: {data.get('session_id')}")

        elif msg_type == "session_status_update":
            print(f"📊 Status update: {data.get('status')} - {data.get('message', '')}")

        elif msg_type == "session_ended":
            # This is the important one - session has ended!
            pass  # Handled in connect_websocket

        else:
            print(f"📨 Received: {msg_type}")

    async def send_end_request(self):
        """Request session end via WebSocket."""
        if self.ws:
            await self.ws.send_str("end_session")
            print("📤 Sent end session request")


# ============================================================================
# Example 3: Hybrid Client (Best of both worlds)
# ============================================================================

class HybridClient:
    """
    Combines HTTP and WebSocket approaches.
    Starts session via HTTP, gets updates via WebSocket, can end via either.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.session_id: Optional[str] = None

    async def start_session_and_monitor(self, name: str, mood: str = None, **kwargs):
        """Start session and monitor via WebSocket until it ends."""

        # 1. Start session via HTTP
        async with aiohttp.ClientSession() as http_session:
            payload = {
                "name": name,
                "mood": mood,
                **kwargs
            }

            async with http_session.post(f"{self.base_url}/start-session", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.session_id = data["session_id"]
                    print(f"✅ Session started: {self.session_id}")
                else:
                    raise Exception(f"Failed to start session: {resp.status}")

        # 2. Connect to WebSocket for real-time updates
        async with aiohttp.ClientSession() as ws_session:
            async with ws_session.ws_connect(
                    f"{self.ws_url}/ws/session/{self.session_id}"
            ) as ws:
                print(f"🔌 Connected to WebSocket")

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")

                        if msg_type == "session_ended":
                            print(f"\n🎉 SESSION ENDED NOTIFICATION RECEIVED!")
                            print(f"{'=' * 60}")
                            print(f"   Reason: {data.get('reason')}")
                            print(f"   Duration: {data.get('duration_seconds', 0):.1f}s")
                            print(f"   Ended at: {data.get('timestamp')}")
                            print(f"{'=' * 60}")
                            return data

                        elif msg_type == "session_status_update":
                            print(f"📊 {data.get('message', 'Status update')}")

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"❌ WebSocket error")
                        break


# ============================================================================
# Usage Examples
# ============================================================================

async def example_polling():
    """Example: Using polling to detect session end."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: HTTP Polling Client")
    print("=" * 60 + "\n")

    client = PollingClient()

    # Start session
    await client.start_session(
        name="Alice",
        mood="feeling a bit tired",
        health={
            "steps_today": 3000,
            "sleep_hours_last_night": 6.5
        }
    )

    # Poll until session ends
    final_status = await client.wait_for_session_end(poll_interval=3.0)
    print(f"\n✅ Final status: {final_status}")


async def example_websocket():
    """Example: Using WebSocket for real-time updates."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: WebSocket Client (Real-time)")
    print("=" * 60 + "\n")

    client = WebSocketClient()

    # Start session
    await client.start_session(
        name="Bob",
        mood="stressed about work"
    )

    # Connect and listen for updates
    await client.connect_websocket()


async def example_hybrid():
    """Example: Hybrid approach (recommended)."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Hybrid Client (Recommended)")
    print("=" * 60 + "\n")

    client = HybridClient()

    # Start and monitor in one go
    result = await client.start_session_and_monitor(
        name="Charlie",
        mood="anxious",
        goals="improve sleep and reduce stress"
    )

    print(f"\n✅ Session completed: {result}")


async def example_manual_end():
    """Example: Manually ending a session."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Manual Session End")
    print("=" * 60 + "\n")

    client = PollingClient()

    # Start session
    await client.start_session(name="Dana", mood="good")

    # Wait a bit
    print("Waiting 10 seconds before ending session...")
    await asyncio.sleep(10)

    # Manually end it
    await client.end_session("testing_manual_end")


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║         Wellness API Client Examples                        ║
║                                                              ║
║  Demonstrates different ways to detect session end:         ║
║    1. HTTP Polling (simple, works everywhere)               ║
║    2. WebSocket (real-time, efficient)                      ║
║    3. Hybrid (best of both)                                 ║
║    4. Manual End (client-controlled)                        ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Run the hybrid example (recommended approach)
    asyncio.run(example_hybrid())

    # Uncomment to try other examples:
    # asyncio.run(example_polling())
    # asyncio.run(example_websocket())
    # asyncio.run(example_manual_end())