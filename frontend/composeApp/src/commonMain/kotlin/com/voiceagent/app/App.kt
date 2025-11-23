// ============================================
// File: App.kt (Main Entry Point)
// Copy this entire file
// ============================================
package com.voiceagent.app

import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import com.voiceagent.app.models.AppScreen
import com.voiceagent.app.models.CallScreenConfig
import com.voiceagent.app.models.ThemeMode
import com.voiceagent.app.models.WellnessType
import com.voiceagent.app.screens.CallScreen
import com.voiceagent.app.screens.ChatScreen
import com.voiceagent.app.screens.InsightsScreen
import com.voiceagent.app.screens.LandingScreen
import com.voiceagent.app.screens.OrbSelectionScreen
import com.voiceagent.app.screens.SplashScreen
import com.voiceagent.app.screens.WellnessAgentScreen

@Composable
fun App() {
    var currentScreen by remember { mutableStateOf(AppScreen.SPLASH) }
    var themeMode by remember { mutableStateOf(ThemeMode.LIGHT) }
    var selectedWellnessType by remember { mutableStateOf<WellnessType?>(null) }

    val colorScheme = when (themeMode) {
        ThemeMode.LIGHT -> lightColorScheme(
            primary = Color(0xFF7C4DFF),
            background = Color(0xFFFFF8F0),
            surface = Color(0xFFFFF5E6)
        )
        ThemeMode.DARK -> darkColorScheme(
            primary = Color(0xFF7C4DFF),
            background = Color(0xFF1A1A2E),
            surface = Color(0xFF16213E)
        )
    }

    MaterialTheme(colorScheme = colorScheme) {
        when (currentScreen) {
            AppScreen.SPLASH -> SplashScreen(
                onFinished = { currentScreen = AppScreen.LANDING }
            )
            AppScreen.LANDING -> LandingScreen(
                onWellnessClick = { type ->
                    selectedWellnessType = type
                    currentScreen = AppScreen.ORB_SELECTION
                },
                onInsightsClick = {
                    currentScreen = AppScreen.INSIGHTS
                },
                themeMode = themeMode,
                onThemeChange = {
                    themeMode = if (themeMode == ThemeMode.LIGHT) ThemeMode.DARK else ThemeMode.LIGHT
                }
            )
            AppScreen.ORB_SELECTION -> {
                val type = selectedWellnessType ?: WellnessType.PHYSICAL
                OrbSelectionScreen(
                    wellnessType = type,
                    onCallClick = {
                        // Keep the selected wellness type
                        currentScreen = AppScreen.CALL_SCREEN
                    },
                    onChatClick = {
                        // Keep the selected wellness type
                        currentScreen = AppScreen.WELLNESS
                    },
                    onBack = { currentScreen = AppScreen.LANDING }
                )
            }
            AppScreen.WELLNESS -> {
                val type = selectedWellnessType ?: WellnessType.PHYSICAL
                ChatScreen(
                    wellnessType = type,
                    onBack = { currentScreen = AppScreen.ORB_SELECTION }
                )
            }
            AppScreen.CALL_SCREEN -> {
                val type = selectedWellnessType ?: WellnessType.PHYSICAL
                CallScreen(
                    config = CallScreenConfig(),
                    wellnessType = type,
                    onCallEnded = {
                        // Navigate back when call ends
                        currentScreen = AppScreen.ORB_SELECTION
                    },
                    onBack = {
                        currentScreen = AppScreen.ORB_SELECTION
                    }
                )
            }
            AppScreen.INSIGHTS -> {
                InsightsScreen(
                    onBack = { currentScreen = AppScreen.LANDING }
                )
            }
        }
    }
}