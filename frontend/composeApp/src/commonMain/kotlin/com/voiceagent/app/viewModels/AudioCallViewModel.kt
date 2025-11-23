//// ============================================
//// File: viewmodels/AudioCallViewModel.kt
//// Copy this entire file
//// ============================================
//package com.voiceagent.app.viewmodels
//
//import com.voiceagent.app.network.AudioSessionApi
//import com.voiceagent.app.network.AudioMessage
//import kotlinx.coroutines.CoroutineScope
//import kotlinx.coroutines.Dispatchers
//import kotlinx.coroutines.flow.MutableStateFlow
//import kotlinx.coroutines.flow.StateFlow
//import kotlinx.coroutines.flow.catch
//import kotlinx.coroutines.launch
//
//enum class CallState {
//    IDLE,
//    STARTING_SESSION,
//    WAITING_ORCHESTRATION,
//    CONNECTING_AUDIO,
//    CONNECTED,
//    SPEAKING,
//    LISTENING,
//    ERROR,
//    ENDED
//}
//
//data class CallUiState(
//    val callState: CallState = CallState.IDLE,
//    val sessionId: String? = null,
//    val agentTranscript: String = "",
//    val userTranscript: String = "",
//    val errorMessage: String? = null,
//    val statusMessage: String = "Initializing..."
//)
//
//class AudioCallViewModel(
//    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Main)
//) {
//    private val _uiState = MutableStateFlow(CallUiState())
//    val uiState: StateFlow<CallUiState> = _uiState
//
//    private var currentSessionId: String? = null
//
//    /**
//     * Step 1: Start the call
//     */
//    fun startCall(
//        userName: String,
//        mood: String? = null,
//        stepsToday: Int? = null,
//        sleepHours: Float? = null
//    ) {
//        scope.launch {
//            try {
//                _uiState.value = _uiState.value.copy(
//                    callState = CallState.STARTING_SESSION,
//                    statusMessage = "Starting session..."
//                )
//
//                // Start mobile session
//                val (success, sessionId) = AudioSessionApi.startMobileSession(
//                    name = userName,
//                    mood = mood,
//                    stepsToday = stepsToday,
//                    sleepHours = sleepHours
//                )
//
//                if (!success || sessionId == null) {
//                    _uiState.value = _uiState.value.copy(
//                        callState = CallState.ERROR,
//                        errorMessage = "Failed to start session"
//                    )
//                    return@launch
//                }
//
//                currentSessionId = sessionId
//                _uiState.value = _uiState.value.copy(
//                    sessionId = sessionId,
//                    callState = CallState.WAITING_ORCHESTRATION,
//                    statusMessage = "Analyzing your wellness data..."
//                )
//
//                // Wait for orchestration to complete
//                val orchestrationReady = AudioSessionApi.waitForOrchestrationComplete(sessionId)
//
//                if (!orchestrationReady) {
//                    _uiState.value = _uiState.value.copy(
//                        callState = CallState.ERROR,
//                        errorMessage = "Orchestration timeout"
//                    )
//                    return@launch
//                }
//
//                // Connect to audio WebSocket
//                _uiState.value = _uiState.value.copy(
//                    callState = CallState.CONNECTING_AUDIO,
//                    statusMessage = "Connecting to voice..."
//                )
//
//                connectToAudioSession(sessionId)
//
//            } catch (e: Exception) {
//                _uiState.value = _uiState.value.copy(
//                    callState = CallState.ERROR,
//                    errorMessage = e.message ?: "Unknown error"
//                )
//            }
//        }
//    }
//
//    /**
//     * Step 2: Connect to audio WebSocket and listen for messages
//     */
//    private fun connectToAudioSession(sessionId: String) {
//        scope.launch {
//            AudioSessionApi.connectAudioWebSocket(sessionId)
//                .catch { e ->
//                    _uiState.value = _uiState.value.copy(
//                        callState = CallState.ERROR,
//                        errorMessage = e.message ?: "Connection error"
//                    )
//                }
//                .collect { message ->
//                    handleAudioMessage(message)
//                }
//        }
//    }
//
//    /**
//     * Handle incoming audio messages
//     */
//    private fun handleAudioMessage(message: AudioMessage) {
//        when (message) {
//            is AudioMessage.AudioSessionStarted -> {
//                _uiState.value = _uiState.value.copy(
//                    callState = CallState.CONNECTED,
//                    statusMessage = "Connected! Start speaking..."
//                )
//            }
//
//            is AudioMessage.Audio -> {
//                // TODO: Play audio from server
//                // val audioBytes = Base64.decode(message.data, Base64.DEFAULT)
//                // playAudio(audioBytes)
//                _uiState.value = _uiState.value.copy(
//                    callState = CallState.LISTENING
//                )
//            }
//
//            is AudioMessage.AgentTranscript -> {
//                _uiState.value = _uiState.value.copy(
//                    agentTranscript = message.text,
//                    callState = CallState.LISTENING
//                )
//            }
//
//            is AudioMessage.UserTranscript -> {
//                _uiState.value = _uiState.value.copy(
//                    userTranscript = message.text,
//                    callState = CallState.SPEAKING
//                )
//            }
//
//            is AudioMessage.TurnComplete -> {
//                _uiState.value = _uiState.value.copy(
//                    callState = CallState.CONNECTED,
//                    statusMessage = "Listening..."
//                )
//            }
//
//            is AudioMessage.SessionEnding -> {
//                _uiState.value = _uiState.value.copy(
//                    statusMessage = "Session ending: ${message.reason}"
//                )
//            }
//
//            is AudioMessage.SessionEnded -> {
//                _uiState.value = _uiState.value.copy(
//                    callState = CallState.ENDED,
//                    statusMessage = "Session ended: ${message.reason}"
//                )
//            }
//
//            is AudioMessage.Error -> {
//                _uiState.value = _uiState.value.copy(
//                    callState = CallState.ERROR,
//                    errorMessage = message.message
//                )
//            }
//
//            is AudioMessage.OrchestrationComplete -> {
//                _uiState.value = _uiState.value.copy(
//                    statusMessage = message.message
//                )
//            }
//
//            else -> {}
//        }
//    }
//
//    /**
//     * Send audio to server
//     */
//    fun sendAudio(audioBase64: String) {
//        scope.launch {
//            // TODO: Implement sending audio
//            // This will require keeping a reference to the WebSocket session
//        }
//    }
//
//    /**
//     * End the call
//     */
//    fun endCall() {
//        scope.launch {
//            // TODO: Send end session message
//            _uiState.value = _uiState.value.copy(
//                callState = CallState.ENDED,
//                statusMessage = "Call ended"
//            )
//        }
//    }
//
//    fun cleanup() {
//        AudioSessionApi.cleanup()
//    }
//}