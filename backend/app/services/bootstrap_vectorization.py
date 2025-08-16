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
            # Get current index schema
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            index_json = resp.json()
            
            logger.info(f"Current index schema for '{index_name}': {len(index_json.get('fields', []))} fields")

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
            logger.info(f"Added vectorizer '{vectorizer_name}' to index '{index_name}'")

        # Ensure vector profile references our vectorizer
        vs = index_json.get("vectorSearch") or {}
        profiles = vs.get("profiles") or []
        if profiles:
            # Use the first profile or the one named default-vector-profile
            for p in profiles:
                if p.get("name") == "default-vector-profile" or "vectorizer" not in p:
                    p["vectorizer"] = vectorizer_name
                    logger.info(f"Updated vector profile '{p.get('name', 'unnamed')}' with vectorizer '{vectorizer_name}'")
        else:
            vs["profiles"] = [{
                "name": "default-vector-profile",
                "algorithm": "default-hnsw",
                "vectorizer": vectorizer_name,
            }]
            logger.info(f"Created new vector profile 'default-vector-profile' with vectorizer '{vectorizer_name}'")
        index_json["vectorSearch"] = vs

        # Only update if we made changes
        if has_vectorizer and all(p.get("vectorizer") == vectorizer_name for p in profiles):
            logger.info(f"Vectorizer already properly configured for index '{index_name}'")
            return

        # PUT update only if something changed
        logger.info(f"Updating index '{index_name}' with vectorizer configuration...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            put_resp = await client.put(url, headers=headers, json=index_json)
            put_resp.raise_for_status()
            logger.info(f"Vectorizer ensured for index '{index_name}' using deployment '{embed_deployment}'")
    except Exception as e:
        logger.warning(f"Could not ensure vectorizer for index '{index_name}': {e}")
        logger.exception("Full error details:")


async def ensure_insurance_indexes_exist() -> None:
    """Create the policy and claims indexes if they don't exist"""
    try:
        if not settings.AZURE_SEARCH_API_KEY:
            logger.info("AZURE_SEARCH_API_KEY not set; skipping index creation")
            return

        endpoint = f"https://{settings.AZURE_SEARCH_SERVICE_NAME}.search.windows.net"
        api_version = "2024-07-01"
        
        logger.info(f"Ensuring insurance indexes exist on {endpoint}")
        
        headers = {
            "Content-Type": "application/json",
            "api-key": settings.AZURE_SEARCH_API_KEY,
        }

        # Define the index schema for insurance documents
        index_schema = {
            "name": "",  # Will be set for each index
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "searchable": False},
                {"name": "content", "type": "Edm.String", "searchable": True, "analyzer": "en.microsoft"},
                {"name": "document_title", "type": "Edm.String", "searchable": True, "filterable": True},
                {"name": "document_type", "type": "Edm.String", "filterable": True, "facetable": True},
                {"name": "company", "type": "Edm.String", "filterable": True, "facetable": True},
                {"name": "filing_date", "type": "Edm.String", "filterable": True},
                {"name": "chunk_id", "type": "Edm.String", "filterable": True},
                {"name": "metadata", "type": "Edm.String", "searchable": False},
                {"name": "created_date", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
                {"name": "credibility_score", "type": "Edm.Double", "filterable": True},
                {"name": "is_claim", "type": "Edm.Boolean", "filterable": True},
                {"name": "policy_number", "type": "Edm.String", "filterable": True},
                {"name": "claim_number", "type": "Edm.String", "filterable": True},
                {"name": "insured_name", "type": "Edm.String", "filterable": True},
                {"name": "coverage_type", "type": "Edm.String", "filterable": True},
                {"name": "effective_date", "type": "Edm.String", "filterable": True},
                {"name": "expiration_date", "type": "Edm.String", "filterable": True},
                {"name": "coverage_amount", "type": "Edm.Double", "filterable": True},
                {"name": "deductible", "type": "Edm.Double", "filterable": True},
                {"name": "claim_amount", "type": "Edm.Double", "filterable": True},
                {"name": "date_of_loss", "type": "Edm.String", "filterable": True},
                {"name": "cause_of_loss", "type": "Edm.String", "filterable": True}
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create policy-documents index
            policy_index_name = settings.AZURE_SEARCH_POLICY_INDEX_NAME
            if policy_index_name:
                logger.info(f"Checking/creating policy index: {policy_index_name}")
                policy_url = f"{endpoint}/indexes/{policy_index_name}?api-version={api_version}"
                policy_schema = index_schema.copy()
                policy_schema["name"] = policy_index_name
                
                try:
                    # Check if index exists
                    logger.info(f"Checking if index exists: {policy_url}")
                    resp = await client.get(policy_url, headers=headers)
                    if resp.status_code == 200:
                        logger.info(f"Index '{policy_index_name}' already exists")
                    else:
                        raise Exception(f"Unexpected status: {resp.status_code}")
                except Exception as e:
                    # Index doesn't exist, create it
                    logger.info(f"Creating index '{policy_index_name}' - Error was: {e}")
                    create_url = f"{endpoint}/indexes?api-version={api_version}"
                    logger.info(f"POST to: {create_url}")
                    logger.info(f"Schema: {policy_schema}")
                    resp = await client.post(create_url, headers=headers, json=policy_schema)
                    if resp.status_code == 201:
                        logger.info(f"Successfully created index '{policy_index_name}'")
                    else:
                        logger.error(f"Failed to create index '{policy_index_name}': {resp.status_code} - {resp.text}")
                        resp.raise_for_status()

            # Create claims-documents index
            claims_index_name = settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
            if claims_index_name:
                logger.info(f"Checking/creating claims index: {claims_index_name}")
                claims_url = f"{endpoint}/indexes/{claims_index_name}?api-version={api_version}"
                claims_schema = index_schema.copy()
                claims_schema["name"] = claims_index_name
                
                try:
                    # Check if index exists
                    logger.info(f"Checking if index exists: {claims_url}")
                    resp = await client.get(claims_url, headers=headers)
                    if resp.status_code == 200:
                        logger.info(f"Index '{claims_index_name}' already exists")
                    else:
                        raise Exception(f"Unexpected status: {resp.status_code}")
                except Exception as e:
                    # Index doesn't exist, create it
                    logger.info(f"Creating index '{claims_index_name}' - Error was: {e}")
                    create_url = f"{endpoint}/indexes?api-version={api_version}"
                    logger.info(f"POST to: {create_url}")
                    logger.info(f"Schema: {claims_schema}")
                    resp = await client.post(create_url, headers=headers, json=claims_schema)
                    if resp.status_code == 201:
                        logger.info(f"Successfully created index '{claims_index_name}'")
                    else:
                        logger.error(f"Failed to create index '{claims_index_name}': {resp.status_code} - {resp.text}")
                        resp.raise_for_status()

    except Exception as e:
        logger.warning(f"Could not ensure insurance indexes exist: {e}")
        logger.exception("Full error details:")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _collect_pdf_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return sorted([p for p in directory.glob("*.pdf")])


async def bootstrap_policy_claims_vectorization(azure_manager: AzureServiceManager) -> None:
    """On server startup, vectorize sample policies and claims into their respective indexes.

    - Ensures vectorizers exist on policy/claims indexes.
    - Processes PDFs under `sample-docs/policies` and `sample-docs/claims` using Document Intelligence.
    - Skips documents that already appear in the index by filename.
    """
    try:
        policy_index = getattr(settings, 'AZURE_SEARCH_POLICY_INDEX_NAME', None)
        claims_index = getattr(settings, 'AZURE_SEARCH_CLAIMS_INDEX_NAME', None)
        if not policy_index and not claims_index:
            logger.info("No policy/claims indexes configured; skipping bootstrap vectorization")
            return

        # First, ensure the indexes exist
        await ensure_insurance_indexes_exist()

        # Then ensure vectorizers on indexes (best effort)
        if policy_index:
            await ensure_index_vectorizer(azure_manager, policy_index)
        if claims_index:
            await ensure_index_vectorizer(azure_manager, claims_index)

        # Use InsuranceDocumentService for Document Intelligence processing
        from app.services.insurance_document_service import InsuranceDocumentService
        insurance_service = InsuranceDocumentService(azure_manager)

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
            except Exception:
                pass
        if claims_index:
            try:
                docs = await azure_manager.list_unique_documents(claims_index, top_k=1000)
                existing_claims_names = {d.get('filename') for d in docs if d.get('filename')}
            except Exception:
                pass

        # Process policies using Document Intelligence
        for pdf in _collect_pdf_files(policies_dir):
            if policy_index and pdf.name not in existing_policy_names:
                try:
                    logger.info(f"Processing policy document with Document Intelligence: {pdf.name}")
                    content = pdf.read_bytes()
                    content_type = "application/pdf"
                    
                    # Process with InsuranceDocumentService (uses Document Intelligence)
                    await insurance_service.process_insurance_document(
                        content=content,
                        content_type=content_type,
                        filename=pdf.name,
                        document_type="policy",
                        metadata={
                            "source": "bootstrap",
                            "target_index_name": policy_index,
                            "is_claim": False
                        }
                    )
                    logger.info(f"Successfully processed policy document: {pdf.name}")
                except Exception as e:
                    logger.warning(f"Failed to vectorize policy '{pdf.name}' with Document Intelligence: {e}")

        # Process claims using Document Intelligence
        for pdf in _collect_pdf_files(claims_dir):
            if claims_index and pdf.name not in existing_claims_names:
                try:
                    logger.info(f"Processing claim document with Document Intelligence: {pdf.name}")
                    content = pdf.read_bytes()
                    content_type = "application/pdf"
                    
                    # Process with InsuranceDocumentService (uses Document Intelligence)
                    await insurance_service.process_insurance_document(
                        content=content,
                        content_type=content_type,
                        filename=pdf.name,
                        document_type="claim",
                        metadata={
                            "source": "bootstrap",
                            "target_index_name": claims_index,
                            "is_claim": True
                        }
                    )
                    logger.info(f"Successfully processed claim document: {pdf.name}")
                except Exception as e:
                    logger.warning(f"Failed to vectorize claim '{pdf.name}' with Document Intelligence: {e}")

        logger.info("Bootstrap vectorization for policies/claims completed using Document Intelligence")
    except Exception as e:
        logger.warning(f"Bootstrap vectorization failed: {e}")
        logger.exception("Full error details:")


