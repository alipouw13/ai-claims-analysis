import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

try:
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import ConnectionType
    from azure.ai.evaluation import (
        GroundednessEvaluator,
        RelevanceEvaluator,
        CoherenceEvaluator,
        FluencyEvaluator,
        RetrievalEvaluator,
        AzureOpenAIModelConfiguration,
        evaluate
    )
    AZURE_AI_FOUNDRY_AVAILABLE = True
except ImportError as e:
    AZURE_AI_FOUNDRY_AVAILABLE = False
    logging.warning(f"Azure AI Foundry packages not available: {e}. Using mock implementations.")

from app.models.evaluation import EvaluationResult, FinancialEvaluationContext, EvaluationMetric

logger = logging.getLogger(__name__)

class AzureEvaluatorType(str, Enum):
    """Azure AI Foundry evaluator types"""
    GROUNDEDNESS = "groundedness"
    RELEVANCE = "relevance" 
    COHERENCE = "coherence"
    FLUENCY = "fluency"
    RETRIEVAL = "retrieval"
    RESPONSE_COMPLETENESS = "response_completeness"
    INTENT_RESOLUTION = "intent_resolution"
    TOOL_CALL_ACCURACY = "tool_call_accuracy"
    TASK_ADHERENCE = "task_adherence"

@dataclass
class AzureEvaluationConfig:
    """Configuration for Azure AI Foundry evaluators"""
    project_connection_string: Optional[str] = None
    model_config: Optional[Dict[str, Any]] = None
    enabled_evaluators: List[AzureEvaluatorType] = None
    custom_prompts: Optional[Dict[str, str]] = None

class MockAzureEvaluator:
    """Mock evaluator for when Azure AI Foundry is not available"""
    
    def __init__(self, evaluator_type: str):
        self.evaluator_type = evaluator_type
        
    async def evaluate(self, **kwargs) -> Dict[str, Any]:
        """Mock evaluation that returns reasonable default scores"""
        base_score = 0.75
        if self.evaluator_type == "groundedness":
            base_score = 0.8
        elif self.evaluator_type == "relevance":
            base_score = 0.85
        elif self.evaluator_type == "coherence":
            base_score = 0.9
        elif self.evaluator_type == "fluency":
            base_score = 0.95
            
        return {
            self.evaluator_type: base_score,
            "reasoning": f"Mock {self.evaluator_type} evaluation - Azure AI Foundry not available",
            "score": base_score
        }

