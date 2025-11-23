// ============================================
// File: screens/LandingScreen.kt
// Copy this entire file
// ============================================
package com.voiceagent.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voiceagent.app.models.ThemeMode
import com.voiceagent.app.models.WellnessType

@Composable
fun LandingScreen(
    onWellnessClick: (WellnessType) -> Unit,
    onInsightsClick: () -> Unit = {},
    themeMode: ThemeMode,
    onThemeChange: () -> Unit
) {
    val bgColors = when (themeMode) {
        ThemeMode.LIGHT -> listOf(Color(0xFFFFF5ED), Color(0xFFFFE4D6))
        ThemeMode.DARK -> listOf(Color(0xFF0a0a12), Color(0xFF1a1a28))
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(bgColors)
            )
    ) {
        // Floating Orbs Background
        FloatingOrbs()

        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
        ) {
            // Top Bar
            TopBar(themeMode, onThemeChange)

            // Cards Section
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 10.dp),
                contentAlignment = Alignment.Center
            ) {
                WellnessCards(
                    onWellnessClick = onWellnessClick,
                    onInsightsClick = onInsightsClick,
                    themeMode = themeMode
                )
            }
        }
    }
}

@Composable
private fun FloatingOrbs() {
    val infiniteTransition = rememberInfiniteTransition()

    val orb1Offset by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = -30f,
        animationSpec = infiniteRepeatable(
            animation = tween(20000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        )
    )

    val orb2Offset by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = -30f,
        animationSpec = infiniteRepeatable(
            animation = tween(20000, easing = FastOutSlowInEasing, delayMillis = 5000),
            repeatMode = RepeatMode.Reverse
        )
    )

    val orb3Offset by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = -30f,
        animationSpec = infiniteRepeatable(
            animation = tween(20000, easing = FastOutSlowInEasing, delayMillis = 10000),
            repeatMode = RepeatMode.Reverse
        )
    )

    Box(modifier = Modifier.fillMaxSize()) {
        // Orb 1 - Blue
        Box(
            modifier = Modifier
                .offset(x = (-40).dp, y = (orb1Offset).dp)
                .size(200.dp)
                .align(Alignment.TopStart)
                .offset(y = 100.dp)
                .blur(60.dp)
                .background(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0xFF4facfe), Color(0xFF00f2fe))
                    ),
                    shape = CircleShape,
                    alpha = 0.08f
                )
        )

        // Orb 2 - Yellow
        Box(
            modifier = Modifier
                .offset(x = (-60).dp, y = orb2Offset.dp)
                .size(180.dp)
                .align(Alignment.BottomEnd)
                .offset(y = (-150).dp)
                .blur(60.dp)
                .background(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0xFFffd93d), Color(0xFFffe066))
                    ),
                    shape = CircleShape,
                    alpha = 0.08f
                )
        )

        // Orb 3 - Green
        Box(
            modifier = Modifier
                .size(160.dp)
                .align(Alignment.Center)
                .offset(y = orb3Offset.dp)
                .blur(60.dp)
                .background(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0xFF43e97b), Color(0xFF38f9d7))
                    ),
                    shape = CircleShape,
                    alpha = 0.08f
                )
        )
    }
}

@Composable
private fun TopBar(themeMode: ThemeMode, onThemeChange: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 24.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Logo
        Text(
            text = "ETHOS",
            fontSize = 32.sp,
            fontWeight = FontWeight.Black,
            letterSpacing = 2.sp,
            style = androidx.compose.ui.text.TextStyle(
                brush = Brush.linearGradient(
                    colors = listOf(
                        Color(0xFF4facfe),
                        Color(0xFFffd93d),
                        Color(0xFF43e97b)
                    )
                )
            )
        )

        // Theme Toggle Button
        Button(
            onClick = onThemeChange,
            modifier = Modifier.size(44.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color.White.copy(alpha = 0.05f)
            ),
            contentPadding = PaddingValues(0.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text(
                text = if (themeMode == ThemeMode.LIGHT) "☀️" else "🌙",
                fontSize = 20.sp
            )
        }
    }
}

