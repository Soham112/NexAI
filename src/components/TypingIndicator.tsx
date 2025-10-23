'use client'

import React from 'react'
import { FaUserTie } from 'react-icons/fa'

const TypingIndicator: React.FC = () => {
  return (
    <div className="typing-indicator">
      <FaUserTie />
      <span>NexAI is thinking</span>
      <div className="typing-dots">
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
      </div>
    </div>
  )
}

export default TypingIndicator
