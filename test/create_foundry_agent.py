import os
import sys
import time
from typing import Optional

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def getenv(*names: str, default: Optional[str] = None) -> Optional[str]:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default


def main():
    # Load .env from backend directory if present
    backend_env = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    else:
        # Fallback to loading from cwd if available
        load_dotenv()

    endpoint = getenv("AZURE_AI_PROJECT_ENDPOINT", "PROJECT_ENDPOINT") or (sys.argv[1] if len(sys.argv) > 1 else None)
    deployment = getenv("MODEL_DEPLOYMENT_NAME", "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME") or (sys.argv[2] if len(sys.argv) > 2 else None)
    agent_name = getenv("TEST_AGENT_NAME", default="Chat_Content_Agent")

    if not endpoint or not deployment:
        print("Usage: python scripts/create_foundry_agent.py <project_endpoint> <model_deployment_name>")
        print("Or set AZURE_AI_PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME env vars.")
        sys.exit(2)

    client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

    existing = None
    try:
        for a in client.agents.list_agents():
            if getattr(a, "name", None) == agent_name:
                existing = a
                break
    except Exception:
        existing = None

    if existing is None:
        agent = client.agents.create_agent(
            model=deployment,
            name=agent_name,
            instructions="You are a helpful agent.",
            tools=[],
        )
        print(f"Created agent: {agent.name} ({agent.id})")
    else:
        agent = client.agents.get_agent(existing.id)
        print(f"Reusing agent: {agent.name} ({agent.id})")

    thread = client.agents.threads.create()
    client.agents.messages.create(thread_id=thread.id, role="user", content="Say hello and state today's date.")
    run = client.agents.runs.create(thread_id=thread.id, agent_id=agent.id)

    start = time.time()
    while True:
        r = client.agents.runs.get(thread_id=thread.id, run_id=run.id)
        if r.status in ["completed", "failed", "cancelled", "expired"]:
            break
        if time.time() - start > 120:
            raise TimeoutError("Run did not complete within 120s")
        time.sleep(1)

    msgs = client.agents.messages.list(thread_id=thread.id)
    text = None
    for m in msgs:
        if getattr(m, "role", "") == "assistant":
            if getattr(m, "content", None):
                for c in m.content:
                    if getattr(c, "text", None):
                        text = c.text.value
                        break
        if text:
            break

    print("Assistant:")
    print(text or "<no assistant message>")


if __name__ == "__main__":
    main()


