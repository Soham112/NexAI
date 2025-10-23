# Lambda Function Deployment Guide

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Node.js installed
3. Bedrock Agent already created and configured
4. Database connected to Bedrock Agent knowledge base

## Deployment Steps

### 1. Prepare the Lambda Function

```bash
cd lambda-function-example
npm install
```

### 2. Create the Lambda Function

```bash
# Create the function
aws lambda create-function \
  --function-name nexai-bedrock-agent \
  --runtime nodejs18.x \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-bedrock-role \
  --handler index.handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 512
```

### 3. Set Environment Variables

```bash
aws lambda update-function-configuration \
  --function-name nexai-bedrock-agent \
  --environment Variables='{
    "AWS_REGION":"us-east-1",
    "BEDROCK_AGENT_ID":"your-agent-id",
    "BEDROCK_AGENT_ALIAS_ID":"TSTALIASID"
  }'
```

### 4. Create Function URL (for direct HTTP access)

```bash
aws lambda create-function-url-config \
  --function-name nexai-bedrock-agent \
  --auth-type NONE \
  --cors '{
    "AllowCredentials": false,
    "AllowHeaders": ["content-type"],
    "AllowMethods": ["POST"],
    "AllowOrigins": ["*"],
    "ExposeHeaders": [],
    "MaxAge": 86400
  }'
```

### 5. Update Frontend Environment

Add the Lambda function URL to your `.env.local`:

```bash
LAMBDA_FUNCTION_URL=https://your-lambda-url.lambda-url.us-east-1.on.aws/
```

## IAM Permissions Required

The Lambda execution role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:GetAgent",
        "bedrock:GetAgentAlias"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Testing

Test the Lambda function:

```bash
curl -X POST https://your-lambda-url.lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What courses are available?",
    "conversationId": "test_session",
    "settings": {
      "temperature": 0.7,
      "maxTokens": 1000
    }
  }'
```

## Monitoring

Monitor your Lambda function in the AWS Console:
- CloudWatch Logs for debugging
- Lambda metrics for performance
- X-Ray for tracing (if enabled)
