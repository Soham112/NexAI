"""
AWS Bedrock extractor for job data
"""
import json
import boto3
from typing import Dict, Optional
from config import settings


class BedrockExtractor:
    """Extract structured job data using AWS Bedrock"""
    
    def __init__(self):
        """Initialize Bedrock client"""
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=settings.BEDROCK_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.model_id = settings.BEDROCK_MODEL_ID
    
    def extract_job_data(self, raw_job: Dict) -> Optional[Dict]:
        """
        Extract structured job data from raw HTML using Bedrock
        
        Args:
            raw_job: Dictionary containing raw job data with HTML content
            
        Returns:
            Dictionary with extracted structured data
        """
        html_content = raw_job.get('html_content', raw_job.get('description', ''))
        url = raw_job.get('url', '')
        
        # Create prompt for Bedrock
        prompt = self._create_extraction_prompt(html_content, url)
        
        try:
            # Call Bedrock API
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,
                    "top_p": 0.9
                })
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            extracted_text = response_body['content'][0]['text']
            
            # Parse JSON from response
            extracted_data = json.loads(extracted_text)
            
            # Add original URL
            extracted_data['url'] = url
            
            return extracted_data
            
        except Exception as e:
            print(f"      ✗ Bedrock extraction failed: {str(e)[:100]}")
            return None
    
    def _create_extraction_prompt(self, html_content: str, url: str) -> str:
        """
        Create extraction prompt for Bedrock
        
        Args:
            html_content: Raw HTML content
            url: Job URL
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a job data extraction expert. Extract structured information from the following job posting HTML.

Job URL: {url}

HTML Content:
{html_content[:15000]}

Extract the following information and return it as a valid JSON object:

{{
    "id": "unique job identifier (extract from URL or generate)",
    "title": "job title",
    "company": "company name",
    "location": "job location (city, state, country or 'Remote')",
    "date_posted": "date posted (in ISO format YYYY-MM-DD if available, or empty string)",
    "salary_low": minimum salary as number (or null if not specified),
    "salary_high": maximum salary as number (or null if not specified),
    "description": "clean text description without HTML tags (first 2000 characters)",
    "listed_skills": ["skill1", "skill2", "skill3"] (extract technical skills mentioned)
}}

IMPORTANT RULES:
1. Return ONLY valid JSON, no additional text
2. Extract actual data from the HTML, don't make up information
3. If a field is not found, use null for numbers, empty string for text, or empty array for lists
4. For skills, extract programming languages, frameworks, tools, and technologies mentioned
5. For salary, extract numbers only (remove currency symbols and convert k/K notation to thousands)
6. Clean the description by removing HTML tags and extra whitespace

Return only the JSON object:"""
        
        return prompt


class BedrockBatchExtractor:
    """Batch process multiple jobs with Bedrock"""
    
    def __init__(self):
        """Initialize extractor"""
        self.extractor = BedrockExtractor()
    
    async def extract_batch(self, raw_jobs: list, batch_size: int = 5) -> list:
        """
        Extract data from multiple jobs
        
        Args:
            raw_jobs: List of raw job dictionaries
            batch_size: Number of concurrent extractions
            
        Returns:
            List of extracted job dictionaries
        """
        import asyncio
        
        extracted_jobs = []
        
        for i in range(0, len(raw_jobs), batch_size):
            batch = raw_jobs[i:i + batch_size]
            
            # Process batch
            tasks = []
            for job in batch:
                # Run in thread pool since boto3 is synchronous
                task = asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.extractor.extract_job_data, 
                    job
                )
                tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks)
            
            # Add successful extractions
            for result in batch_results:
                if result:
                    extracted_jobs.append(result)
        
        return extracted_jobs
