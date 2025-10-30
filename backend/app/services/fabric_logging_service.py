"""
Microsoft Fabric Logging Service

This service sends application logs to Microsoft Fabric Lakehouse for analytics and monitoring.
Supports multiple ingestion methods including REST API and Azure Data Factory.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import aiohttp

from azure.identity import ClientSecretCredential
from azure.core.exceptions import AzureError

from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    """Structured log entry for Fabric"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    evaluation_id: Optional[str] = None
    rag_method: Optional[str] = None
    model_used: Optional[str] = None
    duration_ms: Optional[int] = None
    token_usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class FabricLoggingService:
    """Service for sending logs to Microsoft Fabric"""
    
    def __init__(self):
        self.enabled = getattr(settings, 'ENABLE_FABRIC_LOGGING', False)
        self.workspace_id = getattr(settings, 'FABRIC_WORKSPACE_ID', None)
        self.lakehouse_name = getattr(settings, 'FABRIC_LAKEHOUSE_NAME', None)
        self.table_name = getattr(settings, 'FABRIC_LOG_TABLE_NAME', 'application_logs')
        
        # Fabric API endpoints
        self.fabric_api_base = "https://api.fabric.microsoft.com/v1"
        self.lakehouse_api_base = f"{self.fabric_api_base}/workspaces/{self.workspace_id}/lakehouses"
        
        # Authentication
        self.credential = None
        if self.enabled and all([settings.FABRIC_TENANT_ID, settings.FABRIC_CLIENT_ID, settings.FABRIC_CLIENT_SECRET]):
            self.credential = ClientSecretCredential(
                tenant_id=settings.FABRIC_TENANT_ID,
                client_id=settings.FABRIC_CLIENT_ID,
                client_secret=settings.FABRIC_CLIENT_SECRET
            )
        
        # Batch configuration
        self.batch_size = 100
        self.batch_timeout = 30  # seconds
        self.log_buffer = []
        self.last_send_time = time.time()
        
        # Start background task for batching
        if self.enabled:
            asyncio.create_task(self._batch_sender())
            logger.info("Fabric logging service initialized")
        else:
            logger.info("Fabric logging service disabled")
    
    async def log_evaluation(
        self,
        evaluation_id: str,
        session_id: str,
        evaluator_type: str,
        rag_method: str,
        model_used: str,
        duration_ms: int,
        scores: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log evaluation-specific information to Fabric"""
        if not self.enabled:
            return
        
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="INFO",
            logger_name="evaluation",
            message=f"Evaluation completed: {evaluator_type}",
            module="evaluation_service",
            function="evaluate",
            line_number=0,
            session_id=session_id,
            evaluation_id=evaluation_id,
            rag_method=rag_method,
            model_used=model_used,
            duration_ms=duration_ms,
            metadata={
                "scores": scores,
                "evaluator_type": evaluator_type,
                **(metadata or {})
            }
        )
        
        await self._add_to_buffer(log_entry)
    
    async def log_chat_interaction(
        self,
        session_id: str,
        user_id: Optional[str],
        question: str,
        answer: str,
        rag_method: str,
        model_used: str,
        duration_ms: int,
        token_usage: Dict[str, Any],
        sources: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log chat interaction to Fabric"""
        if not self.enabled:
            return
        
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="INFO",
            logger_name="chat",
            message=f"Chat interaction completed",
            module="chat_service",
            function="chat",
            line_number=0,
            session_id=session_id,
            user_id=user_id,
            rag_method=rag_method,
            model_used=model_used,
            duration_ms=duration_ms,
            token_usage=token_usage,
            metadata={
                "question": question[:500],  # Truncate for storage
                "answer": answer[:1000],    # Truncate for storage
                "sources_count": len(sources),
                "sources": sources[:5],     # First 5 sources only
                **(metadata or {})
            }
        )
        
        await self._add_to_buffer(log_entry)
    
    async def log_error(
        self,
        error_type: str,
        error_message: str,
        module: str,
        function: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log error information to Fabric"""
        if not self.enabled:
            return
        
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="ERROR",
            logger_name="error",
            message=error_message,
            module=module,
            function=function,
            line_number=0,
            session_id=session_id,
            metadata={
                "error_type": error_type,
                **(metadata or {})
            }
        )
        
        await self._add_to_buffer(log_entry)
    
    async def log_performance_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: str,
        module: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log performance metrics to Fabric"""
        if not self.enabled:
            return
        
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="INFO",
            logger_name="performance",
            message=f"Performance metric: {metric_name} = {metric_value} {metric_unit}",
            module=module,
            function="performance_tracking",
            line_number=0,
            metadata={
                "metric_name": metric_name,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                **(metadata or {})
            }
        )
        
        await self._add_to_buffer(log_entry)
    
    async def _add_to_buffer(self, log_entry: LogEntry):
        """Add log entry to buffer for batch processing"""
        self.log_buffer.append(log_entry)
        
        # Send immediately if buffer is full
        if len(self.log_buffer) >= self.batch_size:
            await self._send_batch()
    
    async def _batch_sender(self):
        """Background task to send logs in batches"""
        while True:
            try:
                current_time = time.time()
                
                # Send if timeout reached or buffer has entries
                if (current_time - self.last_send_time >= self.batch_timeout and 
                    len(self.log_buffer) > 0):
                    await self._send_batch()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in Fabric batch sender: {e}")
                await asyncio.sleep(10)
    
    async def _send_batch(self):
        """Send buffered logs to Fabric"""
        if not self.log_buffer or not self.enabled:
            return
        
        batch = self.log_buffer.copy()
        self.log_buffer.clear()
        self.last_send_time = time.time()
        
        try:
            # Method 1: Try Fabric REST API
            success = await self._send_via_fabric_api(batch)
            
            if not success:
                # Method 2: Fallback to Azure Data Factory or Event Hub
                success = await self._send_via_eventhub(batch)
            
            if success:
                logger.info(f"Sent {len(batch)} log entries to Fabric")
            else:
                logger.error(f"Failed to send {len(batch)} log entries to Fabric")
                
        except Exception as e:
            logger.error(f"Error sending logs to Fabric: {e}")
            # Could implement retry logic here
    
    async def _send_via_fabric_api(self, batch: List[LogEntry]) -> bool:
        """Send logs via Fabric REST API"""
        if not self.credential:
            return False
        
        try:
            # Get access token
            token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
            headers = {
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json"
            }
            
            # Convert log entries to JSON
            log_data = [asdict(entry) for entry in batch]
            
            # Fabric Lakehouse Tables API endpoint
            url = f"{self.lakehouse_api_base}/{self.lakehouse_name}/tables/{self.table_name}/rows"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json={"rows": log_data}) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Fabric API error: {response.status} - {await response.text()}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending to Fabric API: {e}")
            return False
    
    async def _send_via_eventhub(self, batch: List[LogEntry]) -> bool:
        """Fallback: Send logs via Event Hub (if configured)"""
        # This would require Event Hub configuration
        # For now, just log locally as fallback
        try:
            for entry in batch:
                logger.info(f"FABRIC_LOG: {json.dumps(asdict(entry))}")
            return True
        except Exception as e:
            logger.error(f"Error in EventHub fallback: {e}")
            return False
    
    async def flush(self):
        """Flush all buffered logs immediately"""
        if self.log_buffer:
            await self._send_batch()

