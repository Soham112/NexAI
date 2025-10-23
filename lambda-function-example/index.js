const { BedrockAgentRuntimeClient, InvokeAgentCommand } = require('@aws-sdk/client-bedrock-agent-runtime');

// Initialize Bedrock Agent Runtime client
const bedrockAgentClient = new BedrockAgentRuntimeClient({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

exports.handler = async (event) => {
  console.log('Received event:', JSON.stringify(event, null, 2));
  
  try {
    // Parse the request body
    const body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;
    const { message, conversationId, settings } = body;
    
    if (!message) {
      return {
        statusCode: 400,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
        body: JSON.stringify({
          error: 'Message is required'
        })
      };
    }
    
    // Prepare the Bedrock Agent invocation
    const agentCommand = new InvokeAgentCommand({
      agentId: process.env.BEDROCK_AGENT_ID,
      agentAliasId: process.env.BEDROCK_AGENT_ALIAS_ID || 'TSTALIASID',
      sessionId: conversationId || `session_${Date.now()}`,
      inputText: message,
      sessionState: {
        sessionAttributes: {
          temperature: settings?.temperature || 0.7,
          maxTokens: settings?.maxTokens || 1000
        }
      }
    });
    
    // Invoke the Bedrock Agent
    const agentResponse = await bedrockAgentClient.send(agentCommand);
    
    // Process the streaming response
    let fullResponse = '';
    let sources = [];
    
    for await (const chunk of agentResponse.completion) {
      if (chunk.chunk?.bytes) {
        const chunkData = JSON.parse(new TextDecoder().decode(chunk.chunk.bytes));
        
        if (chunkData.type === 'text') {
          fullResponse += chunkData.text;
        } else if (chunkData.type === 'citations') {
          sources = chunkData.citations || [];
        }
      }
    }
    
    // Return the response
    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({
        response: fullResponse,
        metadata: {
          sources: sources,
          conversationId: conversationId,
          timestamp: new Date().toISOString()
        }
      })
    };
    
  } catch (error) {
    console.error('Lambda function error:', error);
    
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({
        error: 'Internal server error',
        message: error.message
      })
    };
  }
};
