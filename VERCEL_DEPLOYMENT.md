# Vercel Deployment Guide

## Prerequisites
- Vercel CLI installed: `npm install -g vercel`
- Your Lambda endpoint URL ready
- Git repository (optional but recommended)

## Step 1: Login to Vercel
```bash
vercel login
```

## Step 2: Deploy from your project directory
```bash
vercel
```

## Step 3: Set Environment Variables in Vercel Dashboard

After deployment, go to your Vercel dashboard and add these environment variables:

### Required Environment Variables:
```
LAMBDA_FUNCTION_URL=https://0il1g2841g.execute-api.us-east-1.amazonaws.com/default/bedrock-ui-invoke
LAMBDA_API_KEY=your-api-key-if-required
```

### Optional (only if using file uploads):
```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=your-s3-bucket-name
```

## Step 4: Redeploy after setting environment variables
```bash
vercel --prod
```

## Alternative: Deploy via Vercel Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your Git repository
4. Set environment variables in project settings
5. Deploy

## Environment Variables Setup in Vercel Dashboard:

1. Go to your project in Vercel dashboard
2. Click on "Settings" tab
3. Click on "Environment Variables"
4. Add each variable:
   - Name: `LAMBDA_FUNCTION_URL`
   - Value: `https://0il1g2841g.execute-api.us-east-1.amazonaws.com/default/bedrock-ui-invoke`
   - Environment: Production, Preview, Development
5. Click "Save"

## Testing Your Deployment

After deployment, test your chat interface:
1. Visit your Vercel URL
2. Send a test message
3. Verify it connects to your Lambda function
4. Check browser console for any errors

## Troubleshooting

- **Environment variables not working**: Make sure to redeploy after adding them
- **Lambda timeout**: Check your Lambda function logs
- **CORS issues**: Verify your Lambda function allows requests from your Vercel domain
