#!/usr/bin/env python3
"""
Financial & Insurance Analysis MCP Server

A Model Context Protocol (MCP) server for dual-domain financial and insurance 
analysis using our RAG system. This server implements the MCP specification
and can be used by Claude, VS Code, and other MCP clients for both banking
and insurance workflows.

Protocol: https://spec.modelcontextprotocol.io/
"""

import asyncio
import json
import logging
import sys
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

# Fix Windows event loop policy for aiodns compatibility
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Add the parent directory to the Python path to import our backend modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

try:
    from backend.app.services.azure_services import AzureServiceManager
    from backend.app.services.knowledge_base_manager import AdaptiveKnowledgeBaseManager
    from backend.app.services.multi_agent_orchestrator import MultiAgentOrchestrator, AgentType
    from backend.app.services.rag_pipeline import RAGPipeline
    from backend.app.services.agents.multi_agent_insurance_orchestrator import SemanticKernelInsuranceOrchestrator
    from backend.app.services.agents.insurance_agents import create_insurance_agent
    from backend.app.core.config import settings
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running from the project root or the backend is properly set up")
    sys.exit(1)

# MCP Protocol structures
class MCPRequest:
    def __init__(self, id: str, method: str, params: Optional[Dict[str, Any]] = None):
        self.id = id
        self.method = method
        self.params = params or {}

class MCPResponse:
    def __init__(self, id: str, result: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None):
        self.id = id
        self.result = result
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        response = {"jsonrpc": "2.0", "id": self.id}
        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response

