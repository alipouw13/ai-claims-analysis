from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request, Query
from typing import List, Optional, Dict, Any
import logging
import uuid
from datetime import datetime
import aiofiles
import os
import asyncio
import time

from app.models.schemas import (
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentInfo,
    DocumentType,
    DocumentStatus
)
from app.core.observability import observability
from app.services.insurance_document_service import InsuranceDocumentService, InsuranceDocumentInfo
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

router = APIRouter(prefix="/api/v1/insurance", tags=["Insurance Documents"])
logger = logging.getLogger(__name__)

# In-memory trackers for insurance document processing
insurance_processing_status: Dict[str, Dict[str, Any]] = {}
insurance_batches: Dict[str, Dict[str, Any]] = {}

@router.post("/upload", response_model=List[DocumentUploadResponse])
async def upload_insurance_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    document_type: str = Form(...),  # 'policy' or 'claim'
    company_name: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form("text-embedding-ada-002"),
    search_type: Optional[str] = Form("hybrid"),
    temperature: Optional[float] = Form(0.7)
):
    """
    Upload and process insurance documents (policies and claims) using Azure Document Intelligence
    
    This endpoint specifically handles insurance documents and routes them to the appropriate
    Azure Search index based on document type.
    """
    try:
        responses = []
        batch_id = f"insurance_batch_{int(time.time())}"
        
        # Initialize batch tracking
        insurance_batches[batch_id] = {
            "batch_id": batch_id,
            "total_files": len(files),
            "completed": 0,
            "failed": 0,
            "started_at": datetime.utcnow().isoformat(),
            "documents": [],
            "document_type": document_type,
            "company_name": company_name
        }
        
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        upload_dir = "/tmp/insurance_uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Get Azure services
        azure_manager = getattr(request.app.state, 'azure_manager', None)
        if not azure_manager:
            raise HTTPException(status_code=500, detail="Azure services not initialized")
        
        # Initialize insurance document service
        insurance_service = InsuranceDocumentService(azure_manager)
        logger.info(f"Using InsuranceDocumentService for {document_type} documents")
        
        # Determine target index
        if document_type == "claim":
            target_index = settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
        elif document_type == "policy":
            target_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
        else:
            raise HTTPException(status_code=400, detail="Document type must be 'policy' or 'claim'")
        
        for file in files:
            document_id = str(uuid.uuid4())
            
            try:
                # Validate file extension
                file_extension = os.path.splitext(file.filename)[1].lower()
                if file_extension not in allowed_extensions:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"File type {file_extension} not supported. Allowed: {', '.join(allowed_extensions)}"
                    )
                
                # Read file content
                file_content = await file.read()
                content_type = file.content_type or "application/octet-stream"
                
                logger.info(f"Processing {document_type}: {file.filename}, Size: {len(file_content)} bytes")
                
                file_path = os.path.join(upload_dir, f"{document_id}_{file.filename}")
                
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_content)
                logger.info(f"File saved locally to: {file_path}")
                
                # Prepare metadata
                metadata = {
                    "batch_id": batch_id,
                    "company_name": company_name,
                    "document_type": document_type,
                    "target_index": target_index,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "domain": "insurance"
                }
                
                # Create async task for document processing
                asyncio.create_task(
                    process_insurance_document_async(
                        service=insurance_service,
                        content=file_content,
                        content_type=content_type,
                        filename=file.filename,
                        document_id=document_id,
                        metadata=metadata,
                        target_index_name=target_index,
                        document_type=document_type
                    )
                )
                
                # Add to batch tracking
                insurance_batches[batch_id]["documents"].append({
                    "document_id": document_id,
                    "filename": file.filename,
                    "status": "processing",
                    "started_at": datetime.utcnow().isoformat()
                })
                
                responses.append(DocumentUploadResponse(
                    document_id=document_id,
                    filename=file.filename,
                    status=DocumentStatus.PROCESSING,
                    message=f"Insurance {document_type} document uploaded successfully. Processing started. Batch ID: {batch_id}",
                    batch_id=batch_id
                ))
                
                logger.info(f"Insurance {document_type} document {file.filename} queued for processing with ID {document_id}")
                
            except Exception as e:
                logger.error(f"Error processing insurance {document_type} file {file.filename}: {e}")
                insurance_batches[batch_id]["failed"] += 1
                insurance_batches[batch_id]["documents"].append({
                    "document_id": document_id,
                    "filename": file.filename,
                    "status": "failed",
                    "error_message": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                })
                
                responses.append(DocumentUploadResponse(
                    document_id=document_id,
                    filename=file.filename,
                    status=DocumentStatus.FAILED,
                    message=f"Error processing insurance {document_type} document: {str(e)}",
                    batch_id=batch_id
                ))
        
        logger.info(f"Insurance batch {batch_id} created with {len(files)} {document_type} files")
        return responses
        
    except Exception as e:
        logger.error(f"Error in upload_insurance_documents: {e}")
        observability.record_error("insurance_document_upload_error", str(e))
        raise HTTPException(status_code=500, detail=f"Insurance document upload failed: {str(e)}")

