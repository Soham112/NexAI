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

export interface CourseData {
  id: string
  title: string
  description: string
  duration: string
  level: string
  topics: string[]
  prerequisites?: string[]
}

export interface JobData {
  id: string
  title: string
  company: string
  location: string
  salary?: string
  requirements: string[]
  description: string
  postedDate: string
}

export interface ApiResponse<T> {
  data?: T
  error?: string
  timestamp: string
}
