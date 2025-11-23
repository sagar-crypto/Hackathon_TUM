// ============================================
// File: screens/InsightsScreen.kt
// Modern insights dashboard with analytics and events
// ============================================
package com.voiceagent.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voiceagent.app.network.EventsApi
import com.voiceagent.app.network.LiveEvent
import com.voiceagent.app.network.SocialEvent
import kotlinx.coroutines.launch
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.PI

@Composable
fun InsightsScreen(
    onBack: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var liveEvents by remember { mutableStateOf<List<LiveEvent>>(emptyList()) }
    var socialEvents by remember { mutableStateOf<List<SocialEvent>>(emptyList()) }
    var isLoadingLive by remember { mutableStateOf(true) }
    var isLoadingSocial by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        coroutineScope.launch {
            try {
                liveEvents = EventsApi.fetchLiveEvents(
                    lat = 48.137371,
                    lon = 11.575328,
                    radiusKm = 20.0,
                    size = 5
                )
            } catch (e: Exception) {
                println("Error loading live events: ${e.message}")
            } finally {
                isLoadingLive = false
            }
        }

        coroutineScope.launch {
            try {
                socialEvents = EventsApi.fetchSocialEvents("Wellness")
            } catch (e: Exception) {
                println("Error loading social events: ${e.message}")
            } finally {
                isLoadingSocial = false
            }
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF5F7FA))
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding(),
            contentPadding = PaddingValues(bottom = 24.dp)
        ) {
            // Header
            item {
                InsightsHeader(onBack)
            }

            // Happiness Score Card
            item {
                HappinessScoreCard()
            }

            // EQ Graph Section
            item {
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "Emotional Balance",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF2C3E50),
                    modifier = Modifier.padding(horizontal = 20.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
            }

            // Weekly EQ Graph
            item {
                WeeklyEQGraph()
            }

            // Monthly Trends
            item {
                Spacer(modifier = Modifier.height(16.dp))
                MonthlyTrendsCard()
            }

            // Events Section
            item {
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    text = "Events Near You",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF2C3E50),
                    modifier = Modifier.padding(horizontal = 20.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
            }

            // Live Events
            if (isLoadingLive) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(160.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(32.dp),
                            color = Color(0xFF4facfe)
                        )
                    }
                }
            } else if (liveEvents.isNotEmpty()) {
                item {
                    LazyRow(
                        contentPadding = PaddingValues(horizontal = 20.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(liveEvents) { event ->
                            LiveEventCard(event)
                        }
                    }
                }
            }

            // Social Events Section
            item {
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    text = "Wellness Events",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF2C3E50),
                    modifier = Modifier.padding(horizontal = 20.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
            }

            if (isLoadingSocial) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(120.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(32.dp),
                            color = Color(0xFF43e97b)
                        )
                    }
                }
            } else if (socialEvents.isNotEmpty()) {
                items(socialEvents.size) { index ->
                    SocialEventCard(socialEvents[index])
                    if (index < socialEvents.size - 1) {
                        Spacer(modifier = Modifier.height(12.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun InsightsHeader(onBack: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 20.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(CircleShape)
                .background(Color.White),
            contentAlignment = Alignment.Center
        ) {
            IconButton(
                onClick = onBack,
                modifier = Modifier.size(44.dp)
            ) {
                Text(
                    text = "←",
                    color = Color(0xFF2C3E50),
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }

        Spacer(modifier = Modifier.width(16.dp))

        Text(
            text = "Insights",
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF2C3E50)
        )
    }
}

@Composable
private fun HappinessScoreCard() {
    var animatedScore by remember { mutableStateOf(0f) }

    LaunchedEffect(Unit) {
        animate(
            initialValue = 0f,
            targetValue = 78f,
            animationSpec = tween(durationMillis = 2000, easing = FastOutSlowInEasing)
        ) { value, _ ->
            animatedScore = value
        }
    }

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        shape = RoundedCornerShape(24.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Box(
            modifier = Modifier
                .background(
                    brush = Brush.linearGradient(
                        colors = listOf(
                            Color(0xFFFFD93D).copy(alpha = 0.1f),
                            Color(0xFFFFE066).copy(alpha = 0.05f)
                        )
                    )
                )
                .padding(24.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        text = "Happiness Score",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF2C3E50).copy(alpha = 0.7f)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "${animatedScore.toInt()}%",
                        fontSize = 48.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFFFB74D)
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Keep up the great work!",
                        fontSize = 14.sp,
                        color = Color(0xFF2C3E50).copy(alpha = 0.6f)
                    )
                }

                // Animated emoji
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .clip(CircleShape)
                        .background(
                            brush = Brush.radialGradient(
                                colors = listOf(
                                    Color(0xFFFFD93D),
                                    Color(0xFFFFE066)
                                )
                            )
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "😊",
                        fontSize = 40.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun WeeklyEQGraph() {
    val weekData = listOf(
        Pair("Mon", 65f),
        Pair("Tue", 72f),
        Pair("Wed", 68f),
        Pair("Thu", 78f),
        Pair("Fri", 82f),
        Pair("Sat", 75f),
        Pair("Sun", 80f)
    )

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        shape = RoundedCornerShape(24.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Column(
            modifier = Modifier.padding(20.dp)
        ) {
            Text(
                text = "This Week",
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF2C3E50)
            )

            Spacer(modifier = Modifier.height(20.dp))

            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(180.dp)
            ) {
                val spacing = size.width / (weekData.size - 1)
                val maxValue = weekData.maxOf { it.second }
                val heightScale = size.height * 0.7f / maxValue

                // Draw gradient area under line
                val path = Path().apply {
                    moveTo(0f, size.height)
                    weekData.forEachIndexed { index, (_, value) ->
                        val x = index * spacing
                        val y = size.height - (value * heightScale)
                        if (index == 0) lineTo(x, y) else lineTo(x, y)
                    }
                    lineTo(size.width, size.height)
                    close()
                }

                drawPath(
                    path = path,
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color(0xFF4facfe).copy(alpha = 0.3f),
                            Color(0xFF4facfe).copy(alpha = 0.05f)
                        )
                    )
                )

                // Draw line
                val linePath = Path()
                weekData.forEachIndexed { index, (_, value) ->
                    val x = index * spacing
                    val y = size.height - (value * heightScale)
                    if (index == 0) linePath.moveTo(x, y) else linePath.lineTo(x, y)
                }

                drawPath(
                    path = linePath,
                    color = Color(0xFF4facfe),
                    style = Stroke(width = 4f)
                )

                // Draw points
                weekData.forEachIndexed { index, (_, value) ->
                    val x = index * spacing
                    val y = size.height - (value * heightScale)
                    drawCircle(
                        color = Color(0xFF4facfe),
                        radius = 6f,
                        center = Offset(x, y)
                    )
                    drawCircle(
                        color = Color.White,
                        radius = 3f,
                        center = Offset(x, y)
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Day labels
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                weekData.forEach { (day, _) ->
                    Text(
                        text = day,
                        fontSize = 12.sp,
                        color = Color(0xFF2C3E50).copy(alpha = 0.6f),
                        modifier = Modifier.weight(1f),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                }
            }
        }
    }
}

@Composable
private fun MonthlyTrendsCard() {
    val emotions = listOf(
        Triple("Joy", 0.85f, Color(0xFFFFD93D)),
        Triple("Calm", 0.72f, Color(0xFF4facfe)),
        Triple("Energy", 0.68f, Color(0xFF43e97b)),
        Triple("Focus", 0.79f, Color(0xFF9C27B0))
    )

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        shape = RoundedCornerShape(24.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Column(
            modifier = Modifier.padding(20.dp)
        ) {
            Text(
                text = "Monthly Trends",
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF2C3E50)
            )

            Spacer(modifier = Modifier.height(16.dp))

            emotions.forEach { (emotion, value, color) ->
                EmotionBar(emotion, value, color)
                Spacer(modifier = Modifier.height(12.dp))
            }
        }
    }
}

@Composable
private fun EmotionBar(emotion: String, value: Float, color: Color) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = emotion,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = Color(0xFF2C3E50)
            )
            Text(
                text = "${(value * 100).toInt()}%",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = color
            )
        }

        Spacer(modifier = Modifier.height(6.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(RoundedCornerShape(4.dp))
                .background(color.copy(alpha = 0.15f))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(value)
                    .clip(RoundedCornerShape(4.dp))
                    .background(color)
            )
        }
    }
}

