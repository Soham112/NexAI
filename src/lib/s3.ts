import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3'

const s3Client = new S3Client({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY ? {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  } : undefined,
})

export interface CourseData {
  id: string
  title: string
  description: string
  duration: string
  level: string
  topics: string[]
  prerequisites?: string[]
}

export interface JobData {
  id: string
  title: string
  company: string
  location: string
  salary?: string
  requirements: string[]
  description: string
  postedDate: string
}

export async function getCourseData(): Promise<CourseData[]> {
  try {
    // Check if S3 is configured
    if (!process.env.S3_BUCKET_NAME) {
      console.log('S3_BUCKET_NAME not configured, returning empty course data')
      return []
    }

    const command = new GetObjectCommand({
      Bucket: process.env.S3_BUCKET_NAME,
      Key: 'data/clean/catalog/courses.json'
    })
    
    const response = await s3Client.send(command)
    const data = await response.Body?.transformToString()
    
    if (data) {
      return JSON.parse(data)
    }
    
    return []
  } catch (error) {
    console.error('Error fetching course data from S3:', error)
    return []
  }
}

export async function getJobData(): Promise<JobData[]> {
  try {
    // Check if S3 is configured
    if (!process.env.S3_BUCKET_NAME) {
      console.log('S3_BUCKET_NAME not configured, returning empty job data')
      return []
    }

    const command = new GetObjectCommand({
      Bucket: process.env.S3_BUCKET_NAME,
      Key: 'data/clean/jobs/jobs.json'
    })
    
    const response = await s3Client.send(command)
    const data = await response.Body?.transformToString()
    
    if (data) {
      return JSON.parse(data)
    }
    
    return []
  } catch (error) {
    console.error('Error fetching job data from S3:', error)
    return []
  }
}

export { s3Client }
