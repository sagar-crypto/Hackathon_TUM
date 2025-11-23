// ============================================
// File: screens/ChatScreen.kt
// Modern reimagined design with safe area padding
// ============================================
package com.voiceagent.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voiceagent.app.models.WellnessType
import com.voiceagent.app.network.ChatApi
import kotlinx.coroutines.launch
import kotlin.random.Random
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.PI

data class ChatMessage(
    val text: String,
    val isUser: Boolean,
    val id: String = Random.nextLong().toString()
)

@Composable
fun ChatScreen(
    wellnessType: WellnessType,
    onBack: () -> Unit = {}
) {
    val colorScheme = getChatColorScheme(wellnessType)
    var messages by remember { mutableStateOf<List<ChatMessage>>(emptyList()) }
    var inputText by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    val sessionId = remember(Unit) { "mobile-${Random.nextLong().toString().takeLast(10)}" }
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(colorScheme.backgroundColor)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding() // Safe area for notch
                .navigationBarsPadding() // Safe area for bottom
        ) {
            // Header with extra top padding
            Spacer(modifier = Modifier.height(16.dp))

            ChatHeader(
                colorScheme = colorScheme,
                wellnessType = wellnessType,
                onBack = onBack
            )

            // Messages Area with proper spacing
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp),
                state = listState,
                contentPadding = PaddingValues(vertical = 20.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(messages, key = { it.id }) { message ->
                    MessageBubble(message, colorScheme)
                }
            }

            // Input Area with bottom padding
            ChatInputArea(
                inputText = inputText,
                onInputChange = { inputText = it },
                isLoading = isLoading,
                onSendMessage = {
                    if (inputText.isNotBlank() && !isLoading) {
                        val userMessage = inputText
                        inputText = ""
                        isLoading = true

                        coroutineScope.launch {
                            try {
                                // Add user message immediately
                                messages = messages + ChatMessage(userMessage, true)
                                listState.animateScrollToItem(messages.size - 1)

                                // Call API
                                val response = ChatApi.sendMessage(sessionId, userMessage, messages)

                                // Update with full conversation
                                messages = response
                                listState.animateScrollToItem(messages.size - 1)
                            } catch (e: Exception) {
                                println("Chat error: ${e.message}")
                                messages = messages + ChatMessage(
                                    "Sorry, I couldn't process that. Please try again.",
                                    false
                                )
                            } finally {
                                isLoading = false
                            }
                        }
                    }
                },
                colorScheme = colorScheme
            )

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

@Composable
private fun ChatHeader(
    colorScheme: ChatColorScheme,
    wellnessType: WellnessType,
    onBack: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Back Button
        IconButton(
            onClick = onBack,
            modifier = Modifier
                .size(44.dp)
                .clip(CircleShape)
                .background(colorScheme.headerElementBg)
        ) {
            Text(
                text = "←",
                color = colorScheme.textColor,
                fontSize = 24.sp,
                fontWeight = FontWeight.Medium
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        // Profile Orb
        AnimatedProfileOrb(colorScheme)

        Spacer(modifier = Modifier.width(12.dp))

        // Assistant Info
        Column(
            modifier = Modifier.weight(1f)
        ) {
            Text(
                text = "ETHOS",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = colorScheme.textColor,
                letterSpacing = 1.2.sp
            )
            Text(
                text = when (wellnessType) {
                    WellnessType.PHYSICAL -> "Physical Wellness"
                    WellnessType.MENTAL -> "Mental Wellness"
                    WellnessType.SOCIAL -> "Social Wellness"
                },
                fontSize = 13.sp,
                color = colorScheme.textColor.copy(alpha = 0.7f),
                letterSpacing = 0.5.sp
            )
        }

        // Status Indicator
        Box(
            modifier = Modifier
                .size(10.dp)
                .clip(CircleShape)
                .background(Color(0xFF4CAF50))
        )
    }
}

@Composable
private fun AnimatedProfileOrb(colorScheme: ChatColorScheme) {
    val infiniteTransition = rememberInfiniteTransition(label = "orb")

    val pulse by infiniteTransition.animateFloat(
        initialValue = 0.95f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(2500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

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
        modifier = Modifier.size(46.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.size(46.dp)) {
            val center = Offset(size.width / 2, size.height / 2)
            val radius = (size.minDimension / 2) * pulse

            // Outer glow
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        colorScheme.orbGlowColor.copy(alpha = 0.4f),
                        colorScheme.orbGlowColor.copy(alpha = 0.2f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = radius * 1.3f
                ),
                radius = radius * 1.3f,
                center = center
            )

            // Main orb
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
                center.x + cos(rotationRadians) * radius * 0.35f,
                center.y + sin(rotationRadians) * radius * 0.35f
            )

            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.5f),
                        Color.White.copy(alpha = 0.2f),
                        Color.Transparent
                    ),
                    center = highlightOffset,
                    radius = radius * 0.6f
                ),
                radius = radius * 0.6f,
                center = highlightOffset
            )
        }
    }
}

