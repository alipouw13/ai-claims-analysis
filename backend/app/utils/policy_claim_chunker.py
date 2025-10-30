import io
import re
import logging
from datetime import datetime
from typing import List, Dict, Any

from PyPDF2 import PdfReader
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)


def extract_text_from_bytes(content: bytes, content_type: str) -> str:
    """Best-effort text extraction from common formats without Azure DI.

    Supports: PDF (PyPDF2), DOCX (python-docx), TXT fallback.
    """
    try:
        ct = (content_type or "").lower()
        if "pdf" in ct:
            reader = PdfReader(io.BytesIO(content))
            text_parts: List[str] = []
            for page in reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception:
                    continue
            return "\n".join(text_parts)
        elif "word" in ct or ct.endswith("docx"):
            doc = DocxDocument(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            # Try to decode as text
            return content.decode("utf-8", errors="ignore")
    except Exception:
        return content.decode("utf-8", errors="ignore")


def _split_on_headings(text: str, heading_patterns: List[str]) -> Dict[str, str]:
    """Split text into sections using regex heading patterns."""
    combined = re.compile("|".join(heading_patterns), flags=re.IGNORECASE | re.MULTILINE)
    sections: Dict[str, str] = {}

    matches = list(combined.finditer(text))
    if not matches:
        return {"body": text}

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(0).strip().lower()
        key = re.sub(r"[^a-z0-9]+", "_", title)
        sections[key or f"section_{i}"] = text[start:end].strip()
    return sections


def chunk_policy_text(text: str) -> List[Dict[str, Any]]:
    """Enhanced policy chunking with better fallback strategies."""
    # Extract key-value pairs for metadata
    key_values = _extract_key_value_pairs(text)
    
    # Strategy 1: Try flexible insurance-specific section splitting
    insurance_sections = _split_by_flexible_insurance_sections(text)
    
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    
    if len(insurance_sections) > 1:
        # Found meaningful sections
        for section_name, section_content in insurance_sections.items():
            if len(section_content.strip()) < 30:
                continue
                
            # Further split large sections
            subsections = _split_large_section(section_content, max_size=1200)
            
            for i, subsection in enumerate(subsections):
                chunks.append({
                    "chunk_id": f"policy_chunk_{chunk_index}",
                    "content": subsection.strip(),
                    "metadata": {
                        "chunk_index": chunk_index,
                        "section_name": section_name,
                        "section_type": "policy",
                        "chunk_type": "text",
                        "subsection_index": i,
                        "total_subsections": len(subsections),
                        "key_value_pairs": key_values,
                        "content_length": len(subsection.strip())
                    }
                })
                chunk_index += 1
    else:
        # Strategy 2: Fallback to semantic chunking
        chunks = _semantic_chunk_policy(text, key_values)
    
    # Final fallback: create basic chunks if nothing else worked
    if not chunks:
        chunks = _create_basic_policy_chunks(text, key_values)
    
    return chunks


def chunk_claim_text(text: str) -> List[Dict[str, Any]]:
    """Enhanced claims chunking with structured approach."""
    # Extract key-value pairs for metadata
    key_values = _extract_key_value_pairs(text)
    
    # Strategy 1: Claim-specific sections
    claim_sections = _split_by_claim_sections(text)
    
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    
    if len(claim_sections) > 1:
        for section_name, section_content in claim_sections.items():
            if len(section_content.strip()) < 30:
                continue
                
            subsections = _split_large_section(section_content, max_size=1000)
            
            for i, subsection in enumerate(subsections):
                chunks.append({
                    "chunk_id": f"claim_chunk_{chunk_index}",
                    "content": subsection.strip(),
                    "metadata": {
                        "chunk_index": chunk_index,
                        "section_name": section_name,
                        "section_type": "claim",
                        "chunk_type": "text",
                        "subsection_index": i,
                        "total_subsections": len(subsections),
                        "key_value_pairs": key_values,
                        "content_length": len(subsection.strip())
                    }
                })
                chunk_index += 1
    else:
        # Strategy 2: Fallback to semantic chunking
        chunks = _semantic_chunk_claim(text, key_values)
    
    if not chunks:
        chunks = _create_basic_claim_chunks(text, key_values)
    
    return chunks


def _extract_key_value_pairs(text: str) -> Dict[str, str]:
    """Extract key-value pairs similar to Azure Form Recognizer."""
    pairs = {}
    
    # Common insurance key-value patterns
    patterns = [
        (r"Policy\s*(?:Number|ID)[\s:]+([A-Z0-9\-]+)", "policy_number"),
        (r"Policyholder[\s:]+([A-Za-z\s]+?)(?:\n|$)", "policyholder"),
        (r"Property\s+Address[\s:]+([^\n]+?)(?:\n|$)", "property_address"),
        (r"Policy\s+Term[\s:]+([^\n]+?)(?:\n|$)", "policy_term"),
        (r"Coverage\s+Type[\s:]+([^\n]+?)(?:\n|$)", "coverage_type"),
        (r"Deductible[\s:]+\$?([\d,]+)", "deductible"),
        (r"Dwelling\s+Coverage[^$]*\$?([\d,]+)", "dwelling_coverage"),
        (r"Premium[\s:]+\$?([\d,]+)", "premium"),
        (r"Claim\s*(?:Number|ID)[\s:]+([A-Z0-9\-]+)", "claim_number"),
        (r"Date\s+of\s+Loss[\s:]+([^\n]+?)(?:\n|$)", "loss_date"),
        (r"Insured[\s:]+([A-Za-z\s]+?)(?:\n|$)", "insured"),
    ]
    
    for pattern, key in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            pairs[key] = matches[0] if isinstance(matches[0], str) else str(matches[0])
    
    return pairs


def _split_by_flexible_insurance_sections(text: str) -> Dict[str, str]:
    """Split by insurance-specific section headers with flexible patterns."""
    sections = {}
    
    # More flexible insurance section patterns
    patterns = [
        (r"(?:^|\n)(?:DEFINITIONS?|DEFINED TERMS?)[\s:]*", "definitions"),
        (r"(?:^|\n)(?:COVERAGE|INSURING AGREEMENT|WHAT (?:WE|IS) COVER(?:ED)?|COVERED PERILS?)[\s:]*", "coverage"),
        (r"(?:^|\n)(?:EXCLUSIONS?|WHAT (?:WE|IS) (?:DON'T|NOT) COVER(?:ED)?|NOT COVERED)[\s:]*", "exclusions"),
        (r"(?:^|\n)(?:CONDITIONS?|POLICY CONDITIONS?)[\s:]*", "conditions"),
        (r"(?:^|\n)(?:DEDUCTIBLES?|YOUR DEDUCTIBLE)[\s:]*", "deductible"),
        (r"(?:^|\n)(?:LIMITS?|COVERAGE LIMITS?|POLICY LIMITS?)[\s:]*", "limits"),
        (r"(?:^|\n)(?:ENDORSEMENTS?|RIDERS?|ADDITIONAL COVERAGE)[\s:]*", "endorsements"),
        (r"(?:^|\n)(?:DECLARATIONS?|DEC PAGE|POLICY DECLARATIONS?)[\s:]*", "declarations"),
        (r"(?:^|\n)(?:PROPERTY COVERAGE|DWELLING COVERAGE)[\s:]*", "property_coverage"),
        (r"(?:^|\n)(?:LIABILITY COVERAGE|PERSONAL LIABILITY)[\s:]*", "liability_coverage"),
    ]
    
    # Find all section boundaries
    boundaries = []
    for pattern, section_name in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            boundaries.append((match.start(), match.end(), section_name))
    
    # Sort by position
    boundaries.sort()
    
    if not boundaries:
        return {"main_content": text}
    
    # Extract sections
    for i, (start, end, section_name) in enumerate(boundaries):
        section_start = end
        section_end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        section_content = text[section_start:section_end].strip()
        
        if section_content:
            sections[section_name] = section_content
    
    # Add content before first section as intro
    if boundaries:
        intro_content = text[:boundaries[0][0]].strip()
        if intro_content:
            sections["introduction"] = intro_content
    
    return sections if sections else {"main_content": text}


def _split_by_claim_sections(text: str) -> Dict[str, str]:
    """Split by claim-specific section headers."""
    sections = {}
    
    patterns = [
        (r"(?:^|\n)(?:CLAIM (?:NUMBER|ID|INFORMATION)|CLAIM DETAILS?)[\s:]*", "claim_info"),
        (r"(?:^|\n)(?:INSURED|POLICYHOLDER|CLAIMANT)[\s:]*", "insured_info"), 
        (r"(?:^|\n)(?:POLICY (?:NUMBER|ID|INFORMATION)|POLICY DETAILS?)[\s:]*", "policy_info"),
        (r"(?:^|\n)(?:DATE (?:OF )?LOSS|LOSS DATE|INCIDENT DATE)[\s:]*", "loss_date"),
        (r"(?:^|\n)(?:LOSS DESCRIPTION|DESCRIPTION OF LOSS|INCIDENT DESCRIPTION)[\s:]*", "loss_description"),
        (r"(?:^|\n)(?:ADJUSTER NOTES?|ADJUSTER COMMENTS?|INVESTIGATION)[\s:]*", "adjuster_notes"),
        (r"(?:^|\n)(?:COVERAGE DECISION|COVERAGE DETERMINATION|DECISION)[\s:]*", "coverage_decision"),
        (r"(?:^|\n)(?:SETTLEMENT|PAYMENT|PAYOUT)[\s:]*", "settlement"),
        (r"(?:^|\n)(?:ATTACHMENTS?|DOCUMENTS?|SUPPORTING DOCS?)[\s:]*", "attachments"),
    ]
    
    # Find section boundaries
    boundaries = []
    for pattern, section_name in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            boundaries.append((match.start(), match.end(), section_name))
    
    boundaries.sort()
    
    if not boundaries:
        return {"main_content": text}
    
    # Extract sections
    for i, (start, end, section_name) in enumerate(boundaries):
        section_start = end  
        section_end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        section_content = text[section_start:section_end].strip()
        
        if section_content:
            sections[section_name] = section_content
    
    if boundaries:
        intro_content = text[:boundaries[0][0]].strip()
        if intro_content:
            sections["introduction"] = intro_content
    
    return sections if sections else {"main_content": text}


def _split_large_section(content: str, max_size: int = 1200) -> List[str]:
    """Split large sections into smaller chunks with smart boundaries."""
    if len(content) <= max_size:
        return [content]
    
    chunks = []
    
    # Try to split on paragraphs first
    paragraphs = re.split(r'\n\s*\n', content)
    
    current_chunk = ""
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) <= max_size:
            current_chunk += paragraph + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # If still too large, split on sentences
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_size:
            final_chunks.append(chunk)
        else:
            final_chunks.extend(_split_on_sentences(chunk, max_size))
    
    return final_chunks


