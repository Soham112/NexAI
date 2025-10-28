"""
S3 storage manager - stores each URL as separate .txt file
"""
import json
import boto3
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from config import settings


class S3Manager:
    """Manage S3 upload and download operations"""
    
    def __init__(self):
        """Initialize S3 client with credentials from settings"""
        self.s3_client = boto3.client('s3', **settings.get_boto3_config())
        self.bucket_name = settings.S3_BUCKET_NAME
    
    def upload_individual_links(self, job_links: Dict[str, List[str]], 
                               job_title: str, location: str) -> List[str]:
        """
        Upload each job URL as a SEPARATE .txt file to S3
        
        Args:
            job_links: Dictionary of job links by source
            job_title: Job title searched
            location: Location searched
            
        Returns:
            List of S3 keys for uploaded files
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = job_title.replace(" ", "_").lower() if job_title else "all"
        safe_location = location.replace(" ", "_").lower() if location else "all"
        
        uploaded_keys = []
        file_counter = 1
        
        print(f"\n  📤 Uploading individual URL files to S3...")
        
        for source, links in job_links.items():
            for url in links:
                # Create unique filename for each URL
                filename = f'job_link_{safe_title}_{safe_location}_{timestamp}_{file_counter:04d}.txt'
                local_path = settings.RAW_DATA_DIR / filename
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write single URL to file
                with open(local_path, 'w') as f:
                    f.write(f"# Job Link #{file_counter}\n")
                    f.write(f"# Source: {source}\n")
                    f.write(f"# Scraped at: {datetime.now().isoformat()}\n\n")
                    f.write(url)
                
                # Upload to S3
                s3_key = f"{settings.S3_LINKS_PREFIX}{source}/{filename}"
                self.s3_client.upload_file(str(local_path), self.bucket_name, s3_key)
                uploaded_keys.append(s3_key)
                
                if file_counter % 10 == 0 or file_counter == len(links):
                    print(f"    [{file_counter}/{sum(len(v) for v in job_links.values())}] Uploaded", end='\r')
                
                file_counter += 1
        
        print(f"\n  ✅ Uploaded {len(uploaded_keys)} individual URL files")
        
        # Also create a master index file
        index_filename = f'job_links_index_{safe_title}_{safe_location}_{timestamp}.txt'
        index_local_path = settings.RAW_DATA_DIR / index_filename
        
        with open(index_local_path, 'w') as f:
            f.write(f"# Master Index - Job Links for {job_title} in {location}\n")
            f.write(f"# Total URLs: {len(uploaded_keys)}\n")
            f.write(f"# Scraped at: {datetime.now().isoformat()}\n\n")
            
            for key in uploaded_keys:
                f.write(f"{key}\n")
        
        index_s3_key = f"{settings.S3_LINKS_PREFIX}index_{safe_title}_{safe_location}_{timestamp}.txt"
        self.s3_client.upload_file(str(index_local_path), self.bucket_name, index_s3_key)
        
        print(f"  ✅ Created master index: {index_s3_key}")
        
        return uploaded_keys
    
    def download_all_links(self, s3_keys: List[str]) -> List[str]:
        """
        Download all URL files from S3
        
        Args:
            s3_keys: List of S3 keys to download
            
        Returns:
            List of job URLs
        """
        all_urls = []
        
        for s3_key in s3_keys:
            local_path = settings.RAW_DATA_DIR / Path(s3_key).name
            
            try:
                self.s3_client.download_file(self.bucket_name, s3_key, str(local_path))
                
                with open(local_path, 'r') as f:
                    lines = f.readlines()
                    # Get the last non-empty line (the URL)
                    for line in reversed(lines):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            all_urls.append(line)
                            break
            except Exception as e:
                print(f"    ⚠️  Failed to download {s3_key}: {e}")
        
        return all_urls
    
    def upload_raw_jobs(self, raw_jobs: List[dict], 
                       job_title: str, location: str) -> str:
        """
        Upload RAW scraped job data to S3 as text/JSON (before cleaning)
        
        Args:
            raw_jobs: List of raw job dictionaries
            job_title: Job title searched
            location: Location searched
            
        Returns:
            S3 key of uploaded file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = job_title.replace(" ", "_").lower() if job_title else "all"
        safe_location = location.replace(" ", "_").lower() if location else "all"
        filename = f'raw_jobs_{safe_title}_{safe_location}_{timestamp}.json'
        
        local_path = settings.RAW_DATA_DIR / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write as JSON for easier parsing
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(raw_jobs, f, indent=2, ensure_ascii=False)
        
        s3_key = f"raw-jobs/{filename}"
        self.s3_client.upload_file(str(local_path), self.bucket_name, s3_key)
        
        print(f"✓ Uploaded {len(raw_jobs)} raw jobs to s3://{self.bucket_name}/{s3_key}")
        
        return s3_key
    
    def download_raw_jobs(self, s3_key: str) -> List[dict]:
        """
        Download raw job data from S3
        
        Args:
            s3_key: S3 key of the file
            
        Returns:
            List of raw job dictionaries
        """
        local_path = settings.RAW_DATA_DIR / 'downloaded_raw_jobs.json'
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.s3_client.download_file(self.bucket_name, s3_key, str(local_path))
        
        with open(local_path, 'r', encoding='utf-8') as f:
            raw_jobs = json.load(f)
        
        return raw_jobs
    
    def upload_jobs(self, jobs_data: List[dict], 
                   job_title: str, location: str) -> str:
        """
        Upload CLEANED/PROCESSED job data as JSON to S3
        
        Args:
            jobs_data: List of cleaned job dictionaries
            job_title: Job title searched
            location: Location searched
            
        Returns:
            S3 key of uploaded file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = job_title.replace(" ", "_").lower() if job_title else "all"
        safe_location = location.replace(" ", "_").lower() if location else "all"
        filename = f'jobs_{safe_title}_{safe_location}_{timestamp}.json'
        
        local_path = settings.PROCESSED_DATA_DIR / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(jobs_data, f, indent=2, ensure_ascii=False)
        
        s3_key = f"{settings.S3_JOBS_PREFIX}{filename}"
        self.s3_client.upload_file(str(local_path), self.bucket_name, s3_key)
        
        print(f"✓ Uploaded {len(jobs_data)} processed jobs to s3://{self.bucket_name}/{s3_key}")
        
        return s3_key
