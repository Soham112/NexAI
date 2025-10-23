#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, os, sys
from typing import Dict

try:
    from agentcore import Agent  # type: ignore
except Exception:
    class Agent:
        def __init__(self, name: str, system: str, tools=None):
            self.name, self.system, self.tools = name, system, tools or []
        def __call__(self, prompt: str) -> str:
            return f"[Shim Agent: no LLM connected]\nSYSTEM:\n{self.system}\n\nPROMPT:\n{prompt}"

from course_catalog_kb_tool import course_kb_search
from console_agent_tool import invoke_console_agent

# ------------- SYSTEM PROMPT (STRICT) -------------
system_prompt = """
You are NexAI — a router/orchestrator.
Follow these MUST rules:

1) If the user asks about COURSES (UTD course names/descriptions, prerequisites, which course to take, learning path),
   CALL the tool `invoke_console_agent` FIRST with the user’s text as-is.
   - Do not answer from your own knowledge.
   - Return exactly what the console agent responded (you may lightly tidy formatting).

2) If the user asks ONLY about JOBS/ROLES/SKILLS/SALARIES/MARKET TRENDS,
   CALL the tool `course_kb_search` FIRST with a domain hint “jobs-only; exclude course catalog; summarize & cite”.
   - Base your final answer ONLY on the KB snippets returned.

3) If both courses and jobs are requested, FIRST call `course_kb_search` to collect job-side signals,
   THEN call `invoke_console_agent` and include a brief bridge that maps skills → courses.

4) If a required tool returns NO_RESULTS or ERROR, say:
   “I didn’t find enough in the KB/agent for that. Please refine your query.”
   Do not fabricate.

Keep responses concise and structured.
"""

def _domain(p: str):
    t = p.lower()
    jobs = any(k in t for k in ["job","role","skills","salary","market","posting","requirements","trend","usa","united states"])
    courses = any(k in t for k in ["course","utd","subject","credit","prereq","syllabus","catalog","which courses","learning path","buan","mis ","cs "])
    return jobs, courses

agent = Agent(
    name="NexAI",
    system=system_prompt,
    tools=[invoke_console_agent, course_kb_search],
)

def run(payload: Dict) -> str:
    raw = payload.get("prompt", "")
    jobs, courses = _domain(raw)

    # A tiny nudge to the planner
    if courses and not jobs:
        hint = "Planner: Use invoke_console_agent FIRST."
    elif jobs and not courses:
        hint = "Planner: Use course_kb_search FIRST with [jobs-only; exclude course catalog]."
    else:
        hint = "Planner: Do course_kb_search FIRST, then invoke_console_agent."

    print(f"[DEBUG] Using AgentID=DYOPALGMYF, AliasID=Y5ERQMDBRX, KB=2BA9XEXYD4, Region=us-east-1")
    
    response = agent(f"{hint}\n\nUser: {raw}")
    if os.getenv("PRINT_AGENT_RESPONSE", "1") == "1":
        print(response)
    return response

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "invoke":
        payload = json.loads(sys.argv[2])
        run(payload)
    else:
        print("Usage: python agentcore_starter_strands.py invoke '{\"prompt\":\"...\"}'")


# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """
# AgentCore starter with strict domain routing and MUST-use-KB grounding.

# Usage (standalone):
#   python agentcore_starter_strands.py invoke '{"prompt":"List the top 5 job skills for Data Scientist roles in the USA"}'

# In your existing harness (e.g., `agentcore invoke ...`), it’s enough that this file exposes
# the `agent` object and the `run(payload: dict) -> str` helper. Adjust imports if your AgentCore
# package path differs.
# """

# import json
# import os
# import sys
# from typing import Dict

# # --- AgentCore imports (fallback-friendly) ---
# try:
#     from agentcore import Agent  # type: ignore
# except Exception:
#     # Minimal shim for local testing if AgentCore isn't present
#     class Agent:
#         def __init__(self, name: str, system: str, tools=None):
#             self.name = name
#             self.system = system
#             self.tools = tools or []

#         def __call__(self, prompt: str) -> str:
#             # This shim only echoes; real behavior requires AgentCore.
#             return f"[Shim Agent: no LLM connected]\nSYSTEM:\n{self.system}\n\nPROMPT:\n{prompt}"

# # Import the KB tool (kept as a separate module)
# from course_catalog_kb_tool import course_kb_search

# # -------------------------
# # SYSTEM PROMPT (STRICT)
# # -------------------------
# system_prompt = ("""
# "You are a helpful assistant.\n"
#         "\n"
#         "Routing rules:\n"
#         "1) For ANY question about UTD courses, course descriptions, prerequisites, skills taught, "
#         "   scheduling/sections, or \"which course should I take\", FIRST call the tool "
#         "`course_kb_search` with a well-phrased query. Then synthesize an answer using the retrieved "
#         "passages and include brief source URIs.\n"
#         "2) Use `calculate` ONLY for pure numeric/math requests or tiny Python calculations. "
#         "   If a user asks about courses but includes numbers, STILL call `course_kb_search` first.\n"
#         "3) If the KB returns no results, say so briefly and ask a focused follow-up question."
# """)

# # -------------------------
# # Helper: domain hinting
# # -------------------------
# def _domain_hint(p: str) -> str:
#     text = p.lower()
#     jobs_triggers = [
#         "job", "role", "skills", "salary", "market", "employer",
#         "posting", "usa", "united states", "requirements", "trend"
#     ]
#     courses_triggers = [
#         "course", "utd", "subject", "credit", "prereq", "syllabus",
#         "catalog", "cs ", "buan", "mis ", "which courses", "learning path"
#     ]

#     jobs = any(t in text for t in jobs_triggers)
#     courses = any(t in text for t in courses_triggers)

#     if jobs and not courses:
#         return f"{p}\n\n[retrieval-hint: jobs-only; exclude course catalog; summarize by frequency; cite KB sources]"
#     if courses and not jobs:
#         return f"{p}\n\n[retrieval-hint: courses-only; exclude job postings; list course codes + one-line summaries; cite KB sources]"
#     return f"{p}\n\n[retrieval-hint: bridge allowed if needed; first retrieve jobs → then map to UTD courses; cite KB sources]"

# # -------------------------
# # Build Agent
# # -------------------------
# agent = Agent(
#     name="",
#     system=system_prompt,
#     tools=[course_kb_search],
# )

# # -------------------------
# # Public entrypoint
# # -------------------------
# def run(payload: Dict) -> str:
#     raw = payload.get("prompt", "")
#     user_prompt = _domain_hint(raw)

#     # Short, per-turn tool-use gate to reinforce MUST-use behavior
#     tool_gate = (
#         "Reminder: For this query, call `course_kb_search` FIRST using the retrieval-hint. "
#         "Base your final answer ONLY on retrieved KB snippets. "
#         "Do NOT include courses in jobs-only queries, and do NOT include job stats in courses-only queries."
#     )

#     response = agent(f"{tool_gate}\n\n{user_prompt}")
#     # If your harness expects a print, keep this:
#     if os.getenv("PRINT_AGENT_RESPONSE", "1") == "1":
#         print(response)
#     return response

# # CLI compatibility (optional for your harness)
# if __name__ == "__main__":
#     if len(sys.argv) >= 3 and sys.argv[1] == "invoke":
#         try:
#             payload = json.loads(sys.argv[2])
#         except Exception:
#             print("ERROR: Provide JSON payload as the second argument.", file=sys.stderr)
#             sys.exit(2)
#         run(payload)
#     else:
#         print("Usage: python agentcore_starter_strands.py invoke '{\"prompt\":\"...\"}'")
