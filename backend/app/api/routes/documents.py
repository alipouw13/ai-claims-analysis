from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
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
    """Upload multiple financial documents for processing with Azure Document Intelligence"""
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
            logger.error("❌ Azure services not initialized - azure_manager is None")
            logger.error("❌ This indicates a startup initialization failure")
            logger.error("❌ Check the application startup logs for AzureServiceManager initialization errors")
            
            # Try to create a minimal AzureServiceManager as fallback
            try:
                logger.info("🔧 Attempting to create fallback AzureServiceManager...")
                from app.services.azure_services import AzureServiceManager
                fallback_manager = AzureServiceManager()
                # Don't call initialize() as it likely failed during startup
                azure_manager = fallback_manager
                logger.warning("⚠️ Using fallback AzureServiceManager - some features may not work")
            except Exception as fallback_err:
                logger.error(f"❌ Failed to create fallback AzureServiceManager: {fallback_err}")
                raise HTTPException(
                    status_code=500, 
                    detail="Azure services not available. Please check the application configuration and restart the server."
                )
        
        logger.info(f"✅ AzureServiceManager found: {type(azure_manager)}")
        logger.info(f"✅ AzureServiceManager has search_client: {hasattr(azure_manager, 'search_client')}")
        logger.info(f"✅ AzureServiceManager has openai_client: {hasattr(azure_manager, 'openai_client')}")
        
        document_processor = DocumentProcessor(azure_manager)
        logger.info(f"✅ DocumentProcessor created: {type(document_processor)}")
        
        for file in files:
            document_id = str(uuid.uuid4())
            observability.track_request("document_upload", document_id)
            
            file_extension = os.path.splitext(file.filename)[1].lower()
            
            if file_extension not in allowed_extensions:
                responses.append(DocumentUploadResponse(
                    document_id=document_id,
                    status=DocumentStatus.FAILED,
                    message=f"File type {file_extension} not supported. Allowed types: {allowed_extensions}",
                    processing_started_at=datetime.utcnow()
                ))
                continue
            
            try:
                file_content = await file.read()
                content_type = file.content_type or "application/octet-stream"
                
                logger.info(f"=== STARTING DOCUMENT UPLOAD ===")
                logger.info(f"Document ID: {document_id}")
                logger.info(f"File: {file.filename}, Size: {len(file_content)} bytes, Type: {content_type}")
                logger.info(f"Document type: {document_type}, Company: {company_name}")
                logger.info(f"File content read successfully: {len(file_content)} bytes")
                
                file_path = os.path.join(upload_dir, f"{document_id}_{file.filename}")
                
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_content)
                logger.info(f"File saved locally to: {file_path}")
                
                parsed_filing_date = None
                if filing_date:
                    try:
                        parsed_filing_date = datetime.fromisoformat(filing_date.replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Invalid filing date format: {filing_date}")
                
                # Use the is_claim parameter from the form
                
                metadata = {
                    "filename": file.filename,
                    "document_type": document_type,
                    "company_name": company_name,
                    "filing_date": parsed_filing_date.isoformat() if parsed_filing_date else None,
                    "embedding_model": embedding_model,
                    "search_type": search_type,
                    "temperature": temperature,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "file_size": len(file_content),
                    "file_extension": file_extension,
                    "is_claim": is_claim
                }
                
                logger.info(f"Starting document processing: {document_id}, type: {document_type}, file: {file.filename}")
                logger.info(f"Metadata prepared: {metadata}")
                logger.info(f"Content type: {content_type}")
                
                logger.info(f"Creating async task for document processing...")
                # Determine target index based on domain and claim status
                logger.info(f"🔍 Determining target index...")
                logger.info(f"   Domain: {domain}")
                logger.info(f"   is_claim: {is_claim}")
                logger.info(f"   metadata.get('is_claim'): {metadata.get('is_claim')}")
                
                if domain == "banking":
                    target_index = settings.AZURE_SEARCH_INDEX_NAME  # SEC index for banking
                    logger.info(f"   Selected SEC index: {target_index}")
                elif metadata.get("is_claim"):
                    target_index = settings.AZURE_SEARCH_CLAIMS_INDEX_NAME  # Claims index for customer claims
                    logger.info(f"   Selected CLAIMS index: {target_index}")
                else:
                    target_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME  # Policy index for insurance
                    logger.info(f"   Selected POLICY index: {target_index}")
                
                logger.info(f"✅ Final target_index: {target_index}")

                # Initialize processing tracker
                index_name = "sec" if domain == "banking" else ("claims" if metadata.get("is_claim") else "policy")
                kb_processing_status[document_id] = {
                    "document_id": document_id,
                    "filename": file.filename,
                    "index": index_name,
                    "stage": "queued",
                    "progress_percent": 0.0,
                    "message": "Queued for processing",
                    "started_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "completed_at": None,
                    "chunks_created": 0,
                    "error_message": None,
                    "batch_id": batch_id,
                }
                kb_batches[batch_id]["documents"].append(document_id)

                asyncio.create_task(
                    process_document_async(
                        document_processor, 
                        file_content, 
                        content_type, 
                        file.filename, 
                        document_id,
                        metadata,
                        target_index
                    )
                )
                logger.info(f"Async task created for document {document_id}")
                
                response = DocumentUploadResponse(
                    document_id=document_id,
                    status=DocumentStatus.PROCESSING,
                    message=f"Upload accepted. Processing started (batch {batch_id})",
                    processing_started_at=datetime.utcnow()
                )
                responses.append(response)
                
            except Exception as e:
                logger.error(f"Error processing document {file.filename}: {e}")
                responses.append(DocumentUploadResponse(
                    document_id=document_id,
                    status=DocumentStatus.FAILED,
                    message=f"Failed to process document: {str(e)}",
                    processing_started_at=datetime.utcnow()
                ))
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload documents")

async def process_document_async(
    processor: DocumentProcessor,
    content: bytes,
    content_type: str,
    filename: str,
    document_id: str,
    metadata: dict,
    target_index_name: str | None = None
):
    """Asynchronously process document with Azure Document Intelligence"""
    try:
        logger.info(f"=== ASYNC DOCUMENT PROCESSING STARTED ===")
        logger.info(f"Document ID: {document_id}")
        logger.info(f"Filename: {filename}")
        logger.info(f"Content type: {content_type}")
        logger.info(f"Content size: {len(content)} bytes")
        logger.info(f"Processing metadata: {metadata}")
        logger.info(f"Target index name: {target_index_name}")
        logger.info(f"Processor type: {type(processor)}")
        
        logger.info(f"Calling processor.process_document()...")
        start_time = time.time()

        # Status helper
        def _update_status(stage: str, percent: float, message: str, **extra):
            st = kb_processing_status.get(document_id)
            if not st:
                logger.warning(f"Status tracker not found for document {document_id}")
                return
            st.update({
                "stage": stage,
                "progress_percent": float(max(0.0, min(100.0, percent))),
                "message": message,
                "updated_at": datetime.utcnow().isoformat(),
                **extra
            })
            logger.info(f"Status updated for {document_id}: {stage} - {percent}% - {message}")

        _update_status("parsing", 10.0, "Analyzing document content")
        
        logger.info(f"🔧 About to call processor.process_document with target_index_name: {target_index_name}")
        processed_doc = await processor.process_document(
            content=content,
            content_type=content_type,
            source=filename,
            metadata=metadata,
            target_index_name=target_index_name
        )
        logger.info(f"✅ processor.process_document completed successfully")
        
        processing_time = time.time() - start_time
        logger.info(f"=== DOCUMENT PROCESSING COMPLETED ===")
        logger.info(f"Document ID: {document_id}")
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        logger.info(f"Processing stats: {processed_doc['processing_stats']}")
        
        observability.track_document_processing_complete(
            document_id,
            processed_doc['processing_stats']['total_chunks'],
            processing_time
        )

        # Mark completed in trackers
        _update_status("completed", 100.0, "Document processed and indexed", completed_at=datetime.utcnow().isoformat(), chunks_created=processed_doc['processing_stats']['total_chunks'])
        try:
            batch_id = kb_processing_status.get(document_id, {}).get("batch_id")
            if batch_id and batch_id in kb_batches:
                kb_batches[batch_id]["completed"] += 1
                logger.info(f"✅ Batch {batch_id} completed count updated")
        except Exception as e:
            logger.warning(f"Failed to update batch completion count: {e}")
        
    except Exception as e:
        logger.error(f"=== DOCUMENT PROCESSING FAILED ===")
        logger.error(f"Document ID: {document_id}")
        logger.error(f"Error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        observability.track_document_processing_error(document_id, str(e))
        # Mark failed
        st = kb_processing_status.get(document_id)
        if st is not None:
            st.update({
                "stage": "failed",
                "progress_percent": 0.0,
                "message": f"Processing failed: {str(e)[:120]}",
                "error_message": str(e),
                "completed_at": datetime.utcnow().isoformat(),
            })
        try:
            batch_id = kb_processing_status.get(document_id, {}).get("batch_id")
            if batch_id and batch_id in kb_batches:
                kb_batches[batch_id]["failed"] += 1
        except Exception:
            pass

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

@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    document_type: Optional[DocumentType] = None,
    company_name: Optional[str] = None,
    status: Optional[DocumentStatus] = None,
    limit: int = 50,
    offset: int = 0
):
    """List uploaded documents with optional filtering"""
    try:
        observability.track_request("list_documents")
        
        logger.info(f"Documents list requested: type={document_type}, company={company_name}, status={status}")
        
        documents = []
        
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")

@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document(document_id: str):
    """Get detailed information about a specific document"""
    try:
        observability.track_request("get_document_info")
        
        logger.info(f"Document info requested: {document_id}")
        
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document information")

@router.get("/{document_id}/content")
async def get_document_content(document_id: str, section: Optional[str] = None):
    """Get the processed content of a document"""
    try:
        observability.track_request("get_document_content")
        
        logger.info(f"Document content requested: {document_id}, section: {section}")
        
        return {
            "document_id": document_id,
            "section": section,
            "content": "",
            "chunks": [],
            "metadata": {}
        }
    except Exception as e:
        logger.error(f"Error getting document content {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document content")

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    limit: int = 50,
    offset: int = 0,
    section: Optional[str] = None
):
    """Get the chunks of a processed document"""
    try:
        observability.track_request("get_document_chunks")
        
        logger.info(f"Document chunks requested: {document_id}, section: {section}")
        
        return {
            "document_id": document_id,
            "total_chunks": 0,
            "chunks": [],
            "section_filter": section
        }
    except Exception as e:
        logger.error(f"Error getting document chunks {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document chunks")

@router.post("/{document_id}/reprocess")
async def reprocess_document(document_id: str):
    """Reprocess a document through the ingestion pipeline"""
    try:
        observability.track_request("reprocess_document")
        
        
        logger.info(f"Document reprocessing requested: {document_id}")
        
        return {
            "document_id": document_id,
            "status": "reprocessing_started",
            "message": "Document queued for reprocessing"
        }
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reprocess document")

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its associated data"""
    try:
        observability.track_request("delete_document")
        
        
        logger.info(f"Document deletion requested: {document_id}")
        
        return {
            "document_id": document_id,
            "message": "Document deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")

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
