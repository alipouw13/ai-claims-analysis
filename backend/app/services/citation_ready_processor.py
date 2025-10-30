"""
Enhanced Citation-Ready Document Processing

This module provides enhanced document processing for policies and claims
that creates citation-ready search documents similar to SEC document processing.
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.services.document_processor import DocumentChunk

logger = logging.getLogger(__name__)

class CitationReadyDocumentProcessor:
    """
    Enhanced document processor that creates citation-ready search documents
    for policies and claims, matching the citation capabilities of SEC documents.
    """
    
    def __init__(self, azure_manager):
        self.azure_manager = azure_manager
    
    async def prepare_citation_ready_search_documents(
        self, 
        chunks: List[DocumentChunk], 
        document_id: str,
        source: str,
        metadata: Dict[str, Any],
        document_type: str = "policy"
    ) -> List[Dict[str, Any]]:
        """
        Prepare policy/claims chunks for search indexing with enhanced citation metadata.
        
        Args:
            chunks: List of document chunks
            document_id: Unique document identifier
            source: Source filename or identifier
            metadata: Document metadata
            document_type: Type of document (policy, claim, faq, etc.)
            
        Returns:
            List of search documents with citation-ready metadata
        """
        logger.info(f"Preparing {len(chunks)} chunks for citation-ready search indexing")
        
        search_documents = []
        
        # Extract base metadata for citations
        base_citation_info = self._extract_base_citation_info(metadata, source, document_type)
        
        for chunk in chunks:
            if chunk.embedding is None:
                logger.warning(f"Skipping chunk {chunk.chunk_id} - no embedding")
                continue
            
            # Enhanced metadata extraction
            chunk_metadata = chunk.metadata
            enhanced_metadata = self._enhance_chunk_metadata(chunk_metadata, base_citation_info, chunk)
            
            # Calculate confidence score for the chunk
            confidence_score = self._calculate_citation_confidence(chunk, enhanced_metadata)
            
            # Create citation-ready search document
            search_doc = {
                # Standard fields
                "id": f"{document_id}_{chunk.chunk_id}",
                "content": chunk.content,
                "title": self._generate_chunk_title(enhanced_metadata, chunk),
                "document_id": document_id,
                "parent_id": document_id,
                "source": source,
                "content_vector": chunk.embedding,
                
                # Document type and classification
                "document_type": document_type,
                "section_type": enhanced_metadata.get('section_type', 'general'),
                "content_type": enhanced_metadata.get('content_type', 'text'),
                
                # Citation-specific fields
                "citation_info": json.dumps({
                    "document_id": document_id,
                    "source_file": source,
                    "document_type": document_type,
                    "section_name": enhanced_metadata.get('section_name', 'unknown'),
                    "chunk_index": enhanced_metadata.get('chunk_index', 0),
                    "page_number": enhanced_metadata.get('page_number', 0),
                    "policy_number": enhanced_metadata.get('policy_number'),
                    "claim_number": enhanced_metadata.get('claim_number'),
                    "effective_date": enhanced_metadata.get('effective_date'),
                    "processed_at": datetime.now().isoformat(),
                    "confidence_score": confidence_score
                }),
                
                # Insurance-specific fields for filtering and search
                "policy_number": enhanced_metadata.get('policy_number', ''),
                "claim_number": enhanced_metadata.get('claim_number', ''),
                "coverage_type": enhanced_metadata.get('coverage_type', ''),
                "insurance_company": enhanced_metadata.get('insurance_company', ''),
                "effective_date": enhanced_metadata.get('effective_date', ''),
                "expiration_date": enhanced_metadata.get('expiration_date', ''),
                
                # Content analysis fields
                "chunk_id": chunk.chunk_id,
                "chunk_index": enhanced_metadata.get('chunk_index', 0),
                "chunk_method": enhanced_metadata.get('chunk_method', 'unknown'),
                "confidence_score": confidence_score,
                "word_count": len(chunk.content.split()),
                "char_count": len(chunk.content),
                
                # Financial information
                "contains_amounts": self._contains_financial_amounts(chunk.content),
                "contains_dates": self._contains_dates(chunk.content),
                "contains_coverage": self._contains_coverage_info(chunk.content),
                
                # Processing metadata
                "processed_at": datetime.now().isoformat(),
                "processing_method": "enhanced_citation_ready",
                "smart_processing": enhanced_metadata.get('smart_processing', False),
                
                # Quality metrics
                "quality_score": enhanced_metadata.get('quality_score', 0.0),
                "optimal_size": enhanced_metadata.get('optimal_size', False),
                "keywords": enhanced_metadata.get('keywords', [])
            }
            
            search_documents.append(search_doc)
        
        logger.info(f"Created {len(search_documents)} citation-ready search documents")
        return search_documents
    
    def _extract_base_citation_info(self, metadata: Dict[str, Any], source: str, document_type: str) -> Dict[str, Any]:
        """Extract base citation information from document metadata."""
        citation_info = {
            'source_file': source,
            'document_type': document_type,
            'processed_at': datetime.now().isoformat()
        }
        
        # Extract insurance-specific information
        if 'structured_data' in metadata:
            structured = metadata['structured_data']
            
            # Key-value pairs from Form Recognizer
            if 'key_value_pairs' in structured:
                kvp = structured['key_value_pairs']
                citation_info.update({
                    'policy_number': kvp.get('policy_number'),
                    'claim_number': kvp.get('claim_number'),
                    'coverage_type': kvp.get('coverage_type'),
                    'effective_date': kvp.get('effective_date'),
                    'expiration_date': kvp.get('expiration_date'),
                    'insurance_company': kvp.get('insurance_company'),
                    'policyholder': kvp.get('policyholder'),
                    'insured': kvp.get('insured')
                })
            
            # Document type from detection
            if 'document_type' in structured:
                citation_info['detected_document_type'] = structured['document_type']
        
        # Extract from general metadata
        citation_info.update({
            'is_policy': metadata.get('is_policy', False),
            'is_claim': metadata.get('is_claim', False),
            'tags': metadata.get('tags', [])
        })
        
        return citation_info
    
    def _enhance_chunk_metadata(
        self, 
        chunk_metadata: Dict[str, Any], 
        base_citation_info: Dict[str, Any], 
        chunk: DocumentChunk
    ) -> Dict[str, Any]:
        """Enhance chunk metadata with citation-ready information."""
        enhanced = {**chunk_metadata, **base_citation_info}
        
        # Extract section information
        if 'section_name' not in enhanced:
            enhanced['section_name'] = self._extract_section_from_content(chunk.content)
        
        # Determine content type
        enhanced['content_type'] = self._determine_content_type(chunk.content)
        
        # Extract page number if available
        if 'page_number' not in enhanced:
            enhanced['page_number'] = self._extract_page_number(chunk.content)
        
        return enhanced
    
    def _extract_section_from_content(self, content: str) -> str:
        """Extract section name from chunk content."""
        # Look for section headers in the content
        lines = content.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if line and (line.isupper() or line.istitle()) and len(line) < 100:
                # Remove common prefixes/suffixes
                section = line.replace('SECTION', '').replace('Section', '').strip()
                if section:
                    return section.lower().replace(' ', '_')
        
        return 'content_section'
    
    def _determine_content_type(self, content: str) -> str:
        """Determine the type of content in the chunk."""
        content_lower = content.lower()
        
        if 'coverage' in content_lower and ('limit' in content_lower or 'amount' in content_lower):
            return 'coverage_details'
        elif 'exclusion' in content_lower or 'not covered' in content_lower:
            return 'exclusions'
        elif 'deductible' in content_lower:
            return 'deductible_info'
        elif 'claim' in content_lower and ('loss' in content_lower or 'incident' in content_lower):
            return 'claim_details'
        elif 'premium' in content_lower or 'payment' in content_lower:
            return 'payment_info'
        elif 'condition' in content_lower or 'requirement' in content_lower:
            return 'policy_conditions'
        elif '?' in content and 'answer' in content_lower:
            return 'faq_content'
        else:
            return 'general_content'
    
    def _extract_page_number(self, content: str) -> int:
        """Extract page number from content if available."""
        import re
        
        # Look for page number patterns
        patterns = [
            r'page\s+(\d+)',
            r'p\.\s*(\d+)',
            r'pg\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content.lower())
            if match:
                return int(match.group(1))
        
        return 0
    
    def _calculate_citation_confidence(self, chunk: DocumentChunk, metadata: Dict[str, Any]) -> float:
        """Calculate confidence score for citation accuracy."""
        confidence = 0.5  # Base confidence
        
        # Content quality factors
        content_len = len(chunk.content)
        if 200 <= content_len <= 1500:
            confidence += 0.2
        elif content_len >= 100:
            confidence += 0.1
        
        # Metadata completeness
        if metadata.get('section_name') and metadata['section_name'] != 'unknown':
            confidence += 0.1
        
        if metadata.get('policy_number') or metadata.get('claim_number'):
            confidence += 0.1
        
        # Processing method quality
        if metadata.get('smart_processing'):
            confidence += 0.1
        
        if metadata.get('chunk_method') == 'balanced_chunking':
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_chunk_title(self, metadata: Dict[str, Any], chunk: DocumentChunk) -> str:
        """Generate a descriptive title for the chunk."""
        base_title = metadata.get('source_file', 'Insurance Document')
        
        # Remove file extension
        if '.' in base_title:
            base_title = base_title.rsplit('.', 1)[0]
        
        # Add section information
        section = metadata.get('section_name', '').replace('_', ' ').title()
        if section and section != 'Unknown':
            return f"{base_title} - {section}"
        
        # Add document type information
        content_type = metadata.get('content_type', '').replace('_', ' ').title()
        if content_type and content_type != 'General Content':
            return f"{base_title} - {content_type}"
        
        # Add chunk index as fallback
        chunk_index = metadata.get('chunk_index', 0)
        return f"{base_title} - Part {chunk_index + 1}"
    
    def _contains_financial_amounts(self, content: str) -> bool:
        """Check if content contains financial amounts."""
        import re
        return bool(re.search(r'\$[\d,]+', content))
    
    def _contains_dates(self, content: str) -> bool:
        """Check if content contains date information."""
        import re
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in date_patterns)
    
    def _contains_coverage_info(self, content: str) -> bool:
        """Check if content contains coverage information."""
        coverage_terms = [
            'coverage', 'covered', 'protection', 'benefit', 'limit', 
            'deductible', 'premium', 'policy', 'insured'
        ]
        content_lower = content.lower()
        return any(term in content_lower for term in coverage_terms)