import os, json, uuid, boto3

s3 = boto3.client("s3")
BUCKET = os.environ.get("UPLOAD_BUCKET", "resume-uploads-hackathon")

def lambda_handler(event, context):
    # CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            },
            "body": "{}"
        }

    body = json.loads(event.get("body") or "{}")
    filename = body.get("filename", "resume.pdf")
    content_type = body.get("contentType", "application/pdf")

    key = f"resumes/session_{uuid.uuid4().hex}/{filename}"
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=600,
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps({"url": url, "key": key})
    }
