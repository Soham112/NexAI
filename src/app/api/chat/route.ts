import { NextRequest, NextResponse } from 'next/server'
import { getMockResponse } from '../../../lib/mockResponses'

export async function POST(request: NextRequest) {
  try {
    const { message, conversationId, settings } = await request.json()

    // Input validation
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      return NextResponse.json(
        { error: 'Message is required and must be a non-empty string' },
        { status: 400 }
      )
    }

    if (message.length > 10000) {
      return NextResponse.json(
        { error: 'Message is too long (max 10,000 characters)' },
        { status: 400 }
      )
    }

    // Try to get response from Lambda function first
    try {
      if (!process.env.LAMBDA_FUNCTION_URL) {
        throw new Error('LAMBDA_FUNCTION_URL environment variable is not set')
      }
      
      // Add timeout to prevent hanging requests
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 seconds timeout
      
      const lambdaResponse = await fetch(process.env.LAMBDA_FUNCTION_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.LAMBDA_API_KEY || ''}`,
        },
        body: JSON.stringify({
          inputText: message.trim(),
          conversationId: conversationId || `session_${Date.now()}`,
          settings: {
            temperature: Math.max(0, Math.min(1, settings?.temperature || 0.7)),
            maxTokens: Math.max(1, Math.min(4000, settings?.maxTokens || 1000))
          }
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!lambdaResponse.ok) {
        throw new Error(`Lambda function error: ${lambdaResponse.status}`)
      }

      const lambdaData = await lambdaResponse.json()
      
      return NextResponse.json({
        response: lambdaData.outputText || lambdaData.response || lambdaData.message,
        conversationId,
        timestamp: new Date().toISOString(),
        source: 'lambda-bedrock-agent',
        metadata: lambdaData.metadata || null
      })
    } catch (lambdaError) {
      console.log('Lambda function not available, using mock response:', lambdaError)
      
      // Check if it's a timeout error
      const isTimeout = lambdaError instanceof Error && lambdaError.name === 'AbortError'
      if (isTimeout) {
        console.log('Lambda function timed out after 30 seconds')
      }
      
      // Fall back to mock response
      const mockResponse = await getMockResponse(message)
      
      return NextResponse.json({
        response: mockResponse,
        conversationId: conversationId || `session_${Date.now()}`,
        timestamp: new Date().toISOString(),
        source: 'mock',
        error: isTimeout ? 'Lambda timeout' : 'Lambda error'
      })
    }
  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
