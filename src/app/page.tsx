'use client'

import ChatInterface from '../components/ChatInterface'
import WelcomeSection from '../components/WelcomeSection'

export default function Home() {
  return (
    <main className="main-content">
      <WelcomeSection />
      <ChatInterface />
    </main>
  )
}
