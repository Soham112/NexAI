"""
Google search to find Greenhouse and Wellfound job boards
"""
from googlesearch import search
from typing import List
import time


class GoogleJobSearch:
    """Use Google to find job boards"""
    
    @staticmethod
    def search_greenhouse_jobs(job_title: str, location: str, max_results: int = 50) -> List[str]:
        """
        Search Google for Greenhouse job boards
        
        Args:
            job_title: Job title to search
            location: Location to search
            max_results: Maximum number of results
            
        Returns:
            List of Greenhouse job board URLs
        """
        # Build Google search query
        query = f'site:boards.greenhouse.io "{job_title}" "{location}"'
        
        print(f"\n    🔍 Google Search Query: {query}")
        
        job_urls = []
        
        try:
            # Perform Google search
            for url in search(query, num_results=max_results, sleep_interval=2):
                if 'boards.greenhouse.io' in url and '/jobs/' in url:
                    job_urls.append(url)
                    print(f"      ✓ Found: {url}")
                
                # Rate limiting
                time.sleep(0.5)
        
        except Exception as e:
            print(f"    ❌ Google search error: {e}")
            print(f"    💡 TIP: You may need to use a different search method or API")
        
        return job_urls
    
    @staticmethod
    def search_wellfound_jobs(job_title: str, location: str, max_results: int = 50) -> List[str]:
        """
        Search Google for Wellfound jobs
        
        Args:
            job_title: Job title to search
            location: Location to search
            max_results: Maximum number of results
            
        Returns:
            List of Wellfound job URLs
        """
        # Build Google search query
        query = f'site:wellfound.com/l OR site:wellfound.com/company "{job_title}" "{location}"'
        
        print(f"\n    🔍 Google Search Query: {query}")
        
        job_urls = []
        
        try:
            for url in search(query, num_results=max_results, sleep_interval=2):
                if 'wellfound.com' in url and ('/l/' in url or '/jobs/' in url):
                    job_urls.append(url)
                    print(f"      ✓ Found: {url}")
                
                time.sleep(0.5)
        
        except Exception as e:
            print(f"    ❌ Google search error: {e}")
        
        return job_urls
