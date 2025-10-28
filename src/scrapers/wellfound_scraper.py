"""
Wellfound scraper - DISABLED due to anti-bot protection
"""
from typing import List


class WellfoundScraper:
    """Wellfound scraper - currently disabled"""
    
    async def get_all_job_urls(self, job_title: str, location: str) -> List[str]:
        """
        Wellfound scraping is disabled due to strict anti-bot measures
        
        Returns:
            Empty list
        """
        print(f"\n  [WELLFOUND] Skipped")
        print(f"    ℹ️  Wellfound has strict anti-bot protection")
        print(f"    💡 Using Greenhouse only (500+ companies)")
        return []
    
    async def parse_job(self, url: str) -> dict:
        """Not implemented"""
        return None
