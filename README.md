# NexAI - Intelligent Assistant

A modern Next.js application with AI-powered chat interface, designed to integrate with AWS Lambda agents and S3 bucket data for intelligent course catalog and job market assistance.

![NextAI Interface](https://img.shields.io/badge/Next.js-14.0.4-black?style=for-the-badge&logo=next.js)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3.3-blue?style=for-the-badge&logo=typescript)
![AWS](https://img.shields.io/badge/AWS-Lambda%20%7C%20S3-orange?style=for-the-badge&logo=amazon-aws)

## 🚀 Features

- **Modern Chat Interface**: Clean, responsive design with real-time messaging
- **AWS Lambda Integration**: AI-powered responses using Bedrock agents via Lambda functions
- **Resume Upload**: Upload and store resumes directly to S3 bucket with file validation
- **S3 Data Integration**: Real-time access to course catalog and job market data
- **Script Integration**: Seamless integration with existing Python scripts
- **Real-time Chat**: Interactive conversation with typing indicators
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
- **TypeScript Support**: Full type safety and better development experience
- **File Management**: Support for PDF, Word documents, and text files
- **Error Handling**: Comprehensive error handling and user feedback

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** 18.0 or higher ([Download](https://nodejs.org/))
- **npm** or **yarn** package manager
- **AWS Account** with Lambda, Bedrock, and S3 access
- **Python** 3.8+ (for existing scripts integration)

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd NexAI
git checkout main
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Environment Configuration

Create a `.env.local` file in the root directory:

```bash
cp env.example .env.local
```

Fill in your environment variables:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here

# Lambda Configuration
LAMBDA_FUNCTION_URL=your_lambda_function_url_here
LAMBDA_API_KEY=your_lambda_api_key_here
LAMBDA_TIMEOUT_MS=55000

# S3 Configuration
S3_BUCKET_NAME=your_s3_bucket_name_here

# Resume Upload & Analysis Endpoints
NEXT_PUBLIC_UPLOAD_URL_ENDPOINT=/api/upload-url
NEXT_PUBLIC_ANALYZE_ENDPOINT=your_lambda_function_url_here

# Optional: Custom configurations
NEXT_PUBLIC_APP_NAME=NexAI
NEXT_PUBLIC_APP_VERSION=1.0.0
```

### 4. AWS Setup

#### Lambda Function Setup
1. Deploy your Bedrock agent as a Lambda function
2. Configure Lambda function URL for HTTP access
3. Ensure your AWS credentials have Lambda invoke permissions

#### S3 Setup
1. Create an S3 bucket for data storage and resume uploads
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
   ├── resumes/
   │   └── session_*/
   │       └── *.pdf
   ```

### 5. Run the Application

#### Development Mode
```bash
npm run dev
```

#### Production Build
```bash
npm run build
npm start
```

The application will be available at `http://localhost:3000`

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
└── README.md
```

## 🔧 API Endpoints

### Chat API
- **POST** `/api/chat` - Send messages to AI assistant
- **Body**: `{ message: string, conversationId?: string, settings?: object }`

### Data APIs
- **GET** `/api/courses` - Fetch course catalog data from S3
- **GET** `/api/jobs` - Fetch job market data from S3
- **GET** `/api/data?type=catalog|coursebook|trends|all` - Fetch local data files

### Script Integration APIs
- **POST** `/api/scripts` - Execute Python scripts
- **GET** `/api/scripts/list` - List available scripts
- **POST** `/api/upload` - Upload files (including resumes) to S3 (legacy)
- **POST** `/api/upload-url` - Generate presigned S3 URL for secure uploads
- **POST** `/api/upload-proxy` - Server-side file upload to S3 (current method)
- **POST** `/api/analyze` - Analyze uploaded resume using Lambda function

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

## 📄 Resume Upload & Analysis Feature

The application includes a secure resume upload and analysis feature that provides personalized career insights:

### Supported File Types
- **PDF** (.pdf)
- **Word Documents** (.doc, .docx)
- **Text Files** (.txt)

### File Validation
- **Maximum Size**: 10MB
- **File Type Validation**: Only allowed file types are accepted
- **Error Handling**: Clear error messages for invalid files

### Upload & Analysis Process
1. **Step 1**: User clicks "Resume" button in chat interface
2. **Step 2**: File picker opens with supported file types
3. **Step 3**: File is validated for type and size
4. **Step 4**: File is uploaded to S3 via server-side proxy
5. **Step 5**: System calls Lambda function to analyze the resume
6. **Step 6**: Lambda function processes resume with Bedrock Agent
7. **Step 7**: AI analysis returns structured career insights

### Analysis Features
The Lambda function with Bedrock Agent analyzes resumes and provides:
- **Recommended Roles**: Suitable job positions based on experience
- **Relevant Courses**: Educational opportunities to enhance skills
- **Missing Skills**: Skills gaps and improvement areas
- **Project Ideas**: Portfolio projects to strengthen profile
- **Structured Output**: JSON-formatted insights for easy parsing

### S3 Organization
Resumes are organized in S3 with the following structure:
```
resumes/
└── session_{conversationId}/
    └── {timestamp}.{extension}
```

Example: `resumes/session_1761254058565/1761254101924.pdf`

### Current Implementation
The system uses a **server-side proxy upload** approach:
- Files are uploaded through `/api/upload-proxy` endpoint
- Server handles S3 upload using AWS credentials
- Lambda function receives S3 key for analysis
- No CORS issues or client-side credential exposure
- Clean, minimal UI without file display clutter

### Security Benefits
- **Server-Side Upload**: Files uploaded through secure server-side proxy
- **AWS Credentials Protection**: Credentials only used server-side
- **Lambda Function Security**: Analysis performed in secure AWS environment
- **File Validation**: Comprehensive validation before upload
- **Error Handling**: Graceful fallback for failed analysis

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

## 🔍 Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Verify AWS credentials in `.env.local`
   - Check IAM permissions for Lambda, Bedrock, and S3

2. **Lambda Function Timeout**
   - Check Lambda function timeout settings
   - Verify LAMBDA_TIMEOUT_MS environment variable
   - Ensure Lambda function URL is accessible

3. **Script Execution Fails**
   - Ensure Python scripts are executable
   - Check file paths and dependencies

4. **S3 Access Denied**
   - Verify bucket permissions
   - Check bucket name in environment variables
   - Ensure S3 bucket exists and is accessible

5. **Resume Upload Fails**
   - Check S3 bucket permissions for PutObject
   - Verify file size limits (max 10MB)
   - Check supported file types (PDF, DOC, DOCX, TXT)
   - Ensure server-side proxy has proper AWS credentials

6. **Lambda Function Analysis Fails**
   - Verify Lambda function URL is correct
   - Check Lambda function logs in AWS CloudWatch
   - Ensure Lambda function has S3 read permissions
   - Verify Bedrock Agent is properly configured

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
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review AWS documentation for Bedrock and S3

## 🙏 Acknowledgments

- Built with Next.js and React
- Powered by AWS Lambda, Bedrock, and S3 services
- Modern chat interface design

---

**NexAI** - Your intelligent assistant for courses, jobs, and learning resources.

Made with using Next.js, TypeScript, and AWS services.