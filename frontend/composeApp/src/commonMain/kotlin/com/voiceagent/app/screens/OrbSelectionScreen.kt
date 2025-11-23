// ============================================
// File: screens/OrbSelectionScreen.kt
// Copy this entire file
// ============================================
package com.voiceagent.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voiceagent.app.models.WellnessType
import kotlinx.coroutines.delay
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.PI

@Composable
fun OrbSelectionScreen(
    wellnessType: WellnessType,
    onCallClick: () -> Unit,
    onChatClick: () -> Unit,
    onBack: () -> Unit
) {
    val colorScheme = getColorScheme(wellnessType)
    var displayedText by remember { mutableStateOf("") }
    var showButtons by remember { mutableStateOf(false) }
    val greetingText = "How can I help you?"

    LaunchedEffect(Unit) {
        // Typing animation
        for (i in greetingText.indices) {
            displayedText = greetingText.substring(0, i + 1)
            delay(80)
        }
        delay(300)
        showButtons = true
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
        // Back button at top-left
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = 60.dp, start = 24.dp),
            contentAlignment = Alignment.TopStart
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.3f)),
                contentAlignment = Alignment.Center
            ) {
                IconButton(
                    onClick = onBack,
                    modifier = Modifier.size(44.dp)
                ) {
                    Text(
                        text = "←",
                        color = colorScheme.textColor,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(40.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Animated Orb
            AnimatedWellnessOrb(colorScheme)

            Spacer(modifier = Modifier.height(40.dp))

            // Typing greeting text
            Text(
                text = displayedText + if (displayedText.length < greetingText.length) "|" else "",
                fontSize = 24.sp,
                fontWeight = FontWeight.SemiBold,
                color = colorScheme.textColor,
                modifier = Modifier
                    .padding(horizontal = 20.dp)
                    .heightIn(min = 36.dp)
            )

            Spacer(modifier = Modifier.height(50.dp))

            // Action buttons with fade-in animation
            val buttonAlpha by animateFloatAsState(
                targetValue = if (showButtons) 1f else 0f,
                animationSpec = tween(500)
            )

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp),
                horizontalArrangement = Arrangement.spacedBy(24.dp, Alignment.CenterHorizontally)
            ) {
                ActionButton(
                    text = "Call",
                    colors = colorScheme.primaryButtonColors,
                    alpha = buttonAlpha,
                    onClick = onCallClick,
                    modifier = Modifier.weight(1f, fill = false).widthIn(min = 140.dp, max = 200.dp)
                )

                ActionButton(
                    text = "Chat",
                    colors = colorScheme.secondaryButtonColors,
                    alpha = buttonAlpha,
                    onClick = onChatClick,
                    modifier = Modifier.weight(1f, fill = false).widthIn(min = 140.dp, max = 200.dp)
                )
            }
        }
    }
}

@Composable
private fun AnimatedWellnessOrb(colorScheme: OrbColorScheme) {
    val infiniteTransition = rememberInfiniteTransition()

    val pulse by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        )
    )

    val floatY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = -10f,
        animationSpec = infiniteRepeatable(
            animation = tween(4000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        )
    )

    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(8000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        )
    )

    Box(
        modifier = Modifier
            .size(200.dp)
            .offset(y = floatY.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier
                .size(180.dp)
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
private fun ActionButton(
    text: String,
    colors: List<Color>,
    alpha: Float,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Button(
        onClick = onClick,
        modifier = modifier
            .height(56.dp)
            .shadow(
                elevation = (4 + alpha * 11).dp,
                shape = RoundedCornerShape(50),
                spotColor = colors[0].copy(alpha = alpha * 0.4f)
            ),
        shape = RoundedCornerShape(50),
        colors = ButtonDefaults.buttonColors(
            containerColor = Color.Transparent
        ),
        contentPadding = PaddingValues(0.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    brush = Brush.linearGradient(colors = colors),
                    shape = RoundedCornerShape(50)
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = text,
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White.copy(alpha = alpha)
            )
        }
    }
}

private data class OrbColorScheme(
    val backgroundColors: List<Color>,
    val orbColors: List<Color>,
    val primaryButtonColors: List<Color>,
    val secondaryButtonColors: List<Color>,
    val textColor: Color
)

private fun getColorScheme(wellnessType: WellnessType): OrbColorScheme {
    return when (wellnessType) {
        WellnessType.PHYSICAL -> OrbColorScheme(
            backgroundColors = listOf(Color(0xFFE3F2FD), Color(0xFFBBDEFB)),
            orbColors = listOf(Color(0xFF4facfe), Color(0xFF00f2fe)),
            primaryButtonColors = listOf(Color(0xFF4facfe), Color(0xFF00f2fe)),
            secondaryButtonColors = listOf(Color(0xFF42A5F5), Color(0xFF64B5F6)),
            textColor = Color(0xFF1565C0)
        )
        WellnessType.MENTAL -> OrbColorScheme(
            backgroundColors = listOf(Color(0xFFFFF8E1), Color(0xFFFFECB3)),
            orbColors = listOf(Color(0xFFffd93d), Color(0xFFffe066)),
            primaryButtonColors = listOf(Color(0xFFffd93d), Color(0xFFffe066)),
            secondaryButtonColors = listOf(Color(0xFFFFB74D), Color(0xFFFFCC80)),
            textColor = Color(0xFFE65100)
        )
        WellnessType.SOCIAL -> OrbColorScheme(
            backgroundColors = listOf(Color(0xFFE8F5E9), Color(0xFFC8E6C9)),
            orbColors = listOf(Color(0xFF43e97b), Color(0xFF38f9d7)),
            primaryButtonColors = listOf(Color(0xFF43e97b), Color(0xFF38f9d7)),
            secondaryButtonColors = listOf(Color(0xFF66BB6A), Color(0xFF81C784)),
            textColor = Color(0xFF2E7D32)
        )
    }
}