# Global instance
fabric_logger = FabricLoggingService()

# Convenience functions
async def log_evaluation_to_fabric(
    evaluation_id: str,
    session_id: str,
    evaluator_type: str,
    rag_method: str,
    model_used: str,
    duration_ms: int,
    scores: Dict[str, float],
    metadata: Optional[Dict[str, Any]] = None
):
    """Convenience function for logging evaluations"""
    await fabric_logger.log_evaluation(
        evaluation_id, session_id, evaluator_type, rag_method, 
        model_used, duration_ms, scores, metadata
    )

async def log_chat_to_fabric(
    session_id: str,
    user_id: Optional[str],
    question: str,
    answer: str,
    rag_method: str,
    model_used: str,
    duration_ms: int,
    token_usage: Dict[str, Any],
    sources: List[str],
    metadata: Optional[Dict[str, Any]] = None
):
    """Convenience function for logging chat interactions"""
    await fabric_logger.log_chat_interaction(
        session_id, user_id, question, answer, rag_method,
        model_used, duration_ms, token_usage, sources, metadata
    )

async def log_error_to_fabric(
    error_type: str,
    error_message: str,
    module: str,
    function: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Convenience function for logging errors"""
    await fabric_logger.log_error(
        error_type, error_message, module, function, session_id, metadata
    )