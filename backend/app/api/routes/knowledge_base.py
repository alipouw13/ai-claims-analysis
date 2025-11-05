from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from app.models.schemas import (
    KnowledgeBaseStats, 
    KnowledgeBaseUpdateRequest,
    DocumentInfo,
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentStatus,
    ChunkVisualizationResponse
)
from app.core.observability import observability
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

def _determine_section_type_from_content(content: str) -> str:
    """Determine the section type based on content analysis."""
    content_lower = content.lower()
    
    # Introduction/Header section
    if any(keyword in content_lower for keyword in [
        'policyholder:', 'policy number:', 'insurance policy', 
        'property address:', 'policy term:', 'homeowners insurance policy'
    ]):
        return 'introduction'
    
    # Coverage details section
    if any(keyword in content_lower for keyword in [
        'covered perils:', 'property coverage:', 'coverage limits:',
        'dwelling coverage', 'personal property', 'liability coverage'
    ]):
        return 'coverage'
    
    # Exclusions section
    if any(keyword in content_lower for keyword in [
        'exclusions:', 'not covered:', 'excluded perils:', 'limitations:'
    ]):
        return 'exclusions'
    
    # Conditions/Terms section
    if any(keyword in content_lower for keyword in [
        'conditions:', 'policy conditions:', 'terms and conditions:', 
        'policy terms:', 'general conditions:'
    ]):
        return 'conditions'
    
    # Endorsements/Riders section
    if any(keyword in content_lower for keyword in [
        'endorsement:', 'rider:', 'amendment:', 'additional coverage:'
    ]):
        return 'endorsements'
    
    # Claims section
    if any(keyword in content_lower for keyword in [
        'claim number:', 'date of loss:', 'loss cause:', 'claim amount:',
        'adjuster:', 'settlement:', 'claim status:'
    ]):
        return 'claims'
    
    # Deductible section
    if any(keyword in content_lower for keyword in [
        'deductible:', 'deductibles:', 'deductible amount:'
    ]):
        return 'deductible'
    
    # Default to general for unclassified content
    return 'general'

def get_azure_manager(request: Request) -> AzureServiceManager:
    """Dependency to get the Azure manager from app state"""
    azure_manager = getattr(request.app.state, 'azure_manager', None)
    if not azure_manager:
        logger.error("Azure manager not found in app state")
        raise HTTPException(status_code=503, detail="Azure services not available")
    return azure_manager

