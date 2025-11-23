# ETHOS – Your AI Wellness Companion

ETHOS is a voice-first AI wellness companion that checks in on you, listens when you need to vent, and gently nudges you towards healthier habits and social connection. Built for the TUM Hackathon, it combines real-time audio, agentic AI, and a Kotlin Multiplatform mobile app into one cohesive experience. :contentReference[oaicite:0]{index=0}

---

## Table of Contents

- [Why ETHOS](#why-ethos)
- [What ETHOS Does](#what-ethos-does)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Backend Setup](#backend-setup)
- [Mobile App (Kotlin Multiplatform)](#mobile-app-kotlin-multiplatform)
- [Running the Demo](#running-the-demo)
- [Roadmap](#roadmap)
- [Disclaimer](#disclaimer)

---

## Why ETHOS

Modern life is lonely and stressful. Most “wellness” apps either feel like static forms or firehose you with generic content. There’s rarely something that:

- Proactively asks *“How are you really doing?”*
- Lets you **talk naturally**, not just tap buttons.
- Responds with **empathetic, context-aware** support instead of canned tips.
- Nudges you towards **real-world actions**, like going out or doing something you enjoy.

ETHOS is designed to fill that gap: a friendly, always-available companion that listens, reflects, and suggests small, doable steps that make you feel a bit better.

The accompanying slide deck (`Presentation - Your AI Wellness Companion.pptx`) outlines this narrative with sections like *ETHOS*, *Why ETHOS*, *How ETHOS Works*, and an *ETHOS Demo!* that showcases a real conversation scenario. :contentReference[oaicite:1]{index=1}

---

## What ETHOS Does

Right now, ETHOS focuses on being a **solid, end-to-end hackathon prototype** with:

- 🎙 **Voice-to-Voice Conversations**  
  Talk to ETHOS through the mobile app; the backend streams your audio to an LLM (Gemini Live), which replies in natural speech.

- 💭 **Wellness Check-ins**  
  ETHOS asks how you are, follows up with empathetic questions, and mirrors back what it understood (mood, stressors, concerns).

- 🧠 **Agentic Wellness Brain**  
  A dedicated `WellnessAgentLive` uses a `UserContext` + `HealthSnapshot` to reason about:
  - How you’ve been feeling in this session.
  - What topics keep recurring (stress, relationships, work, etc.).
  - What kind of response is appropriate (validation, reframing, gentle advice).

- 🕸 **Multi-Agent Orchestration (Extensible)**  
  An orchestrator (`wellness_orchestrator_live`) can route your requests to specialized tools/agents, e.g.:
  - A **wellness coach agent** (core ETHOS personality).
  - **Event / activity suggestion tools** (Ticketmaster API, social events DB) to suggest things you can actually go out and do.

- 📱 **Kotlin Multiplatform Frontend**  
  A simple but effective mobile UI:
  - “Start Session” button to open a live voice session.
  - Streaming transcripts of both user and ETHOS messages.
  - Visual feedback that the conversation is live.

- 🎬 **Demo Scenario**  
  In the demo (as shown in the *ETHOS Demo!* slide), a user vents about relationship stress, and ETHOS listens, reflects the key emotions, and suggests small, realistic steps instead of generic advice. :contentReference[oaicite:2]{index=2}

---

## Architecture

High-level flow:

1. **User talks into the phone** (Kotlin Multiplatform app).
2. The app streams microphone audio over a **WebSocket** to the Python backend.
3. The backend:
   - Maintains a **session** for that user.
   - Streams audio to **Gemini Live**.
   - Wraps model responses inside the **WellnessAgentLive** logic.
   - Optionally calls other tools (e.g. event APIs, DB) via the **orchestrator**.
4. ETHOS sends back:
   - **Text transcripts** (for UI display).
   - **Audio responses** (for playback in the app).

Conceptually:

```text
[ Kotlin MPP App ]
     |  (audio, text)
     v
[ FastAPI Backend + WebSocket ]
     |
     v
[ WellnessAgentLive  ] --(tools)--> [ Ticketmaster API / Social Events DB ]
     |
     v
[ Gemini Live Model ]
     |
     v
[ Audio + Text Response ] --> back to App
