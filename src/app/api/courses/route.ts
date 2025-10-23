import { NextRequest, NextResponse } from 'next/server'
import { getCourseData } from '../../../lib/s3'

export async function GET(request: NextRequest) {
  try {
    const courses = await getCourseData()
    
    return NextResponse.json({
      courses,
      count: courses.length,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error fetching courses:', error)
    return NextResponse.json(
      { error: 'Failed to fetch courses' },
      { status: 500 }
    )
  }
}
