"""
Agent Deployment API Routes

This module provides API endpoints for deploying Azure AI Foundry agents
with integrated tools including Azure AI Search and Bing grounding.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from app.core.observability import observability
from app.services.agents.agent_deployment_service import AgentDeploymentService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/deploy/financial-qa")
async def deploy_financial_qa_agent(request: Request, agent_name: Optional[str] = None):
    """
    Deploy a financial QA agent with Azure AI Search and Bing tools
    """
    try:
        observability.track_request("deploy_financial_qa_agent")
        
        deployment_service = AgentDeploymentService()
        result = await deployment_service.deploy_financial_qa_agent(agent_name)
        
        if result.get("deployment_status") == "success":
            logger.info(f"Successfully deployed financial QA agent: {result.get('agent_name')}")
            return {
                "message": "Financial QA agent deployed successfully",
                "agent": result
            }
        else:
            logger.error(f"Failed to deploy financial QA agent: {result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to deploy agent: {result.get('error')}"
            )
            
    except Exception as e:
        logger.error(f"Error deploying financial QA agent: {e}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

@router.post("/deploy/insurance")
async def deploy_insurance_agent(request: Request, agent_name: Optional[str] = None):
    """
    Deploy an insurance agent with specialized tools for policy and claims
    """
    try:
        observability.track_request("deploy_insurance_agent")
        
        deployment_service = AgentDeploymentService()
        result = await deployment_service.deploy_insurance_agent(agent_name)
        
        if result.get("deployment_status") == "success":
            logger.info(f"Successfully deployed insurance agent: {result.get('agent_name')}")
            return {
                "message": "Insurance agent deployed successfully",
                "agent": result
            }
        else:
            logger.error(f"Failed to deploy insurance agent: {result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to deploy agent: {result.get('error')}"
            )
            
    except Exception as e:
        logger.error(f"Error deploying insurance agent: {e}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

@router.get("/list")
async def list_deployed_agents(request: Request):
    """
    List all deployed agents
    """
    try:
        observability.track_request("list_deployed_agents")
        
        deployment_service = AgentDeploymentService()
        agents = await deployment_service.list_deployed_agents()
        
        return {
            "agents": agents,
            "total_count": len(agents),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing deployed agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")

@router.get("/status/{agent_name}")
async def get_agent_status(request: Request, agent_name: str):
    """
    Get status of a specific agent
    """
    try:
        observability.track_request("get_agent_status")
        
        deployment_service = AgentDeploymentService()
        status = await deployment_service.get_agent_status(agent_name)
        
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")

@router.get("/tools/schemas")
async def get_tool_schemas(request: Request):
    """
    Get schemas for all available agent tools
    """
    try:
        observability.track_request("get_tool_schemas")
        
        from app.services.agent_tools.azure_search_tool import AzureSearchTool
        from app.services.agent_tools.bing_search_tool import BingSearchTool
        from app.services.agent_tools.knowledge_base_tool import KnowledgeBaseTool
        
        tools = [
            AzureSearchTool(),
            BingSearchTool(),
            KnowledgeBaseTool()
        ]
        
        schemas = [tool.get_tool_schema() for tool in tools]
        
        return {
            "tools": schemas,
            "total_tools": len(schemas),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting tool schemas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tool schemas: {str(e)}")

@router.post("/deploy/custom")
async def deploy_custom_agent(
    request: Request,
    agent_name: str,
    agent_type: str,
    tools: List[str] = None,
    instructions: Optional[str] = None
):
    """
    Deploy a custom agent with specified tools and instructions
    """
    try:
        observability.track_request("deploy_custom_agent")
        
        deployment_service = AgentDeploymentService()
        
        # Validate agent type
        if agent_type not in ["financial", "insurance", "general"]:
            raise HTTPException(
                status_code=400, 
                detail="Agent type must be 'financial', 'insurance', or 'general'"
            )
        
        # Deploy based on type
        if agent_type == "financial":
            result = await deployment_service.deploy_financial_qa_agent(agent_name)
        elif agent_type == "insurance":
            result = await deployment_service.deploy_insurance_agent(agent_name)
        else:
            # For general agents, use financial as default
            result = await deployment_service.deploy_financial_qa_agent(agent_name)
        
        if result.get("deployment_status") == "success":
            logger.info(f"Successfully deployed custom agent: {result.get('agent_name')}")
            return {
                "message": f"Custom {agent_type} agent deployed successfully",
                "agent": result
            }
        else:
            logger.error(f"Failed to deploy custom agent: {result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to deploy agent: {result.get('error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying custom agent: {e}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")