def _split_on_sentences(text: str, max_size: int) -> List[str]:
    """Split text on sentence boundaries."""
    sentences = re.split(r'[.!?]+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if len(current_chunk) + len(sentence) <= max_size:
            current_chunk += sentence + ". "
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def _semantic_chunk_policy(text: str, key_values: Dict[str, str]) -> List[Dict[str, Any]]:
    """Create semantic chunks for policies using content patterns."""
    chunks = []
    
    # Look for coverage items
    coverage_pattern = r"([A-Za-z\s]{5,50}(?:Coverage|Limit)[^$]*\$[\d,]+[^\n]*)"
    coverage_items = re.findall(coverage_pattern, text, re.IGNORECASE)
    
    # Look for bulleted lists
    bullet_pattern = r"([-•]\s*[A-Za-z][^\n]{20,})"
    bullet_items = re.findall(bullet_pattern, text, re.IGNORECASE)
    
    # Create chunks from structured content
    chunk_index = 0
    
    # Header information chunk
    lines = text.split('\n')
    header_content = []
    for line in lines[:10]:  # First 10 lines usually contain key info
        if line.strip() and ('Policy' in line or 'Coverage' in line or 'Deductible' in line):
            header_content.append(line.strip())
    
    if header_content:
        chunks.append({
            "chunk_id": f"policy_chunk_{chunk_index}",
            "content": '\n'.join(header_content),
            "metadata": {
                "chunk_index": chunk_index,
                "section_name": "policy_header",
                "section_type": "policy",
                "chunk_type": "header",
                "key_value_pairs": key_values,
                "content_length": len('\n'.join(header_content))
            }
        })
        chunk_index += 1
    
    # Coverage items chunks
    for item in coverage_items:
        if len(item.strip()) > 30:
            chunks.append({
                "chunk_id": f"policy_chunk_{chunk_index}",
                "content": item.strip(),
                "metadata": {
                    "chunk_index": chunk_index,
                    "section_name": "coverage_items",
                    "section_type": "policy",
                    "chunk_type": "coverage",
                    "key_value_pairs": key_values,
                    "content_length": len(item.strip())
                }
            })
            chunk_index += 1
    
    # Bullet items chunks (group related bullets)
    if bullet_items:
        bullet_chunk = '\n'.join(bullet_items)
        if len(bullet_chunk) > 50:
            chunks.append({
                "chunk_id": f"policy_chunk_{chunk_index}",
                "content": bullet_chunk,
                "metadata": {
                    "chunk_index": chunk_index,
                    "section_name": "bullet_items",
                    "section_type": "policy", 
                    "chunk_type": "list",
                    "key_value_pairs": key_values,
                    "content_length": len(bullet_chunk)
                }
            })
            chunk_index += 1
    
    return chunks


def _semantic_chunk_claim(text: str, key_values: Dict[str, str]) -> List[Dict[str, Any]]:
    """Create semantic chunks for claims using content patterns."""
    chunks = []
    chunk_index = 0
    
    # Extract structured claim information
    lines = text.split('\n')
    
    # Identify claim header information
    header_lines = []
    description_lines = []
    detail_lines = []
    
    current_section = "header"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect section transitions
        if any(keyword in line.lower() for keyword in ['description', 'details', 'notes', 'assessment']):
            current_section = "description"
        elif any(keyword in line.lower() for keyword in ['settlement', 'payment', 'decision', 'conclusion']):
            current_section = "details"
        
        if current_section == "header":
            header_lines.append(line)
        elif current_section == "description":
            description_lines.append(line)
        else:
            detail_lines.append(line)
    
    # Create chunks from sections
    if header_lines:
        chunks.append({
            "chunk_id": f"claim_chunk_{chunk_index}",
            "content": '\n'.join(header_lines),
            "metadata": {
                "chunk_index": chunk_index,
                "section_name": "claim_header",
                "section_type": "claim",
                "chunk_type": "header",
                "key_value_pairs": key_values,
                "content_length": len('\n'.join(header_lines))
            }
        })
        chunk_index += 1
    
    if description_lines:
        chunks.append({
            "chunk_id": f"claim_chunk_{chunk_index}",
            "content": '\n'.join(description_lines),
            "metadata": {
                "chunk_index": chunk_index,
                "section_name": "claim_description",
                "section_type": "claim",
                "chunk_type": "description",
                "key_value_pairs": key_values,
                "content_length": len('\n'.join(description_lines))
            }
        })
        chunk_index += 1
    
    if detail_lines:
        chunks.append({
            "chunk_id": f"claim_chunk_{chunk_index}",
            "content": '\n'.join(detail_lines),
            "metadata": {
                "chunk_index": chunk_index,
                "section_name": "claim_details",
                "section_type": "claim",
                "chunk_type": "details",
                "key_value_pairs": key_values,
                "content_length": len('\n'.join(detail_lines))
            }
        })
        chunk_index += 1
    
    return chunks


def _create_basic_policy_chunks(text: str, key_values: Dict[str, str]) -> List[Dict[str, Any]]:
    """Create basic chunks as final fallback."""
    chunks = []
    max_chunk_size = 800
    overlap = 100
    
    # Simple overlapping chunks
    start = 0
    chunk_index = 0
    
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        
        # Try to end at sentence boundary
        if end < len(text):
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + 200:  # Reasonable chunk size
                end = sentence_end + 1
        
        chunk_content = text[start:end].strip()
        if len(chunk_content) > 50:
            chunks.append({
                "chunk_id": f"policy_chunk_{chunk_index}",
                "content": chunk_content,
                "metadata": {
                    "chunk_index": chunk_index,
                    "section_name": "basic_content",
                    "section_type": "policy",
                    "chunk_type": "text",
                    "key_value_pairs": key_values,
                    "content_length": len(chunk_content)
                }
            })
            chunk_index += 1
        
        start = max(start + 1, end - overlap)
    
    return chunks


def _create_basic_claim_chunks(text: str, key_values: Dict[str, str]) -> List[Dict[str, Any]]:
    """Create basic chunks for claims as final fallback."""
    chunks = []
    max_chunk_size = 600  # Smaller for claims
    overlap = 80
    
    start = 0
    chunk_index = 0
    
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        
        # Try to end at paragraph boundary
        if end < len(text):
            para_end = text.rfind('\n\n', start, end)
            if para_end > start + 100:
                end = para_end
        
        chunk_content = text[start:end].strip()
        if len(chunk_content) > 30:
            chunks.append({
                "chunk_id": f"claim_chunk_{chunk_index}",
                "content": chunk_content,
                "metadata": {
                    "chunk_index": chunk_index,
                    "section_name": "basic_content",
                    "section_type": "claim",
                    "chunk_type": "text",
                    "key_value_pairs": key_values,
                    "content_length": len(chunk_content)
                }
            })
            chunk_index += 1
        
        start = max(start + 1, end - overlap)
    
    return chunks


def smart_chunk_policy_text(text: str) -> List[Dict[str, Any]]:
    """
    Enhanced policy text chunking with intelligent section detection and balanced sizing.
    
    Args:
        text: Raw policy document text
        
    Returns:
        List of chunk dictionaries with enhanced metadata
    """
    logger.info(f"Starting smart policy chunking for {len(text)} characters")
    
    if not text or len(text.strip()) < 10:
        logger.warning("Text too short for chunking")
        return []
    
    try:
        # Use balanced chunker for optimal chunk sizes
        from app.utils.balanced_chunker import BalancedChunker
        
        # Create balanced chunker with policy-optimized settings
        chunker = BalancedChunker(
            target_chunk_size=900,  # Optimal for RAG retrieval
            max_chunk_size=1400,    # Prevent overly large chunks
            min_chunk_size=250,     # Ensure meaningful content
            overlap_ratio=0.12      # Reasonable overlap for context
        )
        
        # Create balanced chunks
        balanced_chunks = chunker.chunk_document(text, "policy")
        
        if balanced_chunks and len(balanced_chunks) > 0:
            logger.info(f"Balanced policy chunking successful: {len(balanced_chunks)} chunks")
            return balanced_chunks
        
        # Fallback to enhanced chunking if balanced fails
        logger.info("Balanced chunking failed, using enhanced fallback")
        enhanced_chunks = chunk_policy_text(text)
        if enhanced_chunks and len(enhanced_chunks) > 0:
            logger.info(f"Enhanced policy chunking fallback: {len(enhanced_chunks)} chunks")
            # Add smart chunking metadata to existing chunks
            for i, chunk in enumerate(enhanced_chunks):
                chunk["metadata"]["chunk_method"] = "enhanced_policy_chunking"
                chunk["metadata"]["smart_processing"] = True
                chunk["metadata"]["processing_timestamp"] = datetime.now().isoformat()
            return enhanced_chunks
        
        # Final fallback to basic chunking
        logger.info("Enhanced chunking also failed, using basic approach")
        basic_chunks = _create_basic_overlapping_chunks(text, chunk_size=1000, overlap=150)
        for chunk in basic_chunks:
            chunk["metadata"]["chunk_method"] = "basic_policy_chunking"
            chunk["metadata"]["smart_processing"] = False
        return basic_chunks
        
    except Exception as e:
        logger.error(f"Error in smart policy chunking: {e}")
        # Final fallback - create one chunk from the whole text
        return [{
            "chunk_id": "policy_chunk_001",
            "content": text,
            "metadata": {
                "section_type": "full_document",
                "confidence": 0.5,
                "chunk_method": "fallback_full_text",
                "word_count": len(text.split()),
                "char_count": len(text),
                "smart_processing": False,
                "error": str(e)
            }
        }]


def smart_chunk_claim_text(text: str) -> List[Dict[str, Any]]:
    """
    Enhanced claim text chunking with intelligent section detection and balanced sizing.
    
    Args:
        text: Raw claim document text
        
    Returns:
        List of chunk dictionaries with enhanced metadata
    """
    logger.info(f"Starting smart claim chunking for {len(text)} characters")
    
    if not text or len(text.strip()) < 10:
        logger.warning("Text too short for chunking")
        return []
    
    try:
        # Use balanced chunker for optimal chunk sizes
        from app.utils.balanced_chunker import BalancedChunker
        
        # Create balanced chunker with claim-optimized settings
        chunker = BalancedChunker(
            target_chunk_size=800,   # Slightly smaller for claims
            max_chunk_size=1200,     # Prevent overly large chunks
            min_chunk_size=200,      # Ensure meaningful content
            overlap_ratio=0.15       # Slightly more overlap for claims
        )
        
        # Create balanced chunks
        balanced_chunks = chunker.chunk_document(text, "claim")
        
        if balanced_chunks and len(balanced_chunks) > 0:
            logger.info(f"Balanced claim chunking successful: {len(balanced_chunks)} chunks")
            return balanced_chunks
        
        # Fallback to enhanced chunking if balanced fails
        logger.info("Balanced chunking failed, using enhanced fallback")
        enhanced_chunks = chunk_claim_text(text)
        if enhanced_chunks and len(enhanced_chunks) > 0:
            logger.info(f"Enhanced claim chunking fallback: {len(enhanced_chunks)} chunks")
            # Add smart chunking metadata to existing chunks
            for i, chunk in enumerate(enhanced_chunks):
                chunk["metadata"]["chunk_method"] = "enhanced_claim_chunking"
                chunk["metadata"]["smart_processing"] = True
                chunk["metadata"]["processing_timestamp"] = datetime.now().isoformat()
            return enhanced_chunks
        
        # Final fallback to basic chunking
        logger.info("Enhanced chunking also failed, using basic approach")
        basic_chunks = _create_basic_overlapping_chunks(text, chunk_size=800, overlap=120)
        for chunk in basic_chunks:
            chunk["metadata"]["chunk_method"] = "basic_claim_chunking"
            chunk["metadata"]["smart_processing"] = False
        return basic_chunks
        
    except Exception as e:
        logger.error(f"Error in smart claim chunking: {e}")
        # Final fallback - create one chunk from the whole text
        return [{
            "chunk_id": "claim_chunk_001",
            "content": text,
            "metadata": {
                "section_type": "full_document",
                "confidence": 0.5,
                "chunk_method": "fallback_full_text",
                "word_count": len(text.split()),
                "char_count": len(text),
                "smart_processing": False,
                "error": str(e)
            }
        }]


def _create_basic_overlapping_chunks(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[Dict[str, Any]]:
    """Create basic overlapping chunks from text."""
    chunks = []
    words = text.split()
    
    if not words:
        return chunks
    
    # Calculate word-based chunk size and overlap
    words_per_chunk = chunk_size // 5  # Rough estimate: 5 chars per word
    overlap_words = overlap // 5
    
    start = 0
    chunk_index = 0
    
    while start < len(words):
        end = min(start + words_per_chunk, len(words))
        chunk_words = words[start:end]
        chunk_content = ' '.join(chunk_words)
        
        if chunk_content.strip():
            chunks.append({
                "chunk_id": f"basic_chunk_{chunk_index:03d}",
                "content": chunk_content,
                "metadata": {
                    "chunk_index": chunk_index,
                    "section_type": "overlapping_chunk",
                    "start_word": start,
                    "end_word": end,
                    "word_count": len(chunk_words),
                    "char_count": len(chunk_content),
                    "chunk_method": "basic_overlapping"
                }
            })
            chunk_index += 1
        
        # Move start position, accounting for overlap
        start = max(start + words_per_chunk - overlap_words, start + 1)
        
        # Prevent infinite loop
        if start >= len(words):
            break
    
    return chunks


