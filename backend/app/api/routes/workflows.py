from fastapi import APIRouter, HTTPException, Request, Query
from typing import Dict, Any
import logging
import base64

from app.services.durable_client import AgentWorkflowClient


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/workflows/ingest")
async def start_ingestion(request: Request) -> Dict[str, Any]:
    try:
        data = await request.json()
        # Allow raw bytes or base64 string from the frontend
        document = data.get("document")
        if not document:
            raise HTTPException(status_code=400, detail="Missing document in body")

        content = document.get("content")
        if isinstance(content, str):
            try:
                # Content may be already base64 from the frontend; keep as-is
                base64.b64decode(content)
            except Exception:
                raise HTTPException(status_code=400, detail="Document content must be base64-encoded")

        client = AgentWorkflowClient()
        result = await client.start_document_ingestion(document)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to start ingestion workflow")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/qa")
async def start_qa(request: Request) -> Dict[str, Any]:
    try:
        qa_payload = await request.json()
        client = AgentWorkflowClient()
        result = await client.start_question_answer(qa_payload)
        return result
    except Exception as e:
        logger.exception("Failed to start QA workflow")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/status")
async def get_status(instance_id: str = Query(...)) -> Dict[str, Any]:
    try:
        client = AgentWorkflowClient()
        return await client.get_instance_status(instance_id)
    except Exception as e:
        logger.exception("Failed to get workflow status")
        raise HTTPException(status_code=500, detail=str(e))