@Composable
private fun LiveEventCard(event: LiveEvent) {
    Surface(
        modifier = Modifier.width(280.dp),
        shape = RoundedCornerShape(20.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            // Event category badge
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(
                        when (event.segment) {
                            "Music" -> Color(0xFF4facfe).copy(alpha = 0.1f)
                            "Sports" -> Color(0xFF43e97b).copy(alpha = 0.1f)
                            else -> Color(0xFFFFD93D).copy(alpha = 0.1f)
                        }
                    )
                    .padding(horizontal = 12.dp, vertical = 6.dp)
            ) {
                Text(
                    text = event.genre ?: event.segment,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = when (event.segment) {
                        "Music" -> Color(0xFF4facfe)
                        "Sports" -> Color(0xFF43e97b)
                        else -> Color(0xFFFFB74D)
                    }
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = event.name,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF2C3E50),
                maxLines = 2
            )

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "📍",
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = event.venueName,
                    fontSize = 13.sp,
                    color = Color(0xFF2C3E50).copy(alpha = 0.7f),
                    maxLines = 1
                )
            }

            Spacer(modifier = Modifier.height(6.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "📅",
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = "${event.localDate} • ${event.localTime.take(5)}",
                    fontSize = 13.sp,
                    color = Color(0xFF2C3E50).copy(alpha = 0.7f)
                )
            }
        }
    }
}

@Composable
private fun SocialEventCard(event: SocialEvent) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        shape = RoundedCornerShape(20.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(60.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(
                        brush = Brush.linearGradient(
                            colors = listOf(
                                Color(0xFF43e97b),
                                Color(0xFF38f9d7)
                            )
                        )
                    ),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "💪",
                    fontSize = 28.sp
                )
            }

            Spacer(modifier = Modifier.width(16.dp))

            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = event.eventName,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF2C3E50)
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = event.description,
                    fontSize = 13.sp,
                    color = Color(0xFF2C3E50).copy(alpha = 0.6f),
                    maxLines = 2
                )

                Spacer(modifier = Modifier.height(6.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "📍 ${event.location}",
                        fontSize = 12.sp,
                        color = Color(0xFF2C3E50).copy(alpha = 0.7f)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = "📅 ${event.date}",
                        fontSize = 12.sp,
                        color = Color(0xFF2C3E50).copy(alpha = 0.7f)
                    )
                }
            }
        }
    }
}