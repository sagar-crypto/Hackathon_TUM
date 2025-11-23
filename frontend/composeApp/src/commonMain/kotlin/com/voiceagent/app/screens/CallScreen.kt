// ============================================
// File: screens/CallScreen.kt
// SIMPLIFIED VERSION - Beautiful orb animations
// ============================================
package com.voiceagent.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voiceagent.app.models.CallScreenConfig
import com.voiceagent.app.models.WellnessType
import com.voiceagent.app.network.AudioSessionApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.PI

enum class CallPhase {
    INCOMING,      // Showing incoming call screen
    ACTIVE,        // Call is active
    ENDING         // Call is ending
}

@Composable
fun CallScreen(
    config: CallScreenConfig = CallScreenConfig(),
    wellnessType: WellnessType = WellnessType.PHYSICAL,
    userName: String = "User",
    userMood: String? = null,
    stepsToday: Int? = null,
    sleepHours: Float? = null,
    conversationSummary: String? = null,
    goals: String? = null,
    onCallEnded: () -> Unit = {},
    onBack: () -> Unit = {}
) {
    val colorScheme = getCallColorScheme(wellnessType)
    var callPhase by remember { mutableStateOf(CallPhase.INCOMING) }
    var statusMessage by remember { mutableStateOf("Connecting...") }
    var sessionId by remember { mutableStateOf<String?>(null) }
    val coroutineScope = rememberCoroutineScope()

    val onCallAnswered: () -> Unit = {
        // Immediately switch to active UI
        callPhase = CallPhase.ACTIVE
        statusMessage = "Starting session..."

        // Start the session in background
        coroutineScope.launch {
            try {
                val (success, sessionIdResponse) = AudioSessionApi.startSession(
                    name = userName,
                    mood = userMood,
                    stepsToday = stepsToday,
                    sleepHours = sleepHours,
                    conversationSummary = conversationSummary,
                    goals = goals
                )

                if (success && sessionIdResponse != null) {
                    sessionId = sessionIdResponse
                    statusMessage = "Session active - AI is analyzing..."

                    // Keep showing the call is active
                    // The session will run on the backend
                } else {
                    statusMessage = "Failed to start session"
                    delay(2000)
                    onCallEnded()
                }
            } catch (e: Exception) {
                statusMessage = "Error: ${e.message}"
                delay(3000)
                callPhase = CallPhase.ENDING
                delay(1000)
                onCallEnded()
            }
        }
    }

    val onEndCallClick: () -> Unit = {
        callPhase = CallPhase.ENDING
        statusMessage = "Ending call..."

        coroutineScope.launch {
            // End the session if we have a session ID
            sessionId?.let { id ->
                AudioSessionApi.endSession(id)
            }

            delay(1000)
            onCallEnded()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = colorScheme.backgroundColors
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
        ) {
            when (callPhase) {
                CallPhase.INCOMING -> {
                    IncomingCallUI(
                        config = config,
                        colorScheme = colorScheme,
                        onCallAnswered = onCallAnswered,
                        onBack = onBack
                    )
                }
                CallPhase.ACTIVE, CallPhase.ENDING -> {
                    ActiveCallUI(
                        colorScheme = colorScheme,
                        statusMessage = statusMessage,
                        isEnding = callPhase == CallPhase.ENDING,
                        onEndCall = onEndCallClick
                    )
                }
            }
        }
    }
}