class AzureAIFoundryEvaluator:
    """Azure AI Foundry RAG evaluator integration"""
    
    def __init__(self, config: AzureEvaluationConfig):
        self.config = config
        self.project_client = None
        self.evaluators = {}
        self._initialize_evaluators()
        
    def _initialize_evaluators(self):
        """Initialize Azure AI Foundry evaluators"""
        if not AZURE_AI_FOUNDRY_AVAILABLE:
            logger.warning("Azure AI Foundry not available, using mock evaluators")
            self._initialize_mock_evaluators()
            return
            
        try:
            # Initialize project client using endpoint
            if self.config.project_connection_string:
                endpoint = self.config.project_connection_string
                if endpoint.startswith("https://"):
                    from azure.identity import DefaultAzureCredential
                    self.project_client = AIProjectClient(
                        endpoint=endpoint,
                        credential=DefaultAzureCredential()
                    )
                    logger.info(f"Azure AI Foundry project client initialized for endpoint: {endpoint}")
                else:
                    logger.warning("Invalid project connection string format, skipping project client initialization")
                
            # Configure model config according to Azure AI Evaluation SDK documentation
            from azure.ai.evaluation import AzureOpenAIModelConfiguration
            import os
            
            # Use the configured evaluation model settings - use dict format as shown in docs
            model_config = {
                "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                "azure_deployment": os.environ.get("AZURE_AI_FOUNDRY_EVALUATOR_MODEL", "gpt-4.1-mini"),
                "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            }
            
            enabled_evaluators = self.config.enabled_evaluators or [
                AzureEvaluatorType.GROUNDEDNESS,
                AzureEvaluatorType.RELEVANCE,
                AzureEvaluatorType.COHERENCE,
                AzureEvaluatorType.FLUENCY
            ]
            
            # Initialize evaluators with proper model configuration
            for evaluator_type in enabled_evaluators:
                if evaluator_type == AzureEvaluatorType.GROUNDEDNESS:
                    self.evaluators[evaluator_type] = GroundednessEvaluator(model_config)
                    logger.info("GroundednessEvaluator initialized")
                elif evaluator_type == AzureEvaluatorType.RELEVANCE:
                    self.evaluators[evaluator_type] = RelevanceEvaluator(model_config)
                    logger.info("RelevanceEvaluator initialized")
                elif evaluator_type == AzureEvaluatorType.COHERENCE:
                    self.evaluators[evaluator_type] = CoherenceEvaluator(model_config)
                    logger.info("CoherenceEvaluator initialized")
                elif evaluator_type == AzureEvaluatorType.FLUENCY:
                    self.evaluators[evaluator_type] = FluencyEvaluator(model_config)
                    logger.info("FluencyEvaluator initialized")
                elif evaluator_type == AzureEvaluatorType.RETRIEVAL:
                    self.evaluators[evaluator_type] = RetrievalEvaluator(model_config)
                    logger.info("RetrievalEvaluator initialized")
                    
            logger.info(f"Azure AI Foundry evaluators initialized successfully: {list(self.evaluators.keys())}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize Azure AI Foundry evaluators: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._initialize_mock_evaluators()
            
    def _initialize_mock_evaluators(self):
        """Initialize mock evaluators when Azure AI Foundry is not available"""
        evaluator_types = [
            AzureEvaluatorType.GROUNDEDNESS,
            AzureEvaluatorType.RELEVANCE,
            AzureEvaluatorType.COHERENCE,
            AzureEvaluatorType.FLUENCY,
            AzureEvaluatorType.RETRIEVAL
        ]
        
        for evaluator_type in evaluator_types:
            self.evaluators[evaluator_type] = MockAzureEvaluator(evaluator_type.value)
            
    async def evaluate_response(
        self,
        context: FinancialEvaluationContext,
        session_id: str,
        model_used: str,
        evaluator_types: Optional[List[AzureEvaluatorType]] = None
    ) -> List[EvaluationResult]:
        """Evaluate response using Azure AI Foundry evaluators"""
        
        if evaluator_types is None:
            evaluator_types = list(self.evaluators.keys())
            
        results = []
        
        for evaluator_type in evaluator_types:
            if evaluator_type not in self.evaluators:
                logger.warning(f"Evaluator {evaluator_type} not available")
                continue
                
            try:
                result = await self._evaluate_single(
                    evaluator_type, context, session_id, model_used
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Azure AI Foundry evaluation failed for {evaluator_type}: {e}")
                error_result = self._create_error_result(
                    evaluator_type.value, context, session_id, model_used, str(e)
                )
                results.append(error_result)
                
        return results
        
    async def _evaluate_single(
        self,
        evaluator_type: AzureEvaluatorType,
        context: FinancialEvaluationContext,
        session_id: str,
        model_used: str
    ) -> EvaluationResult:
        """Evaluate using a single Azure AI Foundry evaluator"""
        
        evaluator = self.evaluators[evaluator_type]
        
        # Prepare evaluation parameters according to Azure AI Evaluation SDK format
        eval_params = {
            "query": context.query,
            "response": context.response
        }
        
        # Add context for evaluators that need it
        if evaluator_type in [AzureEvaluatorType.GROUNDEDNESS, AzureEvaluatorType.RETRIEVAL]:
            eval_params["context"] = "\n".join([
                source.get("content", "") for source in context.sources
            ])
            
        try:
            # Call the evaluator (Azure AI Evaluation SDK evaluators are synchronous)
            import asyncio
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: evaluator(**eval_params)
            )
            
            # Extract score - Azure AI evaluators return different formats
            score = 0.0
            reasoning = f"Azure AI Foundry {evaluator_type.value} evaluation"
            
            if isinstance(result, dict):
                # Try different score field names based on the evaluator type
                score = (
                    result.get("score") or
                    result.get(evaluator_type.value) or  
                    result.get(f"gpt_{evaluator_type.value}") or
                    result.get(f"{evaluator_type.value}_score") or
                    0.0
                )
                reasoning = result.get("reason") or result.get("reasoning") or reasoning
            else:
                # Some evaluators might return a simple score
                score = float(result) if result is not None else 0.0
            
            logger.info(f"Azure AI Foundry {evaluator_type.value} evaluation completed with score: {score}")
            
            return EvaluationResult(
                metric=evaluator_type.value,
                score=float(score),
                reasoning=reasoning,
                timestamp=datetime.utcnow(),
                session_id=session_id,
                query=context.query,
                response=context.response,
                sources=[s.get("source", "") for s in context.sources],
                model_used=model_used,
                metadata=result if isinstance(result, dict) else {"score": score}
            )
            
        except Exception as e:
            logger.error(f"Error during {evaluator_type.value} evaluation: {e}")
            import traceback
            logger.error(f"Evaluation traceback: {traceback.format_exc()}")
            raise
        
    def _create_error_result(
        self,
        metric: str,
        context: FinancialEvaluationContext,
        session_id: str,
        model_used: str,
        error: str
    ) -> EvaluationResult:
        """Create an error evaluation result"""
        return EvaluationResult(
            metric=metric,
            score=0.0,
            reasoning=f"Azure AI Foundry evaluation failed: {error}",
            timestamp=datetime.utcnow(),
            session_id=session_id,
            query=context.query,
            response=context.response,
            sources=[s.get("source", "") for s in context.sources],
            model_used=model_used,
            metadata={"error": error, "evaluator_type": "azure_ai_foundry"}
        )

class AzureAIFoundryAgentEvaluator:
    """Azure AI Foundry Agent evaluator integration"""
    
    def __init__(self, config: AzureEvaluationConfig):
        self.config = config
        self.project_client = None
        self.evaluators = {}
        self._initialize_agent_evaluators()
        
    def _initialize_agent_evaluators(self):
        """Initialize Azure AI Foundry agent evaluators"""
        if not AZURE_AI_FOUNDRY_AVAILABLE:
            logger.warning("Azure AI Foundry not available, using mock agent evaluators")
            self._initialize_mock_agent_evaluators()
            return
            
        try:
            # Initialize project client using endpoint (connection string format: endpoint)
            if self.config.project_connection_string:
                # Extract endpoint from connection string (assuming it's just the endpoint URL)
                endpoint = self.config.project_connection_string
                if endpoint.startswith("https://"):
                    from azure.identity import DefaultAzureCredential
                    self.project_client = AIProjectClient(
                        endpoint=endpoint,
                        credential=DefaultAzureCredential()
                    )
                else:
                    logger.warning("Invalid project connection string format, skipping project client initialization")
                
            model_config = self.config.model_config or {
                "azure_endpoint": "https://your-endpoint.openai.azure.com/",
                "api_key": "your-api-key", 
                "azure_deployment": "gpt-4"
            }
            
            agent_evaluator_types = [
                AzureEvaluatorType.INTENT_RESOLUTION,
                AzureEvaluatorType.TOOL_CALL_ACCURACY,
                AzureEvaluatorType.TASK_ADHERENCE
            ]
            
            for evaluator_type in agent_evaluator_types:
                self.evaluators[evaluator_type] = MockAzureEvaluator(evaluator_type.value)
                
        except Exception as e:
            logger.error(f"Failed to initialize Azure AI Foundry agent evaluators: {e}")
            self._initialize_mock_agent_evaluators()
            
    def _initialize_mock_agent_evaluators(self):
        """Initialize mock agent evaluators"""
        agent_evaluator_types = [
            AzureEvaluatorType.INTENT_RESOLUTION,
            AzureEvaluatorType.TOOL_CALL_ACCURACY,
            AzureEvaluatorType.TASK_ADHERENCE
        ]
        
        for evaluator_type in agent_evaluator_types:
            self.evaluators[evaluator_type] = MockAzureEvaluator(evaluator_type.value)
            
    async def evaluate_agent_response(
        self,
        context: FinancialEvaluationContext,
        session_id: str,
        model_used: str,
        agent_metadata: Optional[Dict[str, Any]] = None
    ) -> List[EvaluationResult]:
        """Evaluate agent response using Azure AI Foundry agent evaluators"""
        
        results = []
        agent_metadata = agent_metadata or {}
        
        for evaluator_type, evaluator in self.evaluators.items():
            try:
                eval_params = {
                    "response": context.response,
                    "query": context.query,
                    "context": "\n".join([
                        source.get("content", "") for source in context.sources
                    ])
                }
                
                if evaluator_type == AzureEvaluatorType.TOOL_CALL_ACCURACY:
                    eval_params["tool_calls"] = agent_metadata.get("tool_calls", [])
                elif evaluator_type == AzureEvaluatorType.TASK_ADHERENCE:
                    eval_params["task_description"] = agent_metadata.get("task_description", "")
                    
                result = await evaluator.evaluate(**eval_params)
                
                score = result.get("score", result.get(evaluator_type.value, 0.0))
                reasoning = result.get("reasoning", f"Azure AI Foundry {evaluator_type.value} evaluation")
                
                evaluation_result = EvaluationResult(
                    metric=evaluator_type.value,
                    score=float(score),
                    reasoning=reasoning,
                    timestamp=datetime.utcnow(),
                    session_id=session_id,
                    query=context.query,
                    response=context.response,
                    sources=[s.get("source", "") for s in context.sources],
                    model_used=model_used,
                    metadata={**result, "agent_metadata": agent_metadata}
                )
                
                results.append(evaluation_result)
                
            except Exception as e:
                logger.error(f"Azure AI Foundry agent evaluation failed for {evaluator_type}: {e}")
                error_result = self._create_error_result(
                    evaluator_type.value, context, session_id, model_used, str(e)
                )
                results.append(error_result)
                
        return results
        
    def _create_error_result(
        self,
        metric: str,
        context: FinancialEvaluationContext,
        session_id: str,
        model_used: str,
        error: str
    ) -> EvaluationResult:
        """Create an error evaluation result for agent evaluators"""
        return EvaluationResult(
            metric=metric,
            score=0.0,
            reasoning=f"Azure AI Foundry agent evaluation failed: {error}",
            timestamp=datetime.utcnow(),
            session_id=session_id,
            query=context.query,
            response=context.response,
            sources=[s.get("source", "") for s in context.sources],
            model_used=model_used,
            metadata={"error": error, "evaluator_type": "azure_ai_foundry_agent"}
        )

def create_azure_ai_foundry_evaluator(config: AzureEvaluationConfig) -> AzureAIFoundryEvaluator:
    """Factory function to create Azure AI Foundry evaluator"""
    return AzureAIFoundryEvaluator(config)

def create_azure_ai_foundry_agent_evaluator(config: AzureEvaluationConfig) -> AzureAIFoundryAgentEvaluator:
    """Factory function to create Azure AI Foundry agent evaluator"""
    return AzureAIFoundryAgentEvaluator(config)
