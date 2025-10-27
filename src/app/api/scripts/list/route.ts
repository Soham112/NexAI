import { NextRequest, NextResponse } from 'next/server'
import { readFile, readdir, stat } from 'fs/promises'
import path from 'path'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const scriptType = searchParams.get('type') || 'all'

    const scriptsDir = './Code'
    const results: any = {}

    // Course Catalog Agent scripts
    if (scriptType === 'all' || scriptType === 'course-catalog') {
      try {
        const courseCatalogDir = path.join(scriptsDir, 'Course_Catalog_Agent')
        const files = await readdir(courseCatalogDir)
        
        results.courseCatalog = files.filter(file => file.endsWith('.py')).map(file => ({
          name: file,
          path: path.join(courseCatalogDir, file),
          type: 'python'
        }))
      } catch (error) {
        console.error('Error reading course catalog scripts:', error)
        results.courseCatalogError = 'Failed to read course catalog scripts'
      }
    }

    // Job Market Agent scripts
    if (scriptType === 'all' || scriptType === 'job-market') {
      try {
        const jobMarketDir = path.join(scriptsDir, 'Job_market_agent')
        const files = await readdir(jobMarketDir)
        
        results.jobMarket = files.filter(file => file.endsWith('.py')).map(file => ({
          name: file,
          path: path.join(jobMarketDir, file),
          type: 'python'
        }))
      } catch (error) {
        console.error('Error reading job market scripts:', error)
        results.jobMarketError = 'Failed to read job market scripts'
      }
    }

    // Demo Agentcore Bedrock scripts
    if (scriptType === 'all' || scriptType === 'demo-bedrock') {
      try {
        const demoDir = path.join(scriptsDir, 'Demo_Agentcore_Bedrock')
        const files = await readdir(demoDir)
        
        results.demoBedrock = files.filter(file => file.endsWith('.py')).map(file => ({
          name: file,
          path: path.join(demoDir, file),
          type: 'python'
        }))
      } catch (error) {
        console.error('Error reading demo bedrock scripts:', error)
        results.demoBedrockError = 'Failed to read demo bedrock scripts'
      }
    }

    return NextResponse.json({
      scripts: results,
      scriptType,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error fetching scripts:', error)
    return NextResponse.json(
      { error: 'Failed to fetch scripts' },
      { status: 500 }
    )
  }
}
