"""
Greenhouse scraper with flexible search options
"""
import httpx
from typing import List
import re


class GreenhouseScraper:
    """Scraper for Greenhouse company job boards"""
    
    def __init__(self):
        """Initialize with company list"""
        from src.data.greenhouse_companies import GREENHOUSE_COMPANIES
        self.companies = GREENHOUSE_COMPANIES
        print(f"    📚 Loaded {len(self.companies)} companies to search")
    
    async def get_all_job_urls(self, job_title: str, location: str, 
                               strict_location: bool = False) -> List[str]:
        """
        Get all job URLs from company list
        
        Args:
            job_title: Job title filter (required)
            location: Location filter (optional if strict_location=False)
            strict_location: If True, require exact location match. If False, be flexible.
            
        Returns:
            List of valid Greenhouse job URLs
        """
        print(f"\n  [GREENHOUSE] Searching {len(self.companies)} company boards...")
        print(f"    Filters: title='{job_title}', location='{location}' (strict={strict_location})")
        
        all_job_urls = []
        companies_with_jobs = 0
        total_jobs_before_filter = 0
        
        for i, company in enumerate(self.companies, 1):
            urls, jobs_found = await self._get_company_jobs(
                company, job_title, location, strict_location
            )
            
            total_jobs_before_filter += jobs_found
            
            if urls:
                all_job_urls.extend(urls)
                companies_with_jobs += 1
                print(f"      [{i}/{len(self.companies)}] ✅ {company}: {len(urls)} jobs matched")
            
            # Show progress every 100 companies
            if i % 100 == 0:
                print(f"      ... Progress: {i}/{len(self.companies)} companies scanned, {len(all_job_urls)} jobs found so far ...")
        
        print(f"\n    📊 SEARCH RESULTS:")
        print(f"      Companies searched: {len(self.companies)}")
        print(f"      Companies with matching jobs: {companies_with_jobs}")
        print(f"      Total jobs before location filter: {total_jobs_before_filter}")
        print(f"      Total jobs after filters: {len(all_job_urls)}")
        
        if len(all_job_urls) < 50 and location and strict_location:
            print(f"\n    💡 TIP: Try running again with broader location search")
            print(f"       - Try 'remote' instead of '{location}'")
            print(f"       - Try leaving location blank")
            print(f"       - Try nearby cities")
        
        return all_job_urls
    
    async def _get_company_jobs(self, company: str, job_title: str, 
                               location: str, strict_location: bool) -> tuple:
        """
        Get jobs from specific company
        
        Returns:
            Tuple of (matching_job_urls, total_jobs_found)
        """
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(api_url)
                
                if response.status_code != 200:
                    return [], 0
                
                data = response.json()
                all_jobs = data.get('jobs', [])
                job_urls = []
                
                for job in all_jobs:
                    job_title_text = job.get('title', '').lower()
                    job_location = job.get('location', {})
                    job_location_text = job_location.get('name', '').lower() if isinstance(job_location, dict) else str(job_location).lower()
                    
                    # Title match (always required)
                    title_match = job_title.lower() in job_title_text if job_title else True
                    
                    if not title_match:
                        continue
                    
                    # Location match (flexible)
                    if not location:
                        # No location filter - accept all
                        location_match = True
                    elif strict_location:
                        # Strict: must contain exact location
                        location_match = location.lower() in job_location_text
                    else:
                        # Flexible: match city, state, or 'remote'
                        location_parts = location.lower().replace(',', ' ').split()
                        location_match = any(part in job_location_text for part in location_parts)
                        
                        # Also accept remote jobs
                        if 'remote' in job_location_text or 'anywhere' in job_location_text:
                            location_match = True
                    
                    if location_match:
                        absolute_url = job.get('absolute_url', '')
                        
                        # Only include valid greenhouse.io URLs
                        if 'greenhouse.io' in absolute_url:
                            job_urls.append(absolute_url)
                
                return job_urls, len(all_jobs)
                
        except Exception as e:
            return [], 0
    
    async def parse_job(self, url: str) -> dict:
        """Parse individual job posting"""
        match = re.search(r'greenhouse\.io/([^/]+)/jobs/(\d+)', url)
        if not match:
            return None
        
        board_token = match.group(1)
        job_id = match.group(2)
        
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url)
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                
                return {
                    "id": str(data.get("id")),
                    "title": data.get("title", ""),
                    "company": board_token.replace("-", " ").title(),
                    "location": data.get("location", {}).get("name", ""),
                    "url": url,
                    "date_posted": data.get("updated_at", ""),
                    "salary_low": None,
                    "salary_high": None,
                    "description": data.get("content", ""),
                    "listed_skills": []
                }
        except Exception as e:
            return None
