package com.voiceagent.app

interface Platform {
    val name: String
}

expect fun getPlatform(): Platform