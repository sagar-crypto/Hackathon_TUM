// ============================================
// File: components/PyramidStructure.kt
// Copy this entire file
// ============================================
package com.voiceagent.app.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsHoveredAsState
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.*

@Composable
fun PyramidStructure(
    onMentalClick: () -> Unit,
    onSocialClick: () -> Unit,
    onPhysicalClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .widthIn(max = 700.dp)
            .height(550.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Bottom
    ) {
        // Level 3: Mental Wellness (Top)
        PyramidLevel(
            text = "Mental\nWellness",
            widthFraction = 0.45f,
            height = 120.dp,
            topCropPercent = 0.10f,
            colors = listOf(Color(0xFFFFA654), Color(0xFFFFBA6B)),
            fontSize = 20.sp,
            onClick = onMentalClick
        )

        // Level 2: Social Wellness (Middle)
        PyramidLevel(
            text = "Social\nWellness",
            widthFraction = 0.70f,
            height = 150.dp,
            topCropPercent = 0.15f,
            colors = listOf(Color(0xFFFF8C42), Color(0xFFFFA054)),
            fontSize = 24.sp,
            onClick = onSocialClick
        )

        // Level 1: Physical Wellness (Base)
        PyramidLevel(
            text = "Physical\nWellness",
            widthFraction = 1.0f,
            height = 180.dp,
            topCropPercent = 0.20f,
            colors = listOf(Color(0xFFFF6B35), Color(0xFFFF8547)),
            fontSize = 28.sp,
            onClick = onPhysicalClick
        )
    }
}

@Composable
fun PyramidLevel(
    text: String,
    widthFraction: Float,
    height: Dp,
    topCropPercent: Float,
    colors: List<Color>,
    fontSize: TextUnit,
    onClick: () -> Unit = {}
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isHovered by interactionSource.collectIsHoveredAsState()

    val animatedOffset by animateDpAsState(
        targetValue = if (isHovered) (-15).dp else 0.dp,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        )
    )

    val animatedScale by animateFloatAsState(
        targetValue = if (isHovered) 1.03f else 1.0f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        )
    )

    val animatedElevation by animateDpAsState(
        targetValue = if (isHovered) 15.dp else 4.dp,
        animationSpec = tween(durationMillis = 400)
    )

    Box(
        modifier = Modifier
            .fillMaxWidth(widthFraction)
            .height(height)
            .offset(y = animatedOffset)
            .graphicsLayer {
                scaleX = animatedScale
                scaleY = animatedScale
            }
            .shadow(
                elevation = animatedElevation,
                shape = TrapezoidShape(topCropPercent),
                clip = false
            )
            .clip(TrapezoidShape(topCropPercent))
            .background(
                brush = Brush.linearGradient(
                    colors = colors,
                    start = Offset(0f, 0f),
                    end = Offset(Float.POSITIVE_INFINITY, Float.POSITIVE_INFINITY)
                )
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            fontSize = fontSize,
            fontWeight = FontWeight.Bold,
            color = Color.White,
            textAlign = TextAlign.Center,
            letterSpacing = 1.sp,
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 30.dp),
            style = androidx.compose.ui.text.TextStyle(
                shadow = Shadow(
                    color = Color.Black.copy(alpha = 0.2f),
                    offset = Offset(0f, 2f),
                    blurRadius = 4f
                )
            )
        )
    }
}

class TrapezoidShape(private val topCropPercent: Float) : Shape {
    override fun createOutline(
        size: Size,
        layoutDirection: LayoutDirection,
        density: Density
    ): Outline {
        val path = Path().apply {
            val topInset = size.width * topCropPercent

            moveTo(topInset, 0f)
            lineTo(size.width - topInset, 0f)
            lineTo(size.width, size.height)
            lineTo(0f, size.height)
            close()
        }
        return Outline.Generic(path)
    }
}