import boto3
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_aws_connection():
    """Test AWS S3 connection"""
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION')
        )
        
        # Test: List buckets
        response = s3_client.list_buckets()
        
        print("✅ AWS Connection Successful!")
        print(f"\n📦 Your S3 Buckets:")
        for bucket in response['Buckets']:
            print(f"  - {bucket['Name']}")
        
        # Test: Check if your job market bucket exists
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if bucket_name in [b['Name'] for b in response['Buckets']]:
            print(f"\n✅ Found your bucket: {bucket_name}")
        else:
            print(f"\n❌ Bucket not found: {bucket_name}")
        
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("\nPlease check:")
        print("  1. Your .env file has correct credentials")
        print("  2. Your IAM user has S3 permissions")
        print("  3. Your access keys are valid")

if __name__ == "__main__":
    test_aws_connection()
