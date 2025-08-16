import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import hashlib
import json
import re
from dataclasses import dataclass
import time

from app.services.azure_services import AzureServiceManager
from app.core.config import settings
from app.core.observability import observability
from app.services.credibility_assessor import CredibilityAssessor
from app.utils.chunker import DocumentChunker

logger = logging.getLogger(__name__)

@dataclass
class InsuranceDocumentInfo:
    """Information about an insurance document"""
    document_id: str
    filename: str
    document_type: str  # 'policy' or 'claim'
    company_name: Optional[str]
    policy_number: Optional[str]
    claim_number: Optional[str]
    insured_name: Optional[str]
    coverage_type: Optional[str]
    effective_date: Optional[date]
    expiration_date: Optional[date]
    upload_timestamp: datetime
    file_size: int
    processing_status: str

@dataclass
class InsuranceDocumentChunk:
    """Chunk of insurance document content"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    citation_info: Optional[Dict[str, Any]] = None

class InsuranceDocumentService:
    """
    Service for processing insurance documents using Azure Document Intelligence
    Handles policies and claims with specialized extraction and chunking
    Similar to SEC document processing but specialized for insurance content
    """
    
    def __init__(self, azure_manager: AzureServiceManager):
        self.azure_manager = azure_manager
        self.credibility_assessor = CredibilityAssessor(azure_manager)
        self.chunker = DocumentChunker(
            chunk_size=getattr(settings, 'chunk_size', 1500)
        )
        
        # Insurance-specific field patterns for extraction
        self.policy_field_patterns = {
            'policy_number': [
                r'policy\s*(?:number|#|id|no)[:.]?\s*([A-Z0-9\-]+)',
                r'policy\s*([A-Z0-9\-]+)',
                r'([A-Z]{2,3}\d{6,})',  # Common policy number formats
            ],
            'insured_name': [
                r'insured\s*(?:name|person|party)[:.]?\s*([A-Za-z\s]+)',
                r'policyholder\s*(?:name|person)[:.]?\s*([A-Za-z\s]+)',
                r'name\s*of\s*insured[:.]?\s*([A-Za-z\s]+)',
            ],
            'coverage_type': [
                r'coverage\s*type[:.]?\s*([A-Za-z\s]+)',
                r'type\s*of\s*coverage[:.]?\s*([A-Za-z\s]+)',
                r'(?:auto|home|life|health|dental|umbrella|commercial)\s*insurance',
            ],
            'effective_date': [
                r'effective\s*date[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'policy\s*effective[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'start\s*date[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ],
            'expiration_date': [
                r'expiration\s*date[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'policy\s*expiration[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'end\s*date[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ],
            'coverage_amount': [
                r'coverage\s*amount[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
                r'limit\s*of\s*liability[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
                r'policy\s*limit[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
            ],
            'deductible': [
                r'deductible[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
                r'policy\s*deductible[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
            ]
        }
        
        self.claim_field_patterns = {
            'claim_number': [
                r'claim\s*(?:number|#|id|no)[:.]?\s*([A-Z0-9\-]+)',
                r'claim\s*([A-Z0-9\-]+)',
                r'([A-Z]{2,3}\d{6,})',  # Common claim number formats
            ],
            'policy_number': [
                r'policy\s*(?:number|#|id|no)[:.]?\s*([A-Z0-9\-]+)',
                r'policy\s*([A-Z0-9\-]+)',
            ],
            'insured_name': [
                r'insured\s*(?:name|person|party)[:.]?\s*([A-Za-z\s]+)',
                r'policyholder\s*(?:name|person)[:.]?\s*([A-Za-z\s]+)',
                r'claimant\s*(?:name|person)[:.]?\s*([A-Za-z\s]+)',
            ],
            'claim_amount': [
                r'claim\s*amount[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
                r'loss\s*amount[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
                r'damage\s*amount[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
                r'total\s*claim[:.]?\s*\$?([\d,]+(?:\.\d{2})?)',
            ],
            'date_of_loss': [
                r'date\s*of\s*loss[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'loss\s*date[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'incident\s*date[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ],
            'cause_of_loss': [
                r'cause\s*of\s*loss[:.]?\s*([A-Za-z\s]+)',
                r'loss\s*cause[:.]?\s*([A-Za-z\s]+)',
                r'incident\s*type[:.]?\s*([A-Za-z\s]+)',
            ]
        }

    async def process_insurance_document(
        self, 
        content: bytes, 
        content_type: str, 
        filename: str, 
        document_type: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process insurance document using Azure Document Intelligence
        
        Args:
            content: Raw document bytes
            content_type: MIME type of the document
            filename: Original filename
            document_type: 'policy' or 'claim'
            metadata: Additional metadata
            
        Returns:
            Dict containing processed document information
        """
        try:
            logger.info(f"=== INSURANCE DOCUMENT PROCESSING START ===")
            logger.info(f"Filename: {filename}")
            logger.info(f"Document Type: {document_type}")
            logger.info(f"Content Type: {content_type}")
            logger.info(f"Content Size: {len(content)} bytes")
            
            start_time = time.time()
            observability.track_document_processing_start(filename, content_type)
            
            # Step 1: Extract content using Azure Document Intelligence
            logger.info("Step 1: Extracting content with Azure Document Intelligence...")
            extracted_content = await self._extract_with_document_intelligence(content, content_type, filename)
            logger.info(f"Step 1 COMPLETE: Content length: {len(extracted_content.get('content', ''))}")
            
            # Step 2: Extract insurance-specific fields
            logger.info("Step 2: Extracting insurance-specific fields...")
            insurance_fields = self._extract_insurance_fields(extracted_content, document_type)
            logger.info(f"Step 2 COMPLETE: Extracted {len(insurance_fields)} fields")
            
            # Step 3: Generate document ID
            logger.info("Step 3: Generating document ID...")
            document_id = self._generate_document_id(filename, extracted_content["content"])
            logger.info(f"Step 3 COMPLETE: Document ID: {document_id}")
            
            # Step 4: Create chunks for indexing
            logger.info("Step 4: Creating document chunks...")
            chunks = self._create_insurance_chunks(extracted_content, document_type, document_id, metadata)
            logger.info(f"Step 4 COMPLETE: Created {len(chunks)} chunks")
            
            # Step 5: Assess credibility
            logger.info("Step 5: Assessing document credibility...")
            credibility_score = await self.credibility_assessor.assess_credibility(
                processed_doc={
                    "content": extracted_content["content"],
                    "metadata": extracted_content["metadata"],
                    "insurance_fields": insurance_fields
                },
                source=filename
            )
            logger.info(f"Step 5 COMPLETE: Credibility score: {credibility_score}")
            
            # Step 6: Prepare result
            result = {
                "document_id": document_id,
                "filename": filename,
                "document_type": document_type,
                "insurance_fields": insurance_fields,
                "chunks": chunks,
                "credibility_score": credibility_score,
                "processing_metadata": {
                    "processing_timestamp": datetime.utcnow().isoformat(),
                    "total_chunks": len(chunks),
                    "total_pages": extracted_content["pages"],
                    "extraction_confidence": self._calculate_extraction_confidence(extracted_content),
                    "model_used": "prebuilt-document",
                    "azure_di_used": True
                }
            }
            
            processing_time = time.time() - start_time
            logger.info("=== INSURANCE DOCUMENT PROCESSING COMPLETE ===")
            observability.track_document_processing_complete(filename, len(chunks), processing_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing insurance document {filename}: {e}")
            observability.record_error("insurance_document_processing_error", str(e))
            raise

    async def _extract_with_document_intelligence(
        self, 
        content: bytes, 
        content_type: str, 
        filename: str
    ) -> Dict[str, Any]:
        """Extract content using Azure Document Intelligence (Form Recognizer)"""
        try:
            if not self.azure_manager or not hasattr(self.azure_manager, 'form_recognizer_client'):
                logger.warning("Azure Document Intelligence not configured, using fallback text extraction")
                return self._fallback_text_extraction(content, filename)
            
            # Use prebuilt-document model for insurance documents
            model_id = "prebuilt-document"
            
            logger.info(f"Analyzing document with Azure Document Intelligence model: {model_id}")
            
            poller = self.azure_manager.form_recognizer_client.begin_analyze_document(
                model_id=model_id,
                document=content
            )
            result = poller.result()
            
            extracted_content = {
                "content": result.content,
                "tables": [],
                "key_value_pairs": {},
                "pages": len(result.pages) if result.pages else 0,
                "paragraphs": [],
                "words": [],
                "lines": [],
                "metadata": {
                    "model_used": model_id,
                    "confidence_scores": {},
                    "processing_time": None
                }
            }
            
            # Extract tables
            if result.tables:
                for i, table in enumerate(result.tables):
                    table_data = {
                        "table_id": f"table_{i}",
                        "rows": table.row_count,
                        "columns": table.column_count,
                        "cells": [],
                        "content": ""
                    }
                    
                    for cell in table.cells:
                        cell_data = {
                            "content": cell.content,
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "confidence": getattr(cell, 'confidence', 0.0)
                        }
                        table_data["cells"].append(cell_data)
                        table_data["content"] += f" {cell.content}"
                    
                    extracted_content["tables"].append(table_data)
            
            # Extract key-value pairs
            if result.key_value_pairs:
                for kv_pair in result.key_value_pairs:
                    if kv_pair.key and kv_pair.value:
                        key_content = kv_pair.key.content
                        value_content = kv_pair.value.content
                        
                        extracted_content["key_value_pairs"][key_content] = {
                            "value": value_content,
                            "confidence": getattr(kv_pair, 'confidence', 0.0)
                        }
            
            # Extract paragraphs
            if result.paragraphs:
                for para in result.paragraphs:
                    extracted_content["paragraphs"].append({
                        "content": para.content,
                        "role": getattr(para, 'role', None)
                    })
            
            # Extract words and lines for detailed analysis
            if result.words:
                for word in result.words:
                    extracted_content["words"].append({
                        "content": word.content,
                        "confidence": getattr(word, 'confidence', 0.0),
                        "bounding_box": getattr(word, 'bounding_box', None)
                    })
            
            if result.lines:
                for line in result.lines:
                    extracted_content["lines"].append({
                        "content": line.content,
                        "confidence": getattr(line, 'confidence', 0.0),
                        "bounding_box": getattr(line, 'bounding_box', None)
                    })
            
            logger.info(f"Document Intelligence extraction completed: {extracted_content['pages']} pages, {len(extracted_content['tables'])} tables, {len(extracted_content['key_value_pairs'])} key-value pairs")
            
            return extracted_content
            
        except Exception as e:
            logger.error(f"Document Intelligence extraction failed: {e}")
            observability.record_error("azure_document_intelligence_error", str(e))
            # Fall back to basic text extraction
            logger.info("Falling back to basic text extraction")
            return self._fallback_text_extraction(content, filename)
    
    def _fallback_text_extraction(self, content: bytes, filename: str) -> Dict[str, Any]:
        """Fallback text extraction when Document Intelligence is not available"""
        try:
            import PyPDF2
            import io
            
            # Try to extract text using PyPDF2
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            logger.info(f"Fallback text extraction completed for {filename}: {len(text_content)} characters")
            
            return {
                "content": text_content,
                "tables": [],
                "key_value_pairs": {},
                "pages": len(pdf_reader.pages),
                "paragraphs": [],
                "words": [],
                "lines": [],
                "metadata": {
                    "model_used": "fallback-pypdf2",
                    "confidence_scores": {},
                    "processing_time": None
                }
            }
            
        except Exception as e:
            logger.error(f"Fallback text extraction also failed: {e}")
            # Last resort: return empty content
            return {
                "content": f"Document content could not be extracted from {filename}",
                "tables": [],
                "key_value_pairs": {},
                "pages": 1,
                "paragraphs": [],
                "words": [],
                "lines": [],
                "metadata": {
                    "model_used": "fallback-empty",
                    "confidence_scores": {},
                    "processing_time": None
                }
            }

    def _extract_insurance_fields(
        self, 
        extracted_content: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Extract insurance-specific fields using Document Intelligence results and regex patterns"""
        insurance_fields = {}
        
        # First, try to extract from Document Intelligence key-value pairs
        for key, value_data in extracted_content.get("key_value_pairs", {}).items():
            key_lower = key.lower()
            value = value_data.get("value", "")
            
            # Map common Document Intelligence keys to insurance fields
            if "policy" in key_lower and "number" in key_lower:
                insurance_fields["policy_number"] = value
            elif "claim" in key_lower and "number" in key_lower:
                insurance_fields["claim_number"] = value
            elif "insured" in key_lower or "policyholder" in key_lower:
                insurance_fields["insured_name"] = value
            elif "coverage" in key_lower and "type" in key_lower:
                insurance_fields["coverage_type"] = value
            elif "effective" in key_lower and "date" in key_lower:
                insurance_fields["effective_date"] = self._parse_date(value)
            elif "expiration" in key_lower and "date" in key_lower:
                insurance_fields["expiration_date"] = self._parse_date(value)
            elif "deductible" in key_lower:
                insurance_fields["deductible"] = self._parse_currency(value)
            elif "coverage" in key_lower and "amount" in key_lower:
                insurance_fields["coverage_amount"] = self._parse_currency(value)
            elif "claim" in key_lower and "amount" in key_lower:
                insurance_fields["claim_amount"] = self._parse_currency(value)
            elif "date" in key_lower and "loss" in key_lower:
                insurance_fields["date_of_loss"] = self._parse_date(value)
            elif "cause" in key_lower and "loss" in key_lower:
                insurance_fields["cause_of_loss"] = value
        
        # Fallback to regex patterns if Document Intelligence didn't extract enough
        patterns = self.policy_field_patterns if document_type == "policy" else self.claim_field_patterns
        content = extracted_content.get("content", "")
        
        for field_name, field_patterns in patterns.items():
            if field_name not in insurance_fields:  # Only use regex if DI didn't find it
                for pattern in field_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if field_name in ["effective_date", "expiration_date", "date_of_loss"]:
                            insurance_fields[field_name] = self._parse_date(value)
                        elif field_name in ["deductible", "coverage_amount", "claim_amount"]:
                            insurance_fields[field_name] = self._parse_currency(value)
                        else:
                            insurance_fields[field_name] = value
                        break
        
        # Extract company name if not found
        if "company_name" not in insurance_fields:
            company_name = self._extract_company_name(content)
            if company_name:
                insurance_fields["company_name"] = company_name
        
        return insurance_fields

    def _create_insurance_chunks(
        self, 
        extracted_content: Dict[str, Any], 
        document_type: str, 
        document_id: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Create chunks from the extracted content using the DocumentChunker"""
        try:
            content = extracted_content.get("content", "")
            if not content:
                logger.warning("No content to chunk")
                return []
            
            # Use the DocumentChunker to create chunks
            chunks = self.chunker.chunk(
                content=content,
                metadata={
                    "document_id": document_id,
                    "document_type": document_type,
                    "source": "azure_document_intelligence",
                    "chunking_method": "intelligent",
                    "total_pages": extracted_content.get("pages", 0),
                    "tables_found": len(extracted_content.get("tables", [])),
                    "key_value_pairs_found": len(extracted_content.get("key_value_pairs", {})),
                    **(metadata or {})
                }
            )
            
            # Enrich chunks with insurance-specific metadata
            for i, chunk in enumerate(chunks):
                chunk["chunk_id"] = f"{document_type}_{document_id}_chunk_{i}"
                chunk["metadata"]["chunk_index"] = i
                chunk["metadata"]["chunk_type"] = "insurance_document"
                
                # Add table context if chunk contains table data
                for table in extracted_content.get("tables", []):
                    if table["content"] in chunk["content"]:
                        chunk["metadata"]["table_context"] = {
                            "table_id": table["table_id"],
                            "rows": table["rows"],
                            "columns": table["columns"]
                        }
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error creating insurance chunks: {e}")
            observability.record_error("insurance_chunking_error", str(e))
            return []

    def _generate_document_id(self, filename: str, content: str) -> str:
        """Generate a unique document ID based on filename and content hash"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        filename_clean = re.sub(r'[^a-zA-Z0-9]', '_', filename)
        timestamp = str(int(datetime.utcnow().timestamp()))[-6:]
        return f"{filename_clean}_{content_hash}_{timestamp}"

    def _calculate_extraction_confidence(self, extracted_content: Dict[str, Any]) -> float:
        """Calculate overall confidence score based on Document Intelligence results"""
        confidence_scores = []
        
        # Check key-value pair confidence
        for value_data in extracted_content.get("key_value_pairs", {}).values():
            if "confidence" in value_data:
                confidence_scores.append(value_data["confidence"])
        
        # Check word confidence
        for word in extracted_content.get("words", []):
            if "confidence" in word:
                confidence_scores.append(word["confidence"])
        
        # Check line confidence
        for line in extracted_content.get("lines", []):
            if "confidence" in line:
                confidence_scores.append(line["confidence"])
        
        if not confidence_scores:
            return 0.0
        
        return sum(confidence_scores) / len(confidence_scores)

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        # Common date patterns - try MM/DD/YYYY or MM-DD-YYYY first
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # MM/DD/YYYY or MM-DD-YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                if len(match.group(3)) == 2:  # 2-digit year
                    year = int(match.group(3))
                    if year < 50:
                        year += 2000
                    else:
                        year += 1900
                else:
                    year = int(match.group(3))
                
                # For MM/DD/YYYY pattern, month is group 1, day is group 2
                if len(match.group(1)) <= 2:  # First group is month
                    month = int(match.group(1))
                    day = int(match.group(2))
                else:  # First group is year (YYYY-MM-DD pattern)
                    month = int(match.group(2))
                    day = int(match.group(3))
                
                try:
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except ValueError:
                    continue
        
        return date_str  # Return original if parsing fails

    def _parse_currency(self, currency_str: str) -> Optional[float]:
        """Parse currency string to float"""
        if not currency_str:
            return None
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,€£¥]', '', currency_str)
        
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _extract_company_name(self, content: str) -> Optional[str]:
        """Extract company name from document content"""
        # Look for common company indicators with better patterns
        company_patterns = [
            r'([A-Za-z\s&]+?)\s+(?:insurance|assurance|group|inc|corp|llc|ltd)\.?',
            r'(?:insurance|assurance|group|inc|corp|llc|ltd)\.?\s+([A-Za-z\s&]+?)(?:\s|$)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:insurance|assurance|group|inc|corp|llc|ltd)',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                company_name = match.group(1).strip()
                if len(company_name) > 3:  # Filter out very short matches
                    return company_name
        
        return None

    # Placeholder methods for future Azure Search integration
    async def get_insurance_documents(self, document_type: str = None, limit: int = 100) -> List[InsuranceDocumentInfo]:
        """Get insurance documents from Azure Search index"""
        # TODO: Implement Azure Search integration
        return []
    
    async def get_document_by_id(self, document_id: str) -> Optional[InsuranceDocumentInfo]:
        """Get specific insurance document by ID"""
        # TODO: Implement Azure Search integration
        return None
    
    async def get_insurance_document_stats(self) -> Dict[str, Any]:
        """Get statistics about insurance documents"""
        # TODO: Implement Azure Search integration
        return {}
    
    async def search_insurance_documents(self, query: str, document_type: str = None) -> List[InsuranceDocumentInfo]:
        """Search insurance documents"""
        # TODO: Implement Azure Search integration
        return []
    
    async def delete_insurance_document(self, document_id: str) -> bool:
        """Delete insurance document"""
        # TODO: Implement Azure Search integration
        return False
