"""
Evaluation API Routes

Provides endpoints for evaluating QA answers using different evaluation methods
and retrieving evaluation results and summaries.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, Query, Path
from datetime import datetime, timedelta

from app.models.schemas import (
    EvaluationRequest, EvaluationResult, EvaluationSummary,
    EvaluatorType, EvaluationMetric
)
from app.services.evaluation_service import evaluation_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate_answer(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    app_request: Request,
    background: bool = Query(False, description="Run evaluation in background")
):
    """
    Evaluate a QA answer using the specified evaluator type.
    
    If background=True, returns immediately with a pending result and runs evaluation in background.
    If background=False (default), waits for evaluation to complete and returns the result.
    """
    try:
        # Ensure AI Foundry project connection is available when evaluator_type is foundry
        if request.evaluator_type.value == 'foundry' and not settings.AZURE_AI_PROJECT_CONNECTION_STRING:
            raise HTTPException(status_code=400, detail="Azure AI Foundry connection string not configured")
        logger.info(f"Received evaluation request for question_id: {request.question_id}, background: {background}")
        
        # Get azure_manager from app state
        azure_manager = getattr(app_request.app.state, 'azure_manager', None)
        
        if background:
            # Return immediately with pending status and run evaluation in background
            pending_result = EvaluationResult(
                question_id=request.question_id,
                session_id=request.session_id,
                evaluator_type=request.evaluator_type,
                rag_method=request.rag_method,
                question=request.question,
                answer=request.answer,
                context=request.context,
                ground_truth=request.ground_truth,
                evaluation_model=request.evaluation_model or "o3-mini",
                reasoning="Evaluation is running in background",
                metadata={"status": "pending", "background": True},
                evaluation_timestamp=datetime.utcnow()
            )
            
            # Store pending result first
            await evaluation_service._store_result(pending_result)
            
            # Add background task for actual evaluation
            background_tasks.add_task(
                evaluation_service._background_evaluate_and_store,
                request,
                azure_manager,
                pending_result.id
            )
            
            logger.info(f"Started background evaluation for question_id: {request.question_id}")
            return pending_result
        else:
            # Perform evaluation synchronously and return result
            result = await evaluation_service.evaluate_answer(request, azure_manager)
            
            # Note: Result is already stored in Cosmos DB by evaluation_service
            logger.info(f"Evaluation completed for question_id: {request.question_id}")
            
            return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_answer endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate/batch", response_model=List[EvaluationResult])
async def evaluate_batch(
    requests: List[EvaluationRequest],
    background_tasks: BackgroundTasks
):
    """
    Evaluate multiple QA answers in batch
    """
    try:
        logger.info(f"Received batch evaluation request for {len(requests)} items")
        
        # Perform batch evaluation
        results = await evaluation_service.evaluate_batch(requests)
        
        # Note: Results are already stored in Cosmos DB by evaluation_service
        logger.info(f"Batch evaluation completed for {len(results)} items")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in evaluate_batch endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/evaluators", response_model=Dict[str, Any])
async def get_available_evaluators():
    """
    Get information about available evaluator types and models
    """
    try:
        available = evaluation_service.get_available_evaluators()
        
        return {
            "available_evaluators": available,
            "evaluator_types": [e.value for e in EvaluatorType],
            "evaluation_metrics": [m.value for m in EvaluationMetric],
            "evaluation_models": [
                "o3-mini",
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in get_available_evaluators endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/question/{question_id}", response_model=List[EvaluationResult])
async def get_evaluation_results_by_question(
    question_id: str = Path(..., description="Question ID")
):
    """
    Get all evaluation results for a specific question
    """
    try:
        # Use evaluation service to get results
        results = await evaluation_service.get_results_by_question(question_id)
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting evaluation results for question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/session/{session_id}", response_model=List[EvaluationResult])
async def get_evaluation_results_by_session(
    session_id: str = Path(..., description="Session ID"),
    evaluator_type: Optional[EvaluatorType] = Query(None, description="Filter by evaluator type"),
    rag_method: Optional[str] = Query(None, description="Filter by RAG method"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results")
):
    """
    Get evaluation results for a session with optional filtering
    """
    try:
        # Use evaluation service to get results
        results = await evaluation_service.get_results_by_session(
            session_id, evaluator_type, rag_method, limit
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting evaluation results for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary/session/{session_id}", response_model=EvaluationSummary)
async def get_evaluation_summary(
    session_id: str = Path(..., description="Session ID"),
    evaluator_type: Optional[EvaluatorType] = Query(None, description="Filter by evaluator type"),
    rag_method: Optional[str] = Query(None, description="Filter by RAG method")
):
    """
    Get evaluation summary for a session
    """
    try:
        # Use evaluation service to get summary
        summary = await evaluation_service.get_session_summary(
            session_id, evaluator_type, rag_method
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting evaluation summary for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics", response_model=Dict[str, Any])
async def get_evaluation_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    evaluator_type: Optional[EvaluatorType] = Query(None, description="Filter by evaluator type"),
    rag_method: Optional[str] = Query(None, description="Filter by RAG method")
):
    """
    Get evaluation analytics across multiple sessions
    """
    try:
        # Use evaluation service to get analytics
        analytics = await evaluation_service.get_analytics(
            days, evaluator_type, rag_method
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting evaluation analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate/foundry", response_model=List[EvaluationResult])
async def evaluate_with_azure_ai_foundry(
    request: EvaluationRequest,
    app_request: Request,
    background: bool = Query(False, description="Run evaluation in background")
):
    """
    Evaluate a QA answer specifically using Azure AI Foundry evaluators.
    
    This endpoint uses Azure AI Foundry's built-in evaluators for:
    - Groundedness
    - Relevance  
    - Coherence
    - Fluency
    - Agent-specific metrics (if applicable)
    """
    try:
        # Force evaluator type to foundry
        request.evaluator_type = EvaluatorType.foundry
        
        logger.info(f"Received Azure AI Foundry evaluation request for question_id: {request.question_id}")
        
        # Get azure_manager from app state
        azure_manager = getattr(app_request.app.state, 'azure_manager', None)
        if not azure_manager:
            raise HTTPException(status_code=500, detail="Azure services not initialized")
        
        # Get evaluation framework
        try:
            from app.core.evaluation import get_evaluation_framework
            evaluation_framework = get_evaluation_framework()
            
            # Prepare evaluation context
            from app.models.evaluation import FinancialEvaluationContext
            
            context = FinancialEvaluationContext(
                query=request.question,
                response=request.answer,
                sources=request.context or [],
                document_types=["financial"],
                financial_context={"session_id": request.session_id}
            )
            
            # Run Azure AI Foundry evaluation
            results = await evaluation_framework.evaluate_response(
                query=request.question,
                response=request.answer,
                sources=request.context or [],
                session_id=request.session_id,
                model_used=request.evaluation_model or "gpt-4.1-mini",
                response_time=0.0,  # Not measured in this context
                ground_truth=request.ground_truth,
                financial_context={"session_id": request.session_id}
            )
            
            logger.info(f"Azure AI Foundry evaluation completed for question_id: {request.question_id}, got {len(results)} results")
            return results
            
        except Exception as eval_error:
            logger.error(f"Azure AI Foundry evaluation framework error: {eval_error}")
            raise HTTPException(status_code=500, detail=f"Evaluation framework error: {str(eval_error)}")
        
    except Exception as e:
        logger.error(f"Error in Azure AI Foundry evaluation endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/foundry/status", response_model=Dict[str, Any])
async def get_foundry_evaluation_status():
    """
    Get the status of Azure AI Foundry evaluation configuration
    """
    try:
        from app.core.evaluation import get_evaluation_framework
        from app.core.config import settings
        
        # Check environment configuration
        env_config = {
            "AZURE_AI_FOUNDRY_EVALUATION_ENABLED": settings.AZURE_AI_FOUNDRY_EVALUATION_ENABLED,
            "EVALUATION_FRAMEWORK_TYPE": settings.EVALUATION_FRAMEWORK_TYPE,
            "AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING_SET": bool(settings.AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING),
            "AZURE_AI_FOUNDRY_EVALUATOR_MODEL": settings.AZURE_AI_FOUNDRY_EVALUATOR_MODEL
        }
        
        try:
            evaluation_framework = get_evaluation_framework()
            framework_type = evaluation_framework.framework_type.value
            azure_config_status = "configured" if evaluation_framework.azure_ai_foundry_evaluator else "not_configured"
            
            return {
                "status": "available",
                "framework_type": framework_type,
                "azure_ai_foundry_configured": azure_config_status == "configured",
                "environment_config": env_config,
                "available_evaluators": [
                    "groundedness",
                    "relevance", 
                    "coherence",
                    "fluency",
                    "retrieval"
                ],
                "agent_evaluators": [
                    "intent_resolution",
                    "tool_call_accuracy", 
                    "task_adherence"
                ],
                "framework_details": {
                    "type": framework_type,
                    "azure_evaluator_initialized": evaluation_framework.azure_ai_foundry_evaluator is not None,
                    "azure_agent_evaluator_initialized": evaluation_framework.azure_ai_foundry_agent_evaluator is not None
                }
            }
        except RuntimeError as e:
            return {
                "status": "not_initialized",
                "framework_type": "unknown", 
                "azure_ai_foundry_configured": False,
                "environment_config": env_config,
                "error": f"Evaluation framework not initialized: {str(e)}",
                "recommendation": "Check that evaluation framework is properly set up in main.py"
            }
        
    except Exception as e:
        logger.error(f"Error getting foundry status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/results/session/{session_id}")
async def delete_evaluation_results(
    session_id: str = Path(..., description="Session ID")
):
    """
    Delete all evaluation results for a session
    """
    try:
        # Use evaluation service to delete results
        deleted_count = await evaluation_service.delete_session_results(session_id)
        
        return {"message": f"Deleted {deleted_count} evaluation results"}
        
    except Exception as e:
        logger.error(f"Error deleting evaluation results for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{evaluation_id}", response_model=EvaluationResult)
async def get_evaluation_result(
    app_request: Request,
    evaluation_id: str = Path(..., description="Evaluation ID")
):
    """
    Get a specific evaluation result by its ID from Cosmos DB
    """
    try:
        logger.info(f"Getting evaluation result for ID: {evaluation_id}")
        
        # Get azure_manager from app state
        azure_manager = getattr(app_request.app.state, 'azure_manager', None)
        
        # Temporarily set azure_manager for this operation
        original_azure_manager = evaluation_service.azure_manager
        evaluation_service.azure_manager = azure_manager
        
        try:
            # Retrieve from Cosmos DB using evaluation service
            result = await evaluation_service.get_evaluation_result(evaluation_id)
        finally:
            # Restore original azure_manager
            evaluation_service.azure_manager = original_azure_manager
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"Evaluation result with ID {evaluation_id} not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation result {evaluation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Note: All Cosmos DB operations and analytics calculations are handled 
# by the evaluation_service to maintain separation of concerns
