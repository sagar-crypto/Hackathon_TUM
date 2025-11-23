// ============================================
// File: utils/ThemeUtils.kt
// Copy this entire file
// ============================================
package com.voiceagent.app.utils

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import com.voiceagent.app.models.ThemeMode

object ThemeUtils {
    fun getBackgroundColor(themeMode: ThemeMode): Color {
        return when (themeMode) {
            ThemeMode.LIGHT -> Color(0xFFFFF8F0)
            ThemeMode.DARK -> Color(0xFF1A1A2E)
        }
    }

    fun getSurfaceColor(themeMode: ThemeMode): Color {
        return when (themeMode) {
            ThemeMode.LIGHT -> Color(0xFFFFF5E6)
            ThemeMode.DARK -> Color(0xFF16213E)
        }
    }

    fun getTextColor(themeMode: ThemeMode): Color {
        return when (themeMode) {
            ThemeMode.LIGHT -> Color.Black
            ThemeMode.DARK -> Color.White
        }
    }

    fun getSecondaryTextColor(themeMode: ThemeMode): Color {
        return when (themeMode) {
            ThemeMode.LIGHT -> Color.DarkGray
            ThemeMode.DARK -> Color.Gray
        }
    }

    fun getBackgroundBrush(themeMode: ThemeMode): Brush {
        return when (themeMode) {
            ThemeMode.LIGHT -> Brush.verticalGradient(
                listOf(Color(0xFFFFF8F0), Color(0xFFFFF5E6), Color(0xFFFFEEDD))
            )
            ThemeMode.DARK -> Brush.verticalGradient(
                listOf(Color(0xFF1A1A2E), Color(0xFF0F0F1E), Color(0xFF1A1A2E))
            )
        }
    }
}