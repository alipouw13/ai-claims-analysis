# Azure Document Intelligence Integration for Insurance Documents

## Overview

This document describes the integration of Azure Document Intelligence (formerly Azure Form Recognizer) for processing insurance documents in the Agentic RAG system. The integration replaces the previous Azure AI Content Understanding approach with a more specialized and accurate document processing pipeline specifically designed for insurance documents.

## Architecture

### Key Components

1. **InsuranceDocumentService**: Core service that orchestrates document processing using Azure Document Intelligence
2. **Field Extraction Patterns**: Insurance-specific regex patterns for extracting key information
3. **Azure Document Intelligence Integration**: Direct integration with Azure's prebuilt-document model
4. **Document Chunking**: Intelligent chunking using the existing DocumentChunker utility
5. **Credibility Assessment**: Document quality and reliability scoring

### Data Flow

```
Insurance Document Upload → Azure Document Intelligence → Field Extraction → Chunking → Indexing
```

## Azure Document Intelligence Integration

### Model Used

- **Model**: `prebuilt-document`
- **Purpose**: General document analysis with enhanced table and key-value pair extraction
- **Benefits**: Better accuracy for insurance documents, improved table recognition, structured output

### Extracted Content

The service extracts the following content types from insurance documents:

- **Text Content**: Full document text with confidence scores
- **Tables**: Structured table data with cell-level information
- **Key-Value Pairs**: Form fields and their values
- **Paragraphs**: Document sections with roles
- **Words**: Individual words with bounding boxes and confidence
- **Lines**: Text lines with positioning information
- **Pages**: Page count and metadata

### Field Extraction

#### Policy Document Fields

- Policy Number
- Insured Name
- Coverage Type
- Effective Date
- Expiration Date
- Coverage Amount
- Deductible

#### Claim Document Fields

- Claim Number
- Policy Number
- Insured Name
- Claim Amount
- Date of Loss
- Cause of Loss

#### Extraction Strategy

1. **Primary**: Use Azure Document Intelligence key-value pairs (most accurate)
2. **Fallback**: Apply insurance-specific regex patterns
3. **Validation**: Parse and normalize extracted values (dates, currency, etc.)

## API Endpoints

### Main Documents Route (`/api/v1/documents/upload`)

Handles all document uploads with conditional processing:

```python
# For insurance documents
if domain == "insurance":
    document_processor = InsuranceDocumentService(azure_manager)
    # Routes to appropriate index based on is_claim parameter
else:
    document_processor = DocumentProcessor(azure_manager)
```

### Insurance-Specific Route (`/api/v1/insurance/upload`)

Dedicated endpoint for insurance documents:

```python
@router.post("/upload")
async def upload_insurance_documents(
    files: List[UploadFile],
    document_type: str,  # 'policy' or 'claim'
    company_name: Optional[str] = None
)
```

### Batch Status Tracking

Both routes provide batch processing status:

```python
@router.get("/batch-status/{batch_id}")
async def get_document_batch_status(batch_id: str)
```

## Configuration

### Environment Variables

```bash
# Azure Document Intelligence (Form Recognizer)
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=your-key-here

# Azure Search Indexes
AZURE_SEARCH_POLICY_INDEX_NAME=policy-documents
AZURE_SEARCH_CLAIMS_INDEX_NAME=claims-documents
```

### Azure Resource Setup

1. **Create Form Recognizer Resource**:
   - Go to Azure Portal
   - Create Cognitive Services resource
   - Select Form Recognizer service
   - Note the endpoint and key

2. **Configure Indexes**:
   - Ensure policy and claims indexes exist
   - Configure appropriate schemas for insurance documents

## Usage Examples

### Processing a Policy Document

```python
from app.services.insurance_document_service import InsuranceDocumentService

# Initialize service
service = InsuranceDocumentService(azure_manager)

# Process document
result = await service.process_insurance_document(
    content=file_content,
    content_type="application/pdf",
    filename="policy.pdf",
    document_type="policy",
    metadata={"company": "Sample Insurance"}
)

# Access results
print(f"Policy Number: {result['insurance_fields']['policy_number']}")
print(f"Coverage Amount: {result['insurance_fields']['coverage_amount']}")
print(f"Chunks Created: {len(result['chunks'])}")
```

### Processing a Claim Document

```python
# Process claim document
result = await service.process_insurance_document(
    content=file_content,
    content_type="application/pdf",
    filename="claim.pdf",
    document_type="claim",
    metadata={"company": "Sample Insurance"}
)

# Access claim-specific fields
print(f"Claim Number: {result['insurance_fields']['claim_number']}")
print(f"Claim Amount: {result['insurance_fields']['claim_amount']}")
print(f"Date of Loss: {result['insurance_fields']['date_of_loss']}")
```

