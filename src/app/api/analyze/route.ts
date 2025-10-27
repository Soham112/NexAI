import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { s3Key, userPrompt, conversationId } = await request.json()

    // Debug logging
    console.log('Analysis request:', { s3Key, userPrompt, conversationId })
    console.log('Analyze endpoint:', process.env.NEXT_PUBLIC_ANALYZE_ENDPOINT)
    console.log('All env vars starting with NEXT_PUBLIC:', Object.keys(process.env).filter(key => key.startsWith('NEXT_PUBLIC')))

    // Validate input
    if (!s3Key || !userPrompt || !conversationId) {
      return NextResponse.json(
        { error: 's3Key, userPrompt, and conversationId are required' },
        { status: 400 }
      )
    }

    // Check if analyze endpoint is configured
    if (!process.env.NEXT_PUBLIC_ANALYZE_ENDPOINT) {
      console.log('Analysis endpoint not configured, returning mock response')
      return NextResponse.json({
        success: true,
        analysis: {
          insights: `✅ Resume uploaded successfully to S3: ${s3Key}\n\n🔍 Analysis Features Available:\n• Recommended roles based on experience\n• Relevant courses to enhance skills\n• Missing skills identification\n• Project ideas for portfolio\n\n💡 Note: Configure NEXT_PUBLIC_ANALYZE_ENDPOINT to enable AI-powered analysis.`,
          recommendedRoles: ["Software Engineer", "Data Analyst", "Product Manager"],
          missingSkills: ["Cloud Computing", "Machine Learning", "Project Management"],
          projectIdeas: ["Build a web application", "Create a data visualization dashboard", "Develop a mobile app"],
          relevantCourses: ["AWS Cloud Practitioner", "Python for Data Science", "Agile Project Management"]
        },
        s3Key,
        timestamp: new Date().toISOString()
      })
    }

    // Call the Lambda function for analysis
    try {
      const requestBody = {
        s3Key,
        userPrompt: userPrompt.trim(),
        conversationId,
        timestamp: new Date().toISOString()
      }
      
      console.log('Calling Lambda function with:', requestBody)
      console.log('Lambda endpoint:', process.env.NEXT_PUBLIC_ANALYZE_ENDPOINT)
      
      const response = await fetch(process.env.NEXT_PUBLIC_ANALYZE_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      })

      console.log('Lambda response status:', response.status)
      console.log('Lambda response headers:', Object.fromEntries(response.headers.entries()))

      if (!response.ok) {
        const errorText = await response.text()
        console.error(`Lambda function error: ${response.status}`, errorText)
        throw new Error(`Lambda function error: ${response.status} - ${errorText}`)
      }

      const analysisResult = await response.json()
      console.log('Lambda function response:', analysisResult)

      // Parse the outputText from Lambda function
      let parsedAnalysis
      try {
        parsedAnalysis = JSON.parse(analysisResult.outputText)
      } catch (parseError) {
        console.error('Error parsing Lambda response:', parseError)
        // Fallback to using the raw outputText
        parsedAnalysis = {
          insights: analysisResult.outputText,
          recommendedRoles: [],
          missingSkills: [],
          projectIdeas: [],
          relevantCourses: []
        }
      }

      // Map the Lambda response to our expected format
      const formattedAnalysis = {
        insights: `✅ Resume analyzed successfully!\n\nYour resume has been processed and analyzed for career insights.`,
        recommendedRoles: parsedAnalysis.roles || [],
        missingSkills: parsedAnalysis.missing_skills || [],
        projectIdeas: parsedAnalysis.projects ? parsedAnalysis.projects.map((p: any) => `${p.title}: ${p.description}`) : [],
        relevantCourses: parsedAnalysis.courses || []
      }

      console.log('Formatted analysis:', formattedAnalysis)

      return NextResponse.json({
        success: true,
        analysis: formattedAnalysis,
        s3Key,
        timestamp: new Date().toISOString()
      })
    } catch (fetchError) {
      console.error('Lambda function fetch error:', fetchError)
      console.error('Error details:', {
        message: fetchError instanceof Error ? fetchError.message : 'Unknown error',
        name: fetchError instanceof Error ? fetchError.name : 'Unknown',
        stack: fetchError instanceof Error ? fetchError.stack : undefined
      })
      // Return fallback response if external endpoint fails
      return NextResponse.json({
        success: true,
        analysis: {
          insights: `✅ Resume uploaded successfully to S3: ${s3Key}\n\n🔍 Analysis Features Available:\n• Recommended roles based on experience\n• Relevant courses to enhance skills\n• Missing skills identification\n• Project ideas for portfolio\n\n⚠️ Note: External analysis endpoint is not available. Configure NEXT_PUBLIC_ANALYZE_ENDPOINT for AI-powered analysis.`,
          recommendedRoles: ["Software Engineer", "Data Analyst", "Product Manager"],
          missingSkills: ["Cloud Computing", "Machine Learning", "Project Management"],
          projectIdeas: ["Build a web application", "Create a data visualization dashboard", "Develop a mobile app"],
          relevantCourses: ["AWS Cloud Practitioner", "Python for Data Science", "Agile Project Management"]
        },
        s3Key,
        timestamp: new Date().toISOString(),
        warning: 'External analysis endpoint not available'
      })
    }
  } catch (error) {
    console.error('Error analyzing resume:', error)
    return NextResponse.json(
      { 
        error: 'Failed to analyze resume',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}