@Composable
private fun IncomingCallUI(
    config: CallScreenConfig,
    colorScheme: CallColorScheme,
    onCallAnswered: () -> Unit,
    onBack: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(60.dp))

        // Back button
        Box(
            modifier = Modifier.fillMaxWidth(),
            contentAlignment = Alignment.TopStart
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(colorScheme.statusBadgeColor),
                contentAlignment = Alignment.Center
            ) {
                IconButton(
                    onClick = onBack,
                    modifier = Modifier.size(44.dp)
                ) {
                    Text(
                        "←",
                        fontSize = 22.sp,
                        color = colorScheme.textColor,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }

        Spacer(modifier = Modifier.weight(0.25f))

        // Beautiful animated orb
        AnimatedWellnessOrb(colorScheme)

        Spacer(modifier = Modifier.height(48.dp))

        // Incoming call badge
        Surface(
            shape = RoundedCornerShape(20.dp),
            color = colorScheme.statusBadgeColor
        ) {
            Text(
                text = config.incomingText,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = colorScheme.textColor,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp),
                letterSpacing = 1.sp
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Caller name
        Text(
            text = config.callerName,
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold,
            color = colorScheme.textColor,
            letterSpacing = 1.2.sp
        )

        Spacer(modifier = Modifier.height(8.dp))

        // Call type
        Text(
            text = config.callType,
            fontSize = 15.sp,
            color = colorScheme.textColor.copy(alpha = 0.75f),
            letterSpacing = 0.5.sp
        )

        Spacer(modifier = Modifier.weight(0.4f))

        // Swipe to answer
        SwipeToAnswerButton(
            config = config,
            colorScheme = colorScheme,
            onCallAnswered = onCallAnswered
        )

        Spacer(modifier = Modifier.height(50.dp))
    }
}

@Composable
private fun ActiveCallUI(
    colorScheme: CallColorScheme,
    statusMessage: String,
    isEnding: Boolean,
    onEndCall: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.weight(0.25f))

        // Pulsing animated orb during call
        PulsingCallOrb(colorScheme, isActive = !isEnding)

        Spacer(modifier = Modifier.height(48.dp))

        // Call status badge
        Surface(
            shape = RoundedCornerShape(20.dp),
            color = colorScheme.statusBadgeColor,
            modifier = Modifier.padding(horizontal = 32.dp)
        ) {
            Text(
                text = if (isEnding) "Call Ending..." else "In Call",
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = colorScheme.textColor,
                modifier = Modifier.padding(horizontal = 24.dp, vertical = 10.dp),
                letterSpacing = 0.5.sp
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Status message
        Text(
            text = statusMessage,
            fontSize = 15.sp,
            color = colorScheme.textColor.copy(alpha = 0.8f),
            textAlign = TextAlign.Center,
            lineHeight = 22.sp,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 40.dp)
        )

        Spacer(modifier = Modifier.weight(0.4f))

        // Modern end call button
        Box(
            modifier = Modifier
                .size(64.dp)
                .clip(CircleShape)
                .background(Color(0xFFEF5350)),
            contentAlignment = Alignment.Center
        ) {
            IconButton(
                onClick = onEndCall,
                enabled = !isEnding,
                modifier = Modifier.size(64.dp)
            ) {
                Text(
                    text = "✕",
                    fontSize = 28.sp,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        Spacer(modifier = Modifier.height(40.dp))
    }
}

@Composable
private fun PulsingCallOrb(colorScheme: CallColorScheme, isActive: Boolean) {
    val infiniteTransition = rememberInfiniteTransition(label = "orb")

    // Enhanced pulsing effect - breathing animation
    val pulse by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.12f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    // Subtle floating effect
    val floatY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = -8f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "float"
    )

    // Rotating highlight
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(10000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "rotation"
    )

    // Outer ring pulsing
    val ringPulse by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "ringPulse"
    )

    Box(
        modifier = Modifier
            .size(240.dp)
            .offset(y = floatY.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier.size(240.dp)
        ) {
            val center = Offset(size.width / 2, size.height / 2)
            val radius = (size.minDimension / 2.2f) * if (isActive) pulse else 1f

            // Outermost pulsing ring (only when active)
            if (isActive) {
                drawCircle(
                    color = colorScheme.orbColors[0].copy(alpha = 0.15f * ringPulse),
                    radius = radius * 1.6f,
                    center = center
                )

                drawCircle(
                    color = colorScheme.orbColors[0].copy(alpha = 0.2f * ringPulse),
                    radius = radius * 1.4f,
                    center = center
                )
            }

            // Main glow layer
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        colorScheme.orbColors[0].copy(alpha = 0.5f),
                        colorScheme.orbColors[0].copy(alpha = 0.3f),
                        colorScheme.orbColors[1].copy(alpha = 0.15f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = radius * 1.35f
                ),
                radius = radius * 1.35f,
                center = center
            )

            // Main orb with gradient
            drawCircle(
                brush = Brush.linearGradient(
                    colors = colorScheme.orbColors,
                    start = Offset(center.x - radius, center.y - radius),
                    end = Offset(center.x + radius, center.y + radius)
                ),
                radius = radius,
                center = center
            )

            // Rotating highlight for 3D effect
            val rotationRadians = (rotation * PI / 180.0).toFloat()
            val highlightOffset = Offset(
                center.x + cos(rotationRadians) * radius * 0.4f,
                center.y + sin(rotationRadians) * radius * 0.4f
            )

            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.5f),
                        Color.White.copy(alpha = 0.25f),
                        Color.Transparent
                    ),
                    center = highlightOffset,
                    radius = radius * 0.55f
                ),
                radius = radius * 0.55f,
                center = highlightOffset
            )

            // Inner shine for depth
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.4f),
                        Color.White.copy(alpha = 0.1f),
                        Color.Transparent
                    ),
                    center = Offset(center.x - radius * 0.25f, center.y - radius * 0.25f),
                    radius = radius * 0.5f
                ),
                radius = radius * 0.5f,
                center = Offset(center.x - radius * 0.25f, center.y - radius * 0.25f)
            )
        }
    }
}

