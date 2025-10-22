# course_catalog_kb_tool.py
from typing import List, Dict, Any
import os, boto3
from strands import tool  # <-- add

_REGION = os.getenv("AWS_REGION", "us-east-1")
_KB_ID = os.getenv("COURSE_KB_ID")
_runtime = boto3.client("bedrock-agent-runtime", region_name=_REGION)

def kb_retrieve(query: str, top_k: int = 5) -> Dict[str, Any]:
    if not _KB_ID:
        raise RuntimeError("COURSE_KB_ID env var is not set.")
    
    if not isinstance(top_k, int) or top_k <= 0:
        top_k = 5

    resp = _runtime.retrieve(
        knowledgeBaseId=_KB_ID,
        retrievalQuery={"text": query.strip()},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": top_k}},
    )

    chunks = []
    for item in resp.get("retrievalResults", []):
        text = item.get("content", {}).get("text", "")
        score = item.get("score")
        # source = None
        loc = (item.get("location") or {}).get("s3Location") or {}
        source = loc.get("uri")  # e.g., s3://bucket/prefix/file#offsets
        chunks.append({"text": text, "score": score, "source": source})
    return {"query": query, "results": chunks}

@tool
def course_kb_search(query: str, top_k: int = 5) -> str:
    """Search the UTD Course Catalog KB and return the top passages with sources."""
    data = kb_retrieve(query, top_k)
    rows = []
    for r in data["results"]:
        score = f"{r['score']:.2f}" if isinstance(r["score"], (int, float)) else str(r["score"])
        rows.append(f"- {r['text']}\n  Source: {r['source']}  (score: {score})")
    return "\n".join(rows) if rows else "No results."



# # course_catalog_kb_tool.py
# from typing import List, Dict, Any
# import os
# import boto3

# # Read once at import
# _REGION = os.getenv("AWS_REGION", "us-east-1")
# _KB_ID = os.getenv("COURSE_KB_ID")  # we’ll set this in the YAML below
# _runtime = boto3.client("bedrock-agent-runtime", region_name=_REGION)

# def kb_retrieve(query: str, top_k: int = 5) -> Dict[str, Any]:
#     """
#     Retrieve top_k passages from your Bedrock Knowledge Base.
#     Returns passages + metadata that your agent can reason over.
#     """
#     if not _KB_ID:
#         raise RuntimeError("COURSE_KB_ID env var is not set. Add it in .bedrock_agentcore.yaml env.")

#     resp = _runtime.retrieve(
#         knowledgeBaseId=_KB_ID,
#         retrievalQuery={"text": query},
#         retrievalConfiguration={
#             "vectorSearchConfiguration": {"numberOfResults": top_k}
#         },
#     )

#     chunks = []
#     for item in resp.get("retrievalResults", []):
#         text = item.get("content", {}).get("text", "")
#         score = item.get("score")
#         source = None
#         for ref in item.get("location", {}).get("s3Location", []):
#             source = ref.get("uri")
#         chunks.append({"text": text, "score": score, "source": source})

#     return {"query": query, "results": chunks}
