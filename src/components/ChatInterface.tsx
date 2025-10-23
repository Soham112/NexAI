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
  const conversationIdRef = useRef<string>(`session_${Date.now()}`)

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

  const handleSendMessage = async () => {
    const message = inputValue.trim()
    if (!message || isTyping) return

    // Input validation
    if (message.length > 10000) {
      addMessage('nexai', 'Message is too long. Please keep it under 10,000 characters.')
      return
    }

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
          conversationId: conversationIdRef.current,
          settings: {
            model: 'lambda-bedrock-agent',
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
      
      // Handle different response formats and errors
      if (data.error) {
        addMessage('nexai', `Sorry, I encountered an issue: ${data.error}. Please try again.`)
        return
      }
      
      // Add response with source information if available
      let responseText = data.response
      if (data.metadata && data.metadata.sources && data.metadata.sources.length > 0) {
        responseText += `\n\n*Sources: ${data.metadata.sources.join(', ')}*`
      }
      
      addMessage('nexai', responseText)
    } catch (error) {
      console.error('Error getting response:', error)
      setTyping(false)
      addMessage('nexai', 'Sorry, I encountered an error. Please try again.')
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
  const isMessageTooLong = inputValue.length > 10000

  return (
    <>
      <div className="input-section">
        <div className="input-container">
          <input
            ref={inputRef}
            type="text"
            className="input-field"
            placeholder="Ask NexAI"
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
          {inputValue.length > 0 && (
            <div className={`character-count ${isMessageTooLong ? 'error' : ''}`}>
              {inputValue.length}/10,000 characters
            </div>
          )}
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