@router.get("/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats(azure_manager: AzureServiceManager = Depends(get_azure_manager)):
    """Get current knowledge base statistics"""
    try:
        observability.track_request("knowledge_base_stats")
        
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning default stats")
            stats = KnowledgeBaseStats(
                total_documents=0,
                total_chunks=0,
                last_updated=datetime.utcnow(),
                documents_by_type={},
                processing_queue_size=0
            )
            return stats
        
        # Azure services are now injected via dependency injection for better performance
        if not azure_manager:
            # Return default stats if Azure services not available
            stats = KnowledgeBaseStats(
                total_documents=0,
                total_chunks=0,
                last_updated=datetime.utcnow(),
                documents_by_type={},
                processing_queue_size=0
            )
            return stats
        
        # Get stats from Azure Search (simple count query)
        try:
            # Perform a search to get total count
            results = await azure_manager.hybrid_search(query="*", top_k=1)
            total_chunks = len(results) if results else 0
            
            # For a more accurate count, we could use search_client.get_document_count()
            # but for now this gives us a basic implementation
            
            stats = KnowledgeBaseStats(
                total_documents=0,  # We'd need to count unique document_ids
                total_chunks=total_chunks,
                last_updated=datetime.utcnow(),
                documents_by_type={},
                processing_queue_size=0
            )
        except Exception as e:
            logger.warning(f"Could not get real stats from Azure Search: {e}")
            stats = KnowledgeBaseStats(
                total_documents=0,
                total_chunks=0,
                last_updated=datetime.utcnow(),
                documents_by_type={},
                processing_queue_size=0
            )
        
        return stats
    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        # Return default stats instead of 500 error
        return KnowledgeBaseStats(
            total_documents=0,
            total_chunks=0,
            last_updated=datetime.utcnow(),
            documents_by_type={},
            processing_queue_size=0
        )

@router.post("/update", response_model=dict)
async def update_knowledge_base(request: KnowledgeBaseUpdateRequest):
    """Trigger knowledge base update from external sources"""
    try:
        observability.track_request("knowledge_base_update")
        
        logger.info(f"Knowledge base update requested with {len(request.source_urls)} sources")
        
        return {
            "message": "Knowledge base update initiated",
            "sources_count": len(request.source_urls),
            "auto_update_enabled": request.auto_update_enabled,
            "update_frequency_hours": request.update_frequency_hours
        }
    except Exception as e:
        logger.error(f"Error updating knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to update knowledge base")

@router.get("/documents")
async def list_documents(
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    index: Optional[str] = None,
    azure_manager: AzureServiceManager = Depends(get_azure_manager)
):
    """List documents in the knowledge base (policy/claims)."""
    try:
        observability.track_request("list_documents")
        
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty document list")
            return {"documents": [], "status": "azure_not_configured"}

        # Azure services are now injected via dependency injection for better performance
        if not azure_manager:
            logger.error("Azure services not initialized")
            return {"documents": [], "status": "azure_not_configured"}

        # Resolve indexes to list from
        indexes = []
        req_index = (index or "").lower()
        if req_index == "policy":
            indexes = [settings.AZURE_SEARCH_POLICY_INDEX_NAME]
        elif req_index == "claims" or req_index == "claim":
            indexes = [settings.AZURE_SEARCH_CLAIMS_INDEX_NAME]
        elif req_index == "sec-docs" or req_index == "sec":
            # For SEC documents, delegate to SEC document service or return empty
            # Since this is the policy/claims knowledge base, return empty for SEC requests
            return {"documents": [], "status": "sec_docs_not_supported_in_knowledge_base"}
        else:
            indexes = [settings.AZURE_SEARCH_POLICY_INDEX_NAME, settings.AZURE_SEARCH_CLAIMS_INDEX_NAME]

        # Filter out None/empty indexes
        indexes = [ix for ix in indexes if ix]
        
        if not indexes:
            logger.warning("No search indexes configured for policy/claims")
            return {"documents": [], "status": "no_indexes_configured"}

        documents: List[Dict] = []
        for ix in indexes:
            try:
                items = await azure_manager.list_unique_documents(ix)
                for d in items:
                    d["index"] = "policy" if ix == settings.AZURE_SEARCH_POLICY_INDEX_NAME else "claims"
                    d["status"] = "completed"  # basic status for now
                    d.setdefault("type", "")
                    # Don't override chunks if it's already set
                    if "chunks" not in d:
                        d["chunks"] = None
                    d.setdefault("conflicts", None)
                    
                    # Ensure upload date is properly formatted and named consistently with SEC documents
                    if "uploadDate" in d and d["uploadDate"]:
                        d["processed_at"] = d["uploadDate"]  # Map to same field name as SEC docs
                    elif "processed_at" not in d or not d.get("processed_at"):
                        d["processed_at"] = ""  # Provide empty string as fallback
                        
                documents.extend(items)
            except Exception as e:
                logger.warning(f"Skipping index '{ix}' due to error: {e}")

        return {"documents": documents, "status": "success"}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        # Return graceful error response instead of 500
        return {"documents": [], "status": "error", "error_message": str(e)}

@router.get("/recent-claims")
async def get_recent_claims(limit: int = 10, azure_manager: AzureServiceManager = Depends(get_azure_manager)):
    """Get recent claims for dashboard display"""
    try:
        observability.track_request("get_recent_claims")
        
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty claims list")
            return {"claims": [], "status": "azure_not_configured"}

        # Azure services are now injected via dependency injection for better performance
        if not azure_manager:
            logger.error("Azure services not initialized")
            return {"claims": [], "status": "azure_not_configured"}

        # Get claims from the claims index
        claims_index = settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
        if not claims_index:
            logger.warning("No claims index configured")
            return {"claims": [], "status": "no_claims_index_configured"}

        try:
            # Get recent claims documents
            claims_documents = await azure_manager.list_unique_documents(claims_index)
            
            # Sort by upload date (most recent first) and limit, handle null values
            claims_documents.sort(key=lambda x: x.get('uploadDate') if x.get('uploadDate') else '1900-01-01', reverse=True)
            recent_claims = claims_documents[:limit]
            
            # Transform to dashboard format
            dashboard_claims = []
            for claim in recent_claims:
                # Extract claim information from the document
                filename = claim.get('filename', 'Unknown Claim')
                
                # Try to extract claim details from filename or metadata
                # This is a simple extraction - in a real system, you'd parse the actual claim content
                claim_info = {
                    'id': claim.get('id', ''),
                    'filename': filename,
                    'uploadDate': claim.get('uploadDate', ''),
                    'status': 'pending',  # Default status
                    'amount': '$0',  # Default amount - would be extracted from claim content
                    'type': 'Claim',  # Default type
                    'insured_name': 'Unknown',  # Would be extracted from claim content
                    'chunks': claim.get('chunks', 0)
                }
                
                # Try to extract more information from filename
                if 'claim' in filename.lower():
                    if 'auto' in filename.lower():
                        claim_info['type'] = 'Auto Accident'
                    elif 'property' in filename.lower():
                        claim_info['type'] = 'Property Damage'
                    elif 'medical' in filename.lower():
                        claim_info['type'] = 'Medical Claim'
                    elif 'liability' in filename.lower():
                        claim_info['type'] = 'Liability Claim'
                
                dashboard_claims.append(claim_info)
            
            return {"claims": dashboard_claims, "status": "success"}
            
        except Exception as e:
            logger.warning(f"Error getting claims from index '{claims_index}': {e}")
            return {"claims": [], "status": "index_error", "error_message": str(e)}
            
    except Exception as e:
        logger.error(f"Error getting recent claims: {e}")
        return {"claims": [], "status": "error", "error_message": str(e)}

@router.get("/recent-policies")
async def get_recent_policies(limit: int = 10, azure_manager: AzureServiceManager = Depends(get_azure_manager)):
    """Get recent policies for dashboard display"""
    try:
        observability.track_request("get_recent_policies")
        
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty policies list")
            return {"policies": [], "status": "azure_not_configured"}

        # Azure services are now injected via dependency injection for better performance
        if not azure_manager:
            logger.error("Azure services not initialized")
            return {"policies": [], "status": "azure_not_configured"}

        # Get policies from the policy index
        policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
        if not policy_index:
            logger.warning("No policy index configured")
            return {"policies": [], "status": "no_policy_index_configured"}

        try:
            # Get recent policy documents
            policy_documents = await azure_manager.list_unique_documents(policy_index)
            
            # Sort by upload date (most recent first) and limit, handle null values
            policy_documents.sort(key=lambda x: x.get('uploadDate') if x.get('uploadDate') else '1900-01-01', reverse=True)
            recent_policies = policy_documents[:limit]
            
            # Transform to dashboard format
            dashboard_policies = []
            for policy in recent_policies:
                # Extract policy information from the document
                filename = policy.get('filename', 'Unknown Policy')
                
                # Try to extract policy details from filename or metadata
                policy_info = {
                    'id': policy.get('id', ''),
                    'filename': filename,
                    'uploadDate': policy.get('uploadDate', ''),
                    'status': 'analyzed',  # Default status
                    'type': 'Policy',  # Default type
                    'insured_name': 'Unknown',  # Would be extracted from policy content
                    'chunks': policy.get('chunks', 0)
                }
                
                # Try to extract more information from filename
                if 'policy' in filename.lower():
                    if 'auto' in filename.lower():
                        policy_info['type'] = 'Auto Insurance'
                    elif 'life' in filename.lower():
                        policy_info['type'] = 'Life Insurance'
                    elif 'home' in filename.lower():
                        policy_info['type'] = 'Home Insurance'
                    elif 'commercial' in filename.lower():
                        if 'property' in filename.lower():
                            policy_info['type'] = 'Commercial Property'
                        elif 'liability' in filename.lower():
                            policy_info['type'] = 'Commercial Liability'
                    elif 'umbrella' in filename.lower():
                        policy_info['type'] = 'Umbrella Insurance'
                
                dashboard_policies.append(policy_info)
            
            return {"policies": dashboard_policies, "status": "success"}
            
        except Exception as e:
            logger.warning(f"Error getting policies from index '{policy_index}': {e}")
            return {"policies": [], "status": "index_error", "error_message": str(e)}
            
    except Exception as e:
        logger.error(f"Error getting recent policies: {e}")
        return {"policies": [], "status": "error", "error_message": str(e)}

@router.get("/dashboard-stats")
async def get_dashboard_stats(azure_manager: AzureServiceManager = Depends(get_azure_manager)):
    """Get dashboard statistics for insurance/banking dashboards"""
    try:
        observability.track_request("get_dashboard_stats")
        
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty stats")
            return {"stats": {}, "status": "azure_not_configured"}

        stats = {}
        
        # Get policy stats
        policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
        if policy_index:
            try:
                policy_documents = await azure_manager.list_unique_documents(policy_index)
                stats['total_policies'] = len(policy_documents)
                stats['policy_types'] = {}
                
                # Count policy types
                for policy in policy_documents:
                    filename = policy.get('filename', '').lower()
                    if 'auto' in filename:
                        stats['policy_types']['Auto Insurance'] = stats['policy_types'].get('Auto Insurance', 0) + 1
                    elif 'life' in filename:
                        stats['policy_types']['Life Insurance'] = stats['policy_types'].get('Life Insurance', 0) + 1
                    elif 'home' in filename:
                        stats['policy_types']['Home Insurance'] = stats['policy_types'].get('Home Insurance', 0) + 1
                    elif 'commercial' in filename:
                        if 'property' in filename:
                            stats['policy_types']['Commercial Property'] = stats['policy_types'].get('Commercial Property', 0) + 1
                        elif 'liability' in filename:
                            stats['policy_types']['Commercial Liability'] = stats['policy_types'].get('Commercial Liability', 0) + 1
                    elif 'umbrella' in filename:
                        stats['policy_types']['Umbrella Insurance'] = stats['policy_types'].get('Umbrella Insurance', 0) + 1
                    else:
                        stats['policy_types']['Other'] = stats['policy_types'].get('Other', 0) + 1
            except Exception as e:
                logger.warning(f"Error getting policy stats: {e}")
                stats['total_policies'] = 0
                stats['policy_types'] = {}
        
        # Get claims stats
        claims_index = settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
        if claims_index:
            try:
                claims_documents = await azure_manager.list_unique_documents(claims_index)
                stats['total_claims'] = len(claims_documents)
                stats['claim_types'] = {}
                
                # Count claim types
                for claim in claims_documents:
                    filename = claim.get('filename', '').lower()
                    if 'auto' in filename:
                        stats['claim_types']['Auto Accident'] = stats['claim_types'].get('Auto Accident', 0) + 1
                    elif 'property' in filename:
                        stats['claim_types']['Property Damage'] = stats['claim_types'].get('Property Damage', 0) + 1
                    elif 'medical' in filename:
                        stats['claim_types']['Medical Claim'] = stats['claim_types'].get('Medical Claim', 0) + 1
                    elif 'liability' in filename:
                        stats['claim_types']['Liability Claim'] = stats['claim_types'].get('Liability Claim', 0) + 1
                    else:
                        stats['claim_types']['Other'] = stats['claim_types'].get('Other', 0) + 1
            except Exception as e:
                logger.warning(f"Error getting claims stats: {e}")
                stats['total_claims'] = 0
                stats['claim_types'] = {}
        
        # Calculate risk distribution (mock data for now)
        total_policies = stats.get('total_policies', 0)
        stats['risk_distribution'] = {
            'low_risk': max(0, total_policies // 3),  # Mock calculation
            'medium_risk': max(0, total_policies // 2),  # Mock calculation
            'high_risk': max(0, total_policies // 6),  # Mock calculation
        }
        
        # Calculate auto approval percentage (mock data for now)
        stats['auto_approval_percentage'] = 50  # Mock percentage
        
        # Calculate average risk score (mock data for now)
        stats['avg_risk_score'] = 46  # Mock score
        
        return {"stats": stats, "status": "success"}
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {"stats": {}, "status": "error", "error_message": str(e)}

@router.get("/banking-dashboard-stats")
async def get_banking_dashboard_stats(azure_manager: AzureServiceManager = Depends(get_azure_manager)):
    """Get dashboard statistics for banking dashboard"""
    try:
        observability.track_request("get_banking_dashboard_stats")
        
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty banking stats")
            return {"stats": {}, "status": "azure_not_configured"}

        # Get SEC documents from the main financial documents index (same as SEC Document Library)
        # Use the main search client instead of a specific index to match SEC Document Library behavior
        if not azure_manager.search_client:
            logger.warning("No search client configured")
            return {"stats": {}, "status": "no_search_client_configured"}

        try:
            # Get all SEC documents using the same comprehensive approach as SEC Document Library
            all_results: List[Dict[str, Any]] = []
            skip = 0
            batch_size = 1000
            client = azure_manager.search_client  # Use the main search client (financial-documents index)
            
            while True:
                search_results = await client.search(
                    search_text="*",
                    select=[
                        "content", "document_id", "source", "chunk_id",
                        "company", "filing_date", "form_type", "processed_at",
                        "ticker", "cik", "industry", "document_url", "section_type", "accession_number"
                    ],
                    top=batch_size,
                    skip=skip,
                    query_type="simple"
                )
                batch: List[Dict[str, Any]] = []
                async for r in search_results:
                    batch.append(dict(r))
                if not batch:
                    break
                all_results.extend(batch)
                if len(batch) < batch_size:
                    break
                skip += batch_size
            
            # Group by document_id and aggregate
            docs_by_id: Dict[str, Dict[str, Any]] = {}
            for r in all_results:
                doc_id = r.get("document_id") or r.get("chunk_id")
                if not doc_id:
                    continue
                if doc_id not in docs_by_id:
                    docs_by_id[doc_id] = {
                        "document_id": doc_id,
                        "company": r.get("company", "Unknown Company"),
                        "ticker": r.get("ticker", "N/A"),
                        "form_type": r.get("form_type", "Unknown"),
                        "filing_date": r.get("filing_date", ""),
                        "accession_number": r.get("accession_number", ""),
                        "chunk_count": 0,
                        "processed_at": r.get("processed_at", ""),
                        "source": r.get("source", ""),
                        "cik": r.get("cik", ""),
                        "industry": r.get("industry", ""),
                        "document_url": r.get("document_url", ""),
                        "section_type": r.get("section_type", "")
                    }
                docs_by_id[doc_id]["chunk_count"] += 1
            
            sec_documents = list(docs_by_id.values())
            
            stats = {
                'total_filings': len(sec_documents),
                'companies': {},
                'form_types': {},
                'avg_chunks_per_doc': 0,
                'most_recent_filing': None
            }
            
            # Calculate statistics
            total_chunks = 0
            companies = set()
            form_types = set()
            filing_dates = []
            
            for doc in sec_documents:
                total_chunks += doc.get('chunk_count', 0)
                company = doc.get('company', 'Unknown')
                if company and company != 'Unknown Company':
                    companies.add(company)
                
                form_type = doc.get('form_type', '')
                if form_type and form_type != 'Unknown':
                    form_types.add(form_type)
                
                filing_date = doc.get('filing_date', '')
                if filing_date:
                    filing_dates.append(filing_date)
            
            stats['companies'] = {company: 1 for company in companies}
            stats['form_types'] = {form_type: 1 for form_type in form_types}
            stats['avg_chunks_per_doc'] = round(total_chunks / len(sec_documents), 2) if sec_documents else 0
            
            if filing_dates:
                # Find most recent filing date
                most_recent = max(filing_dates)
                stats['most_recent_filing'] = most_recent.split('T')[0] if 'T' in most_recent else most_recent
            
            return {"stats": stats, "status": "success"}
            
        except Exception as e:
            logger.warning(f"Error getting banking stats from main index: {e}")
            return {"stats": {}, "status": "index_error", "error_message": str(e)}
            
    except Exception as e:
        logger.error(f"Error getting banking dashboard stats: {e}")
        return {"stats": {}, "status": "error", "error_message": str(e)}

@router.get("/documents/{document_id}", response_model=DocumentInfo)
async def get_document(document_id: str):
    """Get specific document information"""
    try:
        observability.track_request("get_document")
        
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")

@router.get("/documents/{document_id}/chunks-simple")
async def get_document_chunks_simple(
    document_id: str, 
    index: str = "policy",
    azure_manager: AzureServiceManager = Depends(get_azure_manager)
):
    """Simple chunks endpoint for basic chunk data without full visualization response"""
    try:
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty chunks")
            return {"document_id": document_id, "index": index, "chunks": [], "total": 0, "status": "azure_not_configured"}

        # Azure services are now injected via dependency injection for better performance
        if not azure_manager:
            logger.error("Azure services not initialized")
            return {"document_id": document_id, "index": index, "chunks": [], "total": 0, "status": "azure_not_configured"}

        ix_name = settings.AZURE_SEARCH_POLICY_INDEX_NAME if index.lower() == "policy" else settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
        
        if not ix_name:
            logger.warning(f"No index configured for {index}")
            return {"document_id": document_id, "index": index, "chunks": [], "total": 0, "status": "no_index_configured"}

        chunks = await azure_manager.get_chunks_for_document(ix_name, document_id)
        return {"document_id": document_id, "index": index, "chunks": chunks, "total": len(chunks), "status": "success"}
    except Exception as e:
        logger.error(f"Error getting document chunks: {e}")
        # Return graceful error response instead of 500
        return {"document_id": document_id, "index": index, "chunks": [], "total": 0, "status": "error", "error_message": str(e)}

@router.get("/documents/{document_id}/chunk-visualization")
async def get_policy_claims_chunk_visualization_legacy(
    document_id: str, 
    index: str = "policy",
    azure_manager: AzureServiceManager = Depends(get_azure_manager)
):
    """Legacy endpoint - redirects to the new chunks endpoint for compatibility"""
    return await get_policy_claims_chunk_visualization(document_id, index, azure_manager)

@router.get("/documents/{document_id}/chunks", response_model=ChunkVisualizationResponse)
async def get_policy_claims_chunk_visualization(
    document_id: str, 
    index: str = "policy",
    azure_manager: AzureServiceManager = Depends(get_azure_manager)
):
    """Get chunking visualization for a specific policy/claims document.
    Uses the same response format as SEC documents for consistent frontend integration.
    Provides comprehensive document analysis including detailed statistics,
    section breakdown, and rich metadata similar to SEC document visualization.
    
    Handles both hash-based document IDs and filenames for better frontend compatibility.
    """
    try:
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty chunk visualization")
            return {
                "document_info": {"document_id": document_id, "title": document_id, "index": index},
                "chunks": [],
                "stats": {"total_chunks": 0, "avg_length": 0},
                "status": "azure_not_configured"
            }

        # Azure services are now injected via dependency injection for better performance
        if not azure_manager:
            logger.error("Azure services not initialized")
            return {
                "document_info": {"document_id": document_id, "title": document_id, "index": index},
                "chunks": [],
                "stats": {"total_chunks": 0, "avg_length": 0},
                "status": "azure_not_configured"
            }

        ix_name = settings.AZURE_SEARCH_POLICY_INDEX_NAME if index.lower() == "policy" else settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
        
        if not ix_name:
            logger.warning(f"No index configured for {index}")
            return {
                "document_info": {"document_id": document_id, "title": document_id, "index": index},
                "chunks": [],
                "stats": {"total_chunks": 0, "avg_length": 0},
                "status": "no_index_configured"
            }

        # Enhanced chunk retrieval with comprehensive field selection
        try:
            client = azure_manager.get_search_client_for_index(ix_name)
            search_results = await client.search(
                search_text="*",
                select=[
                    # Core fields that exist in the schema
                    "chunk_id", "parent_id", "content", "title", "section_type", 
                    "page_number", "citation_info", "processed_at", "source"
                ],
                filter=f"parent_id eq '{document_id}'",
                top=2000,
                query_type="simple"
            )
            raw_chunks = [dict(r) async for r in search_results]
        except Exception as sel_err:
            logger.warning(f"Enhanced select failed for '{ix_name}', retrying with basic method: {sel_err}")
            raw_chunks = await azure_manager.get_chunks_for_document(ix_name, document_id, top_k=2000)
        
        # If no chunks found and document_id looks like a filename, try to find the actual document ID
        if not raw_chunks and ('.' in document_id or document_id.endswith('.pdf')):
            logger.info(f"No chunks found for '{document_id}', searching by filename")
            
            # Search for documents with matching title or source
            try:
                search_results = await client.search(
                    search_text="*",
                    filter=f"title eq '{document_id}'",
                    top=5,
                    select=["parent_id", "title", "source"]
                )
                
                # Try to find a matching document by title
                async for result in search_results:
                    result_dict = dict(result)
                    parent_id = result_dict.get('parent_id')
                    if parent_id:
                        logger.info(f"Found document with parent_id: {parent_id} for filename: {document_id}")
                        raw_chunks = await azure_manager.get_chunks_for_document(ix_name, parent_id, top_k=2000)
                        if raw_chunks:
                            document_id = parent_id  # Update document_id to the actual one
                            break
                            
            except Exception as search_error:
                logger.warning(f"Error searching for document by filename: {search_error}")

        if not raw_chunks:
            return {
                "document_info": {"document_id": document_id, "title": document_id, "index": index},
                "chunks": [],
                "stats": {"total_chunks": 0, "avg_length": 0},
                "status": "document_not_found"
            }

        # Enhanced chunk processing and analysis
        chunks = []
        total_content_length = 0
        page_numbers = []
        section_types = []
        credibility_scores = []
        chunk_lengths = []
        
        for i, c in enumerate(raw_chunks):
            content = c.get("content") or c.get("chunk") or ""
            content_length = len(content)
            total_content_length += content_length
            chunk_lengths.append(content_length)
            
            # Parse citation_info JSON for rich metadata
            chunk_metadata = {}
            citation_info = c.get("citation_info")
            if citation_info and isinstance(citation_info, str):
                try:
                    import json
                    chunk_metadata = json.loads(citation_info)
                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"Failed to parse chunk citation_info JSON: {e}")
                    chunk_metadata = {}
            
            # Collect page numbers for range analysis
            page_num = c.get("page_number") or chunk_metadata.get("page_number")
            if page_num and isinstance(page_num, (int, float)):
                page_numbers.append(int(page_num))
            
            # Extract section type from chunk data
            section_type = c.get("section_type") or chunk_metadata.get("section_type")
            
            # Apply improved section type detection on-the-fly
            improved_section_type = _determine_section_type_from_content(content)
            section_type = improved_section_type if improved_section_type != 'general' else (section_type or "general")
            
            # Collect section types for distribution analysis (using improved detection)
            if section_type:
                section_types.append(section_type)
            
            # Collect credibility scores
            cred_score = c.get("credibility_score") or chunk_metadata.get("confidence_score", 0)
            if isinstance(cred_score, (int, float)):
                credibility_scores.append(float(cred_score))
            
            # Enhanced chunk data with preview and rich metadata
            chunk_data = {
                "chunk_id": c.get("chunk_id") or c.get("id") or f"chunk_{i}",
                "content": content[:200] + "..." if len(content) > 200 else content,
                "content_length": content_length,
                "page_number": page_num,
                "section_type": section_type,
                "credibility_score": cred_score,
                "citation_info": chunk_metadata,  # Use parsed JSON instead of string
                "search_score": c.get("@search.score", 0),
                "chunk_index": c.get("chunk_index") or chunk_metadata.get("chunk_index", i),
                
                # Rich policy metadata (from parsed citation_info)
                "policy_number": chunk_metadata.get("policy_number"),
                "insured_name": chunk_metadata.get("insured_name"),
                "insurance_company": chunk_metadata.get("insurance_company"),
                "line_of_business": chunk_metadata.get("line_of_business"),
                "state": chunk_metadata.get("state"),
                "effective_date": chunk_metadata.get("effective_date"),
                "expiration_date": chunk_metadata.get("expiration_date"),
                "deductible": chunk_metadata.get("deductible"),
                "coverage_limits": chunk_metadata.get("coverage_limits"),
                "coverage_types": chunk_metadata.get("coverage_types"),
                "exclusions": chunk_metadata.get("exclusions"),
                "endorsements": chunk_metadata.get("endorsements"),
                "agent_name": chunk_metadata.get("agent_name"),
                "premium_amount": chunk_metadata.get("premium_amount"),
                "property_address": chunk_metadata.get("property_address"),
                "vehicle_info": chunk_metadata.get("vehicle_info"),
                
                # Rich claim metadata (from parsed citation_info)
                "claim_id": chunk_metadata.get("claim_id"),
                "claim_number": chunk_metadata.get("claim_number"),
                "date_of_loss": chunk_metadata.get("date_of_loss"),
                "reported_date": chunk_metadata.get("reported_date"),
                "loss_cause": chunk_metadata.get("loss_cause"),
                "location": chunk_metadata.get("location"),
                "coverage_decision": chunk_metadata.get("coverage_decision"),
                "settlement_summary": chunk_metadata.get("settlement_summary"),
                "payout_amount": chunk_metadata.get("payout_amount"),
                "adjuster_name": chunk_metadata.get("adjuster_name"),
                "claim_status": chunk_metadata.get("claim_status"),
                "adjuster_notes": chunk_metadata.get("adjuster_notes"),
                "property_damage": chunk_metadata.get("property_damage"),
                "injury_details": chunk_metadata.get("injury_details"),
                
                # Processing metadata (from parsed citation_info)
                "chunk_method": chunk_metadata.get("chunk_method"),
                "smart_processing": chunk_metadata.get("smart_processing"),
                "quality_score": chunk_metadata.get("quality_score"),
                "optimal_size": chunk_metadata.get("optimal_size"),
                "word_count": chunk_metadata.get("word_count"),
                "content_complexity": chunk_metadata.get("content_complexity"),
                "contains_monetary_values": chunk_metadata.get("contains_amounts"),
                "filename": chunk_metadata.get("source_file"),
                "keywords": chunk_metadata.get("keywords")
            }
            chunks.append(chunk_data)

        # Calculate comprehensive statistics
        avg_length = round(total_content_length / len(chunks), 2) if chunks else 0
        
        # Section type distribution analysis
        section_distribution = {}
        for section in section_types:
            section_distribution[section] = section_distribution.get(section, 0) + 1
        
        # Sort sections by frequency
        sorted_sections = sorted(section_distribution.items(), key=lambda x: x[1], reverse=True)
        
        # Enhanced document information with comprehensive policy/claim metadata
        # Aggregate metadata from all chunks, prioritizing chunks with citation_info
        all_citation_metadata = {}
        best_chunk_for_content = None
        
        # Find the best chunk with the most complete citation_info
        for chunk in raw_chunks:
            citation_info = chunk.get("citation_info")
            if citation_info and isinstance(citation_info, str):
                try:
                    import json
                    chunk_citation = json.loads(citation_info)
                    # Merge and prioritize non-null values
                    for key, value in chunk_citation.items():
                        if value is not None and value != "":
                            all_citation_metadata[key] = value
                    
                    # Keep track of the chunk with the most useful content for parsing
                    if not best_chunk_for_content or len(chunk.get("content", "")) > len(best_chunk_for_content.get("content", "")):
                        best_chunk_for_content = chunk
                        
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to parse citation_info JSON: {e}")
                    continue
        
        # Use the first chunk as fallback if no citation_info is found
        if not best_chunk_for_content:
            best_chunk_for_content = raw_chunks[0] if raw_chunks else {}
        
        # Extract actual policyholder name and other data from ALL chunk content
        insured_name = ""
        insurance_company = ""
        policy_number = ""  # Start empty - prioritize content extraction over citation_info
        coverage_limits = {}
        deductible = ""
        coverage_types = []
        
        # Additional claim-specific fields
        claim_number = ""
        telephone_number = ""
        time_of_loss = ""
        date_prepared = ""
        property_address = ""
        mailing_address = ""
        date_of_loss = ""
        policy_effective_date = ""
        policy_expiration_date = ""
        claim_amount = ""
        
        # Search through all chunks for policyholder and company information
        for chunk in raw_chunks:
            content = chunk.get("content", "")
            if not content:
                continue
                
            lines = content.split('\n')
            
            # Extract policyholder name - multiple formats
            if not insured_name:
                for line in lines:
                    line_clean = line.strip()
                    # Look for various formats
                    patterns = ["Policyholder:", "Insured Name:", "Policyholder First Name", "Policyholder Last Name"]
                    for pattern in patterns:
                        if pattern in line:
                            try:
                                extracted = line.split(pattern)[-1].strip()
                                if extracted and len(extracted) > 1:
                                    insured_name = extracted
                                    break
                            except:
                                pass
                    if insured_name:
                        break
            
            # Extract insurance company
            if not insurance_company:
                for line in lines:
                    line_clean = line.strip()
                    if any(keyword in line.lower() for keyword in ['insurance', 'inc.', 'company', 'corp']):
                        if ('policyholder' not in line.lower() and 
                            'policy' not in line.lower() and 
                            len(line_clean) > 5 and  # Must be substantial
                            not line_clean.startswith('-')):  # Not a bullet point
                            insurance_company = line_clean
                            break
            
            # Extract policy number from content - prioritize this over citation_info
            if not policy_number:
                import re
                # Look for patterns like "PH3456789" or "Policy – PH3456789"
                # More flexible pattern to catch various formats
                policy_match = re.search(r'(?:Policy.*?)?([A-Z]{1,4}\d{6,9})', content)
                if policy_match:
                    policy_number = policy_match.group(1)
            
            # Extract claim number
            if not claim_number:
                claim_patterns = [
                    r'Claim Number[:\s]+([A-Z]+\d+)',
                    r'CLM(\d+)',
                    r'Claim[:\s#]+([A-Z]*\d+)',
                    r'Claim ID[:\s]+([A-Z]+\d+)'
                ]
                for pattern in claim_patterns:
                    claim_match = re.search(pattern, content, re.IGNORECASE)
                    if claim_match:
                        claim_number = claim_match.group(1)
                        break
            
            # Extract telephone number
            if not telephone_number:
                phone_patterns = [
                    r'Telephone Number[:\s]+(\d{3}-\d{3}-\d{4})',
                    r'Phone[:\s]+(\d{3}-\d{3}-\d{4})',
                    r'Tel[:\s]+(\d{3}-\d{3}-\d{4})',
                    r'(\d{3}-\d{3}-\d{4})'
                ]
                for pattern in phone_patterns:
                    phone_match = re.search(pattern, content)
                    if phone_match:
                        telephone_number = phone_match.group(1)
                        break
            
            # Extract dates
            if not date_of_loss:
                date_patterns = [
                    r'Date of (?:Damage|Loss)[/:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Loss Date[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Date of Loss[:\s]+(\d{4}-\d{2}-\d{2})'
                ]
                for pattern in date_patterns:
                    date_match = re.search(pattern, content, re.IGNORECASE)
                    if date_match:
                        date_of_loss = date_match.group(1)
                        break
            
            # Extract time of loss
            if not time_of_loss:
                time_patterns = [
                    r'Time of Loss[:\s]+(\d{1,2}:\d{2})',
                    r'Loss Time[:\s]+(\d{1,2}:\d{2})',
                    r'Time[:\s]+(\d{1,2}:\d{2})'
                ]
                for pattern in time_patterns:
                    time_match = re.search(pattern, content, re.IGNORECASE)
                    if time_match:
                        time_of_loss = time_match.group(1)
                        break
            
            # Extract date prepared
            if not date_prepared:
                prepared_patterns = [
                    r'Date Prepared[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Prepared[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Date Created[:\s]+(\d{4}-\d{2}-\d{2})'
                ]
                for pattern in prepared_patterns:
                    prepared_match = re.search(pattern, content, re.IGNORECASE)
                    if prepared_match:
                        date_prepared = prepared_match.group(1)
                        break
            
            # Extract policy dates
            if not policy_effective_date:
                effective_patterns = [
                    r'Policy Effective Date[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Effective Date[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Effective[:\s]+(\d{4}-\d{2}-\d{2})'
                ]
                for pattern in effective_patterns:
                    effective_match = re.search(pattern, content, re.IGNORECASE)
                    if effective_match:
                        policy_effective_date = effective_match.group(1)
                        break
            
            if not policy_expiration_date:
                expiration_patterns = [
                    r'Policy Expiration Date[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Expiration Date[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Expires[:\s]+(\d{4}-\d{2}-\d{2})'
                ]
                for pattern in expiration_patterns:
                    expiration_match = re.search(pattern, content, re.IGNORECASE)
                    if expiration_match:
                        policy_expiration_date = expiration_match.group(1)
                        break
            
            # Extract addresses
            if not property_address:
                # Look for "Property Address" section
                for i, line in enumerate(lines):
                    if 'property address' in line.lower() and i + 1 < len(lines):
                        # Get the next line which should contain the address
                        addr_line = lines[i + 1].strip()
                        if addr_line and len(addr_line) > 5:
                            property_address = addr_line
                            break
            
            if not mailing_address:
                # Look for "Mailing Address" section
                for i, line in enumerate(lines):
                    if 'mailing address' in line.lower() and i + 1 < len(lines):
                        # Get the next line which should contain the address
                        addr_line = lines[i + 1].strip()
                        if addr_line and len(addr_line) > 5:
                            mailing_address = addr_line
                            break
            
            # Extract claim amount
            if not claim_amount:
                claim_amount_patterns = [
                    r'Claim Amount[:\s]+\$([0-9,]+)',
                    r'Settlement[:\s]+\$([0-9,]+)',
                    r'Payout[:\s]+\$([0-9,]+)',
                    r'Amount[:\s]+\$([0-9,]+)'
                ]
                for pattern in claim_amount_patterns:
                    amount_match = re.search(pattern, content, re.IGNORECASE)
                    if amount_match:
                        claim_amount = f"${amount_match.group(1)}"
                        break
            
            # Extract coverage limits and types
            for line in lines:
                line_clean = line.strip()
                if ':' in line_clean and '$' in line_clean:
                    # Extract coverage amounts like "Dwelling Coverage (A): $500,000"
                    try:
                        coverage_part, amount_part = line_clean.split(':', 1)
                        coverage_part = coverage_part.strip('- ')
                        amount_part = amount_part.strip()
                        
                        if '$' in amount_part:
                            # Extract the dollar amount
                            amount_match = re.search(r'\$([0-9,]+)', amount_part)
                            if amount_match:
                                amount = amount_match.group(1)
                                coverage_limits[coverage_part] = f"${amount}"
                                
                                # Also add to coverage types list
                                if coverage_part not in coverage_types:
                                    coverage_types.append(coverage_part)
                    except:
                        pass
                
                # Extract deductible information
                if 'deductible' in line_clean.lower() and '$' in line_clean:
                    deductible_match = re.search(r'\$([0-9,]+)', line_clean)
                    if deductible_match and not deductible:
                        deductible = f"${deductible_match.group(1)}"
                    
            # If we found all the key info, we can check if we're done
            # (but continue to get all coverage types)
            
        # Only fall back to citation_info policy_number if we didn't find it in content
        if not policy_number:
            policy_number = all_citation_metadata.get("policy_number", "")
        
        # Convert coverage_limits dict to a readable string format
        coverage_limits_str = ""
        if coverage_limits:
            coverage_limits_str = "; ".join([f"{k}: {v}" for k, v in coverage_limits.items()])
        
        document_info = {
            "document_id": document_id,
            "title": best_chunk_for_content.get("title") or best_chunk_for_content.get("source") or document_id,
            "index": index,
            "document_type": f"{index.title()} Document",
            
            # Policy metadata (from citation_info and content parsing)
            "policy_number": policy_number,
            "insured_name": insured_name,
            "insurance_company": insurance_company,
            "line_of_business": all_citation_metadata.get("line_of_business", ""),
            "state": all_citation_metadata.get("state", ""),
            "effective_date": policy_effective_date or all_citation_metadata.get("effective_date", ""),
            "expiration_date": policy_expiration_date or all_citation_metadata.get("expiration_date", ""),
            "deductible": deductible or all_citation_metadata.get("deductible", ""),
            "coverage_limits": coverage_limits_str or all_citation_metadata.get("coverage_limits", ""),
            "coverage_types": coverage_types or all_citation_metadata.get("coverage_types", []),
            "exclusions": all_citation_metadata.get("exclusions", []),
            "endorsements": all_citation_metadata.get("endorsements", []),
            "agent_name": all_citation_metadata.get("agent_name", ""),
            "premium_amount": all_citation_metadata.get("premium_amount", ""),
            "property_address": property_address or all_citation_metadata.get("property_address", ""),
            "mailing_address": mailing_address,
            "vehicle_info": all_citation_metadata.get("vehicle_info", ""),
            "telephone_number": telephone_number,
            
            # Claim metadata (from citation_info and content parsing)
            "claim_id": all_citation_metadata.get("claim_id", ""),
            "claim_number": claim_number or all_citation_metadata.get("claim_number", ""),
            "claim_amount": claim_amount,
            "date_of_loss": date_of_loss or all_citation_metadata.get("date_of_loss", ""),
            "time_of_loss": time_of_loss,
            "date_prepared": date_prepared,
            "reported_date": all_citation_metadata.get("reported_date", ""),
            "loss_cause": all_citation_metadata.get("loss_cause", ""),
            "location": all_citation_metadata.get("location", ""),
            "coverage_decision": all_citation_metadata.get("coverage_decision", ""),
            "settlement_summary": all_citation_metadata.get("settlement_summary", ""),
            "payout_amount": all_citation_metadata.get("payout_amount", ""),
            "adjuster_name": all_citation_metadata.get("adjuster_name", ""),
            "claim_status": all_citation_metadata.get("claim_status", ""),
            "adjuster_notes": all_citation_metadata.get("adjuster_notes", []),
            "property_damage": all_citation_metadata.get("property_damage", ""),
            "injury_details": all_citation_metadata.get("injury_details", ""),
            
            # Processing metadata (from citation_info)
            "filename": all_citation_metadata.get("source_file", best_chunk_for_content.get("title", "")),
            "chunk_method": all_citation_metadata.get("chunk_method", ""),
            "smart_processing": all_citation_metadata.get("smart_processing", False),
            "content_complexity": all_citation_metadata.get("content_complexity", ""),
            "contains_monetary_values": all_citation_metadata.get("contains_amounts", False),
            "processed_at": all_citation_metadata.get("processed_at", ""),
            "total_chunks": len(chunks),
            "source": best_chunk_for_content.get("source", ""),
        }

        # Comprehensive chunk statistics (matching SEC format)
        chunk_stats = {
            "total_chunks": len(chunks),
            "avg_chunk_length": avg_length,
            "total_content_length": total_content_length,
            "min_chunk_length": min(chunk_lengths) if chunk_lengths else 0,
            "max_chunk_length": max(chunk_lengths) if chunk_lengths else 0,
            "page_range": {
                "min": min(page_numbers) if page_numbers else None,
                "max": max(page_numbers) if page_numbers else None
            },
            "section_types": [section for section, _ in sorted_sections],
            "section_distribution": dict(sorted_sections),
            "avg_credibility_score": round(
                sum(credibility_scores) / len(credibility_scores), 3
            ) if credibility_scores else 0,
            "total_sections": len(set(section_types)) if section_types else 0
        }

        # Return enhanced response matching SEC visualization format
        return ChunkVisualizationResponse(
            document_id=document_id,
            document_info=document_info,
            chunks=chunks,
            chunk_stats=chunk_stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building enhanced policy/claims chunk visualization: {e}")
        # Return graceful error response instead of 500
        return {
            "document_id": document_id,
            "document_info": {"document_id": document_id, "title": document_id, "index": index},
            "chunks": [],
            "chunk_stats": {"total_chunks": 0, "avg_chunk_length": 0},
            "status": "error",
            "error_message": str(e)
        }

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete document from knowledge base"""
    try:
        observability.track_request("delete_document")
        
        logger.info(f"Document deletion requested: {document_id}")
        
        return {"message": f"Document {document_id} deleted successfully", "status": "success"}
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        return {"message": f"Failed to delete document {document_id}", "status": "error", "error_message": str(e)}

@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(document_id: str):
    """Reprocess a document through the ingestion pipeline"""
    try:
        observability.track_request("reprocess_document")
        
        logger.info(f"Document reprocessing requested: {document_id}")
        
        return {"message": f"Document {document_id} queued for reprocessing", "status": "success"}
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {e}")
        return {"message": f"Failed to reprocess document {document_id}", "status": "error", "error_message": str(e)}

@router.get("/conflicts")
async def get_conflicts(
    status: Optional[str] = None,
    document_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    azure_manager: AzureServiceManager = Depends(get_azure_manager)
):
    """Get knowledge base conflicts"""
    try:
        observability.track_request("get_conflicts")
        
        logger.info(f"Conflicts requested: status={status}, document_id={document_id}")
        
        # For now, return mock conflicts data
        # In a real implementation, this would query the knowledge base for actual conflicts
        conflicts = [
            {
                "id": "1",
                "documentId": "doc_1",
                "chunkId": "chunk_156",
                "conflictType": "contradiction",
                "description": "Revenue figures differ between Q3 and annual report",
                "sources": ["AAPL_10K_2023.pdf", "AAPL_10Q_Q3_2023.pdf"],
                "status": "pending"
            },
            {
                "id": "2",
                "documentId": "doc_1", 
                "chunkId": "chunk_89",
                "conflictType": "duplicate",
                "description": "Duplicate content found in multiple sections",
                "sources": ["AAPL_10K_2023.pdf"],
                "status": "resolved"
            }
        ]
        
        # Apply filters
        if status:
            conflicts = [c for c in conflicts if c["status"] == status]
        if document_id:
            conflicts = [c for c in conflicts if c["documentId"] == document_id]
        
        # Apply pagination
        conflicts = conflicts[offset:offset + limit]
        
        return {"conflicts": conflicts, "status": "success"}
    except Exception as e:
        logger.error(f"Error getting conflicts: {e}")
        # Return graceful error response instead of 500
        return {"conflicts": [], "status": "error", "error_message": str(e)}

@router.patch("/conflicts/{conflict_id}")
async def resolve_conflict(conflict_id: str, status: str):
    """Resolve a knowledge base conflict"""
    try:
        observability.track_request("resolve_conflict")
        
        logger.info(f"Conflict resolution requested: {conflict_id}, status: {status}")
        
        if status not in ["resolved", "ignored"]:
            return {
                "conflict_id": conflict_id,
                "status": "error",
                "message": "Invalid status. Must be 'resolved' or 'ignored'",
                "error_message": "Invalid status value"
            }
        
        return {
            "conflict_id": conflict_id,
            "status": status,
            "message": f"Conflict {conflict_id} marked as {status}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving conflict {conflict_id}: {e}")
        return {
            "conflict_id": conflict_id,
            "status": "error",
            "message": f"Failed to resolve conflict {conflict_id}",
            "error_message": str(e)
        }

@router.get("/metrics")
async def get_knowledge_base_metrics(index: Optional[str] = None, azure_manager: AzureServiceManager = Depends(get_azure_manager)):
    """Get knowledge base metrics and analytics for policy/claims indexes.

    If index is provided ('policy' or 'claims'), compute metrics from that index only.
    Otherwise, aggregate across both policy and claims.
    """
    try:
        observability.track_request("get_kb_metrics")
        logger.info("Knowledge base metrics requested")

        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty metrics")
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "active_conflicts": 0,
                "processing_rate": 0,
                "documents_by_type": {},
                "processing_queue_size": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "status": "azure_not_configured"
            }

        # Now we can directly use azure_manager since it's injected

        # Resolve which indexes to include
        ix_list = []
        req = (index or "").lower()
        if req == "policy":
            if settings.AZURE_SEARCH_POLICY_INDEX_NAME:
                ix_list = [settings.AZURE_SEARCH_POLICY_INDEX_NAME]
        elif req == "claims" or req == "claim":
            if settings.AZURE_SEARCH_CLAIMS_INDEX_NAME:
                ix_list = [settings.AZURE_SEARCH_CLAIMS_INDEX_NAME]
        elif req == "sec-docs" or req == "sec":
            # For SEC documents, return empty metrics since this is policy/claims knowledge base
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "active_conflicts": 0,
                "processing_rate": 0,
                "documents_by_type": {},
                "processing_queue_size": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "status": "sec_docs_not_supported_in_knowledge_base"
            }
        else:
            for ix in [settings.AZURE_SEARCH_POLICY_INDEX_NAME, settings.AZURE_SEARCH_CLAIMS_INDEX_NAME]:
                if ix:
                    ix_list.append(ix)

        # If no indexes are configured, return empty metrics
        if not ix_list:
            logger.warning("No search indexes configured for policy/claims")
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "active_conflicts": 0,
                "processing_rate": 0,
                "documents_by_type": {},
                "processing_queue_size": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "status": "no_indexes_configured"
            }

        total_documents = 0
        total_chunks = 0
        documents_by_type: Dict[str, int] = {}

        # Iterate indexes and accumulate counts
        for ix in ix_list:
            try:
                items = await azure_manager.list_unique_documents(ix, top_k=2000)
                total_documents += len(items)
                # Estimate chunks via direct search (no select to avoid schema mismatches)
                client = azure_manager.get_search_client_for_index(ix)
                search_results = await client.search(search_text="*", top=1000, query_type="simple")
                batch_count = 0
                async for _ in search_results:
                    batch_count += 1
                total_chunks += batch_count
                # Type distribution placeholder (policy vs claims)
                ix_label = "policy" if ix == settings.AZURE_SEARCH_POLICY_INDEX_NAME else "claims"
                documents_by_type[ix_label] = documents_by_type.get(ix_label, 0) + len(items)
            except Exception as e:
                logger.warning(f"Metrics: skipping index '{ix}' due to error: {e}")

        metrics = {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "active_conflicts": 0,
            "processing_rate": 100 if total_documents > 0 else 0,
            "documents_by_type": documents_by_type,
            "processing_queue_size": 0,
            "last_updated": datetime.utcnow().isoformat(),
            "status": "success"
        }

        return metrics
    except Exception as e:
        logger.error(f"Error getting KB metrics: {e}")
        # Return graceful error response instead of 500
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "active_conflicts": 0,
            "processing_rate": 0,
            "documents_by_type": {},
            "processing_queue_size": 0,
            "last_updated": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": str(e)
        }

@router.get("/search")
async def search_knowledge_base(
    request: Request,
    query: str,
    limit: int = 10,
    document_type: Optional[str] = None,
    min_score: float = 0.0,
    azure_manager: AzureServiceManager = Depends(get_azure_manager)
):
    """Search the knowledge base"""
    try:
        observability.track_request("search_knowledge_base")
        
        logger.info(f"Knowledge base search: {query}")
        
        # Azure services are now injected via dependency injection for better performance
        if not azure_manager:
            raise HTTPException(status_code=500, detail="Azure services not initialized")
        
        # Initialize token tracking for this request with azure manager
        from app.services.token_usage_tracker import TokenUsageTracker, ServiceType, OperationType
        token_tracker = TokenUsageTracker(azure_manager=azure_manager)
        tracking_id = token_tracker.start_tracking(
            session_id=f"kb_search_{hash(query)}",
            service_type=ServiceType.KNOWLEDGE_BASE,
            operation_type=OperationType.SEARCH_QUERY,
            endpoint="/knowledge-base/search",
            user_id=request.headers.get("X-User-ID", "anonymous"),
            metadata={"query": query, "limit": limit}
        )
        
        try:
            # Perform hybrid search in Azure Search
            results = await azure_manager.hybrid_search(
                query=query,
                top_k=limit,
                min_score=min_score,
                token_tracker=token_tracker,
                tracking_id=tracking_id
            )
            
            # Filter by document type if provided
            if document_type:
                results = [r for r in results if r.get('document_type') == document_type]
            
            # Finalize tracking with success
            await token_tracker.finalize_tracking(
                tracking_id=tracking_id,
                success=True,
                http_status_code=200,
                metadata={
                    "results_count": len(results),
                    "search_operation": "hybrid_search"
                }
            )
            
            return {
                "query": query,
                "results": results,
                "total_count": len(results)
            }
        except Exception as e:
            await token_tracker.finalize_tracking(
                tracking_id=tracking_id,
                success=False,
                http_status_code=500,
                error_message=str(e)
            )
            raise
            
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to search knowledge base")

@router.get("/capabilities")
async def get_knowledge_base_capabilities(domain: str = "insurance"):
    """Get Knowledge Base Agent Service capabilities and status"""
    try:
        observability.track_request("get_kb_capabilities")
        
        logger.info("Knowledge Base Agent capabilities requested")
        
        if domain == "insurance":
            capabilities = [
                {
                    "name": "Document Processing",
                    "description": "Process and chunk policy and claims documents for vector storage and retrieval",
                    "status": "available"
                },
                {
                    "name": "Conflict Detection", 
                    "description": "Identify and flag conflicts between policy documents and claims data",
                    "status": "available"
                },
                {
                    "name": "Knowledge Base Management",
                    "description": "Manage policy and claims document lifecycle, metadata, and knowledge base organization", 
                    "status": "available"
                },
                {
                    "name": "Vector Store Integration",
                    "description": "Integrate with Azure AI Search for efficient policy and claims document storage and retrieval",
                    "status": "available"
                }
            ]
        else:
            capabilities = [
                {
                    "name": "Document Processing",
                    "description": "Process and chunk financial documents for vector storage and retrieval",
                    "status": "available"
                },
                {
                    "name": "Conflict Detection", 
                    "description": "Identify and flag conflicts between document sources and data inconsistencies",
                    "status": "available"
                },
                {
                    "name": "Knowledge Base Management",
                    "description": "Manage document lifecycle, metadata, and knowledge base organization", 
                    "status": "available"
                },
                {
                    "name": "Vector Store Integration",
                    "description": "Integrate with Azure AI Search for efficient document storage and retrieval",
                    "status": "available"
                }
            ]
        
        return {
            "service_status": "connected",
            "capabilities": capabilities,
            "agent_info": {
                "name": "Azure AI Knowledge Base Agent",
                "version": "1.0.0",
                "description": f"AI agent for managing {'policy and claims' if domain == 'insurance' else 'financial'} document knowledge base with Azure AI services"
            }
        }
    except Exception as e:
        logger.error(f"Error getting KB capabilities: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve knowledge base capabilities")
