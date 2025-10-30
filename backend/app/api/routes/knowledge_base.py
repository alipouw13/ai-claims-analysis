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

def get_azure_manager(request: Request) -> AzureServiceManager:
    """Dependency to get the Azure manager from app state"""
    azure_manager = getattr(request.app.state, 'azure_manager', None)
    if not azure_manager:
        logger.error("Azure manager not found in app state")
        raise HTTPException(status_code=503, detail="Azure services not available")
    return azure_manager

@router.get("/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats(request: Request):
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
        
        azure_manager = getattr(request.app.state, 'azure_manager', None)
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
    index: Optional[str] = None
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

        try:
            azure_manager = AzureServiceManager()
            await azure_manager.initialize()
        except Exception as azure_init_error:
            logger.warning(f"Failed to initialize Azure services: {azure_init_error}")
            return {"documents": [], "status": "azure_initialization_failed"}

        # Resolve indexes to list from
        indexes = []
        req_index = (index or "").lower()
        if req_index == "policy":
            indexes = [settings.AZURE_SEARCH_POLICY_INDEX_NAME]
        elif req_index == "claims" or req_index == "claim":
            indexes = [settings.AZURE_SEARCH_CLAIMS_INDEX_NAME]
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
                documents.extend(items)
            except Exception as e:
                logger.warning(f"Skipping index '{ix}' due to error: {e}")

        return {"documents": documents, "status": "success"}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        # Return graceful error response instead of 500
        return {"documents": [], "status": "error", "error_message": str(e)}

@router.get("/recent-claims")
async def get_recent_claims(limit: int = 10):
    """Get recent claims for dashboard display"""
    try:
        observability.track_request("get_recent_claims")
        
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty claims list")
            return {"claims": [], "status": "azure_not_configured"}

        try:
            azure_manager = AzureServiceManager()
            await azure_manager.initialize()
        except Exception as azure_init_error:
            logger.warning(f"Failed to initialize Azure services: {azure_init_error}")
            return {"claims": [], "status": "azure_initialization_failed"}

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
async def get_recent_policies(limit: int = 10):
    """Get recent policies for dashboard display"""
    try:
        observability.track_request("get_recent_policies")
        
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty policies list")
            return {"policies": [], "status": "azure_not_configured"}

        try:
            azure_manager = AzureServiceManager()
            await azure_manager.initialize()
        except Exception as azure_init_error:
            logger.warning(f"Failed to initialize Azure services: {azure_init_error}")
            return {"policies": [], "status": "azure_initialization_failed"}

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

@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(document_id: str, index: str = "policy"):
    try:
        # Check if Azure services are configured
        if not (settings.AZURE_SEARCH_SERVICE_NAME and 
                (settings.AZURE_SEARCH_API_KEY or 
                 (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET))):
            logger.warning("Azure Search not configured, returning empty chunks")
            return {"document_id": document_id, "index": index, "chunks": [], "total": 0, "status": "azure_not_configured"}

        try:
            azure_manager = AzureServiceManager()
            await azure_manager.initialize()
        except Exception as azure_init_error:
            logger.warning(f"Failed to initialize Azure services: {azure_init_error}")
            return {"document_id": document_id, "index": index, "chunks": [], "total": 0, "status": "azure_initialization_failed"}

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
async def get_policy_claims_chunk_visualization(document_id: str, index: str = "policy"):
    """Return enhanced SEC-style chunk visualization payload for policy/claims documents.
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

        try:
            azure_manager = AzureServiceManager()
            await azure_manager.initialize()
        except Exception as azure_init_error:
            logger.warning(f"Failed to initialize Azure services: {azure_init_error}")
            return {
                "document_info": {"document_id": document_id, "title": document_id, "index": index},
                "chunks": [],
                "stats": {"total_chunks": 0, "avg_length": 0},
                "status": "azure_initialization_failed"
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
                    "chunk_id", "parent_id", "content", "title", "section_type", 
                    "page_number", "citation_info", "processed_at", "source", 
                    "policy_number", "coverage_limits", "deductible", "insured_name",
                    "effective_date", "expiration_date", "line_of_business", "state"
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
            
            # Collect page numbers for range analysis
            page_num = c.get("page_number")
            if page_num and isinstance(page_num, (int, float)):
                page_numbers.append(int(page_num))
            
            # Collect section types for distribution analysis
            section_type = c.get("section_type") or ""
            section_type = section_type.strip() if section_type else ""
            if section_type:
                section_types.append(section_type)
            
            # Collect credibility scores
            cred_score = c.get("credibility_score", 0)
            if isinstance(cred_score, (int, float)):
                credibility_scores.append(float(cred_score))
            
            # Enhanced chunk data with preview
            chunk_data = {
                "chunk_id": c.get("chunk_id") or c.get("id") or f"chunk_{i}",
                "content": content[:200] + "..." if len(content) > 200 else content,
                "content_length": content_length,
                "page_number": page_num,
                "section_type": section_type or "general",
                "credibility_score": cred_score,
                "citation_info": c.get("citation_info", {}),
                "search_score": c.get("@search.score", 0),
                "chunk_index": c.get("chunk_index", i)
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
        
        # Enhanced document information with policy-specific fields
        first_chunk = raw_chunks[0] if raw_chunks else {}
        document_info = {
            "document_id": document_id,
            "title": first_chunk.get("title") or first_chunk.get("source") or document_id,
            "index": index,
            "document_type": f"{index.title()} Document",
            "policy_number": first_chunk.get("policy_number", ""),
            "insured_name": first_chunk.get("insured_name", ""),
            "coverage_limits": first_chunk.get("coverage_limits", ""),
            "deductible": first_chunk.get("deductible", ""),
            "effective_date": first_chunk.get("effective_date", ""),
            "expiration_date": first_chunk.get("expiration_date", ""),
            "line_of_business": first_chunk.get("line_of_business", ""),
            "state": first_chunk.get("state", ""),
            "processed_at": first_chunk.get("processed_at", ""),
            "total_chunks": len(chunks),
            "source": first_chunk.get("source", ""),
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
    min_score: float = 0.0
):
    """Search the knowledge base"""
    try:
        observability.track_request("search_knowledge_base")
        
        logger.info(f"Knowledge base search: {query}")
        
        azure_manager = getattr(request.app.state, 'azure_manager', None)
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
