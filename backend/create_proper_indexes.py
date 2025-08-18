#!/usr/bin/env python3
"""
Script to create Azure AI Search indexes for policies and claims following Microsoft Content Processing Solution Accelerator patterns.
This script creates the missing indexes with proper vector search configuration.
"""

import asyncio
import logging
import os
from pathlib import Path
import sys

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType, SimpleField, 
    SearchableField, VectorSearch, HnswAlgorithmConfiguration,
    VectorSearchProfile, SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearch
)
from azure.core.credentials import AzureKeyCredential
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_search_indexes():
    """Create the policy and claims indexes in Azure AI Search with proper vector configuration"""
    
    if not settings.AZURE_SEARCH_SERVICE_NAME or not settings.AZURE_SEARCH_API_KEY:
        logger.error("Azure Search service name or API key not configured")
        logger.error("Please set AZURE_SEARCH_SERVICE_NAME and AZURE_SEARCH_API_KEY environment variables")
        return False
    
    endpoint = f"https://{settings.AZURE_SEARCH_SERVICE_NAME}.search.windows.net"
    credential = AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
    search_index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    
    # Configure vector search following Content Processing Solution Accelerator patterns
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="default-hnsw",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="default-vector-profile",
                algorithm_configuration_name="default-hnsw"
            )
        ]
    )
    
    # Configure semantic search
    semantic_config = SemanticConfiguration(
        name="default-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[
                SemanticField(field_name="content"),
                SemanticField(field_name="section_type")
            ],
            keywords_fields=[
                SemanticField(field_name="policy_number"),
                SemanticField(field_name="insured_name"),
                SemanticField(field_name="claim_id")
            ]
        )
    )
    
    semantic_search = SemanticSearch(
        configurations=[semantic_config],
        default_configuration_name="default-semantic-config"
    )
    
    # Create policy index
    policy_index_name = "policy-documents"
    try:
        logger.info(f"Creating policy index: {policy_index_name}")
        policy_fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="section_type", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="processed_at", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="citation_info", type=SearchFieldDataType.String),
            # Policy-specific metadata
            SimpleField(name="policy_number", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="insured_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="line_of_business", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="state", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="effective_date", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="expiration_date", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="deductible", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="coverage_limits", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="exclusions", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="endorsements", type=SearchFieldDataType.String, filterable=True),
            # Vector field
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="default-vector-profile"
            )
        ]
        
        policy_index = SearchIndex(
            name=policy_index_name,
            fields=policy_fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        search_index_client.create_index(policy_index)
        logger.info(f"Successfully created policy index: {policy_index_name}")
        
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info(f"Policy index {policy_index_name} already exists")
        else:
            logger.error(f"Failed to create policy index: {e}")
            return False
    
    # Create claims index
    claims_index_name = "claims-documents"
    try:
        logger.info(f"Creating claims index: {claims_index_name}")
        claims_fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="section_type", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="processed_at", type=SearchFieldDataType.String, filterable=True),
            # Claims-specific metadata
            SimpleField(name="claim_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="policy_number", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="insured_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="date_of_loss", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="loss_cause", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="location", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="coverage_decision", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="settlement_summary", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="payout_amount", type=SearchFieldDataType.Double, filterable=True),
            # Vector field
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="default-vector-profile"
            )
        ]
        
        claims_index = SearchIndex(
            name=claims_index_name,
            fields=claims_fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        search_index_client.create_index(claims_index)
        logger.info(f"Successfully created claims index: {claims_index_name}")
        
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info(f"Claims index {claims_index_name} already exists")
        else:
            logger.error(f"Failed to create claims index: {e}")
            return False
    
    logger.info("Index creation completed successfully!")
    return True

if __name__ == "__main__":
    success = create_search_indexes()
    if success:
        logger.info("✅ All indexes created successfully!")
        logger.info("The policy and claims indexes are now ready for document processing.")
    else:
        logger.error("❌ Failed to create indexes. Please check your Azure configuration.")
        sys.exit(1)