@Composable
private fun WellnessCards(
    onWellnessClick: (WellnessType) -> Unit,
    onInsightsClick: () -> Unit,
    themeMode: ThemeMode
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .widthIn(max = 393.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // Insights Card - Full Width (New)
        InsightsCard(
            themeMode = themeMode,
            onClick = onInsightsClick,
            modifier = Modifier.fillMaxWidth()
        )

        // Full Width Card - Physical (Blue)
        WellnessCard(
            title = "Physical",
            wellnessType = WellnessType.PHYSICAL,
            progress = 65,
            colors = listOf(Color(0xFF4facfe), Color(0xFF00f2fe)),
            themeMode = themeMode,
            onClick = { onWellnessClick(WellnessType.PHYSICAL) },
            modifier = Modifier.fillMaxWidth()
        )

        // Two Square Cards Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Mental Card (Orange)
            WellnessCard(
                title = "Mental",
                wellnessType = WellnessType.MENTAL,
                progress = 80,
                colors = listOf(Color(0xFFffd93d), Color(0xFFffe066)),
                themeMode = themeMode,
                onClick = { onWellnessClick(WellnessType.MENTAL) },
                modifier = Modifier.weight(1f)
            )

            // Social Card (Green)
            WellnessCard(
                title = "Social",
                wellnessType = WellnessType.SOCIAL,
                progress = 45,
                colors = listOf(Color(0xFF43e97b), Color(0xFF38f9d7)),
                themeMode = themeMode,
                onClick = { onWellnessClick(WellnessType.SOCIAL) },
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun WellnessCard(
    title: String,
    wellnessType: WellnessType,
    progress: Int,
    colors: List<Color>,
    themeMode: ThemeMode,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val borderColor = colors[0].copy(alpha = 0.3f)
    val textColor = Color(0xFF2d2d2d)
    val labelColor = Color(0xFF2d2d2d).copy(alpha = 0.6f)

    Box(
        modifier = modifier
            .heightIn(min = 180.dp)
            .clip(RoundedCornerShape(20.dp))
            .background(Color.White.copy(alpha = 0.7f))
            .clickable { onClick() }
            .then(
                Modifier.padding(1.dp)
                    .clip(RoundedCornerShape(20.dp))
            ),
        contentAlignment = Alignment.Center
    ) {
        // Border overlay
        Box(
            modifier = Modifier
                .matchParentSize()
                .clip(RoundedCornerShape(20.dp))
                .background(Color.Transparent)
                .padding(1.dp)
        ) {
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .clip(RoundedCornerShape(19.dp))
                    .background(Color.Transparent)
            )
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Animated Orb Icon
            AnimatedOrbIcon(colors)

            // Title
            Text(
                text = title,
                fontSize = 22.sp,
                fontWeight = FontWeight.ExtraBold,
                color = textColor,
                letterSpacing = (-0.5).sp
            )

            // Progress Section
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(
                    text = "Progress",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = labelColor
                )

                // Progress Bar
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(5.dp)
                        .clip(RoundedCornerShape(5.dp))
                        .background(colors[0].copy(alpha = 0.15f))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxHeight()
                            .fillMaxWidth(progress / 100f)
                            .clip(RoundedCornerShape(5.dp))
                            .background(
                                brush = Brush.horizontalGradient(colors)
                            )
                    )
                }
            }
        }
    }
}

