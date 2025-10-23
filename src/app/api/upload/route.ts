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

    const command = new PutObjectCommand({
      Bucket: process.env.S3_BUCKET_NAME,
      Key: key,
      Body: typeof data === 'string' ? data : JSON.stringify(data),
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
