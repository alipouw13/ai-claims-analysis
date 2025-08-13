import logging
from typing import Dict, Any, List

from app.services.azure_services import AzureServiceManager
from app.services.knowledge_base_manager_insurance import InsuranceKnowledgeBaseManager
from app.services.azure_ai_agent_service_insurance import InsuranceAIAgentService

logger = logging.getLogger(__name__)

class InsuranceMultiAgentOrchestrator:
    """Insurance domain orchestrator that mirrors the financial orchestrator but uses insurance agents and KB manager."""

    def __init__(self, azure_manager: AzureServiceManager, kb_manager: InsuranceKnowledgeBaseManager):
        self.azure_manager = azure_manager
        self.kb_manager = kb_manager
        self.agents: Dict[str, Any] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        project_client = self.azure_manager.get_project_client()
        self.agent_service = InsuranceAIAgentService(project_client)
        self.agents['chat'] = 'Insurance_Chat_Agent'
        self.agents['kb_manager'] = 'Insurance_KB_Manager_Agent'
        self.agents['qa_basic'] = 'Insurance_QA_Agent_Basic'
        self.agents['qa_thorough'] = 'Insurance_QA_Agent_Thorough'
        self.agents['qa_comprehensive'] = 'Insurance_QA_Agent_Comprehensive'
        self.agents['content'] = 'Insurance_Content_Agent'
        logger.info("Initialized insurance agent names")

    async def process_qa(self, question: str, verification_level: str, session_id: str, model_config: Dict[str, Any]):
        # Retrieve context using insurance KB
        search_results = await self.kb_manager.search_knowledge_base(
            query=question,
            filters=model_config.get('filters'),
            top_k=10,
        )
        # Pick QA agent by level
        level = (verification_level or 'thorough').lower()
        agent_name = self.agents['qa_thorough']
        if level == 'basic':
            agent_name = self.agents['qa_basic']
        elif level == 'comprehensive':
            agent_name = self.agents['qa_comprehensive']

        # Ensure agent exists
        await self.agent_service.ensure_insurance_qa_agent(level, model_config.get('chat_deployment'))

        # Build context
        retrieved_context = "\n\n".join([r.get('content','')[:1000] for r in search_results])
        instructions = (
            "Use the retrieved policy clauses and claim notes to answer. Cite explicit section numbers and claim IDs."
        )
        # Run via chat agent pattern (simple path; full agent run could be added as needed)
        chat_agent = await self.agent_service.ensure_insurance_chat_agent(model_config.get('chat_deployment'))
        # Fallback to direct AOAI is handled elsewhere; here we return context and let caller drive
        return {
            'agent_name': agent_name,
            'context': retrieved_context,
            'sources': search_results,
            'instructions': instructions,
        }

