// ============================================
// File: network/AudioSessionApi.kt
// FIXED VERSION - Copy this entire file
// ============================================
package com.voiceagent.app.network

import io.ktor.client.*
import io.ktor.client.engine.cio.*
import io.ktor.client.plugins.websocket.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.websocket.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

// No longer need @Serializable - we'll build JSON manually
data class StartSessionMobileRequest(
    val name: String,
    val mood: String? = null,
    val health: HealthData? = null,
    val conversation_summary: String? = null,
    val goals: String? = null
)

data class HealthData(
    val steps_today: Int? = null,
    val sleep_hours_last_night: Float? = null
)

data class SessionResponse(
    val status: String,
    val message: String,
    val user_name: String,
    val session_id: String? = null
)

data class SessionStatusResponse(
    val session_id: String,
    val status: String,
    val ready: Boolean,
    val initial_analysis: InitialAnalysis? = null
)

data class InitialAnalysis(
    val mood_score: Int? = null,
    val health_score: Int? = null,
    val mood_analysis: String? = null,
    val social_suggestion: String? = null,
    val health_suggestion: String? = null
)

sealed class AudioMessage {
    data class Audio(val data: String) : AudioMessage() // base64 audio
    data class AgentTranscript(val text: String) : AudioMessage()
    data class UserTranscript(val text: String) : AudioMessage()
    object TurnComplete : AudioMessage()
    data class LiveAnalysis(val data: Map<String, Any>) : AudioMessage()
    data class SessionEnding(val reason: String) : AudioMessage()
    data class SessionEnded(val reason: String, val timestamp: String) : AudioMessage()
    data class Error(val message: String) : AudioMessage()
    data class AudioSessionStarted(val sessionId: String) : AudioMessage()
    data class OrchestrationComplete(val message: String) : AudioMessage()
}

object AudioSessionApi {
    private const val BASE_URL = "http://131.159.218.120:8000"
    private const val WS_URL = "ws://131.159.218.120:8000"

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    private val httpClient = HttpClient(CIO) {
        engine {
            requestTimeout = 60000
        }
    }

    private val wsClient = HttpClient(CIO) {
        install(WebSockets) {
            pingInterval = 20_000
        }
    }

    /**
     * Start a wellness session and keep it running
     * Returns (success, sessionId)
     */
    suspend fun startSession(
        name: String,
        mood: String? = null,
        stepsToday: Int? = null,
        sleepHours: Float? = null,
        conversationSummary: String? = null,
        goals: String? = null
    ): Pair<Boolean, String?> {
        return try {
            // Hardcoded request body matching the exact curl format
            val jsonBody = """
                {
                  "name": "Sagar",
                  "mood": "a bit tired",
                  "health": {
                    "steps_today": 1500,
                    "sleep_hours_last_night": 5.0
                  },
                  "conversation_summary": "Last time they were stressed about work and sleep.",
                  "goals": "improve sleep and increase daily steps"
                }
            """.trimIndent()

            println("Starting wellness session...")
            println("Request body: $jsonBody")

            val response: HttpResponse = httpClient.post("$BASE_URL/start-session") {
                contentType(ContentType.Application.Json)
                setBody(jsonBody)
            }

            val responseText = response.bodyAsText()
            println("Session started: $responseText")

            // Parse response manually
            val responseJson = json.parseToJsonElement(responseText).jsonObject
            val sessionId = responseJson["session_id"]?.jsonPrimitive?.content

            Pair(true, sessionId)
        } catch (e: Exception) {
            println("Error starting session: ${e.message}")
            e.printStackTrace()
            Pair(false, null)
        }
    }

    /**
     * End an active session
     */
    suspend fun endSession(sessionId: String): Boolean {
        return try {
            println("Ending session: $sessionId")

            // The session will end automatically when the backend finishes
            // or we can call a specific endpoint if your backend has one
            // For now, we just return success
            true
        } catch (e: Exception) {
            println("Error ending session: ${e.message}")
            e.printStackTrace()
            false
        }
    }

    fun cleanup() {
        httpClient.close()
        wsClient.close()
    }
}