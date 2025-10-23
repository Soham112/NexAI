import { NextRequest, NextResponse } from 'next/server'
import { bedrockClient, InvokeModelCommand } from '../../../lib/bedrock'
import { getMockResponse } from '../../../lib/mockResponses'

export async function POST(request: NextRequest) {
  try {
    const { message, conversationId, settings } = await request.json()

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      )
    }

    // Try to get response from Bedrock first
    try {
      const command = new InvokeModelCommand({
        modelId: process.env.BEDROCK_MODEL_ID || 'anthropic.claude-3-sonnet-20240229-v1:0',
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify({
          anthropic_version: 'bedrock-2023-05-31',
          max_tokens: 1000,
          temperature: settings?.temperature || 0.7,
          messages: [
            {
              role: 'user',
              content: message
            }
          ]
        })
      })

      const bedrockResponse = await bedrockClient.send(command)
      const responseBody = JSON.parse(new TextDecoder().decode(bedrockResponse.body))
      const aiResponse = responseBody.content[0].text

      return NextResponse.json({
        response: aiResponse,
        conversationId,
        timestamp: new Date().toISOString()
      })
    } catch (bedrockError) {
      console.log('Bedrock API not available, using mock response:', bedrockError)
      
      // Fall back to mock response
      const mockResponse = await getMockResponse(message)
      
      return NextResponse.json({
        response: mockResponse,
        conversationId,
        timestamp: new Date().toISOString(),
        source: 'mock'
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
