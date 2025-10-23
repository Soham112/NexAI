'use client'

import { useState } from 'react'
import ChatInterface from '../components/ChatInterface'
import WelcomeSection from '../components/WelcomeSection'

export default function Home() {
  const [isChatMode, setIsChatMode] = useState(false)

  const handleStartChat = () => {
    setIsChatMode(true)
  }

  return (
    <main className="main-content">
      {!isChatMode ? (
        <WelcomeSection onStartChat={handleStartChat} />
      ) : (
        <ChatInterface />
      )}
    </main>
  )
}