@Composable
private fun AnimatedOrbIcon(colors: List<Color>) {
    val infiniteTransition = rememberInfiniteTransition()

    val pulse by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        )
    )

    Box(
        modifier = Modifier.size(70.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier
                .size((70 * pulse).dp)
        ) {
            val center = Offset(size.width / 2, size.height / 2)
            val radius = size.minDimension / 2

            // Outer glow
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        colors[0].copy(alpha = 0.6f),
                        colors[1].copy(alpha = 0.3f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = radius * 1.5f
                ),
                radius = radius * 1.5f,
                center = center
            )

            // Main orb
            drawCircle(
                brush = Brush.radialGradient(
                    colors = colors,
                    center = center,
                    radius = radius
                ),
                radius = radius,
                center = center
            )
        }
    }
}

@Composable
private fun InsightsCard(
    themeMode: ThemeMode,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val colors = listOf(
        Color(0xFF9C27B0),
        Color(0xFFE91E63)
    )

    Surface(
        modifier = modifier
            .heightIn(min = 140.dp)
            .clip(RoundedCornerShape(20.dp))
            .clickable { onClick() },
        color = Color.White.copy(alpha = 0.9f),
        shadowElevation = 1.dp
    ) {
        Box(
            modifier = Modifier
                .background(
                    brush = Brush.linearGradient(
                        colors = listOf(
                            colors[0].copy(alpha = 0.05f),
                            colors[1].copy(alpha = 0.03f)
                        )
                    )
                )
                .padding(20.dp)
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
                        text = "Insights",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF2d2d2d),
                        letterSpacing = 0.sp
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Track your wellness journey",
                        fontSize = 14.sp,
                        color = Color(0xFF2d2d2d).copy(alpha = 0.6f),
                        lineHeight = 20.sp
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    // Mini stats row
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        MiniStat("78%", "Happy", Color(0xFFFFB74D))
                        MiniStat("82%", "Energy", Color(0xFF43e97b))
                    }
                }

                Spacer(modifier = Modifier.width(16.dp))

                // Animated mini graph
                AnimatedMiniGraph(colors)
            }
        }
    }
}

@Composable
private fun MiniStat(value: String, label: String, color: Color) {
    Column {
        Text(
            text = value,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
            color = color
        )
        Text(
            text = label,
            fontSize = 11.sp,
            color = Color(0xFF2d2d2d).copy(alpha = 0.5f)
        )
    }
}

@Composable
private fun AnimatedMiniGraph(colors: List<Color>) {
    val infiniteTransition = rememberInfiniteTransition(label = "graph")

    val progress1 by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.7f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "bar1"
    )

    val progress2 by infiniteTransition.animateFloat(
        initialValue = 0.5f,
        targetValue = 0.85f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = FastOutSlowInEasing, delayMillis = 300),
            repeatMode = RepeatMode.Reverse
        ),
        label = "bar2"
    )

    val progress3 by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 0.75f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = FastOutSlowInEasing, delayMillis = 600),
            repeatMode = RepeatMode.Reverse
        ),
        label = "bar3"
    )

    Box(
        modifier = Modifier
            .size(80.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(Color.White.copy(alpha = 0.6f))
            .padding(12.dp)
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val barWidth = size.width / 5
            val spacing = barWidth * 0.4f

            // Bar 1
            drawRoundRect(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        colors[0].copy(alpha = 0.3f),
                        colors[0].copy(alpha = 0.15f)
                    )
                ),
                topLeft = Offset(0f, size.height * (1f - progress1)),
                size = Size(barWidth, size.height * progress1),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(4f, 4f)
            )

            // Bar 2
            drawRoundRect(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        colors[0].copy(alpha = 0.5f),
                        colors[0].copy(alpha = 0.25f)
                    )
                ),
                topLeft = Offset(barWidth + spacing, size.height * (1f - progress2)),
                size = Size(barWidth, size.height * progress2),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(4f, 4f)
            )

            // Bar 3
            drawRoundRect(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        colors[1].copy(alpha = 0.5f),
                        colors[1].copy(alpha = 0.25f)
                    )
                ),
                topLeft = Offset((barWidth + spacing) * 2, size.height * (1f - progress3)),
                size = Size(barWidth, size.height * progress3),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(4f, 4f)
            )
        }
    }
}