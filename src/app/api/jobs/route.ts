import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    // Since we're using Lambda + Bedrock Agent for chat,
    // job data is now handled through the chat interface
    // This endpoint can return mock data or be removed entirely
    
    const jobs = [
      {
        id: '1',
        title: 'Senior AI Engineer',
        company: 'TechCorp',
        location: 'Remote',
        salary: '$120k - $150k',
        requirements: ['5+ years ML experience', 'Python', 'TensorFlow'],
        description: 'Lead AI initiatives and build ML models',
        postedDate: '2024-01-15'
      },
      {
        id: '2',
        title: 'Cloud Solutions Architect', 
        company: 'CloudTech',
        location: 'San Francisco, CA',
        salary: '$140k - $180k',
        requirements: ['AWS certification', '7+ years experience'],
        description: 'Design and implement cloud solutions',
        postedDate: '2024-01-10'
      }
    ]
    
    return NextResponse.json({
      jobs,
      count: jobs.length,
      timestamp: new Date().toISOString(),
      note: 'Job data is now available through chat interface'
    })
  } catch (error) {
    console.error('Error fetching jobs:', error)
    return NextResponse.json(
      { error: 'Failed to fetch jobs' },
      { status: 500 }
    )
  }
}
