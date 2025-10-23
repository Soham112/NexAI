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

  // Helper function to convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => {
        const result = reader.result as string
        // Remove the data URL prefix (e.g., "data:application/pdf;base64,")
        const base64 = result.split(',')[1]
        resolve(base64)
      }
      reader.onerror = error => reject(error)
    })
  }

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
        // Convert file to base64 for upload
        const fileData = await fileToBase64(file)
        
        // Generate unique key for S3
        const timestamp = Date.now()
        const fileExtension = file.name.split('.').pop()
        const s3Key = `resumes/${conversationIdRef.current}/${timestamp}.${fileExtension}`
        
        // Upload to S3 via API
        const response = await fetch('/api/upload', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            data: fileData,
            key: s3Key,
            contentType: file.type
          })
        })
        
        if (!response.ok) {
          throw new Error(`Upload failed: ${response.status}`)
        }
        
        const uploadResult = await response.json()
        
        if (uploadResult.success) {
          setUploadedFile(file)
          addMessage('nexai', `✅ Resume uploaded successfully: ${file.name}`)
        } else {
          throw new Error('Upload failed')
        }
      } catch (error) {
        console.error('Upload error:', error)
        addMessage('nexai', `❌ Failed to upload resume: ${error instanceof Error ? error.message : 'Unknown error'}`)
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
          {inputValue.length > 0 && (
            <div className={`character-count ${isMessageTooLong ? 'error' : ''}`}>
              {inputValue.length}/10,000 characters
            </div>
          )}
          {uploadedFile && (
            <div className="uploaded-file-display">
              <div className="file-info">
                {getFileIcon(uploadedFile)}
                <span className="file-name">{uploadedFile.name}</span>
                <span className="file-size">({(uploadedFile.size / 1024).toFixed(1)} KB)</span>
              </div>
              <button 
                className="remove-file-btn" 
                onClick={removeFile}
                title="Remove file"
              >
                ×
              </button>
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
