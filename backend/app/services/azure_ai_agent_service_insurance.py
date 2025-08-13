from typing import Dict, Any, List
import logging
from datetime import datetime

try:
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import BingGroundingTool
    AZURE_AI_PROJECTS_AVAILABLE = True
except Exception:
    AIProjectClient = None
    BingGroundingTool = None
    AZURE_AI_PROJECTS_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)

class InsuranceAIAgentService:
    """Domain-specific Azure AI Agent helpers for Insurance (policies and claims)."""

    def __init__(self, project_client):
        self.client = project_client
        self.tools: List[Any] = self._initialize_tools()

    def _initialize_tools(self) -> List[Any]:
        tools: List[Any] = []
        try:
            # Attach Bing Web Search tool if connection configured
            if BingGroundingTool is not None:
                import os
                conn_id = os.getenv("BING_CONNECTION_NAME") or os.getenv("BING_CONNECTION_ID")
                if conn_id:
                    bing = BingGroundingTool(connection_id=conn_id)
                    if hasattr(bing, "definitions"):
                        tools += bing.definitions
                    else:
                        tools.append(bing)
                    logger.info("Insurance agents: Bing grounding tool enabled")
        except Exception as e:
            logger.warning(f"Insurance agents: Bing tool init skipped: {e}")
        return tools

    async def find_or_create_agent(self, agent_name: str, instructions: str, model_deployment: str) -> Any:
        """Create or reuse an insurance agent with common tools."""
        try:
            agents = []
            try:
                agents = self.client.agents.list_agents()
            except Exception:
                agents = []
            for a in agents:
                if getattr(a, "name", None) == agent_name:
                    return self.client.agents.get_agent(a.id)
            agent = self.client.agents.create_agent(
                model=model_deployment,
                name=agent_name,
                instructions=instructions,
                tools=self.tools
            )
            return agent
        except Exception as e:
            logger.error(f"Insurance agent creation failed for {agent_name}: {e}")
            raise

    async def ensure_insurance_chat_agent(self, deployment: str) -> Any:
        return await self.find_or_create_agent(
            agent_name="Insurance_Chat_Agent",
            instructions=(
                "You are an insurance assistant. Answer policy and claims questions clearly and cite applicable policy clauses "
                "and claim notes when provided."
            ),
            model_deployment=deployment,
        )

    async def ensure_insurance_kb_manager_agent(self, deployment: str) -> Any:
        return await self.find_or_create_agent(
            agent_name="Insurance_KB_Manager_Agent",
            instructions=(
                "You manage insurance knowledge retrieval. Target policy and claims indexes, select most relevant clauses and claim notes, "
                "merge and deduplicate results, detect clause conflicts, and explain retrieval choices."
            ),
            model_deployment=deployment,
        )

    async def ensure_insurance_qa_agent(self, verification_level: str, deployment: str) -> Any:
        name = f"Insurance_QA_Agent_{verification_level.title()}"
        instructions = (
            "You are an insurance QA analyst specializing in policies and claims.\n\n"
            "Tasks:\n"
            "1. Retrieve relevant policy clauses (coverage, exclusions, endorsements, limits).\n"
            "2. Retrieve relevant claim notes, adjuster summaries, and FNOL details.\n"
            "3. Answer comprehensively and cite sections and claim references.\n"
            "4. Identify missing documentation and potential fraud indicators.\n"
            "5. State confidence based on source quality."
        )
        return await self.find_or_create_agent(name, instructions, deployment)

    async def ensure_insurance_content_agent(self, deployment: str) -> Any:
        return await self.find_or_create_agent(
            agent_name="Insurance_Content_Agent",
            instructions=(
                "You create insurance content: coverage summaries, claim decision letters, customer notices, and internal memos.\n"
                "Include precise references to policy numbers, sections, and claim IDs where relevant. Maintain compliance tone."
            ),
            model_deployment=deployment,
        )