@Composable
private fun MessageBubble(message: ChatMessage, colorScheme: ChatColorScheme) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (message.isUser) Arrangement.End else Arrangement.Start
    ) {
        if (!message.isUser) {
            // Ethos mini avatar
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(CircleShape)
                    .background(
                        brush = Brush.linearGradient(colorScheme.orbColors)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "E",
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
        }

        // Message bubble
        Surface(
            modifier = Modifier.widthIn(max = 260.dp),
            shape = RoundedCornerShape(
                topStart = if (message.isUser) 20.dp else 4.dp,
                topEnd = if (message.isUser) 4.dp else 20.dp,
                bottomStart = 20.dp,
                bottomEnd = 20.dp
            ),
            color = if (message.isUser) {
                Color.Transparent
            } else {
                colorScheme.aiBubbleColor
            },
            shadowElevation = if (message.isUser) 0.dp else 1.dp
        ) {
            Box(
                modifier = if (message.isUser) {
                    Modifier.background(
                        brush = Brush.linearGradient(colorScheme.userBubbleColors)
                    )
                } else {
                    Modifier
                }
            ) {
                Text(
                    text = message.text,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                    color = if (message.isUser) Color.White else colorScheme.aiBubbleTextColor,
                    fontSize = 15.sp,
                    lineHeight = 21.sp
                )
            }
        }

        if (message.isUser) {
            Spacer(modifier = Modifier.width(8.dp))
            // User mini avatar
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(CircleShape)
                    .background(colorScheme.userAvatarColor),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "Y",
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
private fun ChatInputArea(
    inputText: String,
    onInputChange: (String) -> Unit,
    isLoading: Boolean = false,
    onSendMessage: () -> Unit,
    colorScheme: ChatColorScheme
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        verticalAlignment = Alignment.Bottom,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Text Input
        TextField(
            value = inputText,
            onValueChange = onInputChange,
            enabled = !isLoading,
            modifier = Modifier
                .weight(1f)
                .clip(RoundedCornerShape(24.dp)),
            placeholder = {
                Text(
                    if (isLoading) "Thinking..." else "Message ETHOS...",
                    color = colorScheme.inputPlaceholderColor,
                    fontSize = 15.sp
                )
            },
            colors = TextFieldDefaults.colors(
                focusedContainerColor = colorScheme.inputBackgroundColor,
                unfocusedContainerColor = colorScheme.inputBackgroundColor,
                disabledContainerColor = colorScheme.inputBackgroundColor,
                focusedTextColor = colorScheme.inputTextColor,
                unfocusedTextColor = colorScheme.inputTextColor,
                disabledTextColor = colorScheme.inputTextColor.copy(alpha = 0.5f),
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
                disabledIndicatorColor = Color.Transparent,
                cursorColor = colorScheme.primaryColor
            ),
            shape = RoundedCornerShape(24.dp),
            maxLines = 4
        )

        // Send Button
        Box(
            modifier = Modifier
                .size(52.dp)
                .clip(CircleShape)
                .background(
                    brush = if (isLoading) {
                        Brush.linearGradient(
                            colors = colorScheme.sendButtonColors.map { it.copy(alpha = 0.5f) }
                        )
                    } else {
                        Brush.linearGradient(colorScheme.sendButtonColors)
                    }
                ),
            contentAlignment = Alignment.Center
        ) {
            IconButton(
                onClick = onSendMessage,
                enabled = !isLoading && inputText.isNotBlank(),
                modifier = Modifier.size(52.dp)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                } else {
                    Text(
                        text = "→",
                        color = Color.White,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

private data class ChatColorScheme(
    val backgroundColor: Color,
    val textColor: Color,
    val headerElementBg: Color,
    val orbColors: List<Color>,
    val orbGlowColor: Color,
    val userBubbleColors: List<Color>,
    val userAvatarColor: Color,
    val aiBubbleColor: Color,
    val aiBubbleTextColor: Color,
    val inputBackgroundColor: Color,
    val inputTextColor: Color,
    val inputPlaceholderColor: Color,
    val sendButtonColors: List<Color>,
    val primaryColor: Color
)

private fun getChatColorScheme(wellnessType: WellnessType): ChatColorScheme {
    return when (wellnessType) {
        WellnessType.PHYSICAL -> ChatColorScheme(
            backgroundColor = Color(0xFFE3F2FD),
            textColor = Color(0xFF1565C0),
            headerElementBg = Color.White.copy(alpha = 0.5f),
            orbColors = listOf(Color(0xFF4facfe), Color(0xFF00f2fe)),
            orbGlowColor = Color(0xFF4facfe),
            userBubbleColors = listOf(Color(0xFF2196F3), Color(0xFF1976D2)),
            userAvatarColor = Color(0xFF1976D2),
            aiBubbleColor = Color.White,
            aiBubbleTextColor = Color(0xFF2C3E50),
            inputBackgroundColor = Color.White,
            inputTextColor = Color(0xFF2C3E50),
            inputPlaceholderColor = Color(0xFF90A4AE),
            sendButtonColors = listOf(Color(0xFF2196F3), Color(0xFF1976D2)),
            primaryColor = Color(0xFF2196F3)
        )
        WellnessType.MENTAL -> ChatColorScheme(
            backgroundColor = Color(0xFFFFF8E1),
            textColor = Color(0xFFE65100),
            headerElementBg = Color.White.copy(alpha = 0.5f),
            orbColors = listOf(Color(0xFFffd93d), Color(0xFFffe066)),
            orbGlowColor = Color(0xFFffd93d),
            userBubbleColors = listOf(Color(0xFFFF9800), Color(0xFFF57C00)),
            userAvatarColor = Color(0xFFF57C00),
            aiBubbleColor = Color.White,
            aiBubbleTextColor = Color(0xFF2C3E50),
            inputBackgroundColor = Color.White,
            inputTextColor = Color(0xFF2C3E50),
            inputPlaceholderColor = Color(0xFF90A4AE),
            sendButtonColors = listOf(Color(0xFFFF9800), Color(0xFFF57C00)),
            primaryColor = Color(0xFFFF9800)
        )
        WellnessType.SOCIAL -> ChatColorScheme(
            backgroundColor = Color(0xFFE8F5E9),
            textColor = Color(0xFF2E7D32),
            headerElementBg = Color.White.copy(alpha = 0.5f),
            orbColors = listOf(Color(0xFF43e97b), Color(0xFF38f9d7)),
            orbGlowColor = Color(0xFF43e97b),
            userBubbleColors = listOf(Color(0xFF4CAF50), Color(0xFF388E3C)),
            userAvatarColor = Color(0xFF388E3C),
            aiBubbleColor = Color.White,
            aiBubbleTextColor = Color(0xFF2C3E50),
            inputBackgroundColor = Color.White,
            inputTextColor = Color(0xFF2C3E50),
            inputPlaceholderColor = Color(0xFF90A4AE),
            sendButtonColors = listOf(Color(0xFF4CAF50), Color(0xFF388E3C)),
            primaryColor = Color(0xFF4CAF50)
        )
    }
}