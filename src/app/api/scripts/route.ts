import { NextRequest, NextResponse } from 'next/server'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

export async function POST(request: NextRequest) {
  try {
    const { scriptType, parameters } = await request.json()

    let scriptPath: string
    let command: string

    switch (scriptType) {
      case 'course-catalog':
        scriptPath = './Code/Course_Catalog_Agent/catalog_functions.py'
        command = `python ${scriptPath} ${parameters?.join(' ') || ''}`
        break
      
      case 'job-scraper':
        scriptPath = './Code/Job_market_agent/job_scrape_with_salary.py'
        command = `python ${scriptPath} ${parameters?.join(' ') || ''}`
        break
      
      case 'utd-trends':
        scriptPath = './Code/Course_Catalog_Agent/utdTrends_scrape.py'
        command = `python ${scriptPath} ${parameters?.join(' ') || ''}`
        break
      
      default:
        return NextResponse.json(
          { error: 'Invalid script type' },
          { status: 400 }
        )
    }

    try {
      const { stdout, stderr } = await execAsync(command, {
        cwd: process.cwd(),
        timeout: 300000 // 5 minutes timeout
      })

      return NextResponse.json({
        success: true,
        output: stdout,
        error: stderr,
        scriptType,
        timestamp: new Date().toISOString()
      })
    } catch (execError: any) {
      return NextResponse.json({
        success: false,
        error: execError.message,
        scriptType,
        timestamp: new Date().toISOString()
      })
    }
  } catch (error) {
    console.error('Script execution error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
