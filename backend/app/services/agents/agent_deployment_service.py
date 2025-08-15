"""
Agent Deployment Service for Azure AI Foundry

This service handles deploying agents with integrated tools using the new Azure AI Foundry project-based approach.
- Azure AI Search tools
- Bing Search tools for grounding
- Knowledge Base tools
- Code interpreter
- File Search

Based on Azure AI Foundry documentation:
https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/azure-ai-search?tabs=pythonsdk
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import Agent, AgentTool, AzureAISearchConnection
    from azure.identity import DefaultAzureCredential
    AZURE_AI_ML_AVAILABLE = True
except ImportError:
    AZURE_AI_ML_AVAILABLE = False
    # Create mock classes for type annotations
    class Agent:
        def __init__(self, name: str, description: str, tools: List, instructions: str):
            self.name = name
            self.description = description
            self.tools = tools
            self.instructions = instructions
            self.id = f"mock-{name}"
    
    class AgentTool:
        def __init__(self, name: str, description: str, type: str):
            self.name = name
            self.description = description
            self.type = type
    
    class AzureAISearchConnection:
        def __init__(self, name: str, endpoint: str, api_key: str):
            self.name = name
            self.endpoint = endpoint
            self.api_key = api_key
    
    logger.warning("Azure AI ML SDK not available, using mock implementation")

from app.core.config import settings
from app.services.azure_services import AzureServiceManager
from app.services.agent_tools.azure_search_tool import AzureSearchTool
from app.services.agent_tools.bing_search_tool import BingSearchTool
from app.services.agent_tools.knowledge_base_tool import KnowledgeBaseTool

class AgentDeploymentService:
    """
    Service for deploying Azure AI Foundry agents with integrated tools using project-based approach
    """
    
    def __init__(self):
        self.azure_manager = None
        self.project_client = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the agent deployment service"""
        try:
            if not AZURE_AI_ML_AVAILABLE:
                logger.warning("Azure AI ML SDK not available, using mock agent deployment service")
                return
                
            # Initialize Azure Service Manager (uses project-based approach)
            self.azure_manager = AzureServiceManager()
            await self.azure_manager.initialize()
            
            # Get project client (new approach - no workspace needed)
            self.project_client = self.azure_manager.get_project_client()
            
            self._initialized = True
            logger.info("Agent deployment service initialized with project-based approach")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent deployment service: {e}")
            raise
    
    async def deploy_financial_qa_agent(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Deploy a financial QA agent with Azure AI Search and Bing tools
        
        Args:
            agent_name: Name for the agent (optional)
            
        Returns:
            Deployment result with agent details
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            agent_name = agent_name or "financial-qa-agent"
            
            # Create connections for tools
            connections = await self._create_agent_connections(agent_name)
            
            # Create tools
            tools = await self._create_agent_tools(agent_name, connections)
            
            # Create agent with tools
            agent = await self._create_agent_with_tools(agent_name, tools)
            
            # Deploy the agent
            deployment_result = await self._deploy_agent(agent)
            
            return {
                "agent_name": agent_name,
                "deployment_status": "success",
                "agent_id": deployment_result.get("agent_id"),
                "tools": [tool.get_tool_schema() for tool in tools],
                "connections": connections,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy financial QA agent: {e}")
            return {
                "agent_name": agent_name,
                "deployment_status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def deploy_insurance_agent(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Deploy an insurance agent with specialized tools for policy and claims
        
        Args:
            agent_name: Name for the agent (optional)
            
        Returns:
            Deployment result with agent details
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            agent_name = agent_name or "insurance-agent"
            
            # Create connections for tools
            connections = await self._create_agent_connections(agent_name)
            
            # Create specialized insurance tools
            tools = await self._create_insurance_tools(agent_name, connections)
            
            # Create agent with tools
            agent = await self._create_agent_with_tools(agent_name, tools)
            
            # Deploy the agent
            deployment_result = await self._deploy_agent(agent)
            
            return {
                "agent_name": agent_name,
                "deployment_status": "success",
                "agent_id": deployment_result.get("agent_id"),
                "tools": [tool.get_tool_schema() for tool in tools],
                "connections": connections,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy insurance agent: {e}")
            return {
                "agent_name": agent_name,
                "deployment_status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _create_agent_connections(self, agent_name: str) -> Dict[str, str]:
        """Create connections for agent tools"""
        connections = {}
        
        try:
            # Create Azure AI Search connection using project client
            search_connection = AzureAISearchConnection(
                name=f"{agent_name}-search-connection",
                endpoint=settings.AZURE_AI_SEARCH_ENDPOINT,
                api_key=settings.AZURE_SEARCH_API_KEY
            )
            
            self.project_client.connections.create_or_update(search_connection)
            connections["azure_search"] = f"{agent_name}-search-connection"
            logger.info(f"Created Azure AI Search connection: {connections['azure_search']}")
            
        except Exception as e:
            logger.warning(f"Failed to create Azure AI Search connection: {e}")
        
        return connections
    
    async def _create_agent_tools(self, agent_name: str, connections: Dict[str, str]) -> List[Any]:
        """Create tools for the agent"""
        tools = []
        
        # Azure AI Search tool
        try:
            search_tool = AzureSearchTool(connection_name=connections.get("azure_search"))
            await search_tool.initialize()
            tools.append(search_tool)
            logger.info("Added Azure AI Search tool to agent")
        except Exception as e:
            logger.warning(f"Failed to add Azure AI Search tool: {e}")
        
        # Bing Search tool
        try:
            bing_tool = BingSearchTool()
            await bing_tool.initialize()
            tools.append(bing_tool)
            logger.info("Added Bing Search tool to agent")
        except Exception as e:
            logger.warning(f"Failed to add Bing Search tool: {e}")
        
        # Knowledge Base tool
        try:
            kb_tool = KnowledgeBaseTool()
            await kb_tool.initialize()
            tools.append(kb_tool)
            logger.info("Added Knowledge Base tool to agent")
        except Exception as e:
            logger.warning(f"Failed to add Knowledge Base tool: {e}")
        
        return tools
    
    async def _create_insurance_tools(self, agent_name: str, connections: Dict[str, str]) -> List[Any]:
        """Create specialized tools for insurance agent"""
        tools = []
        
        # Azure AI Search tool (specialized for insurance)
        try:
            search_tool = AzureSearchTool(connection_name=connections.get("azure_search"))
            await search_tool.initialize()
            tools.append(search_tool)
            logger.info("Added Azure AI Search tool to insurance agent")
        except Exception as e:
            logger.warning(f"Failed to add Azure AI Search tool: {e}")
        
        # Knowledge Base tool (specialized for insurance)
        try:
            kb_tool = KnowledgeBaseTool()
            await kb_tool.initialize()
            tools.append(kb_tool)
            logger.info("Added Knowledge Base tool to insurance agent")
        except Exception as e:
            logger.warning(f"Failed to add Knowledge Base tool: {e}")
        
        return tools
    
    async def _create_agent_with_tools(self, agent_name: str, tools: List[Any]) -> Agent:
        """Create an agent with integrated tools"""
        try:
            # Convert tools to AgentTool format
            agent_tools = []
            for tool in tools:
                tool_schema = tool.get_tool_schema()
                agent_tool = AgentTool(
                    name=tool_schema["name"],
                    description=tool_schema["description"],
                    type=tool_schema["type"]
                )
                agent_tools.append(agent_tool)
            
            # Create agent configuration
            agent = Agent(
                name=agent_name,
                description=f"AI agent with integrated tools for {agent_name}",
                tools=agent_tools,
                instructions=self._get_agent_instructions(agent_name)
            )
            
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent with tools: {e}")
            raise
    
    async def _deploy_agent(self, agent: Agent) -> Dict[str, Any]:
        """Deploy the agent to Azure AI Foundry"""
        try:
            # Deploy agent using project client (new approach)
            deployment = self.project_client.agents.create_or_update(agent)
            
            return {
                "agent_id": deployment.id,
                "agent_name": deployment.name,
                "status": "deployed",
                "deployment_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy agent: {e}")
            raise
    
    def _get_agent_instructions(self, agent_name: str) -> str:
        """Get agent instructions based on agent type"""
        if "financial" in agent_name.lower():
            return """
            You are a Financial QA Agent with access to Azure AI Search and Bing Search tools.
            
            Your capabilities include:
            - Searching financial documents and SEC filings
            - Retrieving current market information via web search
            - Analyzing financial data and providing insights
            - Verifying financial facts and figures
            
            When answering questions:
            1. Use Azure AI Search to find relevant financial documents
            2. Use Bing Search to get current market information
            3. Combine information from both sources for comprehensive answers
            4. Always cite your sources
            5. Be precise with financial data and calculations
            """
        elif "insurance" in agent_name.lower():
            return """
            You are an Insurance Agent with access to policy and claims data.
            
            Your capabilities include:
            - Searching insurance policies and claims documents
            - Managing knowledge base operations
            - Providing policy information and claims assistance
            - Analyzing insurance data and trends
            
            When answering questions:
            1. Use Azure AI Search to find relevant policy and claims documents
            2. Use Knowledge Base tools to manage document operations
            3. Provide accurate policy information and claims guidance
            4. Always maintain confidentiality of sensitive information
            5. Follow insurance industry best practices
            """
        else:
            return """
            You are an AI Agent with integrated tools for enhanced functionality.
            
            Your capabilities include:
            - Searching documents and knowledge bases
            - Web search for current information
            - Knowledge base management operations
            
            When answering questions:
            1. Use available tools to gather relevant information
            2. Provide comprehensive and accurate answers
            3. Cite your sources when possible
            4. Be helpful and professional in your responses
            """
    
    async def list_deployed_agents(self) -> List[Dict[str, Any]]:
        """List all deployed agents"""
        try:
            if not self._initialized:
                await self.initialize()
            
            agents = []
            for agent in self.project_client.agents.list():
                agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0,
                    "status": "active"
                })
            
            return agents
            
        except Exception as e:
            logger.error(f"Failed to list deployed agents: {e}")
            return []
    
    async def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get status of a specific agent"""
        try:
            if not self._initialized:
                await self.initialize()
            
            agent = self.project_client.agents.get(agent_name)
            
            return {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "tools": [tool.name for tool in agent.tools] if hasattr(agent, 'tools') else [],
                "status": "active",
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")
            return {
                "name": agent_name,
                "status": "not_found",
                "error": str(e)
            }
