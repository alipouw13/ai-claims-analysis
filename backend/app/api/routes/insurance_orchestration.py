"""
Insurance Orchestration API Routes

This module provides API endpoints for insurance workflow orchestration using Semantic Kernel.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.core.observability import observability
from app.services.agents import SemanticKernelInsuranceOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)

# Global orchestrator instance
_insurance_orchestrator: Optional[SemanticKernelInsuranceOrchestrator] = None

async def get_insurance_orchestrator() -> SemanticKernelInsuranceOrchestrator:
    """Get or create insurance orchestrator instance"""
    global _insurance_orchestrator
    
    if _insurance_orchestrator is None:
        try:
            _insurance_orchestrator = SemanticKernelInsuranceOrchestrator()
            await _insurance_orchestrator.initialize()
            logger.info("Insurance orchestrator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize insurance orchestrator: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize insurance orchestrator: {str(e)}"
            )
    
    return _insurance_orchestrator

@router.post("/orchestrate")
async def orchestrate_insurance_workflow(
    workflow_type: str,
    input_data: Dict[str, Any],
    parallel_execution: bool = True,
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Orchestrate insurance workflow using Semantic Kernel
    
    Args:
        workflow_type: Type of workflow ("policy_analysis", "claims_processing", "customer_support")
        input_data: Input data for the workflow
        parallel_execution: Whether to execute agents in parallel
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Workflow orchestration results
    """
    try:
        observability.track_request("orchestrate_insurance_workflow")
        
        # Validate workflow type
        valid_workflow_types = ["policy_analysis", "claims_processing", "customer_support"]
        if workflow_type not in valid_workflow_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid workflow_type. Must be one of: {valid_workflow_types}"
            )
        
        # Execute workflow orchestration
        result = await orchestrator.orchestrate_workflow(
            workflow_type=workflow_type,
            input_data=input_data,
            parallel_execution=parallel_execution
        )
        
        logger.info(f"Insurance workflow orchestration completed: {workflow_type}")
        return {
            "success": True,
            "workflow_type": workflow_type,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Insurance workflow orchestration failed: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="orchestrate_insurance_workflow"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Workflow orchestration failed: {str(e)}"
        )

@router.post("/policy/analyze")
async def analyze_insurance_policy(
    domain: str,
    policy_data: Dict[str, Any],
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Analyze insurance policy using domain-specific agent
    
    Args:
        domain: Insurance domain ("auto", "life", "health", "dental", "general")
        policy_data: Policy data to analyze
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Policy analysis results
    """
    try:
        observability.track_request("analyze_insurance_policy")
        
        # Validate domain
        valid_domains = ["auto", "life", "health", "dental", "general"]
        if domain not in valid_domains:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain. Must be one of: {valid_domains}"
            )
        
        # Execute policy analysis
        result = await orchestrator.orchestrate_workflow(
            workflow_type="policy_analysis",
            input_data={"domain": domain, "policy_data": policy_data},
            parallel_execution=True
        )
        
        logger.info(f"Insurance policy analysis completed for domain: {domain}")
        return {
            "success": True,
            "domain": domain,
            "analysis_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Insurance policy analysis failed: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="analyze_insurance_policy"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Policy analysis failed: {str(e)}"
        )

@router.post("/claims/process")
async def process_insurance_claim(
    domain: str,
    claim_data: Dict[str, Any],
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Process insurance claim using domain-specific agent
    
    Args:
        domain: Insurance domain ("auto", "life", "health", "dental", "general")
        claim_data: Claim data to process
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Claim processing results
    """
    try:
        observability.track_request("process_insurance_claim")
        
        # Validate domain
        valid_domains = ["auto", "life", "health", "dental", "general"]
        if domain not in valid_domains:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain. Must be one of: {valid_domains}"
            )
        
        # Execute claim processing
        result = await orchestrator.orchestrate_workflow(
            workflow_type="claims_processing",
            input_data={"domain": domain, "claim_data": claim_data},
            parallel_execution=True
        )
        
        logger.info(f"Insurance claim processing completed for domain: {domain}")
        return {
            "success": True,
            "domain": domain,
            "processing_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Insurance claim processing failed: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="process_insurance_claim"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Claim processing failed: {str(e)}"
        )

