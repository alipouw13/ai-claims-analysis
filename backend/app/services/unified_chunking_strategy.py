"""
Unified Chunking Strategy

This module provides a unified chunking approach for policies, claims, and SEC documents
to ensure consistent citation and retrieval capabilities across all document types.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.utils.chunker import DocumentChunker
from app.utils.balanced_chunker import BalancedChunker
from app.services.document_processor import DocumentChunk
from app.core.config import settings

logger = logging.getLogger(__name__)

class UnifiedDocumentChunker:
    """
    Unified chunking strategy that provides consistent chunking across
    SEC documents, policies, and claims for optimal Q&A retrieval and citations.
    """
    
    def __init__(self):
        # Initialize MD2Chunks-style chunker (same as SEC documents)
        self.md2_chunker = DocumentChunker(
            chunk_size=getattr(settings, 'chunk_size', 1500),
        )
        
        # Initialize balanced chunker for enhanced policy/claims processing
        self.balanced_chunker = BalancedChunker(
            target_chunk_size=900,  # Optimized for RAG
            max_chunk_size=1400,
            min_chunk_size=250,
            overlap_ratio=0.12
        )
    
    async def chunk_document(
        self, 
        text: str, 
        document_type: str, 
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Unified chunking that adapts strategy based on document type while
        maintaining consistency for citation and retrieval.
        
        Args:
            text: Document text to chunk
            document_type: Type of document (sec, policy, claim, faq)
            source: Source filename or identifier
            metadata: Additional metadata
            
        Returns:
            List of chunk dictionaries with unified metadata structure
        """
        logger.info(f"Unified chunking for {document_type} document: {len(text)} chars")
        
        if not text or len(text.strip()) < 50:
            logger.warning("Text too short for chunking")
            return []
        
        chunks = []
        
        try:
            if document_type == "sec":
                # Use MD2Chunks approach for SEC documents (maintain existing behavior)
                chunks = await self._chunk_sec_document(text, metadata)
            else:
                # Use enhanced approach for policies, claims, and FAQs
                chunks = await self._chunk_insurance_document(text, document_type, metadata)
            
            # Apply unified metadata enhancement to all chunks
            enhanced_chunks = self._apply_unified_metadata(chunks, document_type, source, metadata)
            
            logger.info(f"Unified chunking complete: {len(enhanced_chunks)} chunks")
            return enhanced_chunks
            
        except Exception as e:
            logger.error(f"Error in unified chunking: {e}")
            # Fallback to basic chunking
            return self._fallback_chunking(text, document_type, source, metadata)
    
    async def _chunk_sec_document(self, text: str, metadata: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunk SEC documents using MD2Chunks approach."""
        logger.info("Using MD2Chunks approach for SEC document")
        
        # Clean content for markdown processing
        cleaned_text = self._clean_sec_content(text)
        
        # Use md2chunks chunker
        chunk_data = self.md2_chunker.chunk(
            cleaned_text,
            chunk_size=getattr(settings, 'chunk_size', 1500),
            overlap=getattr(settings, 'chunk_overlap', 200),
            metadata=metadata or {}
        )
        
        return chunk_data
    
    async def _chunk_insurance_document(
        self, 
        text: str, 
        document_type: str, 
        metadata: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Chunk insurance documents using enhanced balanced approach."""
        logger.info(f"Using enhanced balanced approach for {document_type} document")
        
        # Use balanced chunker for optimal RAG performance
        chunks = self.balanced_chunker.chunk_document(text, document_type)
        
        # Convert to unified format
        chunk_data = []
        for i, chunk in enumerate(chunks):
            chunk_dict = {
                "content": chunk["content"],
                "metadata": {
                    **chunk.get("metadata", {}),
                    "chunk_index": i,
                    "token_count": len(chunk["content"]) // 4,  # Rough token estimate
                    "chunking_method": f"balanced_{document_type}_chunking",
                    "document_type": document_type
                }
            }
            chunk_data.append(chunk_dict)
        
        return chunk_data
    
    def _apply_unified_metadata(
        self, 
        chunks: List[Dict[str, Any]], 
        document_type: str, 
        source: str,
        metadata: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply unified metadata structure to all chunks for consistent citation."""
        enhanced_chunks = []
        
        for i, chunk_data in enumerate(chunks):
            content = chunk_data["content"]
            chunk_metadata = chunk_data.get("metadata", {})
            
            # Create unified metadata structure
            unified_metadata = {
                # Core chunking metadata
                "chunk_index": i,
                "chunk_id": f"{document_type}_chunk_{i+1:03d}",
                "token_count": chunk_metadata.get("token_count", len(content) // 4),
                "char_count": len(content),
                "word_count": len(content.split()),
                
                # Document identification
                "document_type": document_type,
                "source": source,
                "processed_at": datetime.now().isoformat(),
                
                # Chunking method information
                "chunking_method": chunk_metadata.get("chunking_method", "unified_chunking"),
                "chunk_quality": self._assess_chunk_quality(content, document_type),
                
                # Content analysis
                "section_type": chunk_metadata.get("section_type", self._detect_section_type(content, document_type)),
                "content_type": self._categorize_content(content, document_type),
                
                # Citation-ready fields
                "contains_financial_data": self._contains_financial_data(content),
                "contains_dates": self._contains_dates(content),
                "contains_key_terms": self._extract_key_terms(content, document_type),
                
                # Preserve original metadata
                **chunk_metadata
            }
            
            # Add document-specific metadata
            if metadata:
                unified_metadata.update(self._extract_document_specific_metadata(metadata, document_type))
            
            enhanced_chunk = {
                "content": content,
                "metadata": unified_metadata
            }
            
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def _clean_sec_content(self, text: str) -> str:
        """Clean SEC content for better chunking."""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove page numbers and headers/footers
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'\f', '\n\n', text)  # Form feeds to double newlines
        
        return text.strip()
    
    def _detect_section_type(self, content: str, document_type: str) -> str:
        """Detect the type of section based on content and document type."""
        content_lower = content.lower()
        
        if document_type == "sec":
            # SEC-specific section detection
            if "item 1" in content_lower or "business" in content_lower:
                return "business_overview"
            elif "item 2" in content_lower or "risk factors" in content_lower:
                return "risk_factors"
            elif "item 7" in content_lower or "management" in content_lower:
                return "management_discussion"
            elif "financial statements" in content_lower:
                return "financial_statements"
            else:
                return "general_sec"
        
        elif document_type in ["policy", "claim", "faq"]:
            # Insurance-specific section detection
            if "coverage" in content_lower:
                return "coverage_details"
            elif "exclusion" in content_lower:
                return "exclusions"
            elif "deductible" in content_lower:
                return "deductible_info"
            elif "claim" in content_lower and "loss" in content_lower:
                return "claim_details"
            elif "premium" in content_lower:
                return "premium_info"
            elif "?" in content and "answer" in content_lower:
                return "faq_item"
            else:
                return f"general_{document_type}"
        
        return "general"
    
    def _categorize_content(self, content: str, document_type: str) -> str:
        """Categorize content for better retrieval."""
        content_lower = content.lower()
        
        # Financial content
        if any(term in content_lower for term in ["$", "amount", "cost", "price", "premium"]):
            return "financial_content"
        
        # Regulatory/legal content
        if any(term in content_lower for term in ["regulation", "compliance", "legal", "law"]):
            return "regulatory_content"
        
        # Procedural content
        if any(term in content_lower for term in ["process", "procedure", "step", "how to"]):
            return "procedural_content"
        
        # Definition content
        if any(term in content_lower for term in ["definition", "means", "defined as"]):
            return "definition_content"
        
        return "general_content"
    
    def _assess_chunk_quality(self, content: str, document_type: str) -> float:
        """Assess the quality of a chunk for retrieval purposes."""
        quality = 0.5  # Base quality
        
        # Length quality
        content_len = len(content)
        if 200 <= content_len <= 1500:
            quality += 0.2
        elif content_len >= 100:
            quality += 0.1
        
        # Structure quality
        sentences = content.count('.') + content.count('!') + content.count('?')
        if sentences >= 2:
            quality += 0.1
        
        # Content richness
        if self._contains_financial_data(content):
            quality += 0.1
        
        if self._contains_dates(content):
            quality += 0.1
        
        return min(1.0, quality)
    
    def _contains_financial_data(self, content: str) -> bool:
        """Check if content contains financial data."""
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
    
    def _extract_key_terms(self, content: str, document_type: str) -> List[str]:
        """Extract key terms based on document type."""
        content_lower = content.lower()
        key_terms = []
        
        if document_type == "sec":
            sec_terms = ["revenue", "earnings", "profit", "loss", "assets", "liabilities", "cash flow"]
            key_terms.extend([term for term in sec_terms if term in content_lower])
        
        elif document_type in ["policy", "claim", "faq"]:
            insurance_terms = ["coverage", "deductible", "premium", "claim", "policy", "liability"]
            key_terms.extend([term for term in insurance_terms if term in content_lower])
        
        return key_terms[:5]  # Limit to top 5 terms
    
    def _extract_document_specific_metadata(self, metadata: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """Extract document-specific metadata for citations."""
        specific_metadata = {}
        
        if document_type == "sec":
            # SEC-specific metadata
            specific_metadata.update({
                "ticker": metadata.get("ticker"),
                "company_name": metadata.get("company_name"),
                "form_type": metadata.get("form_type"),
                "filing_date": metadata.get("filing_date"),
                "accession_number": metadata.get("accession_number")
            })
        
        elif document_type in ["policy", "claim", "faq"]:
            # Insurance-specific metadata
            if "structured_data" in metadata:
                kvp = metadata["structured_data"].get("key_value_pairs", {})
                specific_metadata.update({
                    "policy_number": kvp.get("policy_number"),
                    "claim_number": kvp.get("claim_number"),
                    "coverage_type": kvp.get("coverage_type"),
                    "effective_date": kvp.get("effective_date"),
                    "insurance_company": kvp.get("insurance_company")
                })
        
        # Remove None values
        return {k: v for k, v in specific_metadata.items() if v is not None}
    
    def _fallback_chunking(
        self, 
        text: str, 
        document_type: str, 
        source: str, 
        metadata: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fallback chunking when all other methods fail."""
        logger.warning("Using fallback chunking")
        
        # Simple paragraph-based chunking
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            para_size = len(paragraph)
            
            if current_size + para_size > 1000 and current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "chunk_index": len(chunks),
                        "chunk_id": f"fallback_chunk_{len(chunks)+1:03d}",
                        "chunking_method": "fallback_paragraph",
                        "document_type": document_type,
                        "source": source,
                        "char_count": len(chunk_content),
                        "processed_at": datetime.now().isoformat()
                    }
                })
                current_chunk = [paragraph]
                current_size = para_size
            else:
                current_chunk.append(paragraph)
                current_size += para_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "metadata": {
                    "chunk_index": len(chunks),
                    "chunk_id": f"fallback_chunk_{len(chunks)+1:03d}",
                    "chunking_method": "fallback_paragraph",
                    "document_type": document_type,
                    "source": source,
                    "char_count": len(chunk_content),
                    "processed_at": datetime.now().isoformat()
                }
            })
        
        return chunks