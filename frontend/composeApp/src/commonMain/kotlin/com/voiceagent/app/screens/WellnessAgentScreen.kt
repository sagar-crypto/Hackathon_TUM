// ============================================
// File: screens/WellnessAgentScreen.kt
// Copy this entire file
// ============================================
package com.voiceagent.app.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voiceagent.app.components.InputField
import com.voiceagent.app.models.AgentStatus
import com.voiceagent.app.models.ThemeMode
import com.voiceagent.app.network.WellnessAgentApi
import com.voiceagent.app.utils.ThemeUtils
import kotlinx.coroutines.launch

@Composable
fun WellnessAgentScreen(
    onBack: () -> Unit = {},
    themeMode: ThemeMode = ThemeMode.DARK,
    onThemeChange: () -> Unit = {}
) {
    var status by remember { mutableStateOf(AgentStatus.IDLE) }
    var isConnected by remember { mutableStateOf(false) }
    var statusMessage by remember { mutableStateOf("Fill in your details") }
    var userName by remember { mutableStateOf("") }
    var userMood by remember { mutableStateOf("") }
    var stepsToday by remember { mutableStateOf("") }
    var sleepHours by remember { mutableStateOf("") }
    var conversationSummary by remember { mutableStateOf("") }
    var goals by remember { mutableStateOf("") }

    val scope = rememberCoroutineScope()

    val bgColor = ThemeUtils.getBackgroundColor(themeMode)
    val surfaceColor = ThemeUtils.getSurfaceColor(themeMode)
    val textColor = ThemeUtils.getTextColor(themeMode)
    val secondaryTextColor = ThemeUtils.getSecondaryTextColor(themeMode)

    LaunchedEffect(Unit) {
        isConnected = WellnessAgentApi.checkHealth()
        statusMessage = if (isConnected) "Server connected!" else "Server not connected"
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(bgColor)
            .padding(top = 60.dp, start = 16.dp, end = 16.dp, bottom = 16.dp)
    ) {
        WellnessHeader(onBack, textColor, secondaryTextColor)
        Spacer(modifier = Modifier.height(12.dp))
        ConnectionStatus(isConnected) {
            scope.launch { isConnected = WellnessAgentApi.checkHealth() }
        }
        Spacer(modifier = Modifier.height(12.dp))
        StatusIndicator(status, statusMessage, surfaceColor, textColor)
        Spacer(modifier = Modifier.height(12.dp))
        WellnessForm(
            userName, userMood, stepsToday, sleepHours, conversationSummary, goals,
            onNameChange = { userName = it },
            onMoodChange = { userMood = it },
            onStepsChange = { stepsToday = it.filter { c -> c.isDigit() } },
            onSleepChange = { sleepHours = it.filter { c -> c.isDigit() || c == '.' } },
            onSummaryChange = { conversationSummary = it },
            onGoalsChange = { goals = it },
            surfaceColor, textColor, themeMode,
            modifier = Modifier.weight(1f)
        )
        Spacer(modifier = Modifier.height(16.dp))
        StartSessionButton(
            isConnected, userName, status,
            onClick = {
                scope.launch {
                    status = AgentStatus.CONNECTING
                    statusMessage = "Starting session..."
                    val (success, msg) = WellnessAgentApi.startSession(
                        userName, userMood.ifBlank { null }, stepsToday.toIntOrNull(),
                        sleepHours.toFloatOrNull(), conversationSummary.ifBlank { null },
                        goals.ifBlank { null }
                    )
                    status = if (success) AgentStatus.ACTIVE else AgentStatus.ERROR
                    statusMessage = if (success) "🎙️ Session Active! Speak into Mac's mic" else msg
                }
            }
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            "Voice session runs on Mac (mic + speakers)",
            color = secondaryTextColor,
            fontSize = 12.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun WellnessHeader(
    onBack: () -> Unit,
    textColor: Color,
    secondaryTextColor: Color
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
        horizontalArrangement = Arrangement.Start,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Button(
            onClick = onBack,
            modifier = Modifier.size(48.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF7C4DFF)),
            shape = CircleShape
        ) {
            Text("←", fontSize = 20.sp, color = Color.White)
        }

        Column(
            modifier = Modifier.weight(1f),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                "🧘 Wellness Agent",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = textColor
            )
            Text(
                "Your AI Wellness Companion",
                fontSize = 14.sp,
                color = secondaryTextColor
            )
        }

        Box(modifier = Modifier.size(48.dp))
    }
}

