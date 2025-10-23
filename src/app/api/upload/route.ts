import { NextRequest, NextResponse } from 'next/server'
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'

const s3Client = new S3Client({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || '',
  },
})

export async function POST(request: NextRequest) {
  try {
    const { data, key, contentType = 'application/json' } = await request.json()

    if (!data || !key) {
      return NextResponse.json(
        { error: 'Data and key are required' },
        { status: 400 }
      )
    }

    // Handle base64 data (for file uploads)
    let body: string | Buffer
    if (typeof data === 'string' && data.startsWith('data:')) {
      // Handle data URL format
      const base64Data = data.split(',')[1]
      body = Buffer.from(base64Data, 'base64')
    } else if (typeof data === 'string') {
      // Handle plain base64 string
      body = Buffer.from(data, 'base64')
    } else {
      // Handle JSON data
      body = JSON.stringify(data)
    }

    const command = new PutObjectCommand({
      Bucket: process.env.S3_BUCKET_NAME,
      Key: key,
      Body: body,
      ContentType: contentType,
    })

    await s3Client.send(command)

    return NextResponse.json({
      success: true,
      key,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error uploading to S3:', error)
    return NextResponse.json(
      { error: 'Failed to upload to S3' },
      { status: 500 }
    )
  }
}
