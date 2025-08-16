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
from app.services.document_processor import DocumentProcessor
from app.services.insurance_document_service import InsuranceDocumentService
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory trackers for policy/claims upload progress (mirrors SEC batch UX)
kb_processing_status: Dict[str, Dict[str, Any]] = {}
kb_batches: Dict[str, Dict[str, Any]] = {}

@router.post("/upload", response_model=List[DocumentUploadResponse])
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    embedding_model: Optional[str] = Form("text-embedding-ada-002"),
    search_type: Optional[str] = Form("hybrid"),
    temperature: Optional[float] = Form(0.7),
    document_type: Optional[DocumentType] = Form(None),
    company_name: Optional[str] = Form(None),
    filing_date: Optional[str] = Form(None),
    domain: Optional[str] = Form("insurance"),
    is_claim: Optional[bool] = Form(False)
):
    """
    Upload and process insurance documents (policies and claims) using Azure Document Intelligence
    """
    try:
        responses = []
        batch_id = f"kb_batch_{int(time.time())}"
        kb_batches[batch_id] = {
            "batch_id": batch_id,
            "total_files": len(files),
            "completed": 0,
            "failed": 0,
            "started_at": datetime.utcnow().isoformat(),
            "documents": []
        }
        
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        upload_dir = "/tmp/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        azure_manager = getattr(request.app.state, 'azure_manager', None)
        if not azure_manager:
            raise HTTPException(status_code=500, detail="Azure services not initialized")
        
        # Use InsuranceDocumentService for insurance documents, DocumentProcessor for others
        if domain == "insurance":
            document_processor = InsuranceDocumentService(azure_manager)
            logger.info("Using InsuranceDocumentService with Azure Document Intelligence for insurance documents")
        else:
            document_processor = DocumentProcessor(azure_manager)
            logger.info("Using DocumentProcessor for non-insurance documents")
        
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
                
                logger.info(f"File: {file.filename}, Size: {len(file_content)} bytes, Type: {content_type}")
                logger.info(f"Document type: {document_type}, Company: {company_name}")
                logger.info(f"File content read successfully: {len(file_content)} bytes")
                
                file_path = os.path.join(upload_dir, f"{document_id}_{file.filename}")
                
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_content)
                logger.info(f"File saved locally to: {file_path}")
                
                # Determine target index based on domain and document type
                if domain == "insurance":
                    if is_claim:
                        target_index_name = settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
                        document_type_str = "claim"
                    else:
                        target_index_name = settings.AZURE_SEARCH_POLICY_INDEX_NAME
                        document_type_str = "policy"
                else:
                    target_index_name = settings.AZURE_SEARCH_INDEX_NAME
                    document_type_str = document_type or "unknown"
                
                # Prepare metadata
                metadata = {
                    "batch_id": batch_id,
                    "company_name": company_name,
                    "filing_date": filing_date,
                    "domain": domain,
                    "is_claim": is_claim,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "target_index": target_index_name
                }
                
                # Create async task for document processing
                if domain == "insurance":
                    # Use InsuranceDocumentService for insurance documents
                    asyncio.create_task(
                        process_insurance_document_async(
                            service=document_processor,
                            content=file_content,
                            content_type=content_type,
                            filename=file.filename,
                            document_id=document_id,
                            metadata=metadata,
                            target_index_name=target_index_name,
                            document_type=document_type_str
                        )
                    )
                else:
                    # Use generic DocumentProcessor for other documents
                    asyncio.create_task(
                        process_document_async(
                            service=document_processor,
                            content=file_content,
                            content_type=content_type,
                            filename=file.filename,
                            document_id=document_id,
                            metadata=metadata,
                            target_index_name=target_index_name
                        )
                    )
                
                # Add to batch tracking
                kb_batches[batch_id]["documents"].append({
                    "document_id": document_id,
                    "filename": file.filename,
                    "status": "processing",
                    "started_at": datetime.utcnow().isoformat()
                })
                
                responses.append(DocumentUploadResponse(
                    document_id=document_id,
                    filename=file.filename,
                    status=DocumentStatus.PROCESSING,
                    message=f"Document uploaded successfully. Processing started. Batch ID: {batch_id}",
                    batch_id=batch_id
                ))
                
                logger.info(f"Document {file.filename} queued for processing with ID {document_id}")
                
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {e}")
                kb_batches[batch_id]["failed"] += 1
                kb_batches[batch_id]["documents"].append({
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
                    message=f"Error processing document: {str(e)}",
                    batch_id=batch_id
                ))
        
        logger.info(f"Batch {batch_id} created with {len(files)} files")
        return responses
        
    except Exception as e:
        logger.error(f"Error in upload_documents: {e}")
        observability.record_error("document_upload_error", str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

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
        if batch_id in kb_batches:
            kb_batches[batch_id]["completed"] += 1
            kb_batches[batch_id]["documents"].append({
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
            
            logger.info(f"Batch {batch_id} updated: {kb_batches[batch_id]['completed']}/{kb_batches[batch_id]['total_files']} completed")
        
        observability.track_document_processing_complete(filename, len(result.get('chunks', [])))
        
    except Exception as e:
        logger.error(f"Error in async insurance document processing for {filename}: {e}")
        
        batch_id = metadata.get("batch_id", "unknown")
        if batch_id in kb_batches:
            kb_batches[batch_id]["failed"] += 1
            kb_batches[batch_id]["documents"].append({
                "document_id": document_id,
                "filename": filename,
                "status": "failed",
                "error_message": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
        
        observability.record_error("insurance_document_processing_async_error", str(e))

async def process_document_async(
    service: DocumentProcessor,
    content: bytes,
    content_type: str,
    filename: str,
    document_id: str,
    metadata: dict,
    target_index_name: str
):
    """Asynchronously process document with generic DocumentProcessor"""
    try:
        logger.info(f"=== ASYNC DOCUMENT PROCESSING STARTED ===")
        logger.info(f"Document ID: {document_id}")
        logger.info(f"Filename: {filename}")
        logger.info(f"Target Index: {target_index_name}")
        
        result = await service.process_document(
            content=content,
            content_type=content_type,
            source=filename,
            metadata=metadata,
            target_index_name=target_index_name
        )
        
        logger.info(f"Document processing completed for {filename}")
        
        batch_id = metadata.get("batch_id", "unknown")
        if batch_id in kb_batches:
            kb_batches[batch_id]["completed"] += 1
            kb_batches[batch_id]["documents"].append({
                "document_id": document_id,
                "filename": filename,
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Batch {batch_id} updated: {kb_batches[batch_id]['completed']}/{kb_batches[batch_id]['total_files']} completed")
        
        observability.track_document_processing_complete(filename, 0)
        
    except Exception as e:
        logger.error(f"Error in async document processing for {filename}: {e}")
        
        batch_id = metadata.get("batch_id", "unknown")
        if batch_id in kb_batches:
            kb_batches[batch_id]["failed"] += 1
            kb_batches[batch_id]["documents"].append({
                "document_id": document_id,
                "filename": filename,
                "status": "failed",
                "error_message": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
        
        observability.record_error("document_processing_async_error", str(e))

@router.get("/upload/status/{document_id}")
async def get_upload_status(document_id: str):
    status = kb_processing_status.get(document_id)
    if not status:
        raise HTTPException(status_code=404, detail="Document not found in processing tracker")
    return status

@router.get("/upload/batch/{batch_id}/status")
async def get_upload_batch_status(batch_id: str):
    batch = kb_batches.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    doc_ids = batch.get("documents", [])
    if doc_ids:
        progress = sum(kb_processing_status.get(d, {}).get("progress_percent", 0.0) for d in doc_ids) / len(doc_ids)
    else:
        progress = 0.0
    return {**batch, "overall_progress_percent": round(progress, 2)}

@router.get("/batch-status/{batch_id}")
async def get_document_batch_status(batch_id: str):
    """Get the status of a document processing batch"""
    try:
        if batch_id not in kb_batches:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        batch = kb_batches[batch_id]
        
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
            "documents": batch["documents"]
        }
        
    except Exception as e:
        logger.error(f"Error getting batch status for {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting batch status: {str(e)}")

@router.get("/documents")
async def list_documents(
    domain: Optional[str] = Query(None, description="Filter by domain (e.g., 'insurance', 'banking')"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return")
):
    """List processed documents with optional filtering"""
    try:
        # TODO: Implement actual document listing from Azure Search indexes
        # For now, return mock data based on domain
        if domain == "insurance":
            documents = [
                {
                    "id": "mock_insurance_1",
                    "filename": "sample_policy.pdf",
                    "document_type": "policy",
                    "company_name": "Sample Insurance Co",
                    "upload_date": "2024-01-15T10:00:00Z",
                    "status": "processed"
                },
                {
                    "id": "mock_insurance_2",
                    "filename": "sample_claim.pdf",
                    "document_type": "claim",
                    "company_name": "Sample Insurance Co",
                    "upload_date": "2024-01-15T11:00:00Z",
                    "status": "processed"
                }
            ]
        else:
            documents = [
                {
                    "id": "mock_general_1",
                    "filename": "sample_document.pdf",
                    "document_type": "general",
                    "upload_date": "2024-01-15T09:00:00Z",
                    "status": "processed"
                }
            ]
        
        return {"documents": documents[:limit]}
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get a specific document by ID"""
    try:
        # TODO: Implement actual document retrieval from Azure Search
        # For now, return mock data
        return {
            "id": document_id,
            "filename": "sample_document.pdf",
            "content": "This is sample document content...",
            "metadata": {
                "upload_date": "2024-01-15T10:00:00Z",
                "status": "processed"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting document: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document by ID"""
    try:
        # TODO: Implement actual document deletion from Azure Search
        logger.info(f"Document {document_id} deleted")
        return {"message": f"Document {document_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

# Batch processing status endpoints (similar to SEC documents)
@router.get("/batch/{batch_id}/status")
async def get_batch_processing_status(batch_id: str):
    """Get the current status of a batch processing operation"""
    if batch_id not in kb_batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch = kb_batches[batch_id]
    
    # Calculate overall progress
    total_docs = batch["total_files"]
    completed_docs = batch["completed"]
    failed_docs = batch["failed"]
    overall_progress = ((completed_docs + failed_docs) / total_docs * 100) if total_docs > 0 else 0
    
    # Get current processing status for each document
    current_processing = []
    for doc_id in batch["documents"]:
        if doc_id in kb_processing_status:
            doc_status = kb_processing_status[doc_id]
            current_processing.append({
                "document_id": doc_id,
                "filename": doc_status.get("filename", "Unknown"),
                "index": doc_status.get("index", "policy"),
                "stage": doc_status.get("stage", "unknown"),
                "progress_percent": doc_status.get("progress_percent", 0.0),
                "message": doc_status.get("message", "Unknown"),
                "started_at": doc_status.get("started_at", ""),
                "updated_at": doc_status.get("updated_at", ""),
                "completed_at": doc_status.get("completed_at"),
                "error_message": doc_status.get("error_message"),
                "chunks_created": doc_status.get("chunks_created", 0),
                "tokens_used": doc_status.get("tokens_used", 0)
            })
    
    return {
        "batch_id": batch_id,
        "total_documents": total_docs,
        "completed_documents": completed_docs,
        "failed_documents": failed_docs,
        "current_processing": current_processing,
        "overall_progress_percent": overall_progress,
        "started_at": batch["started_at"],
        "finished_at": batch.get("finished_at"),
        "status": "completed" if overall_progress >= 100 else "processing"
    }

@router.get("/batches")
async def list_batch_statuses():
    """List all batch processing statuses"""
    return list(kb_batches.values())

@router.delete("/batch/{batch_id}")
async def delete_batch_status(batch_id: str):
    """Delete a batch processing status (for cleanup)"""
    if batch_id in kb_batches:
        del kb_batches[batch_id]
    
    # Also clean up individual document statuses
    if batch_id in kb_batches:
        for doc_id in kb_batches[batch_id]["documents"]:
            if doc_id in kb_processing_status:
                del kb_processing_status[doc_id]
    
    return {"message": f"Batch {batch_id} status deleted"}

@router.get("/{document_id}/citations")
async def get_document_citations(document_id: str):
    """Get all citations that reference this document"""
    try:
        observability.track_request("get_document_citations")
        
        logger.info(f"Document citations requested: {document_id}")
        
        return {
            "document_id": document_id,
            "citations": [],
            "total_citations": 0
        }
    except Exception as e:
        logger.error(f"Error getting document citations {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document citations")

@router.get("/{document_id}/extracted-data")
async def get_document_extracted_data(document_id: str):
    """Get the extracted structured data from a processed document"""
    try:
        observability.track_request("get_document_extracted_data")
        
        logger.info(f"Document extracted data requested: {document_id}")
        
        # In a real implementation, this would query your document processing results
        # For now, return mock data similar to the Content Processing Solution Accelerator
        
        # Check if document exists in processing status
        if document_id not in kb_processing_status:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_status = kb_processing_status[document_id]
        
        # Mock extracted data based on document type
        extracted_data = {
            "policy_claim_info": {
                "first_name": "Emma",
                "last_name": "Martinez",
                "telephone_number": "718-555-0321",
                "policy_number": "PH789012",
                "coverage_type": "Homeowners",
                "claim_number": "CL456789",
                "policy_effective_date": "2020-08-10",
                "policy_expiration_date": "2021-08-10",
                "damage_deductible": 1000,
                "date_of_damage_loss": "2021-07-25",
                "time_of_loss": "16:45",
                "date_prepared": "2021-07-26"
            },
            "property_address": {
                "street": "9101 Oak St",
                "city": "Brooklyn",
                "state": "NY",
                "postal_code": "11201",
                "country": "USA"
            },
            "mailing_address": {
                "street": "9101 Oak St",
                "city": "Brooklyn",
                "state": "NY",
                "postal_code": "11201",
                "country": "USA"
            },
            "claim_details": {
                "cause_of_loss": "A tree fell on the roof during a storm, causing structural damage and water leakage into the attic.",
                "estimated_loss": 25000,
                "items_damaged": [
                    {
                        "item": "Samsung Galaxy S20",
                        "description": "Smartphone damaged by water",
                        "date_acquired": "2020-03-15",
                        "cost_new": 999,
                        "repair_cost": 450
                    },
                    {
                        "item": "Dell XPS 15 Laptop",
                        "description": "Laptop damaged by falling debris",
                        "date_acquired": "2019-11-20",
                        "cost_new": 1499,
                        "repair_cost": 800
                    }
                ]
            },
            "processing_metadata": {
                "entity_score": 99.5,
                "schema_score": 98.2,
                "confidence_score": 97.8,
                "processing_time_seconds": 2.3,
                "extraction_model": "gpt-4",
                "schema_version": "1.0"
            }
        }
        
        return {
            "document_id": document_id,
            "filename": doc_status.get("filename", "Unknown"),
            "extracted_data": extracted_data,
            "processing_status": doc_status.get("stage", "unknown"),
            "processing_timestamp": doc_status.get("completed_at"),
            "chunks_created": doc_status.get("chunks_created", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document extracted data {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document extracted data")

@router.get("/{document_id}/processing-steps")
async def get_document_processing_steps(document_id: str):
    """Get the processing steps and their status for a document"""
    try:
        observability.track_request("get_document_processing_steps")
        
        logger.info(f"Document processing steps requested: {document_id}")
        
        # Check if document exists in processing status
        if document_id not in kb_processing_status:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_status = kb_processing_status[document_id]
        
        # Mock processing steps based on the document status
        processing_steps = [
            {
                "step": "Document Upload",
                "status": "completed",
                "message": "Document uploaded successfully",
                "timestamp": doc_status.get("started_at", ""),
                "duration_seconds": 0.5
            },
            {
                "step": "Content Extraction",
                "status": "completed",
                "message": "Text and form fields extracted using Azure Document Intelligence",
                "timestamp": doc_status.get("started_at", ""),
                "duration_seconds": 1.2
            },
            {
                "step": "Data Mapping",
                "status": "completed",
                "message": "Data mapped to insurance claim schema",
                "timestamp": doc_status.get("started_at", ""),
                "duration_seconds": 0.8
            },
            {
                "step": "Validation",
                "status": "completed",
                "message": "Data validated against business rules and compliance requirements",
                "timestamp": doc_status.get("started_at", ""),
                "duration_seconds": 0.3
            },
            {
                "step": "Indexing",
                "status": "completed",
                "message": f"Document indexed with {doc_status.get('chunks_created', 0)} chunks",
                "timestamp": doc_status.get("completed_at", ""),
                "duration_seconds": 0.5
            }
        ]
        
        return {
            "document_id": document_id,
            "processing_steps": processing_steps,
            "total_duration_seconds": sum(step["duration_seconds"] for step in processing_steps),
            "overall_status": doc_status.get("stage", "unknown")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document processing steps {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document processing steps")
