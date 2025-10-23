#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tool: course_kb_search(query, top_k=5)
"""

import json
import os
import textwrap
from typing import List, Dict, Any
import boto3

try:
    from agentcore import tool  # type: ignore
except Exception:
    def tool(fn):
        return fn


def _bedrock_kb_client(region: str):
    return boto3.client("bedrock-agent-runtime", region_name=region)


def _fmt_chunk(i: int, ch: Dict[str, Any]) -> str:
    text = (
        ch.get("content", {}).get("text")
        or ch.get("text")
        or ch.get("content")
        or ""
    )
    text = " ".join(str(text).split())
    text = textwrap.shorten(text, width=900, placeholder=" …")
    loc = ch.get("location", {}) or {}
    s3_uri = loc.get("s3Location", {}).get("uri")
    url = loc.get("url")
    loc_type = loc.get("type")
    source = s3_uri or url or (f"source:{loc_type}" if loc_type else "source:unknown")
    return f"[{i}] {text}\n    — {source}"


@tool
def course_kb_search(query: str, top_k: int = 5) -> str:
    region = os.getenv("AWS_REGION", "us-east-1")
    kb_id = os.getenv("COURSE_KB_ID") or "2BA9XEXYD4"   # hard-fallback KB ID

    if not kb_id:
        return "ERROR: COURSE_KB_ID not set and no hard-fallback provided."

    client = _bedrock_kb_client(region)

    try:
        resp = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": int(top_k)}
            },
        )
    except Exception as e:
        return f"ERROR: Bedrock KB retrieve() failed: {e}"

    results: List[Dict[str, Any]] = (
        resp.get("retrievalResults")
        or resp.get("results")
        or resp.get("response", {}).get("retrievalResults")
        or []
    )

    if not results:
        return "NO_RESULTS: The KB returned no matches for this query."

    lines = ["KB_RESULTS:"]
    for i, r in enumerate(results[:top_k], start=1):
        lines.append(_fmt_chunk(i, r))
    return "\n".join(lines)
