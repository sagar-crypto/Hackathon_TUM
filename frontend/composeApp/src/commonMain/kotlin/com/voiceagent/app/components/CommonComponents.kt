// ============================================
// File: components/CommonComponents.kt
// Copy this entire file
// ============================================
package com.voiceagent.app.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voiceagent.app.models.ThemeMode

@Composable
fun LoadingDots(primaryColor: Color) {
    val infiniteTransition = rememberInfiniteTransition()
    Row {
        for (i in 0 until 3) {
            val dotAlpha by infiniteTransition.animateFloat(
                initialValue = 0.3f,
                targetValue = 1f,
                animationSpec = infiniteRepeatable(
                    tween(600, delayMillis = i * 200),
                    RepeatMode.Reverse
                )
            )
            Box(
                modifier = Modifier
                    .padding(horizontal = 4.dp)
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(primaryColor.copy(alpha = dotAlpha))
            )
        }
    }
}

@Composable
fun InputField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    themeMode: ThemeMode = ThemeMode.DARK,
    keyboardType: KeyboardType = KeyboardType.Text
) {
    val labelColor = when (themeMode) {
        ThemeMode.LIGHT -> Color.DarkGray
        ThemeMode.DARK -> Color.LightGray
    }

    val textColor = when (themeMode) {
        ThemeMode.LIGHT -> Color.Black
        ThemeMode.DARK -> Color.White
    }

    val placeholderColor = when (themeMode) {
        ThemeMode.LIGHT -> Color.Gray
        ThemeMode.DARK -> Color.Gray
    }

    Column {
        Text(
            text = label,
            color = labelColor,
            fontSize = 12.sp,
            modifier = Modifier.padding(bottom = 4.dp)
        )
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            placeholder = {
                Text(placeholder, color = placeholderColor, fontSize = 14.sp)
            },
            modifier = Modifier.fillMaxWidth(),
            colors = OutlinedTextFieldDefaults.colors(
                focusedTextColor = textColor,
                unfocusedTextColor = textColor,
                focusedBorderColor = Color(0xFF7C4DFF),
                unfocusedBorderColor = Color.Gray,
                cursorColor = Color(0xFF7C4DFF)
            ),
            keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
            singleLine = true,
            shape = RoundedCornerShape(12.dp)
        )
    }
}