"""
Semantic Kernel Insurance Orchestrator

This module provides Semantic Kernel integration for insurance agents with custom orchestration logic.
It supports parallel agent execution and domain-specific routing for insurance workflows.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

try:
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    from semantic_kernel.core_plugins import TextPlugin
    from semantic_kernel.planning import SequentialPlanner
    from semantic_kernel.planning.basic_planner import BasicPlanner
    SEMANTIC_KERNEL_AVAILABLE = True
except ImportError:
    SEMANTIC_KERNEL_AVAILABLE = False
    logging.warning("Semantic Kernel not available")

from app.core.config import settings
from app.services.agent_tools import (
    AzureSearchTool,
    BingSearchTool,
    KnowledgeBaseTool,
    CodeInterpreterTool,
    FileSearchTool
)
from .insurance_agents import create_insurance_agent

logger = logging.getLogger(__name__)

class SemanticKernelInsuranceOrchestrator:
    """
    Semantic Kernel orchestrator for insurance agents
    
    This orchestrator uses Semantic Kernel to coordinate multiple insurance agents
    for policy analysis, claims processing, and customer support workflows.
    """
    
    def __init__(self):
        self.kernel = None
        self.agents = {}
        self.tools = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize the Semantic Kernel orchestrator"""
        try:
            if not SEMANTIC_KERNEL_AVAILABLE:
                raise ImportError("Semantic Kernel not available")
            
            # Initialize Semantic Kernel
            self.kernel = Kernel()
            
            # Add Azure OpenAI service
            if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
                chat_service = AzureChatCompletion(
                    service_id="insurance_chat",
                    deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                    endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY
                )
                self.kernel.add_service(chat_service)
            
            # Initialize tools
            await self._initialize_tools()
            
            # Initialize insurance agents
            await self._initialize_agents()
            
            # Add plugins to kernel
            await self._add_plugins_to_kernel()
            
            self._initialized = True
            logger.info("Semantic Kernel Insurance Orchestrator initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Semantic Kernel orchestrator: {e}")
            raise
    
    async def _initialize_tools(self):
        """Initialize agent tools"""
        try:
            # Initialize Azure Search tool
            self.tools["azure_search"] = AzureSearchTool()
            await self.tools["azure_search"].initialize()
            
            # Initialize Bing Search tool
            self.tools["bing_search"] = BingSearchTool()
            await self.tools["bing_search"].initialize()
            
            # Initialize Knowledge Base tool
            self.tools["knowledge_base"] = KnowledgeBaseTool()
            await self.tools["knowledge_base"].initialize()
            
            # Initialize Code Interpreter tool
            self.tools["code_interpreter"] = CodeInterpreterTool()
            await self.tools["code_interpreter"].initialize()
            
            # Initialize File Search tool
            self.tools["file_search"] = FileSearchTool()
            await self.tools["file_search"].initialize()
            
            logger.info("All agent tools initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize tools: {e}")
            raise
    
    async def _initialize_agents(self):
        """Initialize insurance agents"""
        try:
            # Create domain-specific agents with appropriate tools
            agent_configs = {
                "auto": {
                    "tools": ["azure_search", "knowledge_base", "code_interpreter", "file_search"],
                    "indexes": ["claims-documents", "policy-documents"]
                },
                "life": {
                    "tools": ["azure_search", "knowledge_base", "code_interpreter", "file_search"],
                    "indexes": ["policy-documents"]
                },
                "health": {
                    "tools": ["azure_search", "knowledge_base", "code_interpreter", "file_search"],
                    "indexes": ["claims-documents", "policy-documents"]
                },
                "dental": {
                    "tools": ["azure_search", "knowledge_base", "code_interpreter", "file_search"],
                    "indexes": ["claims-documents", "policy-documents"]
                },
                "general": {
                    "tools": ["azure_search", "knowledge_base", "code_interpreter", "file_search", "bing_search"],
                    "indexes": ["claims-documents", "policy-documents"]
                }
            }
            
            for domain, config in agent_configs.items():
                # Select tools for this agent
                agent_tools = [self.tools[tool_name] for tool_name in config["tools"]]
                
                # Create agent
                agent = create_insurance_agent(domain, agent_tools)
                await agent.initialize()
                
                self.agents[domain] = {
                    "agent": agent,
                    "config": config
                }
            
            logger.info(f"Initialized {len(self.agents)} insurance agents")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise
    
    async def _add_plugins_to_kernel(self):
        """Add agent plugins to Semantic Kernel"""
        try:
            # Add text plugin for basic text operations
            text_plugin = TextPlugin()
            self.kernel.import_plugin_from_object(text_plugin, "text")
            
            # Add custom insurance plugins
            await self._add_insurance_plugins()
            
            logger.info("Added plugins to Semantic Kernel")
            
        except Exception as e:
            logger.error(f"Failed to add plugins to kernel: {e}")
            raise
    
    async def _add_insurance_plugins(self):
        """Add insurance-specific plugins to the kernel"""
        try:
            # Create insurance analysis plugin
            insurance_plugin = await self._create_insurance_analysis_plugin()
            self.kernel.import_plugin_from_object(insurance_plugin, "insurance_analysis")
            
            # Create claims processing plugin
            claims_plugin = await self._create_claims_processing_plugin()
            self.kernel.import_plugin_from_object(claims_plugin, "claims_processing")
            
            # Create policy management plugin
            policy_plugin = await self._create_policy_management_plugin()
            self.kernel.import_plugin_from_object(policy_plugin, "policy_management")
            
        except Exception as e:
            logger.error(f"Failed to add insurance plugins: {e}")
            raise
    
    async def _create_insurance_analysis_plugin(self):
        """Create insurance analysis plugin"""
        class InsuranceAnalysisPlugin:
            def __init__(self, orchestrator):
                self.orchestrator = orchestrator
            
            async def analyze_policy(self, domain: str, policy_data: Dict[str, Any]) -> Dict[str, Any]:
                """Analyze insurance policy using domain-specific agent"""
                try:
                    if domain not in self.orchestrator.agents:
                        domain = "general"
                    
                    agent = self.orchestrator.agents[domain]["agent"]
                    
                    if domain == "auto":
                        return await agent.analyze_auto_policy(policy_data)
                    elif domain == "life":
                        return await agent.analyze_life_policy(policy_data)
                    else:
                        # Generic policy analysis
                        return {
                            "domain": domain,
                            "analysis_timestamp": datetime.utcnow().isoformat(),
                            "policy_data": policy_data,
                            "analysis_type": "generic"
                        }
                        
                except Exception as e:
                    logger.error(f"Policy analysis failed: {e}")
                    return {"error": str(e), "domain": domain}
            
            async def process_claim(self, domain: str, claim_data: Dict[str, Any]) -> Dict[str, Any]:
                """Process insurance claim using domain-specific agent"""
                try:
                    if domain not in self.orchestrator.agents:
                        domain = "general"
                    
                    agent = self.orchestrator.agents[domain]["agent"]
                    
                    if domain == "auto":
                        return await agent.process_auto_claim(claim_data)
                    else:
                        # Generic claim processing
                        return {
                            "domain": domain,
                            "processing_timestamp": datetime.utcnow().isoformat(),
                            "claim_data": claim_data,
                            "processing_type": "generic"
                        }
                        
                except Exception as e:
                    logger.error(f"Claim processing failed: {e}")
                    return {"error": str(e), "domain": domain}
        
        return InsuranceAnalysisPlugin(self)
    
    async def _create_claims_processing_plugin(self):
        """Create claims processing plugin"""
        class ClaimsProcessingPlugin:
            def __init__(self, orchestrator):
                self.orchestrator = orchestrator
            
            async def validate_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
                """Validate insurance claim"""
                try:
                    # Use knowledge base tool to validate claim
                    kb_tool = self.orchestrator.tools["knowledge_base"]
                    
                    # Search for similar claims
                    similar_claims = await kb_tool.search_claims(
                        query=claim_data.get("description", ""),
                        max_results=5
                    )
                    
                    validation = {
                        "is_valid": True,
                        "validation_timestamp": datetime.utcnow().isoformat(),
                        "similar_claims_found": len(similar_claims.get("results", [])),
                        "validation_notes": []
                    }
                    
                    # Add validation logic here
                    if not claim_data.get("date_of_loss"):
                        validation["is_valid"] = False
                        validation["validation_notes"].append("Missing date of loss")
                    
                    if not claim_data.get("description"):
                        validation["is_valid"] = False
                        validation["validation_notes"].append("Missing claim description")
                    
                    return validation
                    
                except Exception as e:
                    logger.error(f"Claim validation failed: {e}")
                    return {"error": str(e)}
            
            async def calculate_settlement(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
                """Calculate claim settlement amount"""
                try:
                    # Use code interpreter for calculations
                    code_tool = self.orchestrator.tools["code_interpreter"]
                    
                    # Calculate settlement based on claim data
                    calculation_code = f"""
# Calculate settlement amount
damage_estimate = {claim_data.get('damage_estimate', 0)}
deductible = {claim_data.get('deductible', 500)}
coverage_limit = {claim_data.get('coverage_limit', 10000)}

# Apply deductible
settlement_amount = max(0, damage_estimate - deductible)

# Apply coverage limit
settlement_amount = min(settlement_amount, coverage_limit)

print(f"Settlement calculation:")
print(f"Damage estimate: ${damage_estimate:,.2f}")
print(f"Deductible: ${deductible:,.2f}")
print(f"Coverage limit: ${coverage_limit:,.2f}")
print(f"Recommended settlement: ${settlement_amount:,.2f}")
"""
                    
                    result = await code_tool.execute_code(calculation_code)
                    
                    return {
                        "settlement_calculation": result,
                        "calculation_timestamp": datetime.utcnow().isoformat(),
                        "claim_data": claim_data
                    }
                    
                except Exception as e:
                    logger.error(f"Settlement calculation failed: {e}")
                    return {"error": str(e)}
        
        return ClaimsProcessingPlugin(self)
    
    async def _create_policy_management_plugin(self):
        """Create policy management plugin"""
        class PolicyManagementPlugin:
            def __init__(self, orchestrator):
                self.orchestrator = orchestrator
            
            async def search_policies(self, query: str, domain: str = None) -> Dict[str, Any]:
                """Search for policies"""
                try:
                    # Use Azure Search tool
                    search_tool = self.orchestrator.tools["azure_search"]
                    
                    # Determine which indexes to search
                    indexes = ["policy-documents"]
                    if domain and domain in self.orchestrator.agents:
                        indexes = self.orchestrator.agents[domain]["config"]["indexes"]
                    
                    search_results = await search_tool.hybrid_search(
                        query=query,
                        indexes=indexes,
                        max_results=10
                    )
                    
                    return {
                        "search_results": search_results,
                        "search_timestamp": datetime.utcnow().isoformat(),
                        "domain": domain,
                        "indexes_searched": indexes
                    }
                    
                except Exception as e:
                    logger.error(f"Policy search failed: {e}")
                    return {"error": str(e)}
            
            async def analyze_policy_coverage(self, policy_id: str) -> Dict[str, Any]:
                """Analyze policy coverage"""
                try:
                    # Use knowledge base tool
                    kb_tool = self.orchestrator.tools["knowledge_base"]
                    
                    # Get policy details
                    policy_details = await kb_tool.get_document(policy_id)
                    
                    # Use code interpreter for coverage analysis
                    code_tool = self.orchestrator.tools["code_interpreter"]
                    
                    analysis_code = f"""
# Analyze policy coverage
policy_data = {policy_details}

# Extract coverage information
coverage_types = policy_data.get('coverage', {{}})
total_coverage = sum(coverage_types.values()) if isinstance(coverage_types, dict) else 0

print(f"Policy Coverage Analysis:")
print(f"Policy ID: {policy_id}")
print(f"Coverage types: {list(coverage_types.keys()) if isinstance(coverage_types, dict) else 'N/A'}")
print(f"Total coverage: ${total_coverage:,.2f}")
"""
                    
                    result = await code_tool.execute_code(analysis_code)
                    
                    return {
                        "coverage_analysis": result,
                        "policy_details": policy_details,
                        "analysis_timestamp": datetime.utcnow().isoformat()
                    }
                    
                except Exception as e:
                    logger.error(f"Coverage analysis failed: {e}")
                    return {"error": str(e)}
        
        return PolicyManagementPlugin(self)
    
    async def orchestrate_workflow(
        self, 
        workflow_type: str,
        input_data: Dict[str, Any],
        parallel_execution: bool = True
    ) -> Dict[str, Any]:
        """
        Orchestrate insurance workflow using Semantic Kernel
        
        Args:
            workflow_type: "policy_analysis", "claims_processing", "customer_support"
            input_data: Input data for the workflow
            parallel_execution: Whether to execute agents in parallel
            
        Returns:
            Workflow results
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            workflow_start = datetime.utcnow()
            
            # Create workflow plan
            plan = await self._create_workflow_plan(workflow_type, input_data)
            
            # Execute workflow
            if parallel_execution:
                results = await self._execute_parallel_workflow(plan, input_data)
            else:
                results = await self._execute_sequential_workflow(plan, input_data)
            
            workflow_end = datetime.utcnow()
            
            return {
                "workflow_type": workflow_type,
                "workflow_start": workflow_start.isoformat(),
                "workflow_end": workflow_end.isoformat(),
                "execution_time": (workflow_end - workflow_start).total_seconds(),
                "parallel_execution": parallel_execution,
                "results": results,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Workflow orchestration failed: {e}")
            return {
                "workflow_type": workflow_type,
                "error": str(e),
                "status": "failed"
            }
    
    async def _create_workflow_plan(self, workflow_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create workflow plan using Semantic Kernel planner"""
        try:
            # Create planner
            planner = SequentialPlanner(self.kernel)
            
            # Define workflow goals based on type
            if workflow_type == "policy_analysis":
                goal = f"Analyze insurance policy for domain: {input_data.get('domain', 'general')}"
            elif workflow_type == "claims_processing":
                goal = f"Process insurance claim for domain: {input_data.get('domain', 'general')}"
            elif workflow_type == "customer_support":
                goal = f"Provide customer support for insurance inquiry: {input_data.get('question', '')}"
            else:
                goal = f"Execute {workflow_type} workflow"
            
            # Create plan
            plan = await planner.create_plan(goal)
            
            return {
                "goal": goal,
                "plan": plan,
                "workflow_type": workflow_type
            }
            
        except Exception as e:
            logger.error(f"Failed to create workflow plan: {e}")
            return {
                "goal": "Execute workflow",
                "plan": None,
                "workflow_type": workflow_type,
                "error": str(e)
            }
    
    async def _execute_parallel_workflow(self, plan: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow with parallel agent execution"""
        try:
            # Determine which agents to involve
            domain = input_data.get('domain', 'general')
            involved_agents = [domain]
            
            # Add general agent as fallback
            if domain != 'general':
                involved_agents.append('general')
            
            # Execute agents in parallel
            tasks = []
            for agent_domain in involved_agents:
                if agent_domain in self.agents:
                    task = self._execute_agent_task(agent_domain, plan, input_data)
                    tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            processed_results = {}
            for i, result in enumerate(results):
                agent_domain = involved_agents[i]
                if isinstance(result, Exception):
                    processed_results[agent_domain] = {"error": str(result)}
                else:
                    processed_results[agent_domain] = result
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Parallel workflow execution failed: {e}")
            return {"error": str(e)}
    
    async def _execute_sequential_workflow(self, plan: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow with sequential agent execution"""
        try:
            # Execute plan using Semantic Kernel
            if plan.get("plan"):
                result = await plan["plan"].invoke(input_data)
                return {
                    "plan_execution": result,
                    "execution_type": "sequential"
                }
            else:
                # Fallback to direct agent execution
                domain = input_data.get('domain', 'general')
                if domain in self.agents:
                    agent = self.agents[domain]["agent"]
                    return await self._execute_agent_task(domain, plan, input_data)
                else:
                    return {"error": f"No agent available for domain: {domain}"}
                    
        except Exception as e:
            logger.error(f"Sequential workflow execution failed: {e}")
            return {"error": str(e)}
    
    async def _execute_agent_task(self, domain: str, plan: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task for specific agent"""
        try:
            agent = self.agents[domain]["agent"]
            workflow_type = plan.get("workflow_type", "general")
            
            if workflow_type == "policy_analysis":
                return await agent.analyze_auto_policy(input_data) if domain == "auto" else {"domain": domain, "analysis_type": "generic"}
            elif workflow_type == "claims_processing":
                return await agent.process_auto_claim(input_data) if domain == "auto" else {"domain": domain, "processing_type": "generic"}
            else:
                return {"domain": domain, "task_type": "general", "input_data": input_data}
                
        except Exception as e:
            logger.error(f"Agent task execution failed for {domain}: {e}")
            return {"error": str(e), "domain": domain}
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "initialized": self._initialized,
            "agents_available": list(self.agents.keys()),
            "tools_available": list(self.tools.keys()),
            "semantic_kernel_available": SEMANTIC_KERNEL_AVAILABLE,
            "timestamp": datetime.utcnow().isoformat()
        }
