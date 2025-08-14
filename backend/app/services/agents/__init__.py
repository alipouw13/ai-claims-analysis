"""
Agents Package

This package contains Azure AI Foundry agents with integrated tools
for enhanced functionality including Azure AI Search and Bing grounding.
"""

from .azure_ai_agent_service import AzureAIAgentService
# InsuranceAIAgentService removed - using Semantic Kernel orchestrator instead
from .multi_agent_orchestrator import MultiAgentOrchestrator
from .multi_agent_insurance_orchestrator import SemanticKernelInsuranceOrchestrator
from .agentic_vector_rag_service import AgenticVectorRAGService
from .agent_deployment_service import AgentDeploymentService

from .insurance_agents import (
    InsuranceAgentBase,
    AutoInsuranceAgent,
    LifeInsuranceAgent,
    HealthInsuranceAgent,
    DentalInsuranceAgent,
    GeneralInsuranceAgent,
    create_insurance_agent
)

__all__ = [
    "AzureAIAgentService",
    "InsuranceAIAgentService", 
    "MultiAgentOrchestrator",
    "SemanticKernelInsuranceOrchestrator",
    "AgenticVectorRAGService",
    "AgentDeploymentService",

    "InsuranceAgentBase",
    "AutoInsuranceAgent",
    "LifeInsuranceAgent",
    "HealthInsuranceAgent",
    "DentalInsuranceAgent",
    "GeneralInsuranceAgent",
    "create_insurance_agent"
]