@Composable
private fun ConnectionStatus(isConnected: Boolean, onRetry: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(if (isConnected) Color(0xFF1B5E20) else Color(0xFF7F0000))
            .clickable { onRetry() }
            .padding(10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .clip(CircleShape)
                .background(if (isConnected) Color(0xFF4CAF50) else Color(0xFFFF5252))
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            if (isConnected) "✓ Connected" else "✗ Disconnected (tap to retry)",
            color = Color.White,
            fontSize = 13.sp
        )
    }
}

@Composable
private fun StatusIndicator(
    status: AgentStatus,
    statusMessage: String,
    surfaceColor: Color,
    textColor: Color
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(surfaceColor)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center
    ) {
        val statusColor = when (status) {
            AgentStatus.IDLE -> Color.Gray
            AgentStatus.CONNECTING -> Color(0xFFFFC107)
            AgentStatus.ACTIVE -> Color(0xFF4CAF50)
            AgentStatus.ERROR -> Color(0xFFFF5252)
        }
        Box(
            modifier = Modifier
                .size(12.dp)
                .clip(CircleShape)
                .background(statusColor)
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(statusMessage, color = textColor, fontSize = 14.sp)
    }
}

@Composable
private fun WellnessForm(
    userName: String,
    userMood: String,
    stepsToday: String,
    sleepHours: String,
    conversationSummary: String,
    goals: String,
    onNameChange: (String) -> Unit,
    onMoodChange: (String) -> Unit,
    onStepsChange: (String) -> Unit,
    onSleepChange: (String) -> Unit,
    onSummaryChange: (String) -> Unit,
    onGoalsChange: (String) -> Unit,
    surfaceColor: Color,
    textColor: Color,
    themeMode: ThemeMode,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(surfaceColor)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(
                "👤 Your Information",
                color = textColor,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        }
        item {
            InputField(
                "Name *", userName, onNameChange,
                "Enter your name", themeMode
            )
        }
        item {
            InputField(
                "Current Mood", userMood, onMoodChange,
                "e.g., tired, anxious", themeMode
            )
        }
        item {
            Text(
                "❤️ Health Data",
                color = textColor,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        }
        item {
            InputField(
                "Steps Today", stepsToday, onStepsChange,
                "e.g., 5000", themeMode, KeyboardType.Number
            )
        }
        item {
            InputField(
                "Sleep Hours", sleepHours, onSleepChange,
                "e.g., 7.5", themeMode, KeyboardType.Decimal
            )
        }
        item {
            Text(
                "💬 Context",
                color = textColor,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        }
        item {
            InputField(
                "Previous Summary", conversationSummary, onSummaryChange,
                "What did you discuss?", themeMode
            )
        }
        item {
            Text(
                "🎯 Goals",
                color = textColor,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        }
        item {
            InputField(
                "Wellness Goals", goals, onGoalsChange,
                "e.g., sleep better", themeMode
            )
        }
    }
}

@Composable
private fun StartSessionButton(
    isConnected: Boolean,
    userName: String,
    status: AgentStatus,
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        enabled = isConnected && userName.isNotBlank() && status != AgentStatus.CONNECTING,
        modifier = Modifier.fillMaxWidth().height(60.dp),
        shape = RoundedCornerShape(16.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (status == AgentStatus.ACTIVE) {
                Color(0xFF4CAF50)
            } else {
                Color(0xFF7C4DFF)
            }
        )
    ) {
        Text(
            when (status) {
                AgentStatus.CONNECTING -> "⏳ Connecting..."
                AgentStatus.ACTIVE -> "🎙️ Session Active"
                else -> "🧘 Start Wellness Session"
            },
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold
        )
    }
}