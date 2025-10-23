# NexAI Next.js Application - Deployment Guide

## 🚀 Deployment Options

### Option 1: Vercel (Recommended)

1. **Prepare Repository**
   ```bash
   git add .
   git commit -m "Initial Next.js app setup"
   git push origin main
   ```

2. **Deploy to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Add environment variables in dashboard
   - Deploy automatically

3. **Environment Variables in Vercel**
   ```
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
   S3_BUCKET_NAME=your_bucket
   ```

### Option 2: AWS Amplify

1. **Connect Repository**
   - Go to AWS Amplify console
   - Connect GitHub repository
   - Select branch (main)

2. **Build Settings**
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: .next
       files:
         - '**/*'
     cache:
       paths:
         - node_modules/**/*
         - .next/cache/**/*
   ```

3. **Environment Variables**
   - Add in Amplify console under Environment variables

### Option 3: Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   FROM node:18-alpine AS base
   
   # Install dependencies only when needed
   FROM base AS deps
   RUN apk add --no-cache libc6-compat
   WORKDIR /app
   
   COPY package.json package-lock.json* ./
   RUN npm ci
   
   # Rebuild the source code only when needed
   FROM base AS builder
   WORKDIR /app
   COPY --from=deps /app/node_modules ./node_modules
   COPY . .
   
   RUN npm run build
   
   # Production image, copy all the files and run next
   FROM base AS runner
   WORKDIR /app
   
   ENV NODE_ENV production
   
   RUN addgroup --system --gid 1001 nodejs
   RUN adduser --system --uid 1001 nextjs
   
   COPY --from=builder /app/public ./public
   
   # Set the correct permission for prerender cache
   RUN mkdir .next
   RUN chown nextjs:nodejs .next
   
   # Automatically leverage output traces to reduce image size
   COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
   COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
   
   USER nextjs
   
   EXPOSE 3000
   
   ENV PORT 3000
   
   CMD ["node", "server.js"]
   ```

2. **Build and Run**
   ```bash
   docker build -t nexai-app .
   docker run -p 3000:3000 --env-file .env.local nexai-app
   ```

## 🔧 Production Configuration

### Next.js Configuration
Update `next.config.js` for production:

```javascript
const nextConfig = {
  experimental: {
    appDir: true,
  },
  env: {
    AWS_REGION: process.env.AWS_REGION,
    AWS_ACCESS_KEY_ID: process.env.AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY: process.env.AWS_SECRET_ACCESS_KEY,
    BEDROCK_MODEL_ID: process.env.BEDROCK_MODEL_ID,
    S3_BUCKET_NAME: process.env.S3_BUCKET_NAME,
  },
  // Enable compression
  compress: true,
  // Optimize images
  images: {
    domains: ['your-domain.com'],
  },
  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ]
  },
}
```

### Environment Variables for Production

```env
# Required
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_production_key
AWS_SECRET_ACCESS_KEY=your_production_secret
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
S3_BUCKET_NAME=your_production_bucket

# Optional
NODE_ENV=production
NEXT_PUBLIC_APP_NAME=NextAI
NEXT_PUBLIC_APP_VERSION=1.0.0
```

## 🔒 Security Considerations

### AWS IAM Permissions
Create a dedicated IAM user with minimal permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*:*:model/anthropic.claude-3-sonnet-20240229-v1:0"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### Environment Security
- Never commit `.env.local` to version control
- Use environment variables for all secrets
- Rotate AWS credentials regularly
- Enable AWS CloudTrail for audit logging

## 📊 Monitoring & Analytics

### Vercel Analytics
```bash
npm install @vercel/analytics
```

Add to `src/app/layout.tsx`:
```tsx
import { Analytics } from '@vercel/analytics/react'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  )
}
```

### Error Monitoring
```bash
npm install @sentry/nextjs
```

### Performance Monitoring
- Use Vercel's built-in analytics
- Monitor Core Web Vitals
- Set up alerts for errors and performance issues

## 🔄 CI/CD Pipeline

### GitHub Actions Example
```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run build
      - uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
          scope: ${{ secrets.VERCEL_SCOPE }}
```

## 🚨 Troubleshooting Production Issues

### Common Production Issues

1. **Build Failures**
   - Check Node.js version compatibility
   - Verify all dependencies are installed
   - Review build logs for specific errors

2. **Runtime Errors**
   - Check environment variables
   - Verify AWS credentials
   - Review application logs

3. **Performance Issues**
   - Enable compression
   - Optimize images
   - Use CDN for static assets
   - Monitor bundle size

### Debugging Tools
- Vercel Function Logs
- AWS CloudWatch Logs
- Browser Developer Tools
- Next.js built-in error overlay

## 📈 Scaling Considerations

### Database Integration
- Consider adding a database for conversation history
- Use Redis for session management
- Implement proper data caching

### Load Balancing
- Use Vercel's automatic scaling
- Consider AWS Application Load Balancer for custom deployments
- Implement proper health checks

### Caching Strategy
- Implement Redis caching for API responses
- Use CDN for static assets
- Cache S3 data locally when appropriate

---

For more detailed information, see the main README-NextJS.md file.
