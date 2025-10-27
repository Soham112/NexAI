import { NextRequest, NextResponse } from 'next/server'
import { readFile, readdir } from 'fs/promises'
import path from 'path'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const dataType = searchParams.get('type') || 'all'

    const dataDir = './Code/Course_Catalog_Agent/data/clean'
    const results: any = {}

    if (dataType === 'all' || dataType === 'catalog') {
      try {
        const catalogDir = path.join(dataDir, 'catalog')
        const files = await readdir(catalogDir)
        
        for (const file of files) {
          if (file.endsWith('.json') || file.endsWith('.jsonl')) {
            const filePath = path.join(catalogDir, file)
            const content = await readFile(filePath, 'utf-8')
            
            if (file.endsWith('.jsonl')) {
              results[file] = content.split('\n').filter(line => line.trim()).map(line => JSON.parse(line))
            } else {
              results[file] = JSON.parse(content)
            }
          }
        }
      } catch (error) {
        console.error('Error reading catalog data:', error)
        results.catalogError = 'Failed to read catalog data'
      }
    }

    if (dataType === 'all' || dataType === 'coursebook') {
      try {
        const coursebookDir = path.join(dataDir, 'coursebook')
        const files = await readdir(coursebookDir)
        
        for (const file of files) {
          if (file.endsWith('.json') || file.endsWith('.jsonl')) {
            const filePath = path.join(coursebookDir, file)
            const content = await readFile(filePath, 'utf-8')
            
            if (file.endsWith('.jsonl')) {
              results[file] = content.split('\n').filter(line => line.trim()).map(line => JSON.parse(line))
            } else {
              results[file] = JSON.parse(content)
            }
          }
        }
      } catch (error) {
        console.error('Error reading coursebook data:', error)
        results.coursebookError = 'Failed to read coursebook data'
      }
    }

    if (dataType === 'all' || dataType === 'trends') {
      try {
        const trendsDir = path.join(dataDir, 'utdtrends')
        const files = await readdir(trendsDir)
        
        for (const file of files) {
          if (file.endsWith('.json') || file.endsWith('.jsonl')) {
            const filePath = path.join(trendsDir, file)
            const content = await readFile(filePath, 'utf-8')
            
            if (file.endsWith('.jsonl')) {
              results[file] = content.split('\n').filter(line => line.trim()).map(line => JSON.parse(line))
            } else {
              results[file] = JSON.parse(content)
            }
          }
        }
      } catch (error) {
        console.error('Error reading trends data:', error)
        results.trendsError = 'Failed to read trends data'
      }
    }

    return NextResponse.json({
      data: results,
      dataType,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error fetching local data:', error)
    return NextResponse.json(
      { error: 'Failed to fetch local data' },
      { status: 500 }
    )
  }
}