class FinancialInsuranceMCPServer:
    """
    MCP Server for Financial & Insurance Analysis System following MCP Protocol specification
    Supports both banking/financial analysis and insurance claims processing
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.azure_manager: Optional[AzureServiceManager] = None
        self.kb_manager: Optional[AdaptiveKnowledgeBaseManager] = None
        self.orchestrator: Optional[MultiAgentOrchestrator] = None
        self.rag_pipeline: Optional[RAGPipeline] = None
        self.insurance_orchestrator: Optional[SemanticKernelInsuranceOrchestrator] = None
        self.initialized = False
        
        # MCP server info
        self.server_info = {
            "name": "financial-insurance-analysis-server",
            "version": "1.0.0",
            "description": "Dual-domain Financial & Insurance Analysis using RAG and Multi-Agent System",
            "author": "AI Financial & Insurance Platform Team",
            "license": "MIT",
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
                "logging": True
            }
        }
        
    async def initialize(self):
        """Initialize the MCP server components"""
        try:
            self.logger.info("Initializing Financial RAG MCP Server...")
            
            # Initialize Azure services
            self.azure_manager = AzureServiceManager()
            await self.azure_manager.initialize()
            
            # Initialize knowledge base manager (no initialize method needed)
            self.kb_manager = AdaptiveKnowledgeBaseManager(self.azure_manager)
            
            # Initialize multi-agent orchestrator
            self.orchestrator = MultiAgentOrchestrator(self.azure_manager)
            await self.orchestrator.initialize()
            
            # Initialize RAG pipeline
            self.rag_pipeline = RAGPipeline(self.azure_manager)
            await self.rag_pipeline.initialize()
            
            # Initialize insurance orchestrator
            self.insurance_orchestrator = SemanticKernelInsuranceOrchestrator()
            await self.insurance_orchestrator.initialize()
            
            self.initialized = True
            self.logger.info("✅ Financial RAG MCP Server initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize MCP server: {e}", exc_info=True)
            raise
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Return list of available MCP tools for both banking and insurance domains"""
        return [
            # Banking & Financial Analysis Tools
            {
                "name": "analyze_financial_documents",
                "description": "Comprehensive SEC filing and financial statement analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "documents": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of financial documents to analyze (CIK numbers, filing URLs, or document IDs)"
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["quick", "standard", "comprehensive"],
                            "description": "Depth of financial analysis",
                            "default": "standard"
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific financial metrics to extract",
                            "default": []
                        }
                    },
                    "required": ["documents"]
                }
            },
            {
                "name": "search_financial_database",
                "description": "Financial document search and investment research",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for financial documents"
                        },
                        "document_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types of financial documents to search (10-K, 10-Q, 8-K, etc.)",
                            "default": []
                        },
                        "companies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Company names or ticker symbols to filter by",
                            "default": []
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "extract_financial_metrics",
                "description": "AI-powered extraction of key financial indicators and ratios",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "company": {
                            "type": "string",
                            "description": "Company name or ticker symbol"
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific metrics to extract (revenue, profit margins, debt ratios, etc.)"
                        },
                        "time_period": {
                            "type": "string",
                            "description": "Time period for metrics (latest, annual, quarterly)",
                            "default": "latest"
                        }
                    },
                    "required": ["company", "metrics"]
                }
            },
            {
                "name": "compare_companies",
                "description": "Multi-company financial comparison and peer analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "companies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of companies to compare (names or ticker symbols)"
                        },
                        "comparison_metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Metrics to compare across companies",
                            "default": ["revenue", "profit_margin", "debt_ratio", "roe"]
                        },
                        "analysis_period": {
                            "type": "string",
                            "description": "Time period for comparison",
                            "default": "latest_annual"
                        }
                    },
                    "required": ["companies"]
                }
            },
            {
                "name": "assess_investment_risk",
                "description": "Financial risk analysis and creditworthiness evaluation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity": {
                            "type": "string",
                            "description": "Company or entity to assess"
                        },
                        "risk_factors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific risk factors to evaluate",
                            "default": ["credit", "market", "operational", "regulatory"]
                        },
                        "assessment_depth": {
                            "type": "string",
                            "enum": ["basic", "thorough", "comprehensive"],
                            "description": "Depth of risk assessment",
                            "default": "thorough"
                        }
                    },
                    "required": ["entity"]
                }
            },
            # Insurance & Claims Tools
            {
                "name": "process_insurance_claim",
                "description": "Comprehensive claims analysis and assessment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "enum": ["auto", "life", "health", "dental", "general", "risk_calculation"],
                            "description": "Insurance domain"
                        },
                        "claim_type": {
                            "type": "string",
                            "description": "Type of claim (e.g., collision, medical, death)"
                        },
                        "claim_data": {
                            "type": "object",
                            "description": "Claim details and documentation"
                        },
                        "parallel_execution": {
                            "type": "boolean",
                            "description": "Whether to use parallel agent execution",
                            "default": True
                        }
                    },
                    "required": ["domain", "claim_type", "claim_data"]
                }
            },
            {
                "name": "search_policy_documents",
                "description": "Policy knowledge base search and coverage analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for policy documents"
                        },
                        "policy_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types of policies to search (auto, life, health, etc.)",
                            "default": []
                        },
                        "coverage_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific coverage areas to focus on",
                            "default": []
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "analyze_claim_documents",
                "description": "AI-powered analysis of submitted claim materials",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "documents": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Claim documents to analyze (forms, receipts, reports, etc.)"
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["damage_assessment", "fraud_detection", "coverage_validation", "comprehensive"],
                            "description": "Type of analysis to perform",
                            "default": "comprehensive"
                        },
                        "claim_context": {
                            "type": "object",
                            "description": "Additional context about the claim",
                            "default": {}
                        }
                    },
                    "required": ["documents"]
                }
            },
            {
                "name": "validate_coverage",
                "description": "Policy coverage validation against submitted claims",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "policy_id": {
                            "type": "string",
                            "description": "Policy identifier"
                        },
                        "claim_details": {
                            "type": "object",
                            "description": "Details of the claim to validate"
                        },
                        "validation_level": {
                            "type": "string",
                            "enum": ["basic", "thorough", "comprehensive"],
                            "description": "Level of coverage validation",
                            "default": "thorough"
                        }
                    },
                    "required": ["policy_id", "claim_details"]
                }
            },
            {
                "name": "assess_fraud_risk",
                "description": "Fraud detection and risk assessment for claims",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "claim_data": {
                            "type": "object",
                            "description": "Complete claim information for fraud assessment"
                        },
                        "risk_indicators": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific fraud indicators to check",
                            "default": []
                        },
                        "threshold": {
                            "type": "number",
                            "description": "Risk threshold for flagging (0-100)",
                            "default": 70
                        }
                    },
                    "required": ["claim_data"]
                }
            },
            # Cross-Domain Tools
            {
                "name": "coordinate_multi_domain_agents",
                "description": "Multi-agent coordination across banking and insurance domains",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "request_type": {
                            "type": "string",
                            "description": "Type of cross-domain analysis request"
                        },
                        "content": {
                            "type": "string", 
                            "description": "Content or question requiring multi-domain expertise"
                        },
                        "domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific domains to involve (banking, insurance, etc.)",
                            "default": ["banking", "insurance"]
                        },
                        "requirements": {
                            "type": "object",
                            "description": "Specific requirements for the analysis",
                            "default": {}
                        }
                    },
                    "required": ["request_type", "content"]
                }
            },
            {
                "name": "get_system_statistics",
                "description": "Processing metrics and system performance across all domains",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Domains to include in statistics",
                            "default": ["banking", "insurance"]
                        },
                        "time_range": {
                            "type": "string",
                            "description": "Time range for statistics",
                            "default": "24h"
                        }
                    }
                }
            }
        ]
    
    def get_available_resources(self) -> List[Dict[str, Any]]:
        """Return list of available MCP resources"""
        return [
            {
                "uri": "financial://knowledge-base/statistics",
                "name": "Knowledge Base Statistics",
                "description": "Current statistics and health metrics of the financial knowledge base",
                "mimeType": "application/json"
            },
            {
                "uri": "financial://agents/capabilities", 
                "name": "Agent Capabilities",
                "description": "List of all available agent capabilities and their schemas",
                "mimeType": "application/json"
            },
            {
                "uri": "financial://documents/types",
                "name": "Document Types",
                "description": "Available financial document types in the knowledge base",
                "mimeType": "application/json"
            },
            {
                "uri": "financial://system/status",
                "name": "System Status", 
                "description": "Current status of the financial RAG system",
                "mimeType": "application/json"
            },
            {
                "uri": "insurance://agents/status",
                "name": "Insurance Agent Status",
                "description": "Current status and health of all insurance agents",
                "mimeType": "application/json"
            },
            {
                "uri": "insurance://policies/types",
                "name": "Insurance Policy Types",
                "description": "Available insurance policy types and their schemas",
                "mimeType": "application/json"
            },
            {
                "uri": "insurance://claims/types",
                "name": "Insurance Claim Types",
                "description": "Available insurance claim types and their processing workflows",
                "mimeType": "application/json"
            },
            {
                "uri": "insurance://orchestrator/status",
                "name": "Insurance Orchestrator Status",
                "description": "Current status of the insurance agent orchestrator",
                "mimeType": "application/json"
            }
        ]
    
    def get_available_prompts(self) -> List[Dict[str, Any]]:
        """Return list of available MCP prompts"""
        return [
            {
                "name": "financial_analysis",
                "description": "Template for comprehensive financial analysis",
                "arguments": [
                    {
                        "name": "company",
                        "description": "Company name or ticker symbol",
                        "required": True
                    },
                    {
                        "name": "analysis_type",
                        "description": "Type of analysis (risk, performance, comparison, etc.)",
                        "required": False
                    }
                ]
            },
            {
                "name": "risk_assessment",
                "description": "Template for financial risk assessment",
                "arguments": [
                    {
                        "name": "companies",
                        "description": "List of companies to assess",
                        "required": True
                    },
                    {
                        "name": "risk_factors",
                        "description": "Specific risk factors to focus on",
                        "required": False
                    }
                ]
            },
            {
                "name": "insurance_policy_analysis",
                "description": "Template for insurance policy analysis",
                "arguments": [
                    {
                        "name": "domain",
                        "description": "Insurance domain (auto, life, health, dental, general)",
                        "required": True
                    },
                    {
                        "name": "policy_data",
                        "description": "Policy information and coverage details",
                        "required": True
                    },
                    {
                        "name": "analysis_type",
                        "description": "Type of analysis (basic, comprehensive, risk_assessment)",
                        "required": False
                    }
                ]
            },
            {
                "name": "insurance_claim_processing",
                "description": "Template for insurance claim processing",
                "arguments": [
                    {
                        "name": "domain",
                        "description": "Insurance domain (auto, life, health, dental, general)",
                        "required": True
                    },
                    {
                        "name": "claim_type",
                        "description": "Type of claim (collision, medical, death, etc.)",
                        "required": True
                    },
                    {
                        "name": "claim_data",
                        "description": "Claim details and documentation",
                        "required": True
                    }
                ]
            }
        ]
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tool calls"""
        self.logger.info(f"🔧 Handle tool call - Tool: {name}, Args: {arguments}")
        
        if not self.initialized:
            self.logger.error("❌ Server not initialized!")
            return {"error": "Server not initialized", "success": False}
            
        try:
            session_id = f"mcp_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            self.logger.info(f"📋 Session ID: {session_id}")
            
            # Banking & Financial Analysis Tools
            if name == "analyze_financial_documents":
                self.logger.info("📊 Calling _handle_analyze_financial_documents")
                return await self._handle_analyze_financial_documents(arguments, session_id)
            elif name == "search_financial_database":
                self.logger.info("🔍 Calling _handle_search_financial_database")
                return await self._handle_search_financial_database(arguments, session_id)
            elif name == "extract_financial_metrics":
                self.logger.info("📈 Calling _handle_extract_financial_metrics")
                return await self._handle_extract_financial_metrics(arguments, session_id)
            elif name == "compare_companies":
                self.logger.info("⚖️ Calling _handle_compare_companies")
                return await self._handle_compare_companies(arguments, session_id)
            elif name == "assess_investment_risk":
                self.logger.info("⚠️ Calling _handle_assess_investment_risk")
                return await self._handle_assess_investment_risk(arguments, session_id)
            
            # Insurance & Claims Tools
            elif name == "process_insurance_claim":
                self.logger.info("📦 Calling _handle_process_insurance_claim")
                return await self._handle_process_insurance_claim(arguments, session_id)
            elif name == "search_policy_documents":
                self.logger.info("🔍 Calling _handle_search_policy_documents")
                return await self._handle_search_policy_documents(arguments, session_id)
            elif name == "analyze_claim_documents":
                self.logger.info("📄 Calling _handle_analyze_claim_documents")
                return await self._handle_analyze_claim_documents(arguments, session_id)
            elif name == "validate_coverage":
                self.logger.info("✅ Calling _handle_validate_coverage")
                return await self._handle_validate_coverage(arguments, session_id)
            elif name == "assess_fraud_risk":
                self.logger.info("� Calling _handle_assess_fraud_risk")
                return await self._handle_assess_fraud_risk(arguments, session_id)
            
            # Cross-Domain Tools
            elif name == "coordinate_multi_domain_agents":
                self.logger.info("🤝 Calling _handle_coordinate_multi_domain_agents")
                return await self._handle_coordinate_multi_domain_agents(arguments, session_id)
            elif name == "get_system_statistics":
                self.logger.info("📊 Calling _handle_get_system_statistics")
                return await self._handle_get_system_statistics(arguments, session_id)
            
            # Legacy/Compatibility Tools  
            elif name == "answer_financial_question":
                self.logger.info("🤖 Calling _handle_financial_question")
                return await self._handle_financial_question(arguments, session_id)
            elif name == "search_financial_documents":
                self.logger.info("🔍 Calling _handle_document_search")
                return await self._handle_document_search(arguments)
            elif name == "verify_source_credibility":
                self.logger.info("✅ Calling _handle_credibility_verification")
                return await self._handle_credibility_verification(arguments, session_id)
            elif name == "get_knowledge_base_stats":
                self.logger.info("📊 Calling _handle_knowledge_stats")
                return await self._handle_knowledge_stats()
            elif name == "coordinate_multi_agent_analysis":
                self.logger.info("🤝 Calling _handle_multi_agent_coordination")
                return await self._handle_multi_agent_coordination(arguments, session_id)
            elif name == "deploy_insurance_agent":
                self.logger.info("�️ Calling _handle_deploy_insurance_agent")
                return await self._handle_deploy_insurance_agent(arguments, session_id)
            elif name == "analyze_insurance_policy":
                self.logger.info("📊 Calling _handle_analyze_insurance_policy")
                return await self._handle_analyze_insurance_policy(arguments, session_id)
            elif name == "get_insurance_agent_status":
                self.logger.info("🔍 Calling _handle_get_insurance_agent_status")
                return await self._handle_get_insurance_agent_status(arguments, session_id)
            elif name == "calculate_claim_risk":
                self.logger.info("🔍 Calling _handle_calculate_claim_risk")
                return await self._handle_calculate_claim_risk(arguments, session_id)
            else:
                self.logger.error(f"❌ Unknown tool: {name}")
                return {"error": f"Unknown tool: {name}", "success": False}
                
        except Exception as e:
            self.logger.error(f"❌ Error handling tool call {name}: {e}", exc_info=True)
            return {"error": str(e), "success": False}
    
    async def _handle_financial_question(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle financial question answering"""
        start_time = datetime.utcnow()
        question = arguments["question"]
        context = arguments.get("context", "")
        verification_level = arguments.get("verification_level", "thorough")
        use_multi_agent = arguments.get("use_multi_agent", True)
        
        self.logger.info(f"💭 Financial question started at {start_time.isoformat()}: {question}")
        self.logger.info(f"📝 Context: {context}")
        self.logger.info(f"🔍 Verification level: {verification_level}")
        self.logger.info(f"🤝 Use multi-agent: {use_multi_agent}")
        
        # STEP 1: First search for relevant documents from knowledge base
        step1_start = datetime.utcnow()
        self.logger.info("🔍 Step 1: Searching knowledge base for relevant documents...")
        self.logger.info(f"💭 Question for search: {question}")
        search_top_k = 20 if verification_level == "thorough" else 10
        self.logger.info(f"🔢 Search top_k: {search_top_k}")
        self.logger.info(f"📚 KB Manager available: {self.kb_manager is not None}")
        
        search_results = []
        try:
            if self.kb_manager is None:
                self.logger.error("❌ KB Manager is None - cannot search")
                raise Exception("Knowledge base manager not available")
            
            self.logger.info("🚀 Starting knowledge base search...")
            search_results = await self.kb_manager.search_knowledge_base(
                query=question,
                top_k=search_top_k,
                filters={}
            )
            
            step1_duration = (datetime.utcnow() - step1_start).total_seconds()
            self.logger.info(f"📚 Found {len(search_results)} relevant documents from knowledge base (took {step1_duration:.2f}s)")
            
            # Log first few results for debugging
            for i, result in enumerate(search_results[:3]):
                self.logger.info(f"📄 Document {i+1}: {result.get('title', 'No title')[:100]}...")
                self.logger.info(f"🎯 Score: {result.get('score', 'No score')}")
                self.logger.info(f"📝 Content preview: {result.get('content', 'No content')[:200]}...")
                
        except Exception as e:
            step1_duration = (datetime.utcnow() - step1_start).total_seconds()
            self.logger.error(f"❌ Error searching knowledge base after {step1_duration:.2f}s: {e}", exc_info=True)
            search_results = []
        
        # Prepare full question with context
        full_question = f"{question}"
        if context:
            full_question += f"\n\nAdditional Context: {context}"
        
        self.logger.info(f"🔄 Components status - Orchestrator: {self.orchestrator is not None}, RAG: {self.rag_pipeline is not None}")
        
        # STEP 2: Process with agent/orchestrator, including search results
        step2_start = datetime.utcnow()
        try:
            if use_multi_agent and self.orchestrator:
                # Use multi-agent orchestration with search results as context
                self.logger.info("🤖 Step 2: Using multi-agent orchestration with search results")
                request = {
                    "agent_type": AgentType.QA_AGENT.value,
                    "capability": "answer_financial_question",
                    "question": full_question,
                    "verification_level": verification_level,
                    "search_results": search_results,  # Pass search results as context
                    "context": context
                }
                
                self.logger.info(f"📤 Sending request to orchestrator with {len(search_results)} search results")
                result = await self.orchestrator.process_request(request, session_id)
                self.logger.info(f"📥 Orchestrator result type: {type(result)}")
                self.logger.info(f"📥 Orchestrator result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            else:
                # Use RAG pipeline directly with search results
                self.logger.info("🔍 Step 2: Using RAG pipeline directly with search results")
                result = await self.rag_pipeline.process_question(
                    question=full_question,
                    session_id=session_id,
                    verification_level=verification_level,
                    search_results=search_results  # Pass search results
                )
                
            step2_duration = (datetime.utcnow() - step2_start).total_seconds()
            self.logger.info(f"✅ Agent processing completed in {step2_duration:.2f}s")
                
        except Exception as e:
            step2_duration = (datetime.utcnow() - step2_start).total_seconds()
            self.logger.error(f"❌ Error in agent processing after {step2_duration:.2f}s: {e}", exc_info=True)
            result = {
                "answer": f"Error processing question: {str(e)}",
                "confidence": 0.0,
                "sources": [],
                "error": str(e)
            }
        
        total_duration = (datetime.utcnow() - start_time).total_seconds()
        self.logger.info(f"✅ Final result preparation - Answer length: {len(str(result.get('answer', '')))}")
        self.logger.info(f"📊 Sources count: {len(result.get('sources', []))}")
        self.logger.info(f"⏱️ Total processing time: {total_duration:.2f}s")
        
        return {
            "answer": result.get("answer", ""),
            "confidence": result.get("confidence", 0.0),
            "sources": result.get("sources", []),
            "search_results_count": len(search_results),
            "session_id": session_id,
            "verification_level": verification_level,
            "method": "multi-agent" if use_multi_agent else "rag-pipeline",
            "success": True,
            "processing_time_seconds": total_duration
        }
    
    async def _handle_document_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document search"""
        query = arguments["query"]
        document_types = arguments.get("document_types", [])
        top_k = arguments.get("top_k", 10)
        
        self.logger.info(f"🔍 Document search - Query: {query}")
        self.logger.info(f"📁 Document types filter: {document_types}")
        self.logger.info(f"🔢 Top K: {top_k}")
        self.logger.info(f"📚 KB Manager status: {self.kb_manager is not None}")
        
        filters = {}
        if document_types:
            filters["document_type"] = document_types
        
        self.logger.info(f"🎯 Search filters: {filters}")
        
        try:
            results = await self.kb_manager.search_knowledge_base(
                query=query,
                top_k=top_k,
                filters=filters
            )
            self.logger.info(f"✅ Search completed - Found {len(results)} results")
            self.logger.info(f"📄 First result preview: {results[0] if results else 'No results'}")
            
            return {
                "results": results,
                "total_found": len(results),
                "query": query,
                "filters": filters,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"❌ Document search error: {e}", exc_info=True)
            return {
                "results": [],
                "total_found": 0,
                "query": query,
                "filters": filters,
                "error": str(e),
                "success": False
            }
    
    async def _handle_credibility_verification(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle source credibility verification"""
        sources = arguments["sources"]
        
        request = {
            "agent_type": AgentType.QA_AGENT.value,
            "capability": "verify_source_credibility",
            "sources": sources
        }
        
        result = await self.orchestrator.process_request(request, session_id)
        return result
    
    async def _handle_knowledge_stats(self) -> Dict[str, Any]:
        """Handle knowledge base statistics request"""
        stats = await self.kb_manager.get_knowledge_base_statistics()
        return {
            "statistics": stats,
            "success": True
        }
    
    async def _handle_multi_agent_coordination(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle multi-agent coordination"""
        complex_request = {
            "type": arguments["request_type"],
            "content": arguments["content"],
            "requirements": arguments.get("requirements", {})
        }
        
        result = await self.orchestrator.coordinate_agents(complex_request, session_id)
        return result
    
    async def _handle_deploy_insurance_agent(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle deploying a new insurance agent"""
        agent_name = arguments.get("agent_name")
        agent_type = arguments.get("agent_type")
        tools = arguments.get("tools", ["azure_search", "knowledge_base", "code_interpreter"])
        instructions = arguments.get("instructions", "")

        if not agent_name or not agent_type:
            return {"error": "Missing agent_name or agent_type", "success": False}

        try:
            self.logger.info(f"🛠️ Deploying insurance agent: {agent_name} ({agent_type}) with tools: {tools}")
            new_agent = create_insurance_agent(agent_name, agent_type, tools, instructions)
            await self.insurance_orchestrator.add_agent(new_agent)
            self.logger.info(f"✅ Insurance agent {agent_name} deployed successfully.")
            return {"message": f"Insurance agent {agent_name} deployed successfully.", "success": True}
        except Exception as e:
            self.logger.error(f"❌ Error deploying insurance agent {agent_name}: {e}", exc_info=True)
            return {"error": f"Error deploying insurance agent {agent_name}: {e}", "success": False}

    async def _handle_process_insurance_claim(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle processing an insurance claim"""
        domain = arguments.get("domain")
        claim_type = arguments.get("claim_type")
        claim_data = arguments.get("claim_data")
        parallel_execution = arguments.get("parallel_execution", True)

        if not domain or not claim_type or not claim_data:
            return {"error": "Missing domain, claim_type, or claim_data", "success": False}

        try:
            self.logger.info(f"📦 Processing insurance claim: {domain} - {claim_type}")
            claim_processor = self.insurance_orchestrator.get_agent_by_name(f"{domain}_{claim_type}_agent")
            
            if not claim_processor:
                return {"error": f"No agent found for {domain} {claim_type} claims.", "success": False}

            if parallel_execution:
                self.logger.info("🚀 Executing claim processing in parallel...")
                result = await claim_processor.invoke(claim_data)
            else:
                self.logger.info("🚀 Executing claim processing sequentially...")
                result = await claim_processor.invoke(claim_data)

            self.logger.info(f"📥 Claim processing result: {result}")
            return {"message": f"Insurance claim for {domain} {claim_type} processed successfully.", "result": result, "success": True}
        except Exception as e:
            self.logger.error(f"❌ Error processing insurance claim: {e}", exc_info=True)
            return {"error": f"Error processing insurance claim: {e}", "success": False}

    async def _handle_analyze_insurance_policy(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle analyzing an insurance policy"""
        domain = arguments.get("domain")
        policy_data = arguments.get("policy_data")
        analysis_type = arguments.get("analysis_type", "comprehensive")
        parallel_execution = arguments.get("parallel_execution", True)

        if not domain or not policy_data:
            return {"error": "Missing domain or policy_data", "success": False}

        try:
            self.logger.info(f"📊 Analyzing insurance policy: {domain} - {analysis_type}")
            policy_analyzer = self.insurance_orchestrator.get_agent_by_name(f"{domain}_policy_analyzer_agent")
            
            if not policy_analyzer:
                return {"error": f"No agent found for {domain} policy analysis.", "success": False}

            if parallel_execution:
                self.logger.info("🚀 Executing policy analysis in parallel...")
                result = await policy_analyzer.invoke(policy_data)
            else:
                self.logger.info("🚀 Executing policy analysis sequentially...")
                result = await policy_analyzer.invoke(policy_data)

            self.logger.info(f"📥 Policy analysis result: {result}")
            return {"message": f"Insurance policy for {domain} analyzed successfully.", "result": result, "success": True}
        except Exception as e:
            self.logger.error(f"❌ Error analyzing insurance policy: {e}", exc_info=True)
            return {"error": f"Error analyzing insurance policy: {e}", "success": False}

    async def _handle_get_insurance_agent_status(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle getting status of an insurance agent"""
        agent_name = arguments.get("agent_name")
        if not agent_name:
            return {"error": "Missing agent_name", "success": False}

        try:
            self.logger.info(f"🔍 Checking status of insurance agent: {agent_name}")
            agent = self.insurance_orchestrator.get_agent_by_name(agent_name)
            
            if agent:
                status = {
                    "name": agent.name,
                    "type": agent.type,
                    "tools": agent.tools,
                    "last_activity": agent.last_activity,
                    "health": agent.health,
                    "status": agent.status
                }
                self.logger.info(f"✅ Status for {agent_name}: {status}")
                return {"message": f"Status for {agent_name}: {status}", "success": True}
            else:
                return {"error": f"Agent {agent_name} not found.", "success": False}
        except Exception as e:
            self.logger.error(f"❌ Error getting insurance agent status: {e}", exc_info=True)
            return {"error": f"Error getting insurance agent status: {e}", "success": False}

    async def _handle_calculate_claim_risk(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle claim risk calculation"""
        try:
            self.logger.info(f"🔍 Calculating claim risk with arguments: {arguments}")
            
            claim_data = arguments.get("claim_data", {})
            policy_id = arguments.get("policy_id", "")
            auto_approve_threshold = arguments.get("auto_approve_threshold", 50)
            
            # Use the risk calculation agent
            if hasattr(self, 'insurance_orchestrator') and self.insurance_orchestrator:
                # Create a risk calculation workflow
                workflow_result = await self.insurance_orchestrator.orchestrate_workflow(
                    workflow_type="risk_calculation",
                    input_data={
                        "claim_data": claim_data,
                        "policy_id": policy_id,
                        "auto_approve_threshold": auto_approve_threshold
                    }
                )
                
                return {
                    "success": True,
                    "risk_calculation": workflow_result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # Fallback: simulate risk calculation
                claim_amount = claim_data.get("claim_amount", 0)
                policy_coverage = claim_data.get("policy_coverage", 100000)
                
                if claim_amount <= policy_coverage:
                    risk_assessment = "auto_approve"
                    risk_score = 10 if claim_amount <= policy_coverage * 0.5 else 30
                else:
                    risk_assessment = "manual_review_required"
                    risk_score = min(100, 50 + (claim_amount - policy_coverage) / policy_coverage * 50)
                
                return {
                    "success": True,
                    "risk_assessment": risk_assessment,
                    "claim_amount": claim_amount,
                    "policy_coverage": policy_coverage,
                    "risk_score": risk_score,
                    "recommendation": f"Claim {'auto-approved' if risk_assessment == 'auto_approve' else 'requires manual review'}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error in _handle_calculate_claim_risk: {e}")
            return {"error": str(e)}

    # Banking & Financial Analysis Tool Handlers
    async def _handle_analyze_financial_documents(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Analyze SEC filings and financial documents."""
        try:
            document_ids = arguments.get("document_ids", [])
            analysis_type = arguments.get("analysis_type", "comprehensive")
            
            if not document_ids:
                return {"error": "Missing required document_ids", "success": False}
            
            payload = {
                "document_ids": document_ids,
                "analysis_type": analysis_type,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/analyze-financial-documents", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in analyze_financial_documents: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def _handle_search_financial_database(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Search financial documents and SEC filings."""
        try:
            query = arguments.get("query", "")
            filters = arguments.get("filters", {})
            limit = arguments.get("limit", 10)
            
            if not query:
                return {"error": "Missing required query parameter", "success": False}
            
            payload = {
                "query": query,
                "filters": filters,
                "limit": limit,
                "session_id": session_id,
                "index_name": "financial-documents"  # Default to financial documents
            }
            
            result = await self.http_client.post(f"{self.backend_url}/search-documents", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in search_financial_database: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def _handle_extract_financial_metrics(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Extract financial metrics from documents."""
        try:
            document_id = arguments.get("document_id", "")
            metrics_type = arguments.get("metrics_type", "standard")
            
            if not document_id:
                return {"error": "Missing required document_id", "success": False}
            
            payload = {
                "document_id": document_id,
                "metrics_type": metrics_type,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/extract-financial-metrics", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in extract_financial_metrics: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def _handle_compare_companies(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Compare financial performance between companies."""
        try:
            company_a = arguments.get("company_a", "")
            company_b = arguments.get("company_b", "")
            metrics = arguments.get("metrics", ["revenue", "profit", "debt"])
            
            if not company_a or not company_b:
                return {"error": "Missing required company_a or company_b", "success": False}
            
            payload = {
                "company_a": company_a,
                "company_b": company_b,
                "metrics": metrics,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/compare-companies", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in compare_companies: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def _handle_assess_investment_risk(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Assess investment risk for financial instruments."""
        try:
            investment_data = arguments.get("investment_data", {})
            risk_factors = arguments.get("risk_factors", [])
            
            if not investment_data:
                return {"error": "Missing required investment_data", "success": False}
            
            payload = {
                "investment_data": investment_data,
                "risk_factors": risk_factors,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/assess-investment-risk", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in assess_investment_risk: {str(e)}")
            return {"error": str(e), "success": False}

    # Insurance Tool Handlers
    async def _handle_search_policy_documents(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Search insurance policy documents."""
        try:
            query = arguments.get("query", "")
            policy_type = arguments.get("policy_type", "")
            limit = arguments.get("limit", 10)
            
            if not query:
                return {"error": "Missing required query parameter", "success": False}
            
            filters = {}
            if policy_type:
                filters["policy_type"] = policy_type
            
            payload = {
                "query": query,
                "filters": filters,
                "limit": limit,
                "session_id": session_id,
                "index_name": "policy-documents"
            }
            
            result = await self.http_client.post(f"{self.backend_url}/search-documents", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in search_policy_documents: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def _handle_analyze_claim_documents(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Analyze claim documents for completeness and validity."""
        try:
            claim_id = arguments.get("claim_id", "")
            document_ids = arguments.get("document_ids", [])
            
            if not claim_id or not document_ids:
                return {"error": "Missing required claim_id or document_ids", "success": False}
            
            payload = {
                "claim_id": claim_id,
                "document_ids": document_ids,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/analyze-claim-documents", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in analyze_claim_documents: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def _handle_validate_coverage(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Validate insurance coverage for a claim."""
        try:
            claim_data = arguments.get("claim_data", {})
            policy_id = arguments.get("policy_id", "")
            
            if not claim_data or not policy_id:
                return {"error": "Missing required claim_data or policy_id", "success": False}
            
            payload = {
                "claim_data": claim_data,
                "policy_id": policy_id,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/validate-coverage", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in validate_coverage: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def _handle_assess_fraud_risk(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Assess fraud risk for insurance claims."""
        try:
            claim_data = arguments.get("claim_data", {})
            policy_history = arguments.get("policy_history", {})
            
            if not claim_data:
                return {"error": "Missing required claim_data", "success": False}
            
            payload = {
                "claim_data": claim_data,
                "policy_history": policy_history,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/assess-fraud-risk", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in assess_fraud_risk: {str(e)}")
            return {"error": str(e), "success": False}

    # Cross-Domain Tool Handlers
    async def _handle_coordinate_multi_domain_agents(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Coordinate analysis across banking and insurance domains."""
        try:
            task_description = arguments.get("task_description", "")
            domains = arguments.get("domains", ["banking", "insurance"])
            
            if not task_description:
                return {"error": "Missing required task_description", "success": False}
            
            payload = {
                "task_description": task_description,
                "domains": domains,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/coordinate-multi-domain", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in coordinate_multi_domain_agents: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def _handle_get_system_statistics(self, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Get comprehensive system statistics for both domains."""
        try:
            domains = arguments.get("domains", ["banking", "insurance"])
            
            payload = {
                "domains": domains,
                "session_id": session_id
            }
            
            result = await self.http_client.post(f"{self.backend_url}/system-statistics", payload)
            return {"data": result, "success": True}
            
        except Exception as e:
            self.logger.error(f"❌ Error in get_system_statistics: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def handle_resource_read(self, uri: str) -> Dict[str, Any]:
        """Handle MCP resource read requests"""
        try:
            if uri == "financial://knowledge-base/statistics":
                stats = await self.kb_manager.get_knowledge_base_statistics()
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(stats, indent=2)
                        }
                    ]
                }
            elif uri == "financial://agents/capabilities":
                capabilities = self.orchestrator.get_agent_capabilities()
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(capabilities, indent=2)
                        }
                    ]
                }
            elif uri == "financial://documents/types":
                document_types = [
                    "10-K", "10-Q", "8-K", "proxy-statement",
                    "annual-report", "earnings-report"
                ]
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps({"document_types": document_types}, indent=2)
                        }
                    ]
                }
            elif uri == "financial://system/status":
                status = await self.orchestrator.get_system_status()
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(status, indent=2)
                        }
                    ]
                }
            elif uri == "insurance://agents/status":
                if self.insurance_orchestrator:
                    agent_status = await self.insurance_orchestrator.get_all_agent_status()
                    return {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps(agent_status, indent=2)
                            }
                        ]
                    }
                else:
                    return {"error": {"code": -32603, "message": "Insurance orchestrator not available"}}
            elif uri == "insurance://policies/types":
                policy_types = {
                    "auto": {
                        "description": "Automobile insurance policies",
                        "coverage_types": ["liability", "collision", "comprehensive", "uninsured_motorist"],
                        "required_fields": ["vehicle_info", "driver_info", "coverage_limits"]
                    },
                    "life": {
                        "description": "Life insurance policies",
                        "coverage_types": ["term", "whole", "universal", "variable"],
                        "required_fields": ["insured_info", "beneficiary_info", "coverage_amount"]
                    },
                    "health": {
                        "description": "Health insurance policies",
                        "coverage_types": ["medical", "dental", "vision", "prescription"],
                        "required_fields": ["member_info", "provider_network", "benefits"]
                    },
                    "dental": {
                        "description": "Dental insurance policies",
                        "coverage_types": ["preventive", "basic", "major", "orthodontia"],
                        "required_fields": ["member_info", "provider_network", "benefits"]
                    },
                    "general": {
                        "description": "General insurance policies",
                        "coverage_types": ["property", "casualty", "professional", "cyber"],
                        "required_fields": ["insured_info", "coverage_details", "limits"]
                    }
                }
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(policy_types, indent=2)
                        }
                    ]
                }
            elif uri == "insurance://claims/types":
                claim_types = {
                    "auto": {
                        "collision": "Vehicle collision claims",
                        "comprehensive": "Non-collision damage claims",
                        "liability": "Third-party liability claims",
                        "medical": "Medical expense claims"
                    },
                    "life": {
                        "death": "Death benefit claims",
                        "disability": "Disability benefit claims",
                        "surrender": "Policy surrender claims"
                    },
                    "health": {
                        "medical": "Medical treatment claims",
                        "prescription": "Prescription drug claims",
                        "preventive": "Preventive care claims"
                    },
                    "dental": {
                        "preventive": "Preventive dental care claims",
                        "basic": "Basic dental procedure claims",
                        "major": "Major dental procedure claims"
                    },
                    "general": {
                        "property": "Property damage claims",
                        "casualty": "Casualty claims",
                        "professional": "Professional liability claims"
                    }
                }
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(claim_types, indent=2)
                        }
                    ]
                }
            elif uri == "insurance://orchestrator/status":
                if self.insurance_orchestrator:
                    orchestrator_status = {
                        "initialized": self.insurance_orchestrator._initialized,
                        "agents_count": len(self.insurance_orchestrator.agents),
                        "tools_count": len(self.insurance_orchestrator.tools),
                        "last_activity": datetime.utcnow().isoformat()
                    }
                    return {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps(orchestrator_status, indent=2)
                            }
                        ]
                    }
                else:
                    return {"error": {"code": -32603, "message": "Insurance orchestrator not available"}}
            else:
                return {"error": {"code": -32602, "message": f"Unknown resource: {uri}"}}
                
        except Exception as e:
            self.logger.error(f"Error reading resource {uri}: {e}")
            return {"error": {"code": -32603, "message": str(e)}}
    
    async def handle_prompt_get(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP prompt get requests"""
        try:
            if name == "financial_analysis":
                company = arguments.get("company", "")
                analysis_type = arguments.get("analysis_type", "comprehensive")
                
                prompt = f"""Please provide a {analysis_type} financial analysis for {company}.

Include the following in your analysis:
1. Financial performance overview
2. Key financial ratios and metrics
3. Risk factors and concerns
4. Growth prospects and opportunities
5. Competitive positioning
6. Recent developments and news

Use data from SEC filings, earnings reports, and other reliable financial documents.
Provide specific numbers, dates, and cite your sources."""
                
                return {
                    "description": f"Financial analysis prompt for {company}",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt
                            }
                        }
                    ]
                }
                
            elif name == "risk_assessment":
                companies = arguments.get("companies", [])
                risk_factors = arguments.get("risk_factors", [])
                
                companies_str = ", ".join(companies) if isinstance(companies, list) else str(companies)
                factors_str = ", ".join(risk_factors) if risk_factors else "all major risk factors"
                
                prompt = f"""Please conduct a comprehensive risk assessment for: {companies_str}

Focus on {factors_str} and analyze:
1. Financial risks (credit, liquidity, market)
2. Operational risks (business model, competition)
3. Regulatory and compliance risks
4. Environmental and social risks
5. Technology and cyber risks
6. Geopolitical risks

Compare risk profiles between companies if multiple are provided.
Use the most recent SEC filings and financial reports.
Provide specific examples and quantitative measures where available."""
                
                return {
                    "description": f"Risk assessment prompt for {companies_str}",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt
                            }
                        }
                    ]
                }
            elif name == "insurance_policy_analysis":
                domain = arguments.get("domain", "")
                policy_data = arguments.get("policy_data", {})
                analysis_type = arguments.get("analysis_type", "comprehensive")
                
                prompt = f"""Please provide a {analysis_type} insurance policy analysis for {domain} insurance.

Policy Data: {json.dumps(policy_data, indent=2)}

Include the following in your analysis:
1. Policy coverage assessment
2. Risk evaluation and recommendations
3. Cost-benefit analysis
4. Compliance and regulatory considerations
5. Claims processing implications
6. Policy optimization suggestions

Use domain-specific knowledge for {domain} insurance and provide actionable recommendations."""
                
                return {
                    "description": f"Insurance policy analysis prompt for {domain}",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt
                            }
                        }
                    ]
                }
            elif name == "insurance_claim_processing":
                domain = arguments.get("domain", "")
                claim_type = arguments.get("claim_type", "")
                claim_data = arguments.get("claim_data", {})
                
                prompt = f"""Please process an insurance claim for {domain} insurance.

Claim Type: {claim_type}
Claim Data: {json.dumps(claim_data, indent=2)}

Include the following in your processing:
1. Claim validation and documentation review
2. Coverage verification and eligibility
3. Damage assessment and cost estimation
4. Liability determination and fault analysis
5. Settlement calculation and recommendations
6. Processing timeline and next steps

Use domain-specific knowledge for {domain} {claim_type} claims and provide detailed processing results."""
                
                return {
                    "description": f"Insurance claim processing prompt for {domain} {claim_type}",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt
                            }
                        }
                    ]
                }
            else:
                return {"error": {"code": -32602, "message": f"Unknown prompt: {name}"}}
                
        except Exception as e:
            self.logger.error(f"Error getting prompt {name}: {e}")
            return {"error": {"code": -32603, "message": str(e)}}
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP request according to the protocol"""
        try:
            request = MCPRequest(
                id=request_data.get("id"),
                method=request_data.get("method"),
                params=request_data.get("params", {})
            )
            
            # Handle different MCP methods
            if request.method == "initialize":
                return MCPResponse(
                    id=request.id,
                    result={
                        "protocolVersion": "2024-11-05",
                        "capabilities": self.server_info["capabilities"],
                        "serverInfo": self.server_info
                    }
                ).to_dict()
                
            elif request.method == "tools/list":
                return MCPResponse(
                    id=request.id,
                    result={"tools": self.get_available_tools()}
                ).to_dict()
                
            elif request.method == "tools/call":
                tool_name = request.params.get("name")
                arguments = request.params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, arguments)
                
                return MCPResponse(
                    id=request.id,
                    result={"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
                ).to_dict()
                
            elif request.method == "resources/list":
                return MCPResponse(
                    id=request.id,
                    result={"resources": self.get_available_resources()}
                ).to_dict()
                
            elif request.method == "resources/read":
                uri = request.params.get("uri")
                result = await self.handle_resource_read(uri)
                
                return MCPResponse(
                    id=request.id,
                    result=result
                ).to_dict()
                
            elif request.method == "prompts/list":
                return MCPResponse(
                    id=request.id,
                    result={"prompts": self.get_available_prompts()}
                ).to_dict()
                
            elif request.method == "prompts/get":
                prompt_name = request.params.get("name")
                arguments = request.params.get("arguments", {})
                result = await self.handle_prompt_get(prompt_name, arguments)
                
                return MCPResponse(
                    id=request.id,
                    result=result
                ).to_dict()
                
            elif request.method == "logging/setLevel":
                # Handle logging level changes
                level = request.params.get("level", "info")
                logging.getLogger().setLevel(getattr(logging, level.upper()))
                
                return MCPResponse(
                    id=request.id,
                    result={}
                ).to_dict()
                
            else:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Method not found: {request.method}"}
                ).to_dict()
                
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return MCPResponse(
                id=request_data.get("id"),
                error={"code": -32603, "message": str(e)}
            ).to_dict()


async def main():
    """Main MCP server entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = FinancialInsuranceMCPServer()
    
    try:
        # Initialize the server
        await server.initialize()
        
        # Handle stdin/stdout communication (MCP standard)
        while True:
            try:
                # Read JSON-RPC request from stdin
                line = sys.stdin.readline()
                if not line:
                    break
                    
                request_data = json.loads(line.strip())
                
                # Process the request
                response = await server.process_request(request_data)
                
                # Send response to stdout
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                # Send error response for invalid JSON
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }
                print(json.dumps(error_response), flush=True)
                
            except KeyboardInterrupt:
                break
                
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                error_response = {
                    "jsonrpc": "2.0", 
                    "id": None,
                    "error": {"code": -32603, "message": "Internal error"}
                }
                print(json.dumps(error_response), flush=True)
                
    except Exception as e:
        logging.error(f"Failed to start MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
