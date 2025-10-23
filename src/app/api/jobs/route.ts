import { NextRequest, NextResponse } from 'next/server'
import { getJobData } from '../../../lib/s3'

export async function GET(request: NextRequest) {
  try {
    const jobs = await getJobData()
    
    return NextResponse.json({
      jobs,
      count: jobs.length,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error fetching jobs:', error)
    return NextResponse.json(
      { error: 'Failed to fetch jobs' },
      { status: 500 }
    )
  }
}
