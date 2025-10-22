"""
Strands Agent sample with AgentCore + Course Catalog KB integration
"""
import os
from strands import Agent, tool
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# --- App bootstrap ---
app = BedrockAgentCoreApp()

# --- Environment ---
MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION", "us-east-1")
MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
)

# --- Import the KB tool exposed in course_catalog_kb_tool.py ---
# Expecting a @tool named `course_kb_search(query: str, top_k: int = 5) -> str`
try:
    from course_catalog_kb_tool import course_kb_search  # noqa: F401
except Exception as e:
    # Provide a clear error at runtime if the tool isn't available
    raise RuntimeError(
        "Failed to import course_kb_search from course_catalog_kb_tool.py. "
        "Make sure that file defines a @tool named course_kb_search(query: str, top_k: int = 5) -> str. "
        f"Import error: {e}"
    )

# --- Optional: Code Interpreter tool (handy for dev/testing) ---
ci_sessions = {}
current_session = None

@tool
def calculate(code: str) -> str:
    """Execute short Python snippets. Use ONLY for math or tiny data checks."""
    session_id = current_session or "default"

    if session_id not in ci_sessions:
        ci_sessions[session_id] = {
            "client": CodeInterpreter(REGION),
            "session_id": None,
        }

    ci = ci_sessions[session_id]
    if not ci["session_id"]:
        ci["session_id"] = ci["client"].start(
            name=f"session_{session_id[:30]}",
            session_timeout_seconds=1800,
        )

    result = ci["client"].invoke(
        "executeCode",
        {"code": code, "language": "python"},
    )

    for event in result.get("stream", []):
        stdout = (
            event.get("result", {})
            .get("structuredContent", {})
            .get("stdout")
        )
        if stdout:
            return stdout
    return "Executed"

# --- Agent entrypoint ---
@app.entrypoint
def invoke(payload, context):
    """
    Expected payload: {"prompt": "<user text>"}.
    The agent has two tools:
      1) course_kb_search -> queries the UTD course catalog Knowledge Base.
      2) calculate        -> basic math/code (dev convenience).
    """
    global current_session

    if not MEMORY_ID:
        return {"error": "Memory not configured (BEDROCK_AGENTCORE_MEMORY_ID missing)."}

    # Resolve session/actor (AgentCore provides these headers/fields)
    actor_id = (
        context.headers.get("X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id", "user")
        if hasattr(context, "headers")
        else "user"
    )
    session_id = getattr(context, "session_id", "default")
    current_session = session_id

    # Configure AgentCore memory retrieval
    memory_config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config={
            f"/users/{actor_id}/facts": RetrievalConfig(top_k=3, relevance_score=0.5),
            f"/users/{actor_id}/preferences": RetrievalConfig(top_k=3, relevance_score=0.5),
        },
    )

    # Clear routing guidance so the model uses the right tool automatically
    system_prompt = (
        "You are a helpful assistant.\n"
        "\n"
        "Routing rules:\n"
        "1) For ANY question about UTD courses, course descriptions, prerequisites, skills taught, "
        "   scheduling/sections, or \"which course should I take\", FIRST call the tool "
        "`course_kb_search` with a well-phrased query. Then synthesize an answer using the retrieved "
        "passages and include brief source URIs.\n"
        "2) Use `calculate` ONLY for pure numeric/math requests or tiny Python calculations. "
        "   If a user asks about courses but includes numbers, STILL call `course_kb_search` first.\n"
        "3) If the KB returns no results, say so briefly and ask a focused follow-up question."
    )

    agent = Agent(
        model=MODEL_ID,
        session_manager=AgentCoreMemorySessionManager(memory_config, REGION),
        system_prompt=system_prompt,
        # Put the KB tool first to bias selection toward it
        tools=[course_kb_search, calculate],
    )

    user_prompt = payload.get("prompt", "")
    result = agent(user_prompt)

    # Safely extract text
    text = result.message.get("content", [{}])[0].get("text")
    return {"response": text or str(result)}

if __name__ == "__main__":
    app.run()



# """
# Strands Agent sample with AgentCore
# """
# import os
# from strands import Agent, tool
# from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
# from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
# from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
# from bedrock_agentcore.runtime import BedrockAgentCoreApp

# app = BedrockAgentCoreApp()

# MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
# REGION = os.getenv("AWS_REGION")
# MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# ci_sessions = {}
# current_session = None

# @tool
# def calculate(code: str) -> str:
#     """Execute Python code for calculations or analysis."""
#     session_id = current_session or 'default'

#     if session_id not in ci_sessions:
#         ci_sessions[session_id] = {
#             'client': CodeInterpreter(REGION),
#             'session_id': None
#         }

#     ci = ci_sessions[session_id]
#     if not ci['session_id']:
#         ci['session_id'] = ci['client'].start(
#             name=f"session_{session_id[:30]}",
#             session_timeout_seconds=1800
#         )

#     result = ci['client'].invoke("executeCode", {
#         "code": code,
#         "language": "python"
#     })

#     for event in result.get("stream", []):
#         if stdout := event.get("result", {}).get("structuredContent", {}).get("stdout"):
#             return stdout
#     return "Executed"

# @app.entrypoint
# def invoke(payload, context):
#     global current_session

#     if not MEMORY_ID:
#         return {"error": "Memory not configured"}

#     actor_id = context.headers.get('X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id', 'user') if hasattr(context, 'headers') else 'user'

#     session_id = getattr(context, 'session_id', 'default')
#     current_session = session_id

#     memory_config = AgentCoreMemoryConfig(
#         memory_id=MEMORY_ID,
#         session_id=session_id,
#         actor_id=actor_id,
#         retrieval_config={
#             f"/users/{actor_id}/facts": RetrievalConfig(top_k=3, relevance_score=0.5),
#             f"/users/{actor_id}/preferences": RetrievalConfig(top_k=3, relevance_score=0.5)
#         }
#     )

#     agent = Agent(
#         model=MODEL_ID,
#         session_manager=AgentCoreMemorySessionManager(memory_config, REGION),
#         system_prompt="You are a helpful assistant. Use tools when appropriate.",
#         tools=[calculate]
#     )

#     result = agent(payload.get("prompt", ""))
#     return {"response": result.message.get('content', [{}])[0].get('text', str(result))}

# if __name__ == "__main__":
#     app.run()