@router.post("/support/assist")
async def provide_customer_support(
    question: str,
    domain: Optional[str] = "general",
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Provide customer support for insurance inquiry
    
    Args:
        question: Customer question or inquiry
        domain: Insurance domain (optional, defaults to "general")
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Customer support response
    """
    try:
        observability.track_request("provide_customer_support")
        
        # Validate domain
        valid_domains = ["auto", "life", "health", "dental", "general"]
        if domain not in valid_domains:
            domain = "general"
        
        # Execute customer support workflow
        result = await orchestrator.orchestrate_workflow(
            workflow_type="customer_support",
            input_data={"domain": domain, "question": question},
            parallel_execution=False  # Sequential for customer support
        )
        
        logger.info(f"Customer support completed for domain: {domain}")
        return {
            "success": True,
            "domain": domain,
            "question": question,
            "support_response": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Customer support failed: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="provide_customer_support"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Customer support failed: {str(e)}"
        )

@router.get("/status")
async def get_orchestrator_status(
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Get insurance orchestrator status
    
    Args:
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Orchestrator status information
    """
    try:
        observability.track_request("get_insurance_orchestrator_status")
        
        status = orchestrator.get_orchestrator_status()
        
        return {
            "success": True,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get orchestrator status: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="get_insurance_orchestrator_status"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get orchestrator status: {str(e)}"
        )

@router.post("/tools/validate-claim")
async def validate_insurance_claim(
    claim_data: Dict[str, Any],
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Validate insurance claim using claims processing plugin
    
    Args:
        claim_data: Claim data to validate
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Claim validation results
    """
    try:
        observability.track_request("validate_insurance_claim")
        
        # Access the claims processing plugin
        claims_plugin = orchestrator.kernel.get_plugin("claims_processing")
        
        # Validate claim
        validation_result = await claims_plugin.validate_claim(claim_data)
        
        logger.info("Insurance claim validation completed")
        return {
            "success": True,
            "validation_result": validation_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Claim validation failed: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="validate_insurance_claim"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Claim validation failed: {str(e)}"
        )

@router.post("/tools/calculate-settlement")
async def calculate_claim_settlement(
    claim_data: Dict[str, Any],
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Calculate claim settlement amount using claims processing plugin
    
    Args:
        claim_data: Claim data for settlement calculation
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Settlement calculation results
    """
    try:
        observability.track_request("calculate_claim_settlement")
        
        # Access the claims processing plugin
        claims_plugin = orchestrator.kernel.get_plugin("claims_processing")
        
        # Calculate settlement
        settlement_result = await claims_plugin.calculate_settlement(claim_data)
        
        logger.info("Claim settlement calculation completed")
        return {
            "success": True,
            "settlement_result": settlement_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Settlement calculation failed: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="calculate_claim_settlement"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Settlement calculation failed: {str(e)}"
        )

@router.get("/tools/search-policies")
async def search_insurance_policies(
    query: str,
    domain: Optional[str] = None,
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Search insurance policies using policy management plugin
    
    Args:
        query: Search query
        domain: Insurance domain (optional)
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Policy search results
    """
    try:
        observability.track_request("search_insurance_policies")
        
        # Access the policy management plugin
        policy_plugin = orchestrator.kernel.get_plugin("policy_management")
        
        # Search policies
        search_result = await policy_plugin.search_policies(query, domain)
        
        logger.info(f"Policy search completed for query: {query}")
        return {
            "success": True,
            "search_result": search_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Policy search failed: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="search_insurance_policies"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Policy search failed: {str(e)}"
        )

@router.get("/tools/analyze-coverage/{policy_id}")
async def analyze_policy_coverage(
    policy_id: str,
    orchestrator: SemanticKernelInsuranceOrchestrator = Depends(get_insurance_orchestrator)
):
    """
    Analyze policy coverage using policy management plugin
    
    Args:
        policy_id: Policy ID to analyze
        orchestrator: Insurance orchestrator instance
        
    Returns:
        Coverage analysis results
    """
    try:
        observability.track_request("analyze_policy_coverage")
        
        # Access the policy management plugin
        policy_plugin = orchestrator.kernel.get_plugin("policy_management")
        
        # Analyze coverage
        coverage_result = await policy_plugin.analyze_policy_coverage(policy_id)
        
        logger.info(f"Policy coverage analysis completed for policy: {policy_id}")
        return {
            "success": True,
            "policy_id": policy_id,
            "coverage_result": coverage_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Coverage analysis failed: {e}")
        observability.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            endpoint="analyze_policy_coverage"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Coverage analysis failed: {str(e)}"
        )
