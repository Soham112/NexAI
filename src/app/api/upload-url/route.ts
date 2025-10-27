import { NextRequest, NextResponse } from 'next/server'
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'

const s3Client = new S3Client({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || '',
  },
})

export async function POST(request: NextRequest) {
  try {
    const { fileName, fileType, conversationId } = await request.json()

    // Debug logging
    console.log('Upload URL request:', { fileName, fileType, conversationId })
    console.log('S3 Bucket:', process.env.S3_BUCKET_NAME)
    console.log('AWS Region:', process.env.AWS_REGION)

    // Validate input
    if (!fileName || !fileType || !conversationId) {
      return NextResponse.json(
        { error: 'fileName, fileType, and conversationId are required' },
        { status: 400 }
      )
    }

    // Validate file type
    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
    if (!allowedTypes.includes(fileType)) {
      return NextResponse.json(
        { error: 'Invalid file type. Only PDF, Word documents, and text files are allowed.' },
        { status: 400 }
      )
    }

    // Generate unique S3 key
    const timestamp = Date.now()
    const fileExtension = fileName.split('.').pop()
    const s3Key = `resumes/${conversationId}/${timestamp}.${fileExtension}`

    // Create presigned URL for PUT operation
    const command = new PutObjectCommand({
      Bucket: process.env.S3_BUCKET_NAME,
      Key: s3Key,
      ContentType: fileType,
    })

    const presignedUrl = await getSignedUrl(s3Client, command, { 
      expiresIn: 300, // 5 minutes
    })

    return NextResponse.json({
      success: true,
      presignedUrl,
      s3Key,
      expiresIn: 300,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error generating presigned URL:', error)
    return NextResponse.json(
      { error: 'Failed to generate upload URL' },
      { status: 500 }
    )
  }
}
