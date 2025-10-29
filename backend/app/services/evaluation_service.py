"""
Comprehensive Evaluation Service for RAG QA System

This service provides both Azure AI Foundry and Custom evaluation capabilities
for all RAG methods, measuring various metrics like groundedness, relevance,
coherence, and fluency.

Azure AI Foundry evaluators are run in a subprocess to avoid HTTP client conflicts.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os

# Import OpenAI for custom evaluation
from openai import AsyncAzureOpenAI
from azure.identity import ClientSecretCredential

from ..core.config import settings
from ..models.schemas import (
    EvaluationRequest, EvaluationResult, EvaluationSummary, 
    EvaluatorType, EvaluationMetric
)
from ..core.observability import observability

logger = logging.getLogger(__name__)

class EvaluationService:
    """
    Main evaluation service that orchestrates both Foundry and Custom evaluators
    """
    
    def __init__(self):
        self.foundry_evaluator = None
        self.custom_evaluator = None
        self._foundry_initialized = False
        self._custom_initialized = False
        self.azure_manager = None  # Will be set when needed for evaluation
    
    def _ensure_foundry_evaluator(self):
        """Lazy initialization of Foundry evaluator"""
        if not self._foundry_initialized:
            self._foundry_initialized = True
            try:
                # Check for Azure AI Foundry project connection string
                if settings.AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING and settings.AZURE_AI_FOUNDRY_EVALUATION_ENABLED:
                    self.foundry_evaluator = FoundryEvaluator()
                    logger.info("Azure AI Foundry evaluator initialized")
                else:
                    logger.warning(f"Azure AI Foundry configuration missing - connection_string: {bool(settings.AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING)}, enabled: {settings.AZURE_AI_FOUNDRY_EVALUATION_ENABLED}")
                    self.foundry_evaluator = None
            except Exception as e:
                logger.warning(f"Failed to initialize Foundry evaluator: {e}")
                self.foundry_evaluator = None

    async def _log_run_to_foundry_portal(self, request: EvaluationRequest, result: 'EvaluationResult') -> Optional[str]:
        """If configured, log an evaluation row to Azure AI Foundry so the run appears in the portal.

        We use the azure.ai.evaluation `evaluate` helper with a single-row JSONL dataset created in-memory.
        Returns a Studio URL if available, otherwise None. This is best-effort and non-blocking for main flow.
        """
        try:
            from azure.ai.evaluation import evaluate as az_evaluate, EvaluationResult as AzEvalResult
            if not settings.AZURE_AI_PROJECT_CONNECTION_STRING:
                return None
            # Lazy import to avoid global dependency at module import time
            from azure.ai.projects import AIProjectClient
            project = AIProjectClient.from_connection_string(settings.AZURE_AI_PROJECT_CONNECTION_STRING)

            # Build a single-row dataset payload
            row = {
                "query": request.question,
                "response": result.answer or "",
                "context": "\n".join(request.context or []),
            }

            data = [row]
            metrics = ["groundedness", "relevance", "coherence", "fluency"]
            # Run evaluate; this logs to the Foundry project by default when a project client is provided
            eval_out = az_evaluate(
                data=data,
                evaluators=metrics,
                project=project,
            )

            # Try to extract portal URL
            studio_url = getattr(eval_out, "studio_url", None)
            # Fallback: some versions expose run_url, or output dict
            if not studio_url and isinstance(eval_out, dict):
                studio_url = eval_out.get("studio_url") or eval_out.get("run_url")
            return studio_url
        except Exception as e:
            logger.debug(f"Foundry portal logging skipped: {e}")
            return None
    
    def _ensure_custom_evaluator(self):
        """Lazy initialization of Custom evaluator"""
        if not self._custom_initialized:
            self._custom_initialized = True
            try:
                if settings.AZURE_EVALUATION_ENDPOINT or settings.AZURE_OPENAI_ENDPOINT:
                    logger.info(f"Initializing Custom evaluator with endpoint: {settings.AZURE_EVALUATION_ENDPOINT or settings.AZURE_OPENAI_ENDPOINT}")
                    logger.info(f"Using model deployment: {settings.AZURE_EVALUATION_MODEL_DEPLOYMENT}")
                    self.custom_evaluator = CustomEvaluator()
                    logger.info("Custom evaluator initialized successfully")
                else:
                    logger.warning("Custom evaluation configuration missing, custom evaluator disabled")
            except Exception as e:
                logger.error(f"Failed to initialize Custom evaluator: {e}")
                import traceback
                logger.error(f"Custom evaluator traceback:\n{traceback.format_exc()}")
                self.custom_evaluator = None
    
    def get_available_evaluators(self) -> Dict[str, Any]:
        """Get information about available evaluators"""
        # Ensure evaluators are initialized
        self._ensure_foundry_evaluator()
        self._ensure_custom_evaluator()
        
        # Check if Azure AI Foundry evaluation framework is available
        foundry_available = False
        try:
            from app.core.evaluation import get_evaluation_framework
            evaluation_framework = get_evaluation_framework()
            foundry_available = (
                evaluation_framework.framework_type.value in ["azure_ai_foundry", "hybrid"] and
                evaluation_framework.azure_ai_foundry_evaluator is not None
            )
        except RuntimeError:
            # Evaluation framework not initialized
            foundry_available = False
        except Exception as e:
            logger.warning(f"Error checking evaluation framework: {e}")
            foundry_available = False
        
        # Also check environment variable configuration
        from app.core.config import settings
        foundry_config_available = (
            settings.AZURE_AI_FOUNDRY_EVALUATION_ENABLED and 
            settings.EVALUATION_FRAMEWORK_TYPE in ["azure_ai_foundry", "hybrid"] and
            bool(settings.AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING)
        )
        
        # Foundry is available if either the framework is loaded OR config is properly set
        foundry_available = foundry_available or foundry_config_available
        
        return {
            "foundry_available": foundry_available,
            "custom_available": self.custom_evaluator is not None or True,  # Custom is always available
            "supported_evaluators": [
                {
                    "type": "foundry", 
                    "available": foundry_available,
                    "metrics": ["groundedness", "relevance", "coherence", "fluency", "retrieval"],
                    "agent_metrics": ["intent_resolution", "tool_call_accuracy", "task_adherence"],
                    "framework_type": getattr(settings, 'EVALUATION_FRAMEWORK_TYPE', 'custom'),
                    "config_status": {
                        "foundry_enabled": settings.AZURE_AI_FOUNDRY_EVALUATION_ENABLED,
                        "connection_string_set": bool(settings.AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING),
                        "framework_type": settings.EVALUATION_FRAMEWORK_TYPE
                    }
                },
                {
                    "type": "custom", 
                    "available": True,
                    "metrics": ["groundedness", "relevance", "coherence", "fluency", "financial_accuracy", "citation_quality"]
                }
            ]
        }
    
    async def evaluate_answer(self, request: EvaluationRequest, azure_manager=None) -> EvaluationResult:
        """
        Main evaluation method that routes to appropriate evaluator
        """
        # Temporarily store azure_manager for this evaluation
        original_azure_manager = self.azure_manager
        if azure_manager:
            self.azure_manager = azure_manager
        
        logger.info(f"Starting evaluation for question_id: {request.question_id}, evaluator: {request.evaluator_type}")
        
        start_time = time.time()
        
        try:
            # Route to the appropriate evaluator based on request type - NO FALLBACKS
            if request.evaluator_type == EvaluatorType.FOUNDRY:
                self._ensure_foundry_evaluator()
                if self.foundry_evaluator and getattr(self.foundry_evaluator, 'available_evaluators', {}):
                    logger.info("Using Azure AI Foundry evaluator")
                    result = await self.foundry_evaluator.evaluate(request)
                else:
                    raise ValueError("Azure AI Foundry evaluator is not available or not properly initialized")
            else:  # Custom evaluator requested
                self._ensure_custom_evaluator()
                if self.custom_evaluator and getattr(self.custom_evaluator, 'client', None):
                    logger.info("Using Custom evaluator")
                    result = await self.custom_evaluator.evaluate(request)
                else:
                    raise ValueError("Custom evaluator is not available or not properly initialized")
            
            # Set timing information
            result.evaluation_duration_ms = int((time.time() - start_time) * 1000)
            result.evaluation_timestamp = datetime.utcnow()
            # Best-effort: log this run to Azure AI Foundry portal so it appears in the UI
            try:
                studio_url = await self._log_run_to_foundry_portal(request, result)
                if studio_url:
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata["foundry_studio_url"] = studio_url
            except Exception as _log_err:
                logger.warning(f"Failed to log evaluation to Azure AI Foundry: {_log_err}")
            
            # Store result in Cosmos DB
            await self._store_result(result)
            
            logger.info(f"Evaluation completed for question_id: {request.question_id} in {result.evaluation_duration_ms}ms")
            return result
            
        except Exception as e:
            logger.error(f"Evaluation failed for question_id: {request.question_id}: {e}")
            # Return error result
            error_result = EvaluationResult(
                question_id=request.question_id,
                session_id=request.session_id,
                evaluator_type=request.evaluator_type,
                rag_method=request.rag_method,
                question=request.question,
                answer=request.answer,
                context=request.context,
                ground_truth=request.ground_truth,
                evaluation_model=request.evaluation_model or settings.AZURE_EVALUATION_MODEL_NAME,
                error_message=str(e),
                evaluation_duration_ms=int((time.time() - start_time) * 1000),
                evaluation_timestamp=datetime.utcnow()
            )
            return error_result
        finally:
            # Restore original azure_manager
            self.azure_manager = original_azure_manager
    
    async def evaluate_batch(self, requests: List[EvaluationRequest]) -> List[EvaluationResult]:
        """
        Evaluate multiple requests concurrently
        """
        logger.info(f"Starting batch evaluation for {len(requests)} requests")
        
        # Create evaluation tasks
        tasks = [self.evaluate_answer(request) for request in requests]
        
        # Execute concurrently with some limits
        semaphore = asyncio.Semaphore(5)  # Limit concurrent evaluations
        
        async def evaluate_with_semaphore(request):
            async with semaphore:
                return await self.evaluate_answer(request)
        
        results = await asyncio.gather(*[evaluate_with_semaphore(req) for req in requests])
        
        logger.info(f"Batch evaluation completed for {len(results)} requests")
        return results
    
    async def get_results_by_question(self, question_id: str) -> List[EvaluationResult]:
        """
        Get evaluation results for a specific question
        Note: This would typically query Cosmos DB, but for now returns empty list
        """
        try:
            # TODO: Implement Cosmos DB query to get results by question_id
            logger.info(f"Getting evaluation results for question_id: {question_id}")
            return []
        except Exception as e:
            logger.error(f"Error getting results by question: {e}")
            return []
    
    async def get_results_by_session(
        self, 
        session_id: str, 
        evaluator_type: Optional[EvaluatorType] = None,
        rag_method: Optional[str] = None,
        limit: int = 50
    ) -> List[EvaluationResult]:
        """
        Get evaluation results for a session with optional filtering
        Note: This would typically query Cosmos DB, but for now returns empty list
        """
        try:
            logger.info(f"Getting evaluation results for session_id: {session_id}")
            # TODO: Implement Cosmos DB query with filtering
            return []
        except Exception as e:
            logger.error(f"Error getting results by session: {e}")
            return []
    
    async def get_session_summary(
        self,
        session_id: str,
        evaluator_type: Optional[EvaluatorType] = None,
        rag_method: Optional[str] = None
    ) -> EvaluationSummary:
        """
        Get evaluation summary for a session
        """
        try:
            # Get results for the session
            results = await self.get_results_by_session(session_id, evaluator_type, rag_method, 1000)
            
            # Calculate summary
            summary = EvaluationSummary(
                session_id=session_id,
                total_evaluations=len(results),
                evaluator_type=evaluator_type or EvaluatorType.CUSTOM,
                rag_method=rag_method or "unknown",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
            
            if results:
                # Calculate averages
                groundedness_scores = [r.groundedness_score for r in results if r.groundedness_score is not None]
                relevance_scores = [r.relevance_score for r in results if r.relevance_score is not None]
                coherence_scores = [r.coherence_score for r in results if r.coherence_score is not None]
                fluency_scores = [r.fluency_score for r in results if r.fluency_score is not None]
                overall_scores = [r.overall_score for r in results if r.overall_score is not None]
                
                summary.avg_groundedness = sum(groundedness_scores) / len(groundedness_scores) if groundedness_scores else None
                summary.avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else None
                summary.avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else None
                summary.avg_fluency = sum(fluency_scores) / len(fluency_scores) if fluency_scores else None
                summary.avg_overall = sum(overall_scores) / len(overall_scores) if overall_scores else None
                
                summary.start_time = min(r.evaluation_timestamp for r in results)
                summary.end_time = max(r.evaluation_timestamp for r in results)
                
                # Find best and worst performing questions
                sorted_by_overall = sorted(
                    [r for r in results if r.overall_score is not None],
                    key=lambda x: x.overall_score,
                    reverse=True
                )
                summary.best_performing_questions = [r.question_id for r in sorted_by_overall[:5]]
                summary.worst_performing_questions = [r.question_id for r in sorted_by_overall[-5:]]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            # Return basic summary on error
            return EvaluationSummary(
                session_id=session_id,
                total_evaluations=0,
                evaluator_type=evaluator_type or EvaluatorType.CUSTOM,
                rag_method=rag_method or "unknown",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
    
    async def get_analytics(
        self,
        days: int,
        evaluator_type: Optional[EvaluatorType] = None,
        rag_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get evaluation analytics across multiple sessions
        """
        try:
            logger.info(f"Getting evaluation analytics for {days} days, evaluator_type={evaluator_type}, rag_method={rag_method}")
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Build query conditions - note: evaluation results don't have a 'type' field
            # Instead, we'll filter by the presence of evaluation-specific fields
            conditions = ['c.evaluator_type != null']  # This identifies evaluation results
            # Use evaluation_timestamp as it's the main timestamp field in evaluation results
            conditions.append(f'c.evaluation_timestamp >= "{start_date.isoformat()}"')
            conditions.append(f'c.evaluation_timestamp <= "{end_date.isoformat()}"')
            
            if evaluator_type:
                conditions.append(f'c.evaluator_type = "{evaluator_type.value}"')
            if rag_method:
                conditions.append(f'c.rag_method = "{rag_method}"')
            
            query = f"SELECT * FROM c WHERE {' AND '.join(conditions)}"
            logger.info(f"Analytics query: {query}")
            
            # Initialize azure manager if needed
            if not hasattr(self, 'azure_manager') or not self.azure_manager:
                from app.services.azure_services import AzureServiceManager
                self.azure_manager = AzureServiceManager()
                await self.azure_manager.initialize()
            
            # Query Cosmos DB directly
            if not self.azure_manager.cosmos_client:
                logger.warning("CosmosDB client not available")
                return self._get_empty_analytics()
            
            database = self.azure_manager.cosmos_client.get_database_client(settings.AZURE_COSMOS_DATABASE_NAME)
            container = database.get_container_client(settings.AZURE_COSMOS_EVALUATION_CONTAINER_NAME)
            
            # Execute query
            results = list(container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            logger.info(f"Found {len(results)} evaluation results for analytics")
            
            if not results:
                # Return empty structure if no data
                return {
                    "total_evaluations": 0,
                    "average_scores": {
                        "overall": 0.0,
                        "groundedness": 0.0,
                        "relevance": 0.0,
                        "coherence": 0.0,
                        "fluency": 0.0
                    },
                    "evaluator_distribution": {
                        "foundry": 0,
                        "custom": 0
                    },
                    "rag_method_performance": [],
                    "daily_trends": [],
                    "score_distribution": [],
                    "top_performing_sessions": []
                }
            
            # Calculate analytics
            total_evaluations = len(results)
            
            # Calculate average scores
            all_scores = {
                "overall": [],
                "groundedness": [],
                "relevance": [],
                "coherence": [],
                "fluency": []
            }
            
            evaluator_counts = {"foundry": 0, "custom": 0}
            rag_method_data = {}
            session_scores = {}
            daily_data = {}
            
            for result in results:
                evaluator_type_str = result.get("evaluator_type", "custom")
                if evaluator_type_str == "foundry":
                    evaluator_counts["foundry"] += 1
                else:
                    evaluator_counts["custom"] += 1
                
                # RAG method tracking
                rag_method_name = result.get("rag_method", "unknown")
                if rag_method_name not in rag_method_data:
                    rag_method_data[rag_method_name] = {"count": 0, "scores": []}
                rag_method_data[rag_method_name]["count"] += 1
                
                # Session tracking
                session_id = result.get("session_id")
                if session_id not in session_scores:
                    session_scores[session_id] = []
                
                # Daily tracking - use evaluation_timestamp instead of created_at
                evaluation_timestamp = result.get("evaluation_timestamp", "")
                if evaluation_timestamp:
                    try:
                        date_obj = datetime.fromisoformat(evaluation_timestamp.replace("Z", "+00:00"))
                        date_str = date_obj.strftime("%Y-%m-%d")
                        if date_str not in daily_data:
                            daily_data[date_str] = {"count": 0, "scores": []}
                        daily_data[date_str]["count"] += 1
                    except Exception as e:
                        logger.warning(f"Error parsing date {evaluation_timestamp}: {e}")
                
                # Extract scores directly from document (not from metrics field)
                result_scores = {}
                
                # Extract individual metric scores
                if result.get("groundedness_score") is not None:
                    score = float(result["groundedness_score"])
                    result_scores["groundedness"] = score
                    all_scores["groundedness"].append(score)
                
                if result.get("relevance_score") is not None:
                    score = float(result["relevance_score"])
                    result_scores["relevance"] = score
                    all_scores["relevance"].append(score)
                
                if result.get("coherence_score") is not None:
                    score = float(result["coherence_score"])
                    result_scores["coherence"] = score
                    all_scores["coherence"].append(score)
                
                if result.get("fluency_score") is not None:
                    score = float(result["fluency_score"])
                    result_scores["fluency"] = score
                    all_scores["fluency"].append(score)
                
                # Use overall_score if available, otherwise calculate it
                overall_score = result.get("overall_score")
                if overall_score is not None:
                    overall_score = float(overall_score)
                elif result_scores:
                    # Calculate overall score as average of available metrics
                    overall_score = sum(result_scores.values()) / len(result_scores)
                else:
                    overall_score = 0.0
                
                if overall_score > 0:
                    all_scores["overall"].append(overall_score)
                    session_scores[session_id].append(overall_score)
                    rag_method_data[rag_method_name]["scores"].append(overall_score)
                    
                    if evaluation_timestamp and date_str in daily_data:
                        daily_data[date_str]["scores"].append(overall_score)
            
            # Calculate averages
            average_scores = {}
            for metric, scores in all_scores.items():
                if scores:
                    average_scores[metric] = sum(scores) / len(scores)
                else:
                    average_scores[metric] = 0.0
            
            # Calculate RAG method performance
            rag_method_performance = []
            for method, data in rag_method_data.items():
                avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
                rag_method_performance.append({
                    "method": method,
                    "count": data["count"],
                    "avg_score": avg_score
                })
            
            # Calculate daily trends
            daily_trends = []
            for date_str in sorted(daily_data.keys()):
                data = daily_data[date_str]
                avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
                daily_trends.append({
                    "date": date_str,
                    "evaluations": data["count"],
                    "avg_score": avg_score
                })
            
            # Calculate top performing sessions
            top_performing_sessions = []
            for session_id, scores in session_scores.items():
                if scores:
                    avg_score = sum(scores) / len(scores)
                    top_performing_sessions.append({
                        "session_id": session_id,
                        "avg_score": avg_score,
                        "evaluation_count": len(scores)
                    })
            
            # Sort by score and take top 10
            top_performing_sessions.sort(key=lambda x: x["avg_score"], reverse=True)
            top_performing_sessions = top_performing_sessions[:10]
            
            # Calculate score distribution - adapt to score scale
            overall_scores = all_scores["overall"]
            score_distribution = []
            if overall_scores:
                # Determine if we're dealing with 1-5 scale (Foundry) or 0-1 scale (Custom)
                max_score = max(overall_scores) if overall_scores else 0
                is_foundry_scale = max_score > 1.5  # If max score > 1.5, assume 1-5 scale
                
                if is_foundry_scale:
                    # 1-5 scale distribution
                    ranges = [
                        ("1.0-2.0", 1.0, 2.0),
                        ("2.0-3.0", 2.0, 3.0),
                        ("3.0-4.0", 3.0, 4.0),
                        ("4.0-5.0", 4.0, 5.0)
                    ]
                else:
                    # 0-1 scale distribution  
                    ranges = [
                        ("0.0-0.2", 0.0, 0.2),
                        ("0.2-0.4", 0.2, 0.4),
                        ("0.4-0.6", 0.4, 0.6),
                        ("0.6-0.8", 0.6, 0.8),
                        ("0.8-1.0", 0.8, 1.0)
                    ]
                
                for range_name, min_val, max_val in ranges:
                    if range_name == ranges[-1][0]:  # Include max value in the last bucket
                        count = sum(1 for score in overall_scores if min_val <= score <= max_val)
                    else:
                        count = sum(1 for score in overall_scores if min_val <= score < max_val)
                    score_distribution.append({
                        "range": range_name,
                        "count": count
                    })
            
            analytics_result = {
                "total_evaluations": total_evaluations,
                "average_scores": average_scores,
                "evaluator_distribution": evaluator_counts,
                "rag_method_performance": rag_method_performance,
                "daily_trends": daily_trends,
                "score_distribution": score_distribution,
                "top_performing_sessions": top_performing_sessions
            }
            
            logger.info(f"Analytics calculated: {total_evaluations} evaluations, avg overall: {average_scores.get('overall', 0):.3f}")
            return analytics_result
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            import traceback
            traceback.print_exc()
            # Return empty structure on error
            return {
                "total_evaluations": 0,
                "average_scores": {
                    "overall": 0.0,
                    "groundedness": 0.0,
                    "relevance": 0.0,
                    "coherence": 0.0,
                    "fluency": 0.0
                },
                "evaluator_distribution": {
                    "foundry": 0,
                    "custom": 0
                },
                "rag_method_performance": [],
                "daily_trends": [],
                "score_distribution": [],
                "top_performing_sessions": []
            }
    
    async def delete_session_results(self, session_id: str) -> int:
        """
        Delete all evaluation results for a session
        """
        try:
            logger.info(f"Deleting evaluation results for session_id: {session_id}")
            # TODO: Implement Cosmos DB deletion
            return 0
        except Exception as e:
            logger.error(f"Error deleting session results: {e}")
            return 0

    async def _store_result(self, result: EvaluationResult) -> bool:
        """Store evaluation result in Cosmos DB"""
        try:
            if not self.azure_manager:
                logger.error("Azure manager not available for storing evaluation result")
                return False
            
            # Convert result to dictionary for storage
            result_dict = {
                "id": result.id,
                "question_id": result.question_id,
                "session_id": result.session_id,
                "evaluator_type": result.evaluator_type.value if hasattr(result.evaluator_type, 'value') else str(result.evaluator_type),
                "rag_method": result.rag_method,
                "evaluation_model": result.evaluation_model,
                "question": result.question,
                "answer": result.answer,
                "context": result.context,
                "ground_truth": result.ground_truth,
                "groundedness_score": result.groundedness_score,
                "relevance_score": result.relevance_score,
                "coherence_score": result.coherence_score,
                "fluency_score": result.fluency_score,
                "similarity_score": result.similarity_score,
                "f1_score": result.f1_score,
                "bleu_score": result.bleu_score,
                "rouge_score": result.rouge_score,
                "overall_score": result.overall_score,
                "detailed_scores": result.detailed_scores,
                "reasoning": result.reasoning,
                "feedback": result.feedback,
                "recommendations": result.recommendations,
                "metadata": result.metadata,
                "error_message": result.error_message,
                "evaluation_timestamp": result.evaluation_timestamp,
                "evaluation_duration_ms": result.evaluation_duration_ms
            }
            
            success = await self.azure_manager.save_evaluation_result(result_dict)
            if success:
                logger.info(f"Evaluation result {result.id} stored in Cosmos DB successfully")
            else:
                logger.error(f"Failed to store evaluation result {result.id} in Cosmos DB")
            return success
            
        except Exception as e:
            logger.error(f"Error storing evaluation result: {e}")
            return False

    async def get_evaluation_result(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """Retrieve evaluation result by ID"""
        try:
            if not self.azure_manager:
                logger.error("Azure manager not available for retrieving evaluation result")
                return None
            
            result_dict = await self.azure_manager.get_evaluation_result(evaluation_id)
            if not result_dict:
                return None
            
            # Convert dictionary back to EvaluationResult object
            result = EvaluationResult(
                id=result_dict.get("id"),
                question_id=result_dict.get("question_id"),
                session_id=result_dict.get("session_id"),
                evaluator_type=EvaluatorType(result_dict.get("evaluator_type")),
                rag_method=result_dict.get("rag_method"),
                evaluation_model=result_dict.get("evaluation_model"),
                question=result_dict.get("question"),
                answer=result_dict.get("answer"),
                context=result_dict.get("context", []),
                ground_truth=result_dict.get("ground_truth"),
                groundedness_score=result_dict.get("groundedness_score"),
                relevance_score=result_dict.get("relevance_score"),
                coherence_score=result_dict.get("coherence_score"),
                fluency_score=result_dict.get("fluency_score"),
                similarity_score=result_dict.get("similarity_score"),
                f1_score=result_dict.get("f1_score"),
                bleu_score=result_dict.get("bleu_score"),
                rouge_score=result_dict.get("rouge_score"),
                overall_score=result_dict.get("overall_score"),
                detailed_scores=result_dict.get("detailed_scores", {}),
                reasoning=result_dict.get("reasoning"),
                feedback=result_dict.get("feedback"),
                recommendations=result_dict.get("recommendations", []),
                metadata=result_dict.get("metadata", {}),
                error_message=result_dict.get("error_message"),
                evaluation_timestamp=result_dict.get("evaluation_timestamp"),
                evaluation_duration_ms=result_dict.get("evaluation_duration_ms")
            )
            
            # Handle datetime conversion if needed
            if isinstance(result_dict.get("evaluation_timestamp"), str):
                try:
                    result.evaluation_timestamp = datetime.fromisoformat(result_dict["evaluation_timestamp"].replace('Z', '+00:00'))
                except:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving evaluation result {evaluation_id}: {e}")
            return None

    async def list_evaluation_results(self, session_id: Optional[str] = None, question_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List evaluation results with optional filtering"""
        try:
            from app.services.azure_services import azure_manager
            return await azure_manager.list_evaluation_results(session_id, question_id, limit)
        except Exception as e:
            logger.error(f"Error listing evaluation results: {e}")
            return []

    async def _background_evaluate_and_store(self, request: EvaluationRequest, azure_manager, pending_result_id: str):
        """
        Background method to perform evaluation and update the stored result
        """
        try:
            logger.info(f"Starting background evaluation for question_id: {request.question_id}")
            
            # Store original azure_manager and set the provided one
            original_azure_manager = self.azure_manager
            self.azure_manager = azure_manager
            
            try:
                # Perform the actual evaluation (but prevent infinite recursion by calling the underlying evaluator directly)
                start_time = time.time()
                
                # Route to the appropriate evaluator based on request type
                if request.evaluator_type == EvaluatorType.FOUNDRY:
                    self._ensure_foundry_evaluator()
                    if self.foundry_evaluator and getattr(self.foundry_evaluator, 'available_evaluators', {}):
                        logger.info("Using Azure AI Foundry evaluator for background task")
                        result = await self.foundry_evaluator.evaluate(request)
                    else:
                        raise ValueError("Azure AI Foundry evaluator is not available or not properly initialized")
                else:  # Custom evaluator requested
                    self._ensure_custom_evaluator()
                    if self.custom_evaluator and getattr(self.custom_evaluator, 'client', None):
                        logger.info("Using Custom evaluator for background task")
                        result = await self.custom_evaluator.evaluate(request)
                    else:
                        raise ValueError("Custom evaluator is not available or not properly initialized")
                
                # Set timing information
                result.evaluation_duration_ms = int((time.time() - start_time) * 1000)
                result.evaluation_timestamp = datetime.utcnow()
                
                # Update the result ID to match the pending result
                result.id = pending_result_id
                result.metadata = {"status": "completed", "background": True}
                
                # Store the completed result (this will overwrite the pending result)
                await self._store_result(result)
                
                logger.info(f"Background evaluation completed for question_id: {request.question_id} in {result.evaluation_duration_ms}ms")
                
            finally:
                # Restore original azure_manager
                self.azure_manager = original_azure_manager
                
        except Exception as e:
            logger.error(f"Background evaluation failed for question_id: {request.question_id}: {e}")
            
            # Store error result
            try:
                error_result = EvaluationResult(
                    id=pending_result_id,
                    question_id=request.question_id,
                    session_id=request.session_id,
                    evaluator_type=request.evaluator_type,
                    rag_method=request.rag_method,
                    question=request.question,
                    answer=request.answer,
                    context=request.context,
                    ground_truth=request.ground_truth,
                    evaluation_model=request.evaluation_model or "o3-mini",
                    error_message=str(e),
                    metadata={"status": "error", "background": True},
                    evaluation_timestamp=datetime.utcnow()
                )
                await self._store_result(error_result)
            except Exception as store_error:
                logger.error(f"Failed to store error result: {store_error}")

class FoundryEvaluator:
    """
    Azure AI Foundry evaluator that uses subprocess isolation to avoid HTTP client conflicts.
    
    This implementation runs all Azure AI Foundry evaluations in a separate subprocess to completely
    isolate the Azure AI Evaluation SDK from the OpenAI SDK's HTTP client, preventing conflicts
    that arise from incompatible HTTP client implementations.
    
    Supported evaluators:
    - GroundednessEvaluator: Measures if the answer is supported by the provided context
    - RelevanceEvaluator: Measures how well the answer addresses the question
    - CoherenceEvaluator: Measures logical flow and understandability  
    - FluencyEvaluator: Measures language quality and readability
    """
    
    def __init__(self):
        self.available_evaluators = {}
        self._initialize_evaluators()

    def _initialize_evaluators(self):
        """Initialize Azure AI Foundry evaluators using the Azure AI Evaluation SDK"""
        try:
            logger.info("Initializing Azure AI Foundry evaluators using Azure AI Evaluation SDK...")

            # Import required components from Azure AI Evaluation SDK
            from azure.ai.evaluation import (
                GroundednessEvaluator,
                RelevanceEvaluator,
                CoherenceEvaluator,
                FluencyEvaluator,
                AzureOpenAIModelConfiguration
            )
            
            # Configure the model for evaluation
            model_config = AzureOpenAIModelConfiguration(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                azure_deployment=settings.AZURE_AI_FOUNDRY_EVALUATOR_MODEL or "gpt-4.1-mini",
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
            
            # Initialize individual evaluators
            self.available_evaluators = {
                'groundedness': GroundednessEvaluator(model_config),
                'relevance': RelevanceEvaluator(model_config),
                'coherence': CoherenceEvaluator(model_config),
                'fluency': FluencyEvaluator(model_config)
            }
            
            logger.info(f"Successfully initialized {len(self.available_evaluators)} Azure AI Foundry evaluators")

        except ImportError as e:
            logger.error(f"Azure AI Evaluation SDK not available: {e}")
            self.available_evaluators = {}
        except Exception as e:
            logger.error(f"Failed to initialize Azure AI Foundry evaluators: {e}", exc_info=True)
            self.available_evaluators = {}

    @property
    def evaluators(self):
        """Compatibility property to maintain existing interface"""
        return self.available_evaluators

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Asynchronous evaluation using Azure AI Evaluation SDK with proper Azure AI Foundry integration
        """
        if not self.evaluators:
            raise ValueError("Azure AI Foundry evaluators not available")
            
        result = EvaluationResult(
            question_id=request.question_id,
            session_id=request.session_id,
            evaluator_type=EvaluatorType.FOUNDRY,
            rag_method=request.rag_method,
            question=request.question,
            answer=request.answer,
            context=request.context,
            ground_truth=request.ground_truth,
            evaluation_model=request.evaluation_model or settings.AZURE_EVALUATION_MODEL_NAME
        )

        try:
            # Import Azure AI Evaluation SDK components for proper portal integration
            from azure.ai.evaluation import evaluate
            import tempfile
            import json
            import os
            
            # Prepare data in Azure AI Evaluation SDK format (JSONL)
            eval_data = {
                "query": request.question,
                "response": request.answer,
                "context": "\n".join(request.context) if request.context else "",
                "ground_truth": request.ground_truth or ""
            }
            
            # Create temporary JSONL file for Azure AI Evaluation SDK
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
                json.dump(eval_data, f)
                f.write('\n')
                temp_file = f.name
            
            try:
                # Configure Azure AI project for portal logging (from environment)
                azure_ai_project = None
                if settings.AZURE_SUBSCRIPTION_ID and settings.AZURE_RESOURCE_GROUP and settings.AZURE_AI_PROJECT_NAME:
                    azure_ai_project = {
                        "subscription_id": settings.AZURE_SUBSCRIPTION_ID,
                        "resource_group_name": settings.AZURE_RESOURCE_GROUP,
                        "project_name": settings.AZURE_AI_PROJECT_NAME
                    }
                    logger.info("✅ Azure AI project configured for evaluation logging to portal")
                else:
                    logger.warning("Azure AI project not fully configured - evaluations will run locally only")
                
                # Prepare evaluators with proper keyword mapping per Azure documentation
                evaluators_for_sdk = {}
                requested_metrics = [metric.value.lower() for metric in request.metrics]
                
                for metric in requested_metrics:
                    if metric in self.evaluators:
                        evaluators_for_sdk[metric] = self.evaluators[metric]
                
                logger.info(f"🚀 Running Azure AI Foundry evaluation with SDK evaluate() function for metrics: {list(evaluators_for_sdk.keys())}")
                
                # Run evaluation using Azure AI Evaluation SDK - this logs to Azure AI Foundry portal
                eval_result = evaluate(
                    data=temp_file,
                    evaluators=evaluators_for_sdk,
                    evaluator_config={
                        "groundedness": {
                            "column_mapping": {
                                "query": "${data.query}",
                                "context": "${data.context}",
                                "response": "${data.response}"
                            }
                        },
                        "relevance": {
                            "column_mapping": {
                                "query": "${data.query}",
                                "response": "${data.response}"
                            }
                        },
                        "coherence": {
                            "column_mapping": {
                                "query": "${data.query}",
                                "response": "${data.response}"
                            }
                        },
                        "fluency": {
                            "column_mapping": {
                                "query": "${data.query}",
                                "response": "${data.response}"
                            }
                        }
                    },
                    azure_ai_project=azure_ai_project,  # This enables portal logging
                )
                
                # Extract scores from Azure AI Evaluation SDK result (1-5 Likert scale)
                metrics = eval_result.get('metrics', {})
                
                # Azure AI evaluators use specific naming conventions for metrics
                groundedness_score = (
                    metrics.get('groundedness.groundedness') or 
                    metrics.get('groundedness') or 
                    0.0
                )
                relevance_score = (
                    metrics.get('relevance.relevance') or 
                    metrics.get('relevance') or 
                    0.0
                )
                coherence_score = (
                    metrics.get('coherence.coherence') or 
                    metrics.get('coherence') or 
                    0.0
                )
                fluency_score = (
                    metrics.get('fluency.fluency') or 
                    metrics.get('fluency') or 
                    0.0
                )
                
                # Calculate overall score (average of available scores)
                available_scores = [s for s in [groundedness_score, relevance_score, coherence_score, fluency_score] if s > 0]
                overall_score = sum(available_scores) / len(available_scores) if available_scores else 0.0
                
                # Update result with Azure AI Foundry scores (1-5 Likert scale)
                result.groundedness_score = groundedness_score if groundedness_score > 0 else None
                result.relevance_score = relevance_score if relevance_score > 0 else None
                result.coherence_score = coherence_score if coherence_score > 0 else None
                result.fluency_score = fluency_score if fluency_score > 0 else None
                result.overall_score = overall_score
                
                # Add detailed metadata
                result.detailed_scores = {
                    'groundedness': {'score': groundedness_score} if groundedness_score > 0 else None,
                    'relevance': {'score': relevance_score} if relevance_score > 0 else None,
                    'coherence': {'score': coherence_score} if coherence_score > 0 else None,
                    'fluency': {'score': fluency_score} if fluency_score > 0 else None,
                }
                result.detailed_scores = {k: v for k, v in result.detailed_scores.items() if v is not None}
                
                result.reasoning = f"Azure AI Foundry evaluation completed using official SDK. Scores on 1-5 Likert scale: groundedness={groundedness_score}, relevance={relevance_score}, coherence={coherence_score}, fluency={fluency_score}"
                
                # Add metadata about the evaluation
                result.metadata = {
                    "azure_ai_foundry_results": metrics,
                    "framework_type": "azure_ai_foundry",
                    "evaluation_timestamp": datetime.utcnow().isoformat(),
                    "score_scale": "1-5 Likert scale (Azure AI Foundry standard)",
                    "logged_to_foundry": azure_ai_project is not None,
                    "studio_url": eval_result.get('studio_url'),  # Link to view in Azure AI Foundry portal
                    "sdk_result": eval_result
                }
                
                logger.info(f"✅ Azure AI Foundry evaluation completed:")
                logger.info(f"  ✅ groundedness: {groundedness_score}")
                logger.info(f"  ✅ relevance: {relevance_score}")
                logger.info(f"  ✅ coherence: {coherence_score}")
                logger.info(f"  ✅ fluency: {fluency_score}")
                logger.info(f"  ✅ overall: {overall_score}")
                if azure_ai_project:
                    logger.info(f"  🔗 View in Azure AI Foundry portal: {eval_result.get('studio_url')}")
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except Exception as e:
            logger.error(f"❌ Error in Azure AI Foundry evaluation: {e}", exc_info=True)
            # Set error state but don't fail completely
            result.overall_score = 0.0
            result.reasoning = f"Azure AI Foundry evaluation failed: {str(e)}"
            result.metadata = {"error": str(e), "evaluator_type": "foundry"}

        logger.info(f"Foundry evaluation completed for question_id: {request.question_id}")
        return result

    async def _run_evaluator(self, evaluator_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Azure AI Foundry evaluator using the Azure AI Evaluation SDK
        """
        try:
            logger.info(f"Running {evaluator_name} evaluator using Azure AI Evaluation SDK...")
            
            # Get the evaluator instance
            evaluator = self.available_evaluators.get(evaluator_name)
            if not evaluator:
                raise ValueError(f"Evaluator {evaluator_name} not available")
            
            # Prepare evaluation parameters based on the evaluator requirements
            eval_params = {
                "query": data["query"],
                "response": data["response"]
            }
            
            # Add context for evaluators that need it
            if evaluator_name in ["groundedness"]:
                eval_params["context"] = data["context"]
            
            # Run evaluation in thread pool to avoid blocking
            import asyncio
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: evaluator(**eval_params)
            )
            
            # Process the result - Azure AI evaluators return different formats
            if isinstance(result, dict):
                # Extract score from various possible field names
                score = (
                    result.get("score") or
                    result.get(evaluator_name) or
                    result.get(f"gpt_{evaluator_name}") or
                    result.get(f"{evaluator_name}_score") or
                    0.0
                )
                reasoning = result.get("reason") or result.get("reasoning") or f"Azure AI Foundry {evaluator_name} evaluation"
                
                processed_result = {
                    "score": float(score),
                    "reasoning": reasoning,
                    "raw_result": result
                }
            else:
                # Some evaluators might return a simple score
                processed_result = {
                    "score": float(result) if result is not None else 0.0,
                    "reasoning": f"Azure AI Foundry {evaluator_name} evaluation",
                    "raw_result": result
                }
            
            logger.info(f"Azure AI Evaluation SDK evaluation successful for {evaluator_name}: score={processed_result['score']}")
            return processed_result
            
        except Exception as e:
            logger.error(f"Error running {evaluator_name} evaluator: {e}", exc_info=True)
            return {"score": 0.0, "error": str(e), "reasoning": f"Error in {evaluator_name} evaluation: {str(e)}"}

class CustomEvaluator:
    """
    Custom evaluator using Azure OpenAI for evaluation
    """
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client for evaluation"""
        try:
            # Use API key authentication for simpler setup
            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_EVALUATION_ENDPOINT or settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_EVALUATION_API_KEY or settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
            logger.info("Custom evaluator OpenAI client initialized with API key authentication")
            
        except Exception as e:
            logger.error(f"Failed to initialize custom evaluator: {e}")
            self.client = None
    
    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Evaluate using custom OpenAI-based evaluation
        """
        # Check if client is available
        if not self.client:
            raise ValueError("Custom evaluator OpenAI client not available")
        
        logger.info(f"Starting custom evaluation for question_id: {request.question_id}")
        logger.info(f"Requested metrics: {[m.value for m in request.metrics]}")
        
        result = EvaluationResult(
            question_id=request.question_id,
            session_id=request.session_id,
            evaluator_type=EvaluatorType.CUSTOM,
            rag_method=request.rag_method,
            question=request.question,
            answer=request.answer,
            context=request.context,
            ground_truth=request.ground_truth,
            evaluation_model=request.evaluation_model or settings.AZURE_EVALUATION_MODEL_NAME
        )
        
        try:
            # Run evaluation for each requested metric
            evaluation_tasks = []
            metric_names = []
            
            for metric in request.metrics:
                if metric == EvaluationMetric.GROUNDEDNESS:
                    evaluation_tasks.append(self._evaluate_groundedness(request))
                    metric_names.append("groundedness")
                elif metric == EvaluationMetric.RELEVANCE:
                    evaluation_tasks.append(self._evaluate_relevance(request))
                    metric_names.append("relevance")
                elif metric == EvaluationMetric.COHERENCE:
                    evaluation_tasks.append(self._evaluate_coherence(request))
                    metric_names.append("coherence")
                elif metric == EvaluationMetric.FLUENCY:
                    evaluation_tasks.append(self._evaluate_fluency(request))
                    metric_names.append("fluency")
            
            logger.info(f"Running {len(evaluation_tasks)} evaluation tasks: {metric_names}")
            
            # Run evaluations concurrently
            evaluation_results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)
            
            logger.info(f"Evaluation tasks completed, processing {len(evaluation_results)} results")
            
            # Process results
            detailed_scores = {}
            scores = []
            
            for i, (metric, metric_name) in enumerate(zip(request.metrics, metric_names)):
                logger.info(f"Processing result {i} for metric {metric_name}")
                
                if i < len(evaluation_results):
                    eval_result = evaluation_results[i]
                    
                    if isinstance(eval_result, Exception):
                        logger.error(f"Error in {metric_name} evaluation: {eval_result}")
                        detailed_scores[metric.value] = {"score": 0.0, "error": str(eval_result)}
                    else:
                        logger.info(f"{metric_name} evaluation result: {eval_result}")
                        detailed_scores[metric.value] = eval_result
                        
                        score_value = eval_result.get("score", 0.0)
                        if score_value is not None:
                            if metric == EvaluationMetric.GROUNDEDNESS:
                                result.groundedness_score = score_value
                                scores.append(score_value)
                            elif metric == EvaluationMetric.RELEVANCE:
                                result.relevance_score = score_value
                                scores.append(score_value)
                            elif metric == EvaluationMetric.COHERENCE:
                                result.coherence_score = score_value
                                scores.append(score_value)
                            elif metric == EvaluationMetric.FLUENCY:
                                result.fluency_score = score_value
                                scores.append(score_value)
                            
                            logger.info(f"Set {metric_name} score to {score_value}")
                        else:
                            logger.warning(f"No score found in {metric_name} result: {eval_result}")
                else:
                    logger.error(f"Missing result for metric {metric_name} at index {i}")
            
            # Calculate overall score
            result.overall_score = sum(scores) / len(scores) if scores else 0.0
            result.detailed_scores = detailed_scores
            result.reasoning = f"Evaluated using custom Azure OpenAI-based evaluators. Processed {len(scores)} metrics."
            
            logger.info(f"Custom evaluation completed for question_id: {request.question_id}")
            logger.info(f"Final scores: overall={result.overall_score}, groundedness={result.groundedness_score}, relevance={result.relevance_score}, coherence={result.coherence_score}, fluency={result.fluency_score}")
            
        except Exception as e:
            logger.error(f"Custom evaluation failed: {e}")
            import traceback
            logger.error(f"Custom evaluation traceback:\n{traceback.format_exc()}")
            result.error_message = str(e)
        
        return result
    
    async def _evaluate_groundedness(self, request: EvaluationRequest) -> Dict[str, Any]:
        """Evaluate groundedness using custom prompt"""
        prompt = f"""
        You are an expert evaluator assessing the groundedness of an AI-generated answer.
        Groundedness measures whether the answer is supported by the provided context.

        Question: {request.question}
        
        Context: {chr(10).join(request.context)}
        
        Answer: {request.answer}

        Please evaluate the groundedness on a scale of 0.0 to 1.0 where:
        - 1.0: Fully grounded, every claim is supported by the context
        - 0.8: Mostly grounded, most claims supported
        - 0.6: Partially grounded, some claims supported
        - 0.4: Minimally grounded, few claims supported
        - 0.2: Poorly grounded, very few claims supported
        - 0.0: Not grounded, no claims supported

        Return your evaluation as JSON:
        {{
            "score": <float between 0.0 and 1.0>,
            "reasoning": "<detailed explanation>",
            "supported_claims": ["<list of supported claims>"],
            "unsupported_claims": ["<list of unsupported claims>"]
        }}
        """
        
        return await self._call_evaluation_model(prompt)
    
    async def _evaluate_relevance(self, request: EvaluationRequest) -> Dict[str, Any]:
        """Evaluate relevance using custom prompt"""
        prompt = f"""
        You are an expert evaluator assessing the relevance of an AI-generated answer.
        Relevance measures how well the answer addresses the specific question asked.

        Question: {request.question}
        
        Answer: {request.answer}

        Please evaluate the relevance on a scale of 0.0 to 1.0 where:
        - 1.0: Perfectly relevant, directly answers the question
        - 0.8: Highly relevant, answers most aspects of the question
        - 0.6: Moderately relevant, answers some aspects
        - 0.4: Somewhat relevant, tangentially related
        - 0.2: Minimally relevant, barely addresses the question
        - 0.0: Not relevant, does not address the question

        Return your evaluation as JSON:
        {{
            "score": <float between 0.0 and 1.0>,
            "reasoning": "<detailed explanation>",
            "addressed_aspects": ["<list of question aspects addressed>"],
            "missing_aspects": ["<list of question aspects not addressed>"]
        }}
        """
        
        return await self._call_evaluation_model(prompt)
    
    async def _evaluate_coherence(self, request: EvaluationRequest) -> Dict[str, Any]:
        """Evaluate coherence using custom prompt"""
        prompt = f"""
        You are an expert evaluator assessing the coherence of an AI-generated answer.
        Coherence measures how well the answer flows logically and is easy to understand.

        Question: {request.question}
        
        Answer: {request.answer}

        Please evaluate the coherence on a scale of 0.0 to 1.0 where:
        - 1.0: Highly coherent, logical flow, easy to follow
        - 0.8: Mostly coherent, generally easy to follow
        - 0.6: Moderately coherent, some confusing parts
        - 0.4: Somewhat coherent, several confusing parts
        - 0.2: Minimally coherent, difficult to follow
        - 0.0: Incoherent, no logical flow

        Return your evaluation as JSON:
        {{
            "score": <float between 0.0 and 1.0>,
            "reasoning": "<detailed explanation>",
            "strengths": ["<list of coherent aspects>"],
            "weaknesses": ["<list of incoherent aspects>"]
        }}
        """
        
        return await self._call_evaluation_model(prompt)
    
    async def _evaluate_fluency(self, request: EvaluationRequest) -> Dict[str, Any]:
        """Evaluate fluency using custom prompt"""
        prompt = f"""
        You are an expert evaluator assessing the fluency of an AI-generated answer.
        Fluency measures the quality of language, grammar, and readability.

        Answer: {request.answer}

        Please evaluate the fluency on a scale of 0.0 to 1.0 where:
        - 1.0: Excellent fluency, perfect grammar and style
        - 0.8: Good fluency, minor issues
        - 0.6: Adequate fluency, some grammatical issues
        - 0.4: Poor fluency, many grammatical issues
        - 0.2: Very poor fluency, difficult to read
        - 0.0: Incomprehensible

        Return your evaluation as JSON:
        {{
            "score": <float between 0.0 and 1.0>,
            "reasoning": "<detailed explanation>",
            "grammar_score": <float between 0.0 and 1.0>,
            "style_score": <float between 0.0 and 1.0>,
            "readability_score": <float between 0.0 and 1.0>
        }}
        """
        
        return await self._call_evaluation_model(prompt)
    
    async def _call_evaluation_model(self, prompt: str) -> Dict[str, Any]:
        """Make a call to the evaluation model"""
        try:
            # Use the appropriate model deployment name
            model_deployment = settings.AZURE_EVALUATION_MODEL_DEPLOYMENT or settings.AZURE_OPENAI_DEPLOYMENT_NAME
            logger.info(f"Calling evaluation model: {model_deployment}")
            
            response = await self.client.chat.completions.create(
                model=model_deployment,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a precise AI evaluator. Always return valid JSON format exactly as requested."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            logger.info(f"Model response content: {content}")
            
            # Try to parse JSON response
            try:
                parsed_result = json.loads(content)
                logger.info(f"Successfully parsed JSON result: {parsed_result}")
                return parsed_result
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON parsing failed: {json_error}")
                logger.error(f"Raw content was: {content}")
                
                # Try to extract score from text if JSON parsing fails
                import re
                score_match = re.search(r'"score":\s*([0-9.]+)', content)
                if score_match:
                    extracted_score = float(score_match.group(1))
                    logger.info(f"Extracted score from text: {extracted_score}")
                    return {
                        "score": extracted_score,
                        "reasoning": content,
                        "error": "Could not parse JSON response but extracted score"
                    }
                
                # Fallback if no score found
                return {
                    "score": 0.0,
                    "reasoning": content,
                    "error": f"Could not parse JSON response: {json_error}"
                }
                
        except Exception as e:
            logger.error(f"Error calling evaluation model: {e}")
            import traceback
            logger.error(f"Evaluation model call traceback:\n{traceback.format_exc()}")
            return {
                "score": 0.0,
                "reasoning": f"Evaluation failed: {str(e)}",
                "error": str(e)
            }


# Global evaluation service instance
evaluation_service = EvaluationService()
