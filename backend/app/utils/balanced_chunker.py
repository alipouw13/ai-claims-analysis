"""
Balanced Document Chunking Strategy

This module provides intelligent chunking that balances semantic meaning
with optimal chunk sizes for RAG retrieval.
"""
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class BalancedChunker:
    """
    Intelligent document chunker that creates balanced chunks optimized for RAG.
    """
    
    def __init__(self, 
                 target_chunk_size: int = 800,
                 max_chunk_size: int = 1200,
                 min_chunk_size: int = 200,
                 overlap_ratio: float = 0.15):
        """
        Initialize balanced chunker.
        
        Args:
            target_chunk_size: Ideal chunk size in characters
            max_chunk_size: Maximum allowed chunk size
            min_chunk_size: Minimum chunk size to avoid tiny chunks
            overlap_ratio: Overlap between chunks as ratio of target size
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = int(target_chunk_size * overlap_ratio)
        
    def chunk_document(self, text: str, document_type: str = "unknown") -> List[Dict[str, Any]]:
        """
        Create balanced chunks from document text.
        
        Args:
            text: Document text to chunk
            document_type: Type of document (policy, claim, faq, etc.)
            
        Returns:
            List of chunk dictionaries with metadata
        """
        logger.info(f"Creating balanced chunks for {len(text)} chars, type: {document_type}")
        
        if not text or len(text.strip()) < self.min_chunk_size:
            logger.warning("Text too short for chunking")
            return []
        
        chunks = []
        
        # Step 1: Try semantic sections first
        section_chunks = self._chunk_by_semantic_sections(text, document_type)
        
        if section_chunks:
            # Step 2: Balance section chunks
            balanced_chunks = self._balance_chunk_sizes(section_chunks)
            chunks.extend(balanced_chunks)
        else:
            # Step 3: Fallback to sliding window
            window_chunks = self._chunk_by_sliding_window(text)
            chunks.extend(window_chunks)
        
        # Step 4: Add metadata and finalize
        final_chunks = []
        for i, chunk in enumerate(chunks):
            enhanced_chunk = self._enhance_chunk_metadata(chunk, i, document_type)
            final_chunks.append(enhanced_chunk)
        
        logger.info(f"Created {len(final_chunks)} balanced chunks")
        return final_chunks
    
    def _chunk_by_semantic_sections(self, text: str, document_type: str) -> List[Dict[str, Any]]:
        """Create chunks based on document structure and semantic sections."""
        sections = self._identify_document_sections(text, document_type)
        
        if not sections or len(sections) < 2:
            return []
        
        chunks = []
        
        for section_name, section_content in sections.items():
            if len(section_content.strip()) < self.min_chunk_size:
                continue
            
            # If section is small enough, use as single chunk
            if len(section_content) <= self.max_chunk_size:
                chunks.append({
                    "content": section_content.strip(),
                    "metadata": {
                        "section_name": section_name,
                        "chunk_type": "semantic_section",
                        "char_count": len(section_content.strip())
                    }
                })
            else:
                # Split large sections into sub-chunks
                sub_chunks = self._split_large_section(section_content, section_name)
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _identify_document_sections(self, text: str, document_type: str) -> Dict[str, str]:
        """Identify semantic sections based on document type."""
        sections = {}
        
        if document_type == "policy":
            sections = self._identify_policy_sections(text)
        elif document_type == "claim":
            sections = self._identify_claim_sections(text)
        else:
            sections = self._identify_generic_sections(text)
        
        return sections
    
    def _identify_policy_sections(self, text: str) -> Dict[str, str]:
        """Identify sections in insurance policy documents."""
        patterns = [
            (r"(?:COVERAGE|INSURING AGREEMENT).*", "coverage"),
            (r"(?:EXCLUSIONS?|WHAT (?:WE|IS) (?:DON'T|NOT) COVER).*", "exclusions"),
            (r"(?:CONDITIONS?|POLICY CONDITIONS?).*", "conditions"),
            (r"(?:DEDUCTIBLES?|YOUR DEDUCTIBLE).*", "deductible"),
            (r"(?:DEFINITIONS?|DEFINED TERMS?).*", "definitions"),
            (r"(?:LIMITS?|COVERAGE LIMITS?).*", "limits"),
            (r"(?:PREMIUM|COST|PAYMENT).*", "premium"),
            # Add more flexible patterns for common policy sections
            (r"^[A-Z\s]{10,}$", "header"),  # All caps headers
            (r"^\d+\.\s*[A-Z].*", "numbered_section"),  # Numbered sections
        ]
        
        return self._extract_sections_by_patterns(text, patterns)
    
    def _identify_claim_sections(self, text: str) -> Dict[str, str]:
        """Identify sections in insurance claim documents."""
        patterns = [
            (r"(?:CLAIM (?:INFORMATION|DETAILS?)|CLAIM SUMMARY)[\s:]*", "claim_info"),
            (r"(?:LOSS (?:DESCRIPTION|DETAILS?)|INCIDENT DESCRIPTION)[\s:]*", "loss_description"),
            (r"(?:ADJUSTER (?:NOTES?|COMMENTS?)|INVESTIGATION)[\s:]*", "adjuster_notes"),
            (r"(?:SETTLEMENT|PAYMENT|PAYOUT)[\s:]*", "settlement"),
            (r"(?:DAMAGE\s+ASSESSMENT|PROPERTY\s+DAMAGE)[\s:]*", "damage_assessment"),
        ]
        
        return self._extract_sections_by_patterns(text, patterns)
    
    def _identify_generic_sections(self, text: str) -> Dict[str, str]:
        """Identify sections in generic documents."""
        patterns = [
            (r"^([A-Z][A-Z\s]{5,})\s*$", "header"),  # All caps headers
            (r"^\d+\.\s*([A-Z][A-Za-z\s,&]+)$", "numbered_section"),  # Numbered sections
            (r"^([A-Z][A-Za-z\s,&]{5,}):?\s*$", "title_section"),  # Title case headers
        ]
        
        return self._extract_sections_by_patterns(text, patterns)
    
    def _extract_sections_by_patterns(self, text: str, patterns: List[Tuple[str, str]]) -> Dict[str, str]:
        """Extract sections using regex patterns."""
        sections = {}
        lines = text.split('\n')
        current_section = "introduction"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line matches any section pattern
            section_found = False
            for pattern, section_type in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match and len(line) < 150:  # Reasonable header length
                    # Save previous section
                    if current_content:
                        sections[current_section] = '\n'.join(current_content)
                    
                    # Start new section
                    current_section = f"{section_type}_{len(sections) + 1}"
                    current_content = []
                    section_found = True
                    break
            
            if not section_found:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _split_large_section(self, section_content: str, section_name: str) -> List[Dict[str, Any]]:
        """Split large sections into balanced sub-chunks."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in section_content.split('\n\n') if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in section_content.split('\n') if p.strip()]
        
        current_chunk = []
        current_size = 0
        sub_chunk_index = 1
        
        for paragraph in paragraphs:
            para_size = len(paragraph)
            
            # If adding this paragraph exceeds target, finalize current chunk
            if current_size + para_size > self.target_chunk_size and current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "section_name": f"{section_name}_part_{sub_chunk_index}",
                        "chunk_type": "section_subsection",
                        "char_count": len(chunk_content),
                        "paragraph_count": len(current_chunk)
                    }
                })
                
                # Start new chunk with overlap
                overlap_content = current_chunk[-1] if current_chunk else ""
                current_chunk = [overlap_content, paragraph] if overlap_content else [paragraph]
                current_size = len(overlap_content) + para_size
                sub_chunk_index += 1
            else:
                current_chunk.append(paragraph)
                current_size += para_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "metadata": {
                    "section_name": f"{section_name}_part_{sub_chunk_index}",
                    "chunk_type": "section_subsection",
                    "char_count": len(chunk_content),
                    "paragraph_count": len(current_chunk)
                }
            })
        
        return chunks
    
    def _chunk_by_sliding_window(self, text: str) -> List[Dict[str, Any]]:
        """Create chunks using sliding window approach."""
        chunks = []
        
        # Split into sentences for better boundaries
        sentences = self._split_into_sentences(text)
        
        current_chunk = []
        current_size = 0
        chunk_index = 1
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # If adding sentence exceeds target, finalize chunk
            if current_size + sentence_size > self.target_chunk_size and current_chunk:
                chunk_content = ' '.join(current_chunk)
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        "section_name": f"sliding_window_{chunk_index}",
                        "chunk_type": "sliding_window",
                        "char_count": len(chunk_content),
                        "sentence_count": len(current_chunk)
                    }
                })
                
                # Create overlap
                overlap_sentences = self._create_sentence_overlap(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_size = sum(len(s) for s in current_chunk)
                chunk_index += 1
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "metadata": {
                    "section_name": f"sliding_window_{chunk_index}",
                    "chunk_type": "sliding_window",
                    "char_count": len(chunk_content),
                    "sentence_count": len(current_chunk)
                }
            })
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences with improved accuracy."""
        # Simple sentence splitting with common abbreviations handling
        sentence_ends = r'(?<![A-Z][a-z]\.)\s*[.!?]+\s+'
        sentences = re.split(sentence_ends, text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Avoid very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _create_sentence_overlap(self, sentences: List[str]) -> List[str]:
        """Create overlap from the end of current chunk."""
        if not sentences:
            return []
        
        overlap_chars = 0
        overlap_sentences = []
        
        # Take sentences from the end until we reach desired overlap
        for sentence in reversed(sentences):
            if overlap_chars + len(sentence) <= self.overlap_size:
                overlap_sentences.insert(0, sentence)
                overlap_chars += len(sentence)
            else:
                break
        
        return overlap_sentences
    
    def _balance_chunk_sizes(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Balance chunk sizes by splitting large chunks and merging small ones."""
        balanced_chunks = []
        
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            chunk_size = len(chunk["content"])
            
            # If chunk is too large, split it
            if chunk_size > self.max_chunk_size:
                split_chunks = self._split_oversized_chunk(chunk)
                balanced_chunks.extend(split_chunks)
            
            # If chunk is too small, try to merge with next
            elif chunk_size < self.min_chunk_size and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                combined_size = chunk_size + len(next_chunk["content"])
                
                if combined_size <= self.max_chunk_size:
                    # Merge chunks
                    merged_chunk = self._merge_chunks(chunk, next_chunk)
                    balanced_chunks.append(merged_chunk)
                    i += 1  # Skip next chunk since we merged it
                else:
                    balanced_chunks.append(chunk)
            else:
                balanced_chunks.append(chunk)
            
            i += 1
        
        return balanced_chunks
    
    def _split_oversized_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split an oversized chunk into smaller pieces."""
        content = chunk["content"]
        metadata = chunk["metadata"]
        
        # Try to split by paragraphs first
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 2:
            paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        
        if len(paragraphs) < 2:
            # Split by sentences as last resort
            sentences = self._split_into_sentences(content)
            return self._create_sentence_chunks(sentences, metadata)
        
        # Create chunks from paragraphs
        return self._create_paragraph_chunks(paragraphs, metadata)
    
    def _create_paragraph_chunks(self, paragraphs: List[str], base_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create chunks from paragraphs."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            para_size = len(paragraph)
            
            if current_size + para_size > self.target_chunk_size and current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        **base_metadata,
                        "chunk_type": "split_paragraph",
                        "char_count": len(chunk_content),
                        "split_index": len(chunks) + 1
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
                    **base_metadata,
                    "chunk_type": "split_paragraph",
                    "char_count": len(chunk_content),
                    "split_index": len(chunks) + 1
                }
            })
        
        return chunks
    
    def _create_sentence_chunks(self, sentences: List[str], base_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create chunks from sentences."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.target_chunk_size and current_chunk:
                chunk_content = ' '.join(current_chunk)
                chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        **base_metadata,
                        "chunk_type": "split_sentence",
                        "char_count": len(chunk_content),
                        "split_index": len(chunks) + 1
                    }
                })
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "metadata": {
                    **base_metadata,
                    "chunk_type": "split_sentence",
                    "char_count": len(chunk_content),
                    "split_index": len(chunks) + 1
                }
            })
        
        return chunks
    
    def _merge_chunks(self, chunk1: Dict[str, Any], chunk2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two small chunks into one."""
        combined_content = chunk1["content"] + "\n\n" + chunk2["content"]
        
        return {
            "content": combined_content,
            "metadata": {
                **chunk1["metadata"],
                "chunk_type": "merged",
                "char_count": len(combined_content),
                "merged_from": [
                    chunk1["metadata"].get("section_name", "unknown"),
                    chunk2["metadata"].get("section_name", "unknown")
                ]
            }
        }
    
    def _enhance_chunk_metadata(self, chunk: Dict[str, Any], index: int, document_type: str) -> Dict[str, Any]:
        """Enhance chunk with additional metadata."""
        content = chunk["content"]
        metadata = chunk.get("metadata", {})
        
        # Calculate quality metrics
        quality_score = self._calculate_chunk_quality(content, document_type)
        
        # Extract keywords
        keywords = self._extract_keywords(content, document_type)
        
        # Enhanced metadata
        enhanced_metadata = {
            **metadata,
            "chunk_id": f"{document_type}_balanced_{index+1:03d}",
            "chunk_index": index,
            "document_type": document_type,
            "quality_score": quality_score,
            "keywords": keywords,
            "word_count": len(content.split()),
            "processing_method": "balanced_chunking",
            "processing_timestamp": datetime.now().isoformat(),
            "optimal_size": self.min_chunk_size <= len(content) <= self.max_chunk_size
        }
        
        return {
            "chunk_id": enhanced_metadata["chunk_id"],
            "content": content,
            "metadata": enhanced_metadata
        }
    
    def _calculate_chunk_quality(self, content: str, document_type: str) -> float:
        """Calculate quality score for chunk."""
        score = 0.0
        
        # Size score (optimal range gets higher score)
        content_len = len(content)
        if self.min_chunk_size <= content_len <= self.max_chunk_size:
            if abs(content_len - self.target_chunk_size) <= 200:
                score += 0.3  # Near ideal size
            else:
                score += 0.2  # Acceptable size
        elif content_len >= self.min_chunk_size:
            score += 0.1  # At least minimum size
        
        # Content quality indicators
        if document_type == "policy":
            policy_terms = ["coverage", "deductible", "policy", "premium", "exclusion"]
            score += min(0.3, sum(0.06 for term in policy_terms if term in content.lower()))
        elif document_type == "claim":
            claim_terms = ["claim", "loss", "damage", "settlement", "adjuster"]
            score += min(0.3, sum(0.06 for term in claim_terms if term in claim_terms))
        
        # Structure indicators
        if re.search(r'\$[\d,]+', content):  # Contains monetary amounts
            score += 0.1
        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', content):  # Contains dates
            score += 0.1
        if len(content.split('\n\n')) > 1:  # Has paragraph structure
            score += 0.1
        
        return min(1.0, score)
    
    def _extract_keywords(self, content: str, document_type: str) -> List[str]:
        """Extract relevant keywords from chunk."""
        keywords = []
        content_lower = content.lower()
        
        # Common insurance terms
        insurance_terms = [
            "policy", "coverage", "deductible", "premium", "claim",
            "settlement", "adjuster", "liability", "damage", "loss"
        ]
        
        # Document-specific terms
        if document_type == "policy":
            specific_terms = ["exclusion", "condition", "limit", "insured", "dwelling"]
        elif document_type == "claim":
            specific_terms = ["incident", "repair", "estimate", "investigation", "payout"]
        else:
            specific_terms = []
        
        all_terms = insurance_terms + specific_terms
        
        for term in all_terms:
            if term in content_lower:
                keywords.append(term)
        
        return keywords[:10]  # Limit to top 10 keywords