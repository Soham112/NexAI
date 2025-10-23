'use client'

import React, { useState, useRef, useEffect } from 'react'
import { FaPlus, FaCog, FaPaperPlane, FaUser, FaUserTie } from 'react-icons/fa'
import { useChat } from './ChatContext'
import ChatMessages from './ChatMessages'
import TypingIndicator from './TypingIndicator'

const ChatInterface: React.FC = () => {
  const [inputValue, setInputValue] = useState('')
  const { addMessage, isTyping, setTyping } = useChat()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

  const handleSendMessage = async () => {
    const message = inputValue.trim()
    if (!message || isTyping) return

    // Add user message
    addMessage('user', message)
    setInputValue('')

    // Set typing indicator
    setTyping(true)

    try {
      // Call API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          conversationId: 'session_' + Date.now(),
          settings: {
            model: 'claude-3-7-sonnet',
            temperature: 0.7
          }
        })
      })

      if (!response.ok) {
        throw new Error(`API call failed: ${response.status}`)
      }

      const data = await response.json()
      
      // Remove typing indicator and add response
      setTyping(false)
      addMessage('nextai', data.response)
    } catch (error) {
      console.error('Error getting response:', error)
      setTyping(false)
      addMessage('nextai', 'Sorry, I encountered an error. Please try again.')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  const isSendDisabled = !inputValue.trim() || isTyping

  return (
    <>
      <div className="input-section">
        <div className="input-container">
          <input
            ref={inputRef}
            type="text"
            className="input-field"
            placeholder="Ask NextAI"
            value={inputValue}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            disabled={isTyping}
          />
          <div className="input-actions">
            <button className="input-action-btn" title="Attach file">
              <FaPlus />
            </button>
            <button className="tools-btn">
              <FaCog />
              Tools
            </button>
            <button 
              className="send-btn" 
              onClick={handleSendMessage}
              disabled={isSendDisabled}
            >
              <FaPaperPlane />
            </button>
          </div>
          <div className="tooltip">Click to go back, hold to see history</div>
        </div>
      </div>

      <div className="chat-messages">
        <ChatMessages />
        {isTyping && <TypingIndicator />}
      </div>
    </>
  )
}

export default ChatInterface
