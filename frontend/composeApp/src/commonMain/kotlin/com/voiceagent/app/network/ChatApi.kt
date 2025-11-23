// ============================================
// File: network/ChatApi.kt
// API client for wellness chat
// ============================================
package com.voiceagent.app.network

import io.ktor.client.*
import io.ktor.client.engine.cio.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import com.voiceagent.app.screens.ChatMessage

object ChatApi {
    private const val BASE_URL = "http://131.159.218.120:8000"

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    private val httpClient = HttpClient(CIO) {
        engine {
            requestTimeout = 30000
        }
    }

    suspend fun sendMessage(
        sessionId: String,
        message: String,
        currentMessages: List<ChatMessage>
    ): List<ChatMessage> {
        return try {
            val jsonBody = """
                {
                    "session_id": "$sessionId",
                    "message": "${message.replace("\"", "\\\"").replace("\n", "\\n")}"
                }
            """.trimIndent()

            println("Sending chat message: $message")

            val response: HttpResponse = httpClient.post("$BASE_URL/wellness-chat") {
                contentType(ContentType.Application.Json)
                setBody(jsonBody)
            }

            val responseText = response.bodyAsText()
            println("Chat response: $responseText")

            val responseJson = json.parseToJsonElement(responseText).jsonObject
            val messagesArray = responseJson["messages"]?.jsonArray

            if (messagesArray != null) {
                messagesArray.mapNotNull { msgElement ->
                    try {
                        val msgObj = msgElement.jsonObject
                        val role = msgObj["role"]?.jsonPrimitive?.content
                        val text = msgObj["text"]?.jsonPrimitive?.content ?: ""

                        ChatMessage(
                            text = text,
                            isUser = role == "user"
                        )
                    } catch (e: Exception) {
                        println("Error parsing message: ${e.message}")
                        null
                    }
                }
            } else {
                // Fallback to just adding assistant response
                val reply = responseJson["reply"]?.jsonPrimitive?.content
                if (reply != null) {
                    currentMessages + ChatMessage(reply, false)
                } else {
                    currentMessages
                }
            }
        } catch (e: Exception) {
            println("Error sending chat message: ${e.message}")
            e.printStackTrace()
            currentMessages + ChatMessage(
                "I'm having trouble connecting. Please try again.",
                false
            )
        }
    }

    fun cleanup() {
        httpClient.close()
    }
}