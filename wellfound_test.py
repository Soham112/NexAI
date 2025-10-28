
# Test wellfound scraper standalone
import asyncio
from src.scrapers.wellfound_scraper import WellfoundScraper

async def test():
    scraper = WellfoundScraper()
    urls = await scraper.get_all_job_urls("software engineer", "san francisco")
    print(f"Found {len(urls)} jobs")
    print(urls[:5])

asyncio.run(test())