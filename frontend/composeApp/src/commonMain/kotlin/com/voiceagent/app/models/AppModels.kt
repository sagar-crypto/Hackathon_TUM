// ============================================
// File: models/AppModels.kt
// Copy this entire file
// ============================================
package com.voiceagent.app.models

enum class AppScreen { SPLASH, LANDING, WELLNESS, CALL_SCREEN, ORB_SELECTION, INSIGHTS }
enum class AgentStatus { IDLE, CONNECTING, ACTIVE, ERROR }
enum class ThemeMode { LIGHT, DARK }
enum class WellnessType { MENTAL, SOCIAL, PHYSICAL }

data class CallScreenConfig(
    val callerName: String = "ETHOS",
    val callType: String = "Wellness Assistant",
    val incomingText: String = "Incoming Call",
    val slideText: String = "slide to answer",
    val fontFamily: String = "SF Pro Display",
    val fontSize: Int = 16
)