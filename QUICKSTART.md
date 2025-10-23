# NexAI Next.js Application - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
npm install
```

### 2. Environment Setup
Copy `env.example` to `.env.local` and fill in your AWS credentials:
```bash
cp env.example .env.local
```

### 3. Run Development Server
```bash
npm run dev
```

Visit `http://localhost:3000` to see your application!

## 🔧 Environment Variables Required

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
S3_BUCKET_NAME=your_bucket_name
```

## 📁 Key Files Created

- `src/app/page.tsx` - Main application page
- `src/components/` - All React components
- `src/app/api/` - API routes for chat, data, and scripts
- `src/lib/` - AWS Bedrock and S3 integration
- `package.json` - Dependencies and scripts

## 🔗 Integration Points

1. **AWS Bedrock**: AI chat responses via `/api/chat`
2. **S3 Bucket**: Course and job data via `/api/courses` and `/api/jobs`
3. **Existing Scripts**: Execute Python scripts via `/api/scripts`

## 🎯 Next Steps

1. Set up your AWS credentials
2. Configure your S3 bucket with data files
3. Test the chat functionality
4. Integrate with your existing Python scripts
5. Customize the UI to match your brand

## 📖 Full Documentation

See `README-NextJS.md` for complete documentation, deployment guides, and troubleshooting.