@Composable
private fun AnimatedWellnessOrb(colorScheme: CallColorScheme) {
    val infiniteTransition = rememberInfiniteTransition(label = "orb")

    // Pulsing effect
    val pulse by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    // Floating effect
    val floatY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = -10f,
        animationSpec = infiniteRepeatable(
            animation = tween(4000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "float"
    )

    // Rotation for highlight
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(8000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "rotation"
    )

    Box(
        modifier = Modifier
            .size(200.dp)
            .offset(y = floatY.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier.size(180.dp)
        ) {
            val center = Offset(size.width / 2, size.height / 2)
            val radius = size.minDimension / 2 * pulse

            // Outer glow
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        colorScheme.orbColors[0].copy(alpha = 0.6f),
                        colorScheme.orbColors[0].copy(alpha = 0.4f),
                        colorScheme.orbColors[1].copy(alpha = 0.2f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = radius * 1.4f
                ),
                radius = radius * 1.4f,
                center = center
            )

            // Main orb with gradient
            drawCircle(
                brush = Brush.linearGradient(
                    colors = colorScheme.orbColors,
                    start = Offset(0f, 0f),
                    end = Offset(size.width, size.height)
                ),
                radius = radius,
                center = center
            )

            // Rotating highlight
            val rotationRadians = (rotation * PI / 180.0).toFloat()
            val highlightOffset = Offset(
                center.x + cos(rotationRadians) * radius * 0.3f,
                center.y + sin(rotationRadians) * radius * 0.3f
            )

            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.4f),
                        Color.White.copy(alpha = 0.2f),
                        Color.Transparent
                    ),
                    center = highlightOffset,
                    radius = radius * 0.5f
                ),
                radius = radius * 0.5f,
                center = highlightOffset
            )

            // Inner shine
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.3f),
                        Color.Transparent
                    ),
                    center = Offset(center.x - radius * 0.3f, center.y - radius * 0.3f),
                    radius = radius * 0.4f
                ),
                radius = radius * 0.4f,
                center = Offset(center.x - radius * 0.3f, center.y - radius * 0.3f)
            )
        }
    }
}

