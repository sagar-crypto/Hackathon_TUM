// ============================================
// File: network/EventsApi.kt
// API client for events
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

data class LiveEvent(
    val id: String,
    val name: String,
    val url: String,
    val startDateTime: String,
    val localDate: String,
    val localTime: String,
    val venueName: String,
    val city: String,
    val country: String,
    val segment: String,
    val genre: String?
)

data class SocialEvent(
    val id: Int,
    val eventName: String,
    val date: String,
    val location: String,
    val interestTag: String,
    val description: String,
    val createdAt: String
)

object EventsApi {
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

    suspend fun fetchLiveEvents(
        lat: Double,
        lon: Double,
        radiusKm: Double = 20.0,
        size: Int = 5
    ): List<LiveEvent> {
        return try {
            val jsonBody = """
                {
                    "lat": $lat,
                    "lon": $lon,
                    "radius_km": $radiusKm,
                    "size": $size
                }
            """.trimIndent()

            println("Fetching live events...")

            val response: HttpResponse = httpClient.post("$BASE_URL/events-near-me") {
                contentType(ContentType.Application.Json)
                setBody(jsonBody)
            }

            val responseText = response.bodyAsText()
            println("Live events response: $responseText")

            val responseJson = json.parseToJsonElement(responseText).jsonObject
            val eventsArray = responseJson["events"]?.jsonArray ?: return emptyList()

            eventsArray.mapNotNull { eventElement ->
                try {
                    val eventObj = eventElement.jsonObject
                    LiveEvent(
                        id = eventObj["id"]?.jsonPrimitive?.content ?: "",
                        name = eventObj["name"]?.jsonPrimitive?.content ?: "",
                        url = eventObj["url"]?.jsonPrimitive?.content ?: "",
                        startDateTime = eventObj["start_date_time"]?.jsonPrimitive?.content ?: "",
                        localDate = eventObj["local_date"]?.jsonPrimitive?.content ?: "",
                        localTime = eventObj["local_time"]?.jsonPrimitive?.content ?: "",
                        venueName = eventObj["venue_name"]?.jsonPrimitive?.content ?: "",
                        city = eventObj["city"]?.jsonPrimitive?.content ?: "",
                        country = eventObj["country"]?.jsonPrimitive?.content ?: "",
                        segment = eventObj["segment"]?.jsonPrimitive?.content ?: "",
                        genre = eventObj["genre"]?.jsonPrimitive?.content
                    )
                } catch (e: Exception) {
                    println("Error parsing event: ${e.message}")
                    null
                }
            }
        } catch (e: Exception) {
            println("Error fetching live events: ${e.message}")
            e.printStackTrace()
            emptyList()
        }
    }

    suspend fun fetchSocialEvents(eventName: String = "Wellness"): List<SocialEvent> {
        return try {
            val jsonBody = """
                {
                    "event_name": "$eventName"
                }
            """.trimIndent()

            println("Fetching social events...")

            val response: HttpResponse = httpClient.post("$BASE_URL/social-events") {
                contentType(ContentType.Application.Json)
                setBody(jsonBody)
            }

            val responseText = response.bodyAsText()
            println("Social events response: $responseText")

            val responseJson = json.parseToJsonElement(responseText).jsonObject
            val eventsArray = responseJson["events"]?.jsonArray ?: return emptyList()

            eventsArray.mapNotNull { eventElement ->
                try {
                    val eventObj = eventElement.jsonObject
                    SocialEvent(
                        id = eventObj["id"]?.jsonPrimitive?.content?.toIntOrNull() ?: 0,
                        eventName = eventObj["event_name"]?.jsonPrimitive?.content ?: "",
                        date = eventObj["date"]?.jsonPrimitive?.content ?: "",
                        location = eventObj["location"]?.jsonPrimitive?.content ?: "",
                        interestTag = eventObj["interest_tag"]?.jsonPrimitive?.content ?: "",
                        description = eventObj["description"]?.jsonPrimitive?.content ?: "",
                        createdAt = eventObj["created_at"]?.jsonPrimitive?.content ?: ""
                    )
                } catch (e: Exception) {
                    println("Error parsing social event: ${e.message}")
                    null
                }
            }
        } catch (e: Exception) {
            println("Error fetching social events: ${e.message}")
            e.printStackTrace()
            emptyList()
        }
    }

    fun cleanup() {
        httpClient.close()
    }
}