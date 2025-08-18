import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, List

import httpx

from app.core.config import settings
from app.services.azure_services import AzureServiceManager
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


async def ensure_index_vectorizer(azure_manager: AzureServiceManager, index_name: str) -> None:
    """Ensure the specified index has an Azure OpenAI vectorizer configured and referenced by its vector profile.

    Uses the 2024-07-01 API to add a top-level `vectorizers` collection and to set
    `vectorSearch.profiles[].vectorizer` to the created vectorizer name.
    """
    try:
        if not settings.AZURE_SEARCH_API_KEY:
            logger.info("AZURE_SEARCH_API_KEY not set; skipping vectorizer configuration")
            return

        endpoint = f"https://{settings.AZURE_SEARCH_SERVICE_NAME}.search.windows.net"
        api_version = "2024-07-01"
        url = f"{endpoint}/indexes/{index_name}?api-version={api_version}"

        headers = {
            "Content-Type": "application/json",
            "api-key": settings.AZURE_SEARCH_API_KEY,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            index_json = resp.json()

        vectorizer_name = "aoai_default_vectorizer"
        embed_deployment = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        resource_uri = settings.AZURE_OPENAI_ENDPOINT

        # Ensure vectorizers section exists and contains our vectorizer
        vectorizers = index_json.get("vectorizers") or []
        has_vectorizer = any(v.get("name") == vectorizer_name for v in vectorizers)
        if not has_vectorizer:
            vectorizers.append({
                "name": vectorizer_name,
                "kind": "azureOpenAI",
                "azureOpenAIParameters": {
                    "resourceUri": resource_uri,
                    "deploymentId": embed_deployment,
                    "modelName": embed_deployment,
                },
            })
            index_json["vectorizers"] = vectorizers

        # Ensure vector profile references our vectorizer
        vs = index_json.get("vectorSearch") or {}
        profiles = vs.get("profiles") or []
        if profiles:
            # Use the first profile or the one named default-vector-profile
            for p in profiles:
                if p.get("name") == "default-vector-profile" or "vectorizer" not in p:
                    p["vectorizer"] = vectorizer_name
        else:
            vs["profiles"] = [{
                "name": "default-vector-profile",
                "algorithm": "default-hnsw",
                "vectorizer": vectorizer_name,
            }]
        index_json["vectorSearch"] = vs

        # PUT update only if something changed: for simplicity, always PUT the merged doc
        async with httpx.AsyncClient(timeout=30.0) as client:
            put_resp = await client.put(url, headers=headers, json=index_json)
            put_resp.raise_for_status()
            logger.info(f"Vectorizer ensured for index '{index_name}' using deployment '{embed_deployment}'")
    except Exception as e:
        logger.warning(f"Could not ensure vectorizer for index '{index_name}': {e}")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _collect_pdf_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return sorted([p for p in directory.glob("*.pdf")])


async def bootstrap_policy_claims_vectorization(azure_manager: AzureServiceManager) -> None:
    """On server startup, vectorize sample policies and claims into their respective indexes.

    - Ensures vectorizers exist on policy/claims indexes.
    - Processes PDFs under `sample-docs/policies` and `sample-docs/claims`.
    - Skips documents that already appear in the index by filename.
    """
    try:
        policy_index = getattr(settings, 'AZURE_SEARCH_POLICY_INDEX_NAME', None)
        claims_index = getattr(settings, 'AZURE_SEARCH_CLAIMS_INDEX_NAME', None)
        if not policy_index and not claims_index:
            logger.info("No policy/claims indexes configured; skipping bootstrap vectorization")
            return

        # Ensure vectorizers on indexes (best effort) - handle missing indexes gracefully
        if policy_index:
            try:
                await ensure_index_vectorizer(azure_manager, policy_index)
            except Exception as e:
                logger.warning(f"Could not ensure vectorizer for policy index '{policy_index}': {e}")
                logger.info("Policy index may not exist yet - this is normal for initial setup")
        
        if claims_index:
            try:
                await ensure_index_vectorizer(azure_manager, claims_index)
            except Exception as e:
                logger.warning(f"Could not ensure vectorizer for claims index '{claims_index}': {e}")
                logger.info("Claims index may not exist yet - this is normal for initial setup")

        processor = DocumentProcessor(azure_manager)

        root = _repo_root()
        policies_dir = root / "sample-docs" / "policies"
        claims_dir = root / "sample-docs" / "claims"

        # Build quick sets of existing filenames in each index to avoid reprocessing
        existing_policy_names = set()
        existing_claims_names = set()
        
        if policy_index:
            try:
                docs = await azure_manager.list_unique_documents(policy_index, top_k=1000)
                existing_policy_names = {d.get('filename') for d in docs if d.get('filename')}
            except Exception as e:
                logger.warning(f"Could not list existing policy documents: {e}")
                logger.info("Policy index may not exist yet - skipping policy processing")
        
        if claims_index:
            try:
                docs = await azure_manager.list_unique_documents(claims_index, top_k=1000)
                existing_claims_names = {d.get('filename') for d in docs if d.get('filename')}
            except Exception as e:
                logger.warning(f"Could not list existing claims documents: {e}")
                logger.info("Claims index may not exist yet - skipping claims processing")

        # Process policies only if index exists and is accessible
        if policy_index and policies_dir.exists():
            for pdf in _collect_pdf_files(policies_dir):
                if pdf.name not in existing_policy_names:
                    try:
                        content = pdf.read_bytes()
                        await processor.process_document(
                            content=content,
                            content_type="application/pdf",
                            source=pdf.name,
                            metadata={"is_claim": False},
                            target_index_name=policy_index,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to vectorize policy '{pdf.name}': {e}")

        # Process claims only if index exists and is accessible
        if claims_index and claims_dir.exists():
            for pdf in _collect_pdf_files(claims_dir):
                if pdf.name not in existing_claims_names:
                    try:
                        content = pdf.read_bytes()
                        await processor.process_document(
                            content=content,
                            content_type="application/pdf",
                            source=pdf.name,
                            metadata={"is_claim": True},
                            target_index_name=claims_index,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to vectorize claim '{pdf.name}': {e}")

        logger.info("Bootstrap vectorization for policies/claims completed")
    except Exception as e:
        logger.warning(f"Bootstrap vectorization failed: {e}")
        logger.info("This is normal if indexes don't exist yet - they will be created when needed")


