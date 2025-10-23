# NexAI Next.js Application

A modern, responsive Next.js application converted from the original HTML file, designed to integrate with AWS Bedrock agents and S3 bucket data for intelligent course catalog and job market assistance.

## 🚀 Features

- **Modern Gemini-style Chat Interface**: Clean, responsive design inspired by Google's Gemini
- **AWS Bedrock Integration**: AI-powered responses using Claude models
- **S3 Data Integration**: Real-time access to course catalog and job market data
- **Script Integration**: Seamless integration with existing Python scripts
- **Real-time Chat**: Interactive conversation with typing indicators
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
- **TypeScript Support**: Full type safety and better development experience

## 📁 Project Structure

```
NexAI/
├── src/
│   ├── app/                    # Next.js app directory
│   │   ├── api/               # API routes
│   │   │   ├── chat/         # Chat API endpoint
│   │   │   ├── courses/      # Course data API
│   │   │   ├── jobs/        # Job data API
│   │   │   ├── scripts/     # Script execution API
│   │   │   ├── data/       # Local data access API
│   │   │   └── upload/    # S3 upload API
│   │   ├── globals.css     # Global styles
│   │   ├── layout.tsx     # Root layout
│   │   └── page.tsx      # Home page
│   ├── components/         # React components
│   │   ├── ChatContext.tsx
│   │   ├── ChatInterface.tsx
│   │   ├── ChatMessages.tsx
│   │   ├── Layout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── TopNavigation.tsx
│   │   ├── TypingIndicator.tsx
│   │   └── WelcomeSection.tsx
│   ├── lib/              # Utility libraries
│   │   ├── bedrock.ts   # AWS Bedrock client
│   │   ├── s3.ts       # S3 client and data access
│   │   └── mockResponses.ts
│   └── types/           # TypeScript type definitions
│       └── index.ts
├── Code/               # Existing Python scripts
├── package.json
├── next.config.js
├── tsconfig.json
└── README-NextJS.md
```

## 🛠️ Installation & Setup

### Prerequisites

- Node.js 18+ 
- npm or yarn
- AWS Account with Bedrock and S3 access
- Python 3.8+ (for existing scripts)

### 1. Install Dependencies

```bash
npm install
```

### 2. Environment Configuration

Create a `.env.local` file in the root directory:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# S3 Configuration
S3_BUCKET_NAME=your_s3_bucket_name_here

# Optional: Custom configurations
NEXT_PUBLIC_APP_NAME=NextAI
NEXT_PUBLIC_APP_VERSION=1.0.0
```

### 3. AWS Setup

#### Bedrock Access
1. Enable Claude models in AWS Bedrock console
2. Ensure your AWS credentials have `bedrock:InvokeModel` permissions

#### S3 Setup
1. Create an S3 bucket for data storage
2. Ensure your AWS credentials have S3 read/write permissions
3. Upload your data files to the bucket:
   ```
   your-bucket/
   ├── data/
   │   └── clean/
   │       ├── catalog/
   │       │   ├── courses.json
   │       │   └── courses.jsonl
   │       ├── coursebook/
   │       │   └── sections.jsonl
   │       └── utdtrends/
   │           └── trends.jsonl
   ```

### 4. Run the Application

```bash
# Development mode
npm run dev

# Production build
npm run build
npm start
```

The application will be available at `http://localhost:3000`

## 🔧 API Endpoints

### Chat API
- **POST** `/api/chat` - Send messages to AI assistant
- **Body**: `{ message: string, conversationId?: string, settings?: object }`

### Data APIs
- **GET** `/api/courses` - Fetch course catalog data
- **GET** `/api/jobs` - Fetch job market data
- **GET** `/api/data?type=catalog|coursebook|trends|all` - Fetch local data files

### Script Integration APIs
- **POST** `/api/scripts` - Execute Python scripts
- **GET** `/api/scripts/list` - List available scripts
- **POST** `/api/upload` - Upload data to S3

## 🔗 Integration with Existing Scripts

The application seamlessly integrates with your existing Python scripts:

### Course Catalog Agent
```typescript
// Execute course catalog script
const response = await fetch('/api/scripts', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    scriptType: 'course-catalog',
    parameters: ['--update', '--format', 'json']
  })
})
```

### Job Market Agent
```typescript
// Execute job scraping script
const response = await fetch('/api/scripts', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    scriptType: 'job-scraper',
    parameters: ['--location', 'remote', '--salary', '100000']
  })
})
```

### UTD Trends Scraper
```typescript
// Execute trends scraping script
const response = await fetch('/api/scripts', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    scriptType: 'utd-trends',
    parameters: ['--date', '2024-01-01']
  })
})
```

## 🎨 Customization

### Styling
The application uses CSS modules with global styles. Key customization points:

- **Colors**: Modify CSS variables in `globals.css`
- **Layout**: Adjust component styles in individual CSS files
- **Responsive**: Breakpoints defined in `globals.css`

### Components
All components are modular and can be easily customized:

- **ChatInterface**: Main chat functionality
- **WelcomeSection**: Landing page with action buttons
- **TopNavigation**: Header with branding and user controls
- **Sidebar**: Navigation sidebar

## 🚀 Deployment

### Vercel (Recommended)
1. Push code to GitHub
2. Connect repository to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy automatically

### AWS Amplify
1. Connect GitHub repository
2. Configure build settings
3. Add environment variables
4. Deploy

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🔍 Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Verify AWS credentials in `.env.local`
   - Check IAM permissions for Bedrock and S3

2. **Script Execution Fails**
   - Ensure Python scripts are executable
   - Check file paths and dependencies

3. **S3 Access Denied**
   - Verify bucket permissions
   - Check bucket name in environment variables

4. **Bedrock Model Not Available**
   - Enable Claude models in AWS Bedrock console
   - Verify model ID in environment variables

### Debug Mode
Enable debug logging by setting:
```env
NODE_ENV=development
DEBUG=true
```

## 📈 Performance Optimization

- **Image Optimization**: Next.js automatic image optimization
- **Code Splitting**: Automatic code splitting by Next.js
- **Caching**: API responses cached with appropriate headers
- **Bundle Analysis**: Run `npm run build` to analyze bundle size

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review AWS documentation for Bedrock and S3

---

**NextAI** - Your intelligent assistant for courses, jobs, and learning resources.