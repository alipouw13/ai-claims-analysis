import os
import json
import aiohttp
import logging
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class DurableFunctionsClient:
    """Lightweight HTTP client for Azure Durable Functions.

    This client talks to a Functions host (local or Azure) using the admin HTTP API.
    If DURABLE_FUNCTIONS_BASE_URL is not configured, callers can optionally
    pass fallback callables to execute work in-process for local/dev use.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("DURABLE_FUNCTIONS_BASE_URL")
        self.api_key = api_key or os.getenv("DURABLE_FUNCTIONS_API_KEY")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-functions-key"] = self.api_key
        return headers

    async def start_new(self, orchestrator_name: str, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("DURABLE_FUNCTIONS_BASE_URL is not configured")

        url = f"{self.base_url}/orchestrators/{orchestrator_name}"
        logger.info(f"Starting durable orchestration '{orchestrator_name}'")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self._headers(), data=json.dumps(input_payload), timeout=120) as resp:
                if resp.status >= 300:
                    text = await resp.text()
                    raise RuntimeError(f"Failed to start orchestration {orchestrator_name}: {resp.status} {text}")
                return await resp.json()

    async def get_status(self, instance_id: str) -> Dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("DURABLE_FUNCTIONS_BASE_URL is not configured")

        url = f"{self.base_url}/instances/{instance_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers(), timeout=60) as resp:
                if resp.status >= 300:
                    text = await resp.text()
                    raise RuntimeError(f"Failed to get orchestration status {instance_id}: {resp.status} {text}")
                return await resp.json()


# Convenience helpers for common workflows used by this app
class AgentWorkflowClient:
    def __init__(self, durable: Optional[DurableFunctionsClient] = None):
        self.durable = durable or DurableFunctionsClient()

    async def start_document_ingestion(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Kick off the document intelligence -> chunk -> embed -> index pipeline.

        Expects a payload with fields: content (bytes base64), content_type, filename,
        metadata.
        """
        payload = {"action": "ingest_document", "document": document}
        return await self.durable.start_new("agent_orchestrator", payload)

    async def start_question_answer(self, qa_request: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"action": "answer_question", "request": qa_request}
        return await self.durable.start_new("agent_orchestrator", payload)

    async def get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        return await self.durable.get_status(instance_id)


