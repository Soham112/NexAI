# Lambda + Bedrock Agent Configuration

## Environment Variables Required

Create a `.env.local` file in your project root with the following variables:

```bash
# Lambda Function Configuration (REQUIRED)
LAMBDA_FUNCTION_URL=https://your-lambda-endpoint.amazonaws.com/your-function-name
LAMBDA_API_KEY=your-lambda-api-key-if-required

# AWS Configuration (for Lambda function to access Bedrock Agent)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# Bedrock Agent Configuration (used by Lambda function)
BEDROCK_AGENT_ID=your-bedrock-agent-id
BEDROCK_AGENT_ALIAS_ID=your-bedrock-agent-alias-id

# Database Configuration (used by Lambda function)
DATABASE_URL=your-database-connection-string
DATABASE_TYPE=postgresql|mysql|mongodb

# Optional: S3 Configuration for file uploads
S3_BUCKET_NAME=your-s3-bucket-name
S3_REGION=us-east-1
```

## Architecture Flow

1. **Frontend** → Sends user message to Next.js API route
2. **Next.js API** → Calls Lambda function with message
3. **Lambda Function** → Invokes Bedrock Agent
4. **Bedrock Agent** → Queries database using knowledge base
5. **Database** → Returns relevant data
6. **Bedrock Agent** → Generates contextual response
7. **Lambda** → Returns response to Next.js
8. **Next.js** → Returns response to frontend

## Lambda Function Expected Interface

The Lambda function should accept this payload:
```json
{
  "message": "user question",
  "conversationId": "session_1234567890",
  "settings": {
    "temperature": 0.7,
    "maxTokens": 1000
  }
}
```

And return this response:
```json
{
  "response": "AI generated response",
  "metadata": {
    "sources": ["database_table_1", "database_table_2"],
    "confidence": 0.95
  }
}
```

## Fallback Behavior

If the Lambda function is unavailable or the `LAMBDA_FUNCTION_URL` environment variable is not set, the system will fall back to mock responses to ensure the chat interface remains functional.

## Security Note

The Lambda endpoint URL is now stored securely in environment variables and is not hardcoded in the source code. This prevents accidental exposure of your API endpoints in version control.
