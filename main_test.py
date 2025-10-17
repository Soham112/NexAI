"""
TEST VERSION - Only Steps 1 & 2 (no Bedrock extraction)
"""
import asyncio
from config import settings
from src.utils.validators import get_user_input
from src.scrapers.greenhouse_scraper import GreenhouseScraper
from src.scrapers.wellfound_scraper import WellfoundScraper
from src.storage.s3_manager import S3Manager
import json


async def main():
    """Test version - only scrape and view raw data"""
    
    # Validate settings
    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        return
    
    # Get user input
    job_title, location, strict_location = get_user_input()
    
    print("\n" + "=" * 80)
    print("JOB MARKET AGENT - TEST MODE (Steps 1 & 2 Only)")
    print("=" * 80)
    
    # Initialize
    greenhouse_scraper = GreenhouseScraper()
    wellfound_scraper = WellfoundScraper()
    s3_manager = S3Manager()
    
    # ========================================================================
    # STEP 1: GET JOB URLS
    # ========================================================================
    print(f"\n[STEP 1] Finding jobs for '{job_title}' in '{location or 'ALL locations'}'...")
    
    all_links = {
        "greenhouse": await greenhouse_scraper.get_all_job_urls(job_title, location, strict_location),
        "wellfound": await wellfound_scraper.get_all_job_urls(job_title, location)
    }
    
    total_urls = sum(len(v) for v in all_links.values())
    
    if total_urls == 0:
        print("\n❌ No jobs found!")
        return
    
    print(f"\n  📋 Found {total_urls} job URLs")
    print(f"    - Greenhouse: {len(all_links['greenhouse'])}")
    print(f"    - Wellfound: {len(all_links['wellfound'])}")
    
    # Show first 10 URLs
    print(f"\n  🔗 Sample URLs (first 10):")
    all_urls_list = all_links['greenhouse'][:10] + all_links['wellfound'][:10]
    for i, url in enumerate(all_urls_list[:10], 1):
        print(f"    {i}. {url}")
    
    # Upload URLs to S3
    print(f"\n  📤 Uploading URLs to S3...")
    uploaded_keys = s3_manager.upload_individual_links(all_links, job_title, location or "all")
    
    # ========================================================================
    # STEP 2: SCRAPE RAW HTML
    # ========================================================================
    print(f"\n[STEP 2] Scraping {total_urls} job postings (raw HTML)...")
    
    all_urls = s3_manager.download_all_links(uploaded_keys)
    raw_jobs = []
    
    for i, url in enumerate(all_urls, 1):
        source = "greenhouse" if "greenhouse" in url else "wellfound"
        scraper = greenhouse_scraper if source == "greenhouse" else wellfound_scraper
        
        raw_job = await scraper.parse_job(url)
        if raw_job:
            raw_jobs.append(raw_job)
            title = raw_job.get('title', 'Unknown')[:40]
            company = raw_job.get('company', 'Unknown')[:20]
            print(f"  [{i}/{total_urls}] ✓ {company} | {title}")
    
    print(f"\n  ✅ Scraped {len(raw_jobs)} jobs successfully")
    
    # ========================================================================
    # SHOW RAW OUTPUT (for testing)
    # ========================================================================
    print("\n" + "=" * 80)
    print("📋 RAW OUTPUT PREVIEW")
    print("=" * 80)
    
    if raw_jobs:
        # Show first job in detail
        print(f"\n[SAMPLE JOB 1]")
        sample_job = raw_jobs[0]
        
        print(f"\n  Basic Info:")
        print(f"    ID: {sample_job.get('id')}")
        print(f"    Title: {sample_job.get('title')}")
        print(f"    Company: {sample_job.get('company')}")
        print(f"    Location: {sample_job.get('location')}")
        print(f"    URL: {sample_job.get('url')}")
        print(f"    Date Posted: {sample_job.get('date_posted')}")
        
        # Show HTML content preview
        html_content = sample_job.get('html_content', sample_job.get('description', ''))
        print(f"\n  HTML Content (first 500 chars):")
        print(f"    {html_content[:500]}...")
        print(f"\n  HTML Length: {len(html_content)} characters")
        
        # Save sample to local file for inspection
        sample_file = settings.RAW_DATA_DIR / 'sample_job_output.json'
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample_job, f, indent=2, ensure_ascii=False)
        
        print(f"\n  💾 Full sample saved to: {sample_file}")
        
        # Show structure of all jobs
        print(f"\n[ALL JOBS STRUCTURE]")
        for i, job in enumerate(raw_jobs[:5], 1):  # Show first 5
            print(f"\n  Job {i}:")
            print(f"    Title: {job.get('title', 'N/A')}")
            print(f"    Company: {job.get('company', 'N/A')}")
            print(f"    Location: {job.get('location', 'N/A')}")
            print(f"    URL: {job.get('url', 'N/A')[:60]}...")
            print(f"    Has HTML: {'Yes' if job.get('html_content') or job.get('description') else 'No'}")
            
            html = job.get('html_content', job.get('description', ''))
            print(f"    HTML Size: {len(html)} chars")
        
        if len(raw_jobs) > 5:
            print(f"\n  ... and {len(raw_jobs) - 5} more jobs")
    
    # Save all raw jobs to local JSON for inspection
    all_jobs_file = settings.RAW_DATA_DIR / f'all_raw_jobs_{job_title.replace(" ", "_")}.json'
    with open(all_jobs_file, 'w', encoding='utf-8') as f:
        json.dump(raw_jobs, f, indent=2, ensure_ascii=False)
    
    print(f"\n  💾 All raw jobs saved to: {all_jobs_file}")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE (Steps 1 & 2 Only)")
    print("=" * 80)
    print(f"📊 RESULTS:")
    print(f"  URLs Found: {total_urls}")
    print(f"  Jobs Scraped: {len(raw_jobs)}")
    print(f"  Success Rate: {len(raw_jobs)/total_urls*100:.1f}%")
    
    print(f"\n📁 LOCAL FILES (for inspection):")
    print(f"  Sample Job: {sample_file}")
    print(f"  All Jobs: {all_jobs_file}")
    
    print(f"\n📁 S3 STORAGE:")
    print(f"  Job URLs: s3://{settings.S3_BUCKET_NAME}/{settings.S3_LINKS_PREFIX}")
    
    print("\n💡 NEXT STEPS:")
    print("  1. Inspect the local JSON files above")
    print("  2. Verify the HTML content is complete")
    print("  3. When ready, run main.py for full pipeline with Bedrock")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
