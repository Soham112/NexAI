"""
Main entry point - with AWS Bedrock extraction
"""
import asyncio
from config import settings
from src.utils.validators import get_user_input
from src.scrapers.greenhouse_scraper import GreenhouseScraper
from src.scrapers.wellfound_scraper import WellfoundScraper
from src.storage.s3_manager import S3Manager
from src.extractors.bedrock_extractor import BedrockBatchExtractor


async def main():
    """Run job market agent with Bedrock extraction"""
    
    # Validate settings
    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        return
    
    # Get user input
    job_title, location, strict_location = get_user_input()
    
    print("\n" + "=" * 80)
    print("JOB MARKET AGENT - WITH AWS BEDROCK EXTRACTION")
    print("=" * 80)
    
    # Initialize
    greenhouse_scraper = GreenhouseScraper()
    wellfound_scraper = WellfoundScraper()
    s3_manager = S3Manager()
    bedrock_extractor = BedrockBatchExtractor()
    
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
    
    # Upload URLs
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
    
    print(f"\n  ✅ Scraped {len(raw_jobs)} jobs")
    
    # ========================================================================
    # STEP 3: EXTRACT STRUCTURED DATA WITH AWS BEDROCK
    # ========================================================================
    print(f"\n[STEP 3] Extracting structured data with AWS Bedrock...")
    print(f"  Model: {settings.BEDROCK_MODEL_ID}")
    print(f"  Processing {len(raw_jobs)} jobs in batches of 5...")
    
    extracted_jobs = await bedrock_extractor.extract_batch(raw_jobs, batch_size=5)
    
    print(f"\n  ✅ Successfully extracted {len(extracted_jobs)}/{len(raw_jobs)} jobs")
    
    # Show sample extraction
    if extracted_jobs:
        print(f"\n  📋 Sample Extraction:")
        sample = extracted_jobs[0]
        print(f"    Title: {sample.get('title')}")
        print(f"    Company: {sample.get('company')}")
        print(f"    Location: {sample.get('location')}")
        print(f"    Skills: {', '.join(sample.get('listed_skills', [])[:5])}")
    
    # ========================================================================
    # STEP 4: STORE EXTRACTED DATA IN S3
    # ========================================================================
    print(f"\n[STEP 4] Uploading extracted data to S3...")
    
    extracted_s3_key = s3_manager.upload_extracted_jobs(extracted_jobs, job_title, location or "all")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 80)
    print(f"📊 RESULTS:")
    print(f"  URLs Found: {total_urls}")
    print(f"  Jobs Scraped: {len(raw_jobs)}")
    print(f"  Jobs Extracted: {len(extracted_jobs)}")
    print(f"  Success Rate: {len(extracted_jobs)/len(raw_jobs)*100:.1f}%")
    
    print(f"\n📁 S3 STORAGE:")
    print(f"  Job URLs: s3://{settings.S3_BUCKET_NAME}/{settings.S3_LINKS_PREFIX}")
    print(f"  Extracted JSON: s3://{settings.S3_BUCKET_NAME}/{extracted_s3_key}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
