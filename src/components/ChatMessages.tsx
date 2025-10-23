'use client'

import React, { useEffect, useRef } from 'react'
import { FaUser, FaUserTie } from 'react-icons/fa'
import { useChat } from './ChatContext'
import { format } from 'date-fns'

const ChatMessages: React.FC = () => {
  const { messages } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const formatMessage = (content: string) => {
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>')
      .replace(/^/, '<p>')
      .replace(/$/, '</p>')
  }

  return (
    <div>
      {messages.map((message) => (
        <div key={message.id} className={`message ${message.type}`}>
          <div className="message-avatar">
            {message.type === 'user' ? <FaUser /> : <FaUserTie />}
          </div>
          <div className="message-content">
            <div className="message-bubble">
              <div 
                className="message-text"
                dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
              />
              <div className="message-time">
                {format(message.timestamp, 'HH:mm')}
              </div>
            </div>
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  )
}

export default ChatMessages