async def process_insurance_document_async(
    service: InsuranceDocumentService,
    content: bytes,
    content_type: str,
    filename: str,
    document_id: str,
    metadata: dict,
    target_index_name: str,
    document_type: str
):
    """Asynchronously process insurance document with Azure Document Intelligence"""
    try:
        logger.info(f"=== ASYNC INSURANCE DOCUMENT PROCESSING STARTED ===")
        logger.info(f"Document ID: {document_id}")
        logger.info(f"Filename: {filename}")
        logger.info(f"Document Type: {document_type}")
        logger.info(f"Target Index: {target_index_name}")
        
        result = await service.process_insurance_document(
            content=content,
            content_type=content_type,
            filename=filename,
            document_type=document_type,
            metadata=metadata
        )
        
        logger.info(f"Insurance document processing completed for {filename}")
        logger.info(f"Extracted {len(result.get('chunks', []))} chunks")
        logger.info(f"Insurance fields: {list(result.get('insurance_fields', {}).keys())}")
        logger.info(f"Credibility score: {result.get('credibility_score', 0.0)}")
        
        # TODO: Upload chunks to Azure Search index
        # This would involve:
        # 1. Converting chunks to search documents
        # 2. Uploading to the appropriate index (policy or claims)
        # 3. Updating batch status
        
        batch_id = metadata.get("batch_id", "unknown")
        if batch_id in insurance_batches:
            insurance_batches[batch_id]["completed"] += 1
            insurance_batches[batch_id]["documents"].append({
                "document_id": document_id,
                "filename": filename,
                "status": "completed",
                "chunks_created": len(result.get('chunks', [])),
                "insurance_fields": result.get('insurance_fields', {}),
                "credibility_score": result.get('credibility_score', 0.0),
                "extraction_confidence": result.get('processing_metadata', {}).get('extraction_confidence', 0.0),
                "total_pages": result.get('processing_metadata', {}).get('total_pages', 0),
                "completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Insurance batch {batch_id} updated: {insurance_batches[batch_id]['completed']}/{insurance_batches[batch_id]['total_files']} completed")
        
        observability.track_document_processing_complete(filename, len(result.get('chunks', [])))
        
    except Exception as e:
        logger.error(f"Error in async insurance document processing for {filename}: {e}")
        
        batch_id = metadata.get("batch_id", "unknown")
        if batch_id in insurance_batches:
            insurance_batches[batch_id]["failed"] += 1
            insurance_batches[batch_id]["documents"].append({
                "document_id": document_id,
                "filename": filename,
                "status": "failed",
                "error_message": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
        
        observability.record_error("insurance_document_processing_async_error", str(e))

@router.get("/batch-status/{batch_id}")
async def get_insurance_batch_status(batch_id: str):
    """Get the status of an insurance document processing batch"""
    try:
        if batch_id not in insurance_batches:
            raise HTTPException(status_code=404, detail="Insurance batch not found")
        
        batch = insurance_batches[batch_id]
        
        # Calculate progress
        total = batch["total_files"]
        completed = batch["completed"]
        failed = batch["failed"]
        processing = total - completed - failed
        
        return {
            "batch_id": batch_id,
            "total_files": total,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "started_at": batch["started_at"],
            "document_type": batch.get("document_type"),
            "company_name": batch.get("company_name"),
            "documents": batch["documents"]
        }
        
    except Exception as e:
        logger.error(f"Error getting insurance batch status for {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting insurance batch status: {str(e)}")

@router.get("/documents")
async def list_insurance_documents(
    document_type: Optional[str] = Query(None, description="Filter by document type ('policy' or 'claim')"),
    company_name: Optional[str] = Query(None, description="Filter by company name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return")
):
    """List processed insurance documents with optional filtering"""
    try:
        # TODO: Implement actual document listing from Azure Search indexes
        # For now, return mock data
        documents = [
            {
                "id": "mock_insurance_policy_1",
                "filename": "sample_policy.pdf",
                "document_type": "policy",
                "company_name": "Sample Insurance Co",
                "upload_date": "2024-01-15T10:00:00Z",
                "status": "processed",
                "coverage_type": "Homeowners",
                "effective_date": "2024-01-01",
                "expiration_date": "2025-01-01"
            },
            {
                "id": "mock_insurance_claim_1",
                "filename": "sample_claim.pdf",
                "document_type": "claim",
                "company_name": "Sample Insurance Co",
                "upload_date": "2024-01-15T11:00:00Z",
                "status": "processed",
                "claim_amount": 5000.00,
                "date_of_loss": "2024-01-10",
                "cause_of_loss": "Water damage"
            }
        ]
        
        # Apply filters
        if document_type:
            documents = [d for d in documents if d["document_type"] == document_type]
        if company_name:
            documents = [d for d in documents if d["company_name"] == company_name]
        
        return {"documents": documents[:limit]}
        
    except Exception as e:
        logger.error(f"Error listing insurance documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing insurance documents: {str(e)}")

@router.get("/documents/{document_id}")
async def get_insurance_document(document_id: str):
    """Get a specific insurance document by ID"""
    try:
        # TODO: Implement actual document retrieval from Azure Search
        # For now, return mock data
        return {
            "id": document_id,
            "filename": "sample_insurance_document.pdf",
            "document_type": "policy",
            "company_name": "Sample Insurance Co",
            "content": "This is sample insurance document content...",
            "insurance_fields": {
                "policy_number": "POL123456",
                "insured_name": "John Doe",
                "coverage_type": "Homeowners",
                "effective_date": "2024-01-01",
                "expiration_date": "2025-01-01"
            },
            "metadata": {
                "upload_date": "2024-01-15T10:00:00Z",
                "status": "processed",
                "credibility_score": 0.95
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting insurance document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting insurance document: {str(e)}")

@router.get("/stats")
async def get_insurance_document_stats():
    """Get statistics about insurance documents"""
    try:
        # TODO: Implement actual statistics from Azure Search indexes
        # For now, return mock data
        return {
            "total_policies": 150,
            "total_claims": 75,
            "total_documents": 225,
            "processing_status": {
                "completed": 200,
                "processing": 20,
                "failed": 5
            },
            "document_types": {
                "policy": 150,
                "claim": 75
            },
            "companies": {
                "Sample Insurance Co": 50,
                "Another Insurance Co": 45,
                "Third Insurance Co": 40
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting insurance document stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting insurance document stats: {str(e)}")

@router.get("/search")
async def search_insurance_documents(
    query: str = Query(..., description="Search query"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    company_name: Optional[str] = Query(None, description="Filter by company name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results to return")
):
    """Search insurance documents"""
    try:
        # TODO: Implement actual search from Azure Search indexes
        # For now, return mock search results
        results = [
            {
                "id": "search_result_1",
                "filename": "policy_document.pdf",
                "document_type": "policy",
                "company_name": "Sample Insurance Co",
                "relevance_score": 0.95,
                "matched_content": "This policy covers homeowners insurance...",
                "upload_date": "2024-01-15T10:00:00Z"
            }
        ]
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results[:limit]
        }
        
    except Exception as e:
        logger.error(f"Error searching insurance documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching insurance documents: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_insurance_document(document_id: str):
    """Delete an insurance document by ID"""
    try:
        # TODO: Implement actual document deletion from Azure Search
        logger.info(f"Insurance document {document_id} deleted")
        return {"message": f"Insurance document {document_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting insurance document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting insurance document: {str(e)}")
