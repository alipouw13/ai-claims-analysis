from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import time
import logging
import asyncio
import platform
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Fix Windows event loop policy for aiodns compatibility
# aiodns requires SelectorEventLoop on Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set specific loggers to appropriate levels
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("azure").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("fastapi").setLevel(logging.INFO)

# Reduce noise from some verbose Azure libraries
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)

from app.core.config import settings
from app.api.routes import knowledge_base, chat, admin, documents, qa, sec_documents, deployments, evaluation, workflows, agents, insurance_orchestration, batch
from app.services.azure_services import AzureServiceManager
from app.services.agents.azure_ai_agent_service import AzureAIAgentService
from app.services.bootstrap_vectorization import bootstrap_policy_claims_vectorization
from app.core.observability import observability, setup_fastapi_instrumentation
from app.core.tracing import setup_ai_foundry_tracing
# Temporarily disable evaluation due to package conflicts
from app.core.evaluation import setup_evaluation_framework, EvaluationFrameworkType
from app.core.azure_ai_foundry_evaluators import AzureEvaluationConfig

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with observability and evaluation setup"""
    logger = logging.getLogger(__name__)
    logger.info("Starting RAG Financial Assistant API")
    
    # Initialize Azure AI Foundry tracing
    logger.info("🔍 Setting up Azure AI Foundry tracing...")
    tracing_success = setup_ai_foundry_tracing()
    if tracing_success:
        logger.info("✅ Azure AI Foundry tracing enabled - traces will be visible in AI Foundry portal")
    else:
        logger.warning("⚠️ Azure AI Foundry tracing setup failed - continuing without tracing")
    
    azure_manager = None
    try:
        logger.info("🔧 Initializing Azure Service Manager...")
        azure_manager = AzureServiceManager()
        logger.info("✅ AzureServiceManager instance created")
        
        logger.info("🔧 Calling azure_manager.initialize()...")
        await azure_manager.initialize()
        logger.info("✅ AzureServiceManager initialized successfully")
        
        # Store in app state BEFORE any other operations
        app.state.azure_manager = azure_manager
        logger.info("✅ AzureServiceManager stored in app.state")
        
        # Kick off best-effort bootstrap vectorization of sample policies/claims
        try:
            logger.info("🔧 Starting bootstrap vectorization task...")
            asyncio.create_task(bootstrap_policy_claims_vectorization(azure_manager))
            logger.info("✅ Bootstrap vectorization task scheduled")
        except Exception as boot_err:
            logger.warning(f"❌ Bootstrap vectorization task failed to schedule: {boot_err}")
            logger.warning("This is not critical - the system will still work for uploads")
        
        if hasattr(azure_manager, 'openai_client'):
            # Setup Azure AI Foundry evaluation framework
            try:
                framework_type_str = os.getenv("EVALUATION_FRAMEWORK_TYPE", "custom")
                if framework_type_str == "azure_ai_foundry":
                    framework_type = EvaluationFrameworkType.AZURE_AI_FOUNDRY
                elif framework_type_str == "hybrid":
                    framework_type = EvaluationFrameworkType.HYBRID
                else:
                    framework_type = EvaluationFrameworkType.CUSTOM
                
                azure_config = None
                if framework_type in [EvaluationFrameworkType.AZURE_AI_FOUNDRY, EvaluationFrameworkType.HYBRID]:
                    azure_config = AzureEvaluationConfig(
                        project_connection_string=os.getenv("AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING"),
                        model_config={
                            "azure_endpoint": settings.AZURE_OPENAI_ENDPOINT,
                            "api_key": settings.AZURE_OPENAI_API_KEY,
                            "azure_deployment": settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                            "api_version": settings.AZURE_OPENAI_API_VERSION
                        }
                    )
                
                setup_evaluation_framework(
                    azure_openai_client=azure_manager.openai_client,
                    cosmos_client=getattr(azure_manager, 'cosmos_client', None),
                    framework_type=framework_type,
                    azure_config=azure_config
                )
                logger.info(f"✅ Evaluation framework initialized with type: {framework_type.value}")
            except Exception as eval_error:
                logger.warning(f"⚠️ Evaluation framework setup failed: {eval_error}")
                logger.info("Continuing without evaluation framework")
        
        # Warm up Azure AI Agents: ensure a default agent exists to avoid 404 at runtime
        try:
            from app.services.knowledge_base_manager import AdaptiveKnowledgeBaseManager
            from app.services.agents.multi_agent_orchestrator import MultiAgentOrchestrator
            kb_manager = AdaptiveKnowledgeBaseManager(azure_manager)
            orchestrator = MultiAgentOrchestrator(azure_manager, kb_manager)
            agent_service: AzureAIAgentService = await orchestrator._get_azure_ai_agent_service()
            deployment_name = getattr(settings, 'AZURE_OPENAI_CHAT_DEPLOYMENT_NAME', 'gpt-4.1-mini')
            # Ensure core financial agents
            await agent_service.find_or_create_agent(
                agent_name="Chat_Content_Agent",
                instructions=(
                    "You are a helpful financial assistant. Answer clearly and concisely. "
                    "Cite sources when provided in context."
                ),
                model_deployment=deployment_name,
            )
            # Ensure all three financial QA agents by level
            financial_levels = [
                ("Financial_QA_Agent_Basic", "basic"),
                ("Financial__QA_Agent_Thorough", "thorough"),
                ("Financial__QA_Agent_Comprehensive", "comprehensive"),
            ]
            for agent_name, lvl in financial_levels:
                await agent_service.create_qa_agent(
                    name=agent_name,
                    instructions=f"You are a financial QA agent for {lvl} verification.",
                    model_deployment=deployment_name,
                )
            await agent_service.create_content_generator_agent(
                name="Financial_Content_Generator_Agent",
                instructions="You generate financial content with accurate citations.",
                model_deployment=deployment_name,
            )
            # Insurance agent warm-up removed - using Semantic Kernel orchestrator instead
            logger.info("Azure AI Agent warm-up completed (financial only)")
        except Exception as warm_err:
            logger.warning(f"Agent warm-up failed (will fall back at runtime): {warm_err}")

        logger.info("Azure services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Azure services: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Even if initialization fails, try to create a minimal azure_manager
        try:
            logger.info("🔧 Attempting to create minimal AzureServiceManager...")
            azure_manager = AzureServiceManager()
            # Don't call initialize() if it failed before
            app.state.azure_manager = azure_manager
            logger.warning("⚠️ Minimal AzureServiceManager created - some features may not work")
        except Exception as fallback_err:
            logger.error(f"❌ Failed to create even minimal AzureServiceManager: {fallback_err}")
            app.state.azure_manager = None
    
    yield
    
    logger.info("Shutting down RAG Financial Assistant API")
    if azure_manager:
        try:
            await azure_manager.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

application = FastAPI(
    title="RAG Financial Adaptive Knowledge Base",
    description="Adaptive Knowledge Base Management for Financial Documents with comprehensive observability",
    version="1.0.0",
    lifespan=lifespan
)

setup_fastapi_instrumentation(application)
#setup_ai_foundry_tracing(application)

application.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@application.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """Middleware to handle large file uploads for financial documents"""
    if request.method == "POST" and "upload" in str(request.url).lower():
        max_size = 100 * 1024 * 1024  # 100MB
        content_length = request.headers.get("content-length")
        
        if content_length and int(content_length) > max_size:
            return JSONResponse(
                status_code=413,
                content={"detail": f"File too large. Maximum size allowed is {max_size // (1024*1024)}MB"}
            )
    
    response = await call_next(request)
    return response

@application.middleware("http")
async def track_requests(request: Request, call_next):
    """Middleware to track all requests for observability"""
    start_time = time.time()
    
    session_id = request.headers.get("X-Session-ID")
    user_id = request.headers.get("X-User-ID")
    
    observability.track_request(
        endpoint=str(request.url.path),
        user_id=user_id,
        session_id=session_id
    )
    
    try:
        async with observability.trace_operation(
            "http_request",
            endpoint=str(request.url.path),
            method=request.method,
            session_id=session_id or "unknown"
        ) as span:
            response = await call_next(request)
            
            duration = time.time() - start_time
            observability.track_response_time(
                endpoint=str(request.url.path),
                duration=duration,
                session_id=session_id
            )
            
            span.set_attribute("response.status_code", response.status_code)
            span.set_attribute("response.duration", duration)
            
            return response
            
    except Exception as e:
        duration = time.time() - start_time
        observability.track_error(
            error_type=type(e).__name__,
            endpoint=str(request.url.path),
            error_message=str(e),
            session_id=session_id,
            user_id=user_id
        )
        
        logging.getLogger(__name__).error(f"Request failed: {request.url.path} - {str(e)}")
        raise

application.include_router(knowledge_base.router, prefix="/api/v1/knowledge-base", tags=["Knowledge Base"])
application.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
application.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
application.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
application.include_router(qa.router, prefix="/api/v1/qa", tags=["QA"])
application.include_router(qa.ins_router, prefix="/api/v1/qa", tags=["QA-Insurance"])
application.include_router(evaluation.router, prefix="/api/v1/evaluation", tags=["Evaluation"])
application.include_router(deployments.router, prefix="/api/v1", tags=["Deployments"])
application.include_router(sec_documents.router, tags=["SEC Documents"])
application.include_router(workflows.router, prefix="/api/v1", tags=["Workflows"])
application.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
application.include_router(insurance_orchestration.router, prefix="/api/v1/insurance", tags=["Insurance Orchestration"])
application.include_router(batch.router, prefix="/api/v1", tags=["Batch"])


@application.get("/")
async def root():
    return {"message": "RAG Financial POC - Adaptive Knowledge Base Management"}

@application.get("/health")
async def health_check():
    """Enhanced health check with system metrics"""
    try:
        metrics_summary = observability.get_metrics_summary(hours=1)
        
        return {
            "status": "healthy",
            "service": "rag-financial-backend",
            "version": "1.0.0",
            "metrics": {
                "requests_last_hour": len(metrics_summary.get("requests", {}).get("recent", [])),
                "errors_last_hour": len(metrics_summary.get("errors", {}).get("recent", [])),
                "avg_response_time": metrics_summary.get("response_times", {}).get("average", 0)
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logging.getLogger(__name__).error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "service": "rag-financial-backend",
            "error": str(e),
            "timestamp": time.time()
        }

app = application

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=8000)
