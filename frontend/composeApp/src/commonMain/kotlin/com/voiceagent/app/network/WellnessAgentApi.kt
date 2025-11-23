// ============================================
// File: network/WellnessAgentApi.kt
// Copy this entire file
// ============================================
package com.voiceagent.app.network

import io.ktor.client.*
import io.ktor.client.engine.cio.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*

object WellnessAgentApi {
    private const val BASE_URL = "http://172.20.10.4:8000"

    private val client = HttpClient(CIO) {
        engine { requestTimeout = 60000 }
    }

    suspend fun checkHealth(): Boolean {
        return try {
            val response: HttpResponse = client.get("$BASE_URL/health-check")
            response.bodyAsText().contains("ok")
        } catch (e: Exception) {
            false
        }
    }

    suspend fun startSession(
        name: String,
        mood: String?,
        stepsToday: Int?,
        sleepHours: Float?,
        conversationSummary: String?,
        goals: String?
    ): Pair<Boolean, String> {
        return try {
            val healthJson = if (stepsToday != null || sleepHours != null) {
                buildString {
                    append("\"health\": {")
                    val parts = mutableListOf<String>()
                    stepsToday?.let { parts.add("\"steps_today\": $it") }
                    sleepHours?.let { parts.add("\"sleep_hours_last_night\": $it") }
                    append(parts.joinToString(", "))
                    append("}")
                }
            } else null

            val bodyJson = buildString {
                append("{\"name\": \"$name\"")
                mood?.let { append(", \"mood\": \"$it\"") }
                healthJson?.let { append(", $it") }
                conversationSummary?.let { append(", \"conversation_summary\": \"$it\"") }
                goals?.let { append(", \"goals\": \"$it\"") }
                append("}")
            }

            val response: HttpResponse = client.post("$BASE_URL/start-session") {
                contentType(ContentType.Application.Json)
                setBody(bodyJson)
            }
            val body = response.bodyAsText()
            val success = body.contains("ok")
            Pair(success, if (success) "Session started!" else "Failed")
        } catch (e: Exception) {
            Pair(false, "Connection error: ${e.message}")
        }
    }
}