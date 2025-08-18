from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

# Import the global trackers from documents router
from app.api.routes.documents import kb_processing_status, kb_batches

router = APIRouter()
logger = logging.getLogger(__name__)

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
