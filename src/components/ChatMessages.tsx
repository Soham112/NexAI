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

  const hasSources = (content: string) => {
    return content.includes('*Sources:')
  }

  const extractSources = (content: string) => {
    const sourcesMatch = content.match(/\*Sources: (.*?)\*/)
    return sourcesMatch ? sourcesMatch[1] : null
  }

  const removeSources = (content: string) => {
    return content.replace(/\n\n\*Sources: .*?\*/, '')
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
                dangerouslySetInnerHTML={{ 
                  __html: formatMessage(
                    hasSources(message.content) 
                      ? removeSources(message.content) 
                      : message.content
                  ) 
                }}
              />
              {hasSources(message.content) && (
                <div className="message-sources">
                  <small>
                    <strong>Sources:</strong> {extractSources(message.content)}
                  </small>
                </div>
              )}
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