## Field Extraction Examples

### Sample Policy Document

```
POLICY DOCUMENT
Policy Number: POL123456
Insured Name: John Doe
Coverage Type: Homeowners Insurance
Effective Date: 01/01/2024
Expiration Date: 01/01/2025
Coverage Amount: $500,000
Deductible: $1,000
```

**Extracted Fields**:
- `policy_number`: "POL123456"
- `insured_name`: "John Doe"
- `coverage_type`: "Homeowners Insurance"
- `effective_date`: "2024-01-01"
- `expiration_date`: "2025-01-01"
- `coverage_amount`: 500000.0
- `deductible`: 1000.0

### Sample Claim Document

```
CLAIM FORM
Claim Number: CLM789012
Policy Number: POL123456
Insured Name: John Doe
Date of Loss: 12/15/2023
Cause of Loss: Water damage
Claim Amount: $15,000
```

**Extracted Fields**:
- `claim_number`: "CLM789012"
- `policy_number`: "POL123456"
- `insured_name`: "John Doe"
- `date_of_loss`: "2023-12-15"
- `cause_of_loss`: "Water damage"
- `claim_amount`: 15000.0

## Benefits

### Accuracy Improvements

- **Better Table Recognition**: Azure Document Intelligence excels at extracting tabular data
- **Structured Output**: Consistent JSON structure for all document types
- **Confidence Scoring**: Built-in confidence scores for extracted content
- **Insurance-Specific**: Tailored field extraction for insurance documents

### Performance Benefits

- **Faster Processing**: Optimized for document analysis
- **Scalable**: Handles large document volumes efficiently
- **Reliable**: Azure-managed service with high availability

### Integration Benefits

- **Unified Pipeline**: Same service handles both policies and claims
- **Batch Processing**: Efficient handling of multiple documents
- **Progress Tracking**: Real-time status updates for document processing
- **Error Handling**: Comprehensive error handling and logging

## Migration Guide

### From Azure AI Content Understanding

1. **Update Environment Variables**:
   - Replace `AZURE_AI_CONTENT_UNDERSTANDING_*` with `AZURE_FORM_RECOGNIZER_*`

2. **Update Service Usage**:
   - Replace `ContentUnderstandingService` with `InsuranceDocumentService`
   - Update method calls to use new API

3. **Update Index Schemas**:
   - Ensure indexes support new field structure
   - Update search queries if necessary

### Testing

1. **Run Test Script**:
   ```bash
   cd test
   python test_insurance_document_intelligence.py
   ```

2. **Verify Integration**:
   - Check Azure Document Intelligence connectivity
   - Test with sample insurance documents
   - Verify field extraction accuracy

## Troubleshooting

### Common Issues

1. **Azure Document Intelligence Not Configured**:
   - Check environment variables
   - Verify Azure resource exists and is accessible
   - Check authentication credentials

2. **Field Extraction Failures**:
   - Verify document format is supported
   - Check document quality and readability
   - Review regex patterns for specific fields

3. **Processing Errors**:
   - Check Azure service quotas and limits
   - Verify document size limits
   - Review error logs for specific issues

### Debug Information

The service provides comprehensive logging:

```python
logger.info(f"=== INSURANCE DOCUMENT PROCESSING START ===")
logger.info(f"Filename: {filename}")
logger.info(f"Document Type: {document_type}")
logger.info(f"Content Size: {len(content)} bytes")
```

### Error Handling

- **Graceful Degradation**: Falls back to regex patterns if Azure DI fails
- **Detailed Logging**: Comprehensive error information for debugging
- **Batch Status Updates**: Real-time progress and error reporting

## Future Enhancements

### Planned Features

1. **Custom Models**: Train custom models for specific insurance companies
2. **Advanced Validation**: Business rule validation for extracted data
3. **Integration APIs**: Direct integration with insurance systems
4. **Real-time Processing**: Stream processing for high-volume scenarios

### Performance Optimizations

1. **Caching**: Cache frequently accessed document patterns
2. **Parallel Processing**: Process multiple documents simultaneously
3. **Incremental Updates**: Update only changed document sections

## Conclusion

The Azure Document Intelligence integration provides a robust, accurate, and scalable solution for processing insurance documents. It offers significant improvements over previous approaches while maintaining compatibility with existing systems. The service is ready for production use and provides a solid foundation for future enhancements.
