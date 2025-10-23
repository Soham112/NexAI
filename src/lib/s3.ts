import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3'

const s3Client = new S3Client({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || '',
  },
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
