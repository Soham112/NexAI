'use client'

import React, { createContext, useContext, useState, ReactNode } from 'react'

export interface Message {
  id: string
  type: 'user' | 'nexai'
  content: string
  timestamp: Date
}

export interface ChatContextType {
  messages: Message[]
  isTyping: boolean
  addMessage: (type: 'user' | 'nexai', content: string) => void
  setTyping: (isTyping: boolean) => void
  clearMessages: () => void
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export const useChat = () => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}

interface ChatProviderProps {
  children: ReactNode
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false)

  const addMessage = (type: 'user' | 'nexai', content: string) => {
    const newMessage: Message = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      content,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, newMessage])
  }

  const setTyping = (typing: boolean) => {
    setIsTyping(typing)
  }

  const clearMessages = () => {
    setMessages([])
  }

  const value: ChatContextType = {
    messages,
    isTyping,
    addMessage,
    setTyping,
    clearMessages,
  }

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}
