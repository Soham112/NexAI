"""
Debug script to see what crawl4ai extracts from Wellfound
"""
import asyncio
from src.scrapers.wellfound_scraper import WellfoundScraper


async def debug_wellfound():
    """Debug Wellfound scraping to see what crawl4ai extracts"""
    
    print("=" * 80)
    print("DEBUG: WELLFOUND CRAWL4AI EXTRACTION")
    print("=" * 80)
    
    scraper = WellfoundScraper()
    
    # Test with a common job title and location
    job_title = "data scientist"
    location = "remote"
    
    print(f"\nTesting with:")
    print(f"  Job Title: {job_title}")
    print(f"  Location: {location}")
    print("\n" + "-" * 60)
    
    links = await scraper.extract_links(job_title, location)
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS:")
    print("=" * 80)
    print(f"Total links found: {len(links)}")
    
    if links:
        print("\nLinks found:")
        for i, link in enumerate(links, 1):
            print(f"  {i}. {link}")
    else:
        print("\nNo links found. Check the debug files:")
        print("  - /tmp/wellfound_debug.html (raw HTML)")
        print("  - /tmp/wellfound_next_data.json (JSON data)")


if __name__ == "__main__":
    asyncio.run(debug_wellfound())
