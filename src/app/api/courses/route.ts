import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    // Since we're using Lambda + Bedrock Agent for chat,
    // course data is now handled through the chat interface
    // This endpoint can return mock data or be removed entirely
    
    const courses = [
      {
        id: '1',
        title: 'AI & Machine Learning Fundamentals',
        description: 'Learn the basics of AI and ML',
        duration: '8 weeks',
        level: 'Beginner',
        topics: ['Python', 'TensorFlow', 'Neural Networks']
      },
      {
        id: '2', 
        title: 'Cloud Computing with AWS',
        description: 'Master cloud technologies',
        duration: '12 weeks',
        level: 'Intermediate',
        topics: ['EC2', 'S3', 'Lambda', 'API Gateway']
      }
    ]
    
    return NextResponse.json({
      courses,
      count: courses.length,
      timestamp: new Date().toISOString(),
      note: 'Course data is now available through chat interface'
    })
  } catch (error) {
    console.error('Error fetching courses:', error)
    return NextResponse.json(
      { error: 'Failed to fetch courses' },
      { status: 500 }
    )
  }
}