@Composable
private fun SwipeToAnswerButton(
    config: CallScreenConfig,
    colorScheme: CallColorScheme,
    onCallAnswered: () -> Unit
) {
    var offsetX by remember { mutableStateOf(0f) }
    var isSuccess by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

    val buttonOffset by animateFloatAsState(
        targetValue = offsetX,
        animationSpec = tween(durationMillis = 200, easing = FastOutSlowInEasing),
        label = "buttonOffset"
    )

    val pulseScale by rememberInfiniteTransition(label = "pulse").animateFloat(
        initialValue = 1f, targetValue = 1.03f,
        animationSpec = infiniteRepeatable(
            animation = tween(1800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ), label = "pulseScale"
    )

    val successScale by animateFloatAsState(
        targetValue = if (isSuccess) 1.08f else 1f,
        animationSpec = tween(250, easing = FastOutSlowInEasing),
        label = "successScale"
    )

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxWidth()
            .height(64.dp)
    ) {
        val maxWidth = constraints.maxWidth.toFloat()
        val maxSlide = maxWidth - 64f

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp)
                .clip(RoundedCornerShape(32.dp))
                .background(colorScheme.statusBadgeColor)
        ) {
            // Progress indicator
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .width((buttonOffset + 32).dp)
                    .clip(RoundedCornerShape(32.dp))
                    .background(
                        brush = Brush.horizontalGradient(
                            colors = listOf(
                                colorScheme.accentColor.copy(alpha = 0.25f),
                                colorScheme.accentColor.copy(alpha = 0.4f)
                            )
                        )
                    )
            )

            // Text instruction
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = config.slideText,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = colorScheme.textColor.copy(alpha = 0.7f),
                    letterSpacing = 0.8.sp,
                    textAlign = TextAlign.Center
                )
            }

            // Sliding button
            Box(
                modifier = Modifier
                    .offset(x = buttonOffset.dp, y = 4.dp)
                    .size(56.dp)
                    .graphicsLayer {
                        scaleX = if (isSuccess) successScale else pulseScale
                        scaleY = if (isSuccess) successScale else pulseScale
                    }
                    .clip(CircleShape)
                    .background(
                        if (isSuccess) {
                            colorScheme.accentColor
                        } else {
                            Color.White
                        }
                    )
                    .pointerInput(Unit) {
                        detectDragGestures(
                            onDragEnd = {
                                if (offsetX > maxSlide * 0.75f) {
                                    offsetX = maxSlide
                                    isSuccess = true
                                    coroutineScope.launch {
                                        delay(400)
                                        onCallAnswered()
                                    }
                                } else {
                                    offsetX = 0f
                                }
                            },
                            onDrag = { change, dragAmount ->
                                change.consume()
                                offsetX = (offsetX + dragAmount.x).coerceIn(0f, maxSlide)
                            }
                        )
                    },
                contentAlignment = Alignment.Center
            ) {
                Canvas(modifier = Modifier.size(24.dp)) {
                    val path = Path().apply {
                        moveTo(size.width * 0.833f, size.height * 0.641f)
                        cubicTo(
                            size.width * 0.781f, size.height * 0.641f,
                            size.width * 0.733f, size.height * 0.633f,
                            size.width * 0.686f, size.height * 0.618f
                        )
                        cubicTo(
                            size.width * 0.672f, size.height * 0.613f,
                            size.width * 0.655f, size.height * 0.617f,
                            size.width * 0.644f, size.height * 0.628f
                        )
                        lineTo(size.width * 0.579f, size.height * 0.710f)
                        cubicTo(
                            size.width * 0.461f, size.height * 0.654f,
                            size.width * 0.354f, size.height * 0.547f,
                            size.width * 0.292f, size.height * 0.425f
                        )
                        lineTo(size.width * 0.373f, size.height * 0.356f)
                        cubicTo(
                            size.width * 0.384f, size.height * 0.344f,
                            size.width * 0.388f, size.height * 0.328f,
                            size.width * 0.383f, size.height * 0.313f
                        )
                        cubicTo(
                            size.width * 0.368f, size.height * 0.267f,
                            size.width * 0.360f, size.height * 0.217f,
                            size.width * 0.360f, size.height * 0.166f
                        )
                        cubicTo(
                            size.width * 0.360f, size.height * 0.143f,
                            size.width * 0.341f, size.height * 0.125f,
                            size.width * 0.319f, size.height * 0.125f
                        )
                        lineTo(size.width * 0.175f, size.height * 0.125f)
                        cubicTo(
                            size.width * 0.152f, size.height * 0.125f,
                            size.width * 0.125f, size.height * 0.135f,
                            size.width * 0.125f, size.height * 0.166f
                        )
                        cubicTo(
                            size.width * 0.125f, size.height * 0.553f,
                            size.width * 0.447f, size.height * 0.875f,
                            size.width * 0.833f, size.height * 0.875f
                        )
                        cubicTo(
                            size.width * 0.863f, size.height * 0.875f,
                            size.width * 0.875f, size.height * 0.849f,
                            size.width * 0.875f, size.height * 0.826f
                        )
                        lineTo(size.width * 0.875f, size.height * 0.682f)
                        cubicTo(
                            size.width * 0.875f, size.height * 0.660f,
                            size.width * 0.856f, size.height * 0.641f,
                            size.width * 0.833f, size.height * 0.641f
                        )
                        close()
                    }
                    drawPath(
                        path = path,
                        color = if (isSuccess) Color.White else colorScheme.accentColor,
                        style = Fill
                    )
                }
            }
        }
    }
}

private data class CallColorScheme(
    val backgroundColors: List<Color>,
    val orbColors: List<Color>,
    val textColor: Color,
    val accentColor: Color,
    val statusBadgeColor: Color
)

private fun getCallColorScheme(wellnessType: WellnessType): CallColorScheme {
    return when (wellnessType) {
        WellnessType.PHYSICAL -> CallColorScheme(
            backgroundColors = listOf(Color(0xFFE3F2FD), Color(0xFFBBDEFB)),
            orbColors = listOf(Color(0xFF4facfe), Color(0xFF00f2fe)),
            textColor = Color(0xFF1565C0),
            accentColor = Color(0xFF2196F3),
            statusBadgeColor = Color.White.copy(alpha = 0.5f)
        )
        WellnessType.MENTAL -> CallColorScheme(
            backgroundColors = listOf(Color(0xFFFFF8E1), Color(0xFFFFECB3)),
            orbColors = listOf(Color(0xFFffd93d), Color(0xFFffe066)),
            textColor = Color(0xFFE65100),
            accentColor = Color(0xFFFF9800),
            statusBadgeColor = Color.White.copy(alpha = 0.5f)
        )
        WellnessType.SOCIAL -> CallColorScheme(
            backgroundColors = listOf(Color(0xFFE8F5E9), Color(0xFFC8E6C9)),
            orbColors = listOf(Color(0xFF43e97b), Color(0xFF38f9d7)),
            textColor = Color(0xFF2E7D32),
            accentColor = Color(0xFF4CAF50),
            statusBadgeColor = Color.White.copy(alpha = 0.5f)
        )
    }
}