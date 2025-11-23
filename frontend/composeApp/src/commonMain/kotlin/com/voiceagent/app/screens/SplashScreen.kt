// ============================================
// File: screens/SplashScreen.kt
// Modern splash screen with app aesthetics
// ============================================
package com.voiceagent.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

@Composable
fun SplashScreen(
    onFinished: () -> Unit
) {
    var startAnimation by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        startAnimation = true
        delay(3000)
        onFinished()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFFF5F7FA),
                        Color(0xFFE8F5E9)
                    )
                )
            ),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Animated Buddha figure (bigger)
            AnimatedBuddha(startAnimation)

            Spacer(modifier = Modifier.height(48.dp))

            // App name with fade in
            val textAlpha by animateFloatAsState(
                targetValue = if (startAnimation) 1f else 0f,
                animationSpec = tween(1000, delayMillis = 500, easing = FastOutSlowInEasing),
                label = "textAlpha"
            )

            Text(
                text = "ETHOS",
                fontSize = 42.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 4.sp,
                color = Color(0xFF2C3E50).copy(alpha = textAlpha)
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "You've got a friend in me",
                fontSize = 16.sp,
                fontWeight = FontWeight.Normal,
                color = Color(0xFF2C3E50).copy(alpha = textAlpha * 0.7f),
                letterSpacing = 0.5.sp
            )
        }
    }
}

@Composable
private fun AnimatedBuddha(startAnimation: Boolean) {
    val infiniteTransition = rememberInfiniteTransition(label = "buddha")

    val scale by animateFloatAsState(
        targetValue = if (startAnimation) 1f else 0.3f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "scale"
    )

    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(20000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "rotation"
    )

    val glowPulse by infiniteTransition.animateFloat(
        initialValue = 0.6f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "glow"
    )

    Box(
        modifier = Modifier.size(280.dp * scale),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val centerX = size.width / 2
            val centerY = size.height / 2
            val radius = size.minDimension / 2.5f

            // Outer glow ring
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color(0xFF43e97b).copy(alpha = 0.3f * glowPulse),
                        Color(0xFF38f9d7).copy(alpha = 0.1f * glowPulse),
                        Color.Transparent
                    ),
                    center = Offset(centerX, centerY),
                    radius = radius * 1.4f
                ),
                radius = radius * 1.4f,
                center = Offset(centerX, centerY)
            )

            // Rotating halo
            val haloRadius = radius * 1.15f
            val rotationRad = rotation * PI / 180f
            for (i in 0 until 8) {
                val angle = (i * 45f + rotation) * PI / 180f
                val x = centerX + cos(angle).toFloat() * haloRadius
                val y = centerY + sin(angle).toFloat() * haloRadius

                drawCircle(
                    color = Color(0xFF4facfe).copy(alpha = 0.3f),
                    radius = 4f,
                    center = Offset(x, y)
                )
            }

            // Main circle background
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color(0xFF81C784),
                        Color(0xFF66BB6A)
                    ),
                    center = Offset(centerX, centerY)
                ),
                radius = radius,
                center = Offset(centerX, centerY)
            )

            // Buddha figure (simplified meditation pose)
            val buddhaScale = radius * 0.65f

            // Head
            drawCircle(
                color = Color.White.copy(alpha = 0.95f),
                radius = buddhaScale * 0.28f,
                center = Offset(centerX, centerY - buddhaScale * 0.5f)
            )

            // Body (torso)
            val bodyPath = Path().apply {
                // Start at neck
                moveTo(centerX, centerY - buddhaScale * 0.25f)

                // Left shoulder curve
                cubicTo(
                    centerX - buddhaScale * 0.1f, centerY - buddhaScale * 0.2f,
                    centerX - buddhaScale * 0.25f, centerY - buddhaScale * 0.1f,
                    centerX - buddhaScale * 0.3f, centerY + buddhaScale * 0.05f
                )

                // Left side down to waist
                lineTo(centerX - buddhaScale * 0.28f, centerY + buddhaScale * 0.25f)

                // Bottom of torso
                quadraticBezierTo(
                    centerX, centerY + buddhaScale * 0.3f,
                    centerX + buddhaScale * 0.28f, centerY + buddhaScale * 0.25f
                )

                // Right side up to shoulder
                lineTo(centerX + buddhaScale * 0.3f, centerY + buddhaScale * 0.05f)

                // Right shoulder curve
                cubicTo(
                    centerX + buddhaScale * 0.25f, centerY - buddhaScale * 0.1f,
                    centerX + buddhaScale * 0.1f, centerY - buddhaScale * 0.2f,
                    centerX, centerY - buddhaScale * 0.25f
                )

                close()
            }

            drawPath(
                path = bodyPath,
                color = Color.White.copy(alpha = 0.95f)
            )

            // Left arm
            val leftArmPath = Path().apply {
                moveTo(centerX - buddhaScale * 0.28f, centerY)
                quadraticBezierTo(
                    centerX - buddhaScale * 0.45f, centerY + buddhaScale * 0.1f,
                    centerX - buddhaScale * 0.4f, centerY + buddhaScale * 0.3f
                )
                quadraticBezierTo(
                    centerX - buddhaScale * 0.35f, centerY + buddhaScale * 0.35f,
                    centerX - buddhaScale * 0.25f, centerY + buddhaScale * 0.35f
                )
            }

            drawPath(
                path = leftArmPath,
                color = Color.White.copy(alpha = 0.9f),
                style = androidx.compose.ui.graphics.drawscope.Stroke(width = buddhaScale * 0.16f, cap = androidx.compose.ui.graphics.StrokeCap.Round)
            )

            // Right arm
            val rightArmPath = Path().apply {
                moveTo(centerX + buddhaScale * 0.28f, centerY)
                quadraticBezierTo(
                    centerX + buddhaScale * 0.45f, centerY + buddhaScale * 0.1f,
                    centerX + buddhaScale * 0.4f, centerY + buddhaScale * 0.3f
                )
                quadraticBezierTo(
                    centerX + buddhaScale * 0.35f, centerY + buddhaScale * 0.35f,
                    centerX + buddhaScale * 0.25f, centerY + buddhaScale * 0.35f
                )
            }

            drawPath(
                path = rightArmPath,
                color = Color.White.copy(alpha = 0.9f),
                style = androidx.compose.ui.graphics.drawscope.Stroke(width = buddhaScale * 0.16f, cap = androidx.compose.ui.graphics.StrokeCap.Round)
            )

            // Meditation posture (lotus position legs)
            // Left leg
            val leftLegPath = Path().apply {
                moveTo(centerX - buddhaScale * 0.25f, centerY + buddhaScale * 0.3f)
                quadraticBezierTo(
                    centerX - buddhaScale * 0.35f, centerY + buddhaScale * 0.5f,
                    centerX - buddhaScale * 0.15f, centerY + buddhaScale * 0.6f
                )
                lineTo(centerX + buddhaScale * 0.05f, centerY + buddhaScale * 0.6f)
            }

            drawPath(
                path = leftLegPath,
                color = Color.White.copy(alpha = 0.85f),
                style = androidx.compose.ui.graphics.drawscope.Stroke(width = buddhaScale * 0.14f, cap = androidx.compose.ui.graphics.StrokeCap.Round)
            )

            // Right leg
            val rightLegPath = Path().apply {
                moveTo(centerX + buddhaScale * 0.25f, centerY + buddhaScale * 0.3f)
                quadraticBezierTo(
                    centerX + buddhaScale * 0.35f, centerY + buddhaScale * 0.5f,
                    centerX + buddhaScale * 0.15f, centerY + buddhaScale * 0.6f
                )
                lineTo(centerX - buddhaScale * 0.05f, centerY + buddhaScale * 0.6f)
            }

            drawPath(
                path = rightLegPath,
                color = Color.White.copy(alpha = 0.85f),
                style = androidx.compose.ui.graphics.drawscope.Stroke(width = buddhaScale * 0.14f, cap = androidx.compose.ui.graphics.StrokeCap.Round)
            )

            // Inner glow
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.4f * glowPulse),
                        Color.Transparent
                    ),
                    center = Offset(centerX, centerY),
                    radius = radius * 0.5f
                ),
                radius = radius * 0.5f,
                center = Offset(centerX, centerY)
            )
        }
    }
}