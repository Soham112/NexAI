'use client'

import React, { useState, useRef, useEffect } from 'react'
import { FaUpload, FaPaperPlane, FaFilePdf, FaFileWord, FaFileAlt } from 'react-icons/fa'
import { useChat } from './ChatContext'
import ChatMessages from './ChatMessages'
import TypingIndicator from './TypingIndicator'

const ChatInterface: React.FC = () => {
  const [inputValue, setInputValue] = useState('')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const { addMessage, isTyping, setTyping } = useChat()
  const inputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
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

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file type
      const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
      if (!allowedTypes.includes(file.type)) {
        addMessage('nexai', 'Please upload a PDF, Word document, or text file.')
        return
      }
      
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        addMessage('nexai', 'File size must be less than 10MB.')
        return
      }
      
      setIsUploading(true)
      addMessage('nexai', `Uploading resume: ${file.name}...`)
      
      try {
        // Use proxy upload to avoid CORS and permission issues
        const formData = new FormData()
        formData.append('file', file)
        formData.append('conversationId', conversationIdRef.current)
        
        const uploadResponse = await fetch('/api/upload-proxy', {
          method: 'POST',
          body: formData
        })
        
        if (!uploadResponse.ok) {
          throw new Error(`Upload failed: ${uploadResponse.status}`)
        }
        
        const { s3Key } = await uploadResponse.json()
        
        // Step 3: Analyze the uploaded resume
        addMessage('nexai', `✅ Resume uploaded successfully: ${file.name}`)
        addMessage('nexai', `🔍 Analyzing resume for career insights...`)
        
        const analysisResponse = await fetch('/api/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            s3Key,
            userPrompt: 'Analyze my resume and suggest suitable roles, relevant courses, missing skills, and project ideas.',
            conversationId: conversationIdRef.current
          })
        })
        
        if (!analysisResponse.ok) {
          throw new Error(`Analysis failed: ${analysisResponse.status}`)
        }
        
        const analysisResult = await analysisResponse.json()
        
        if (analysisResult.success) {
          setUploadedFile(file)
          
          // Display the analysis results in the chat
          const analysisData = analysisResult.analysis
          let analysisMessage = `📊 Resume Analysis Complete!\n\n`
          
          if (analysisData.insights) {
            analysisMessage += `**Analysis Insights:**\n${analysisData.insights}\n\n`
          }
          
          if (analysisData.recommendedRoles && analysisData.recommendedRoles.length > 0) {
            analysisMessage += `**🎯 Recommended Roles:**\n${analysisData.recommendedRoles.map(role => `• ${role}`).join('\n')}\n\n`
          }
          
          if (analysisData.missingSkills && analysisData.missingSkills.length > 0) {
            analysisMessage += `**🔧 Missing Skills to Develop:**\n${analysisData.missingSkills.map(skill => `• ${skill}`).join('\n')}\n\n`
          }
          
          if (analysisData.projectIdeas && analysisData.projectIdeas.length > 0) {
            analysisMessage += `**💡 Project Ideas:**\n${analysisData.projectIdeas.map(project => `• ${project}`).join('\n')}\n\n`
          }
          
          if (analysisData.relevantCourses && analysisData.relevantCourses.length > 0) {
            analysisMessage += `**📚 Relevant Courses:**\n${analysisData.relevantCourses.map(course => `• ${course}`).join('\n')}\n\n`
          }
          
          // Add S3 key info
          analysisMessage += `**📁 Resume Location:** ${analysisResult.s3Key}`
          
          addMessage('nexai', analysisMessage)
        } else {
          throw new Error('Analysis failed')
        }
        
      } catch (error) {
        console.error('Upload/Analysis error:', error)
        addMessage('nexai', `❌ Failed to process resume: ${error instanceof Error ? error.message : 'Unknown error'}`)
      } finally {
        setIsUploading(false)
      }
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const removeFile = () => {
    setUploadedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const getFileIcon = (file: File) => {
    if (file.type === 'application/pdf') return <FaFilePdf />
    if (file.type.includes('word')) return <FaFileWord />
    return <FaFileAlt />
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
            <button 
              className="resume-upload-btn" 
              onClick={handleUploadClick}
              disabled={isUploading}
              title="Upload Resume"
            >
              <FaUpload />
              {isUploading ? 'Uploading...' : 'Resume'}
            </button>
            <button 
              className="send-btn" 
              onClick={handleSendMessage}
              disabled={isSendDisabled}
            >
              <FaPaperPlane />
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
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
