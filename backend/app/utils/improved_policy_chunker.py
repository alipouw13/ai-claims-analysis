"""
Improved policy and claims document chunking using Azure Form Recognizer patterns
and better fallback strategies.
"""
import io
import re
from typing import List, Dict, Any, Tuple
from PyPDF2 import PdfReader
from docx import Document as DocxDocument


def extract_text_from_bytes(content: bytes, content_type: str) -> str:
    """Enhanced text extraction with better error handling."""
    try:
        ct = (content_type or "").lower()
        if "pdf" in ct:
            reader = PdfReader(io.BytesIO(content))
            text_parts: List[str] = []
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        # Add page marker for better chunking
                        text_parts.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
                except Exception:
                    continue
            return "\n".join(text_parts)
        elif "word" in ct or ct.endswith("docx"):
            doc = DocxDocument(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            return content.decode("utf-8", errors="ignore")
    except Exception:
        return content.decode("utf-8", errors="ignore")


def extract_key_value_pairs(text: str) -> Dict[str, str]:
    """Extract key-value pairs similar to Azure Form Recognizer."""
    pairs = {}
    
    # Common insurance key-value patterns
    patterns = [
        r"Policy\s*(?:Number|ID)[\s:]+([A-Z0-9\-]+)",
        r"Policyholder[\s:]+([A-Za-z\s]+?)(?:\n|$)",
        r"Property\s+Address[\s:]+([^\\n]+?)(?:\n|$)",
        r"Policy\s+Term[\s:]+([^\\n]+?)(?:\n|$)",
        r"Coverage\s+Type[\s:]+([^\\n]+?)(?:\n|$)",
        r"Deductible[\s:]+\$?([\d,]+)",
        r"Dwelling\s+Coverage[^$]*\$?([\d,]+)",
        r"Premium[\s:]+\$?([\d,]+)",
        r"Claim\s*(?:Number|ID)[\s:]+([A-Z0-9\-]+)",
        r"Date\s+of\s+Loss[\s:]+([^\\n]+?)(?:\n|$)",
        r"Insured[\s:]+([A-Za-z\s]+?)(?:\n|$)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            key = pattern.split('[')[0].replace('\\s', ' ').replace('\\+', '').strip()
            pairs[key] = matches[0] if isinstance(matches[0], str) else str(matches[0])
    
    return pairs


def identify_document_structure(text: str) -> List[Dict[str, Any]]:
    """Identify document structure using multiple strategies."""
    sections = []
    
    # Strategy 1: Insurance-specific headers (flexible patterns)
    insurance_patterns = [
        (r"(?:DEFINITIONS?|DEFINED TERMS?)[\s]*", "definitions"),
        (r"(?:COVERAGE|INSURING AGREEMENT|WHAT WE COVER)[\s]*", "coverage"),
        (r"(?:EXCLUSIONS?|WHAT WE DON'T COVER|NOT COVERED)[\s]*", "exclusions"),
        (r"(?:CONDITIONS?|POLICY CONDITIONS?)[\s]*", "conditions"),
        (r"(?:DEDUCTIBLES?|YOUR DEDUCTIBLE)[\s]*", "deductible"),
        (r"(?:LIMITS?|COVERAGE LIMITS?|POLICY LIMITS?)[\s]*", "limits"),
        (r"(?:ENDORSEMENTS?|RIDERS?|ADDITIONAL COVERAGE)[\s]*", "endorsements"),
        (r"(?:DECLARATIONS?|DEC PAGE|POLICY DECLARATIONS?)[\s]*", "declarations"),
        (r"(?:CLAIM|CLAIMS PROCEDURE|HOW TO FILE)[\s]*", "claims"),
        (r"(?:PREMIUM|COST|PAYMENT)[\s]*", "premium"),
    ]
    
    # Strategy 2: Numbered sections
    numbered_sections = re.findall(r"(\d+\.[\s]*[A-Z][^\\n]{10,50})", text, re.IGNORECASE)
    
    # Strategy 3: Bulleted lists  
    bulleted_sections = re.findall(r"([-•]\s*[A-Z][^\\n]{10,100})", text, re.IGNORECASE)
    
    # Strategy 4: Coverage items (dollar amounts)
    coverage_items = re.findall(r"([A-Za-z\s]{5,30}(?:Coverage|Limit)[^$]*\$[\d,]+)", text, re.IGNORECASE)
    
    return {
        "insurance_sections": insurance_patterns,
        "numbered_sections": numbered_sections,
        "bulleted_sections": bulleted_sections,
        "coverage_items": coverage_items
    }


def smart_chunk_policy_text(text: str) -> List[Dict[str, Any]]:
    """Improved policy chunking with multiple fallback strategies."""
    chunks = []
    chunk_index = 0
    
    # Extract key-value pairs first
    key_values = extract_key_value_pairs(text)
    
    # Strategy 1: Try insurance-specific section splitting
    insurance_sections = _split_by_insurance_sections(text)
    
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
    
    # Ensure we have at least some chunks
    if not chunks:
        chunks = _create_basic_policy_chunks(text, key_values)
    
    return chunks


def smart_chunk_claim_text(text: str) -> List[Dict[str, Any]]:
    """Improved claims chunking with structured approach."""
    chunks = []
    chunk_index = 0
    
    # Extract key-value pairs
    key_values = extract_key_value_pairs(text)
    
    # Strategy 1: Claim-specific sections
    claim_sections = _split_by_claim_sections(text)
    
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
        # Strategy 2: Fallback to structured claim chunking
        chunks = _semantic_chunk_claim(text, key_values)
    
    if not chunks:
        chunks = _create_basic_claim_chunks(text, key_values)
    
    return chunks


def _split_by_insurance_sections(text: str) -> Dict[str, str]:
    """Split by insurance-specific section headers."""
    sections = {}
    
    # More flexible insurance section patterns
    patterns = [
        (r"(?:^|\n)(?:DEFINITIONS?|DEFINED TERMS?)[\s:]*\n", "definitions"),
        (r"(?:^|\n)(?:COVERAGE|INSURING AGREEMENT|WHAT (?:WE|IS) COVER(?:ED)?|COVERED PERILS?)[\s:]*\n", "coverage"),
        (r"(?:^|\n)(?:EXCLUSIONS?|WHAT (?:WE|IS) (?:DON'T|NOT) COVER(?:ED)?|NOT COVERED)[\s:]*\n", "exclusions"),
        (r"(?:^|\n)(?:CONDITIONS?|POLICY CONDITIONS?)[\s:]*\n", "conditions"),
        (r"(?:^|\n)(?:DEDUCTIBLES?|YOUR DEDUCTIBLE)[\s:]*\n", "deductible"),
        (r"(?:^|\n)(?:LIMITS?|COVERAGE LIMITS?|POLICY LIMITS?)[\s:]*\n", "limits"),
        (r"(?:^|\n)(?:ENDORSEMENTS?|RIDERS?|ADDITIONAL COVERAGE)[\s:]*\n", "endorsements"),
        (r"(?:^|\n)(?:DECLARATIONS?|DEC PAGE|POLICY DECLARATIONS?)[\s:]*\n", "declarations"),
        (r"(?:^|\n)(?:PROPERTY COVERAGE|DWELLING COVERAGE)[\s:]*\n", "property_coverage"),
        (r"(?:^|\n)(?:LIABILITY COVERAGE|PERSONAL LIABILITY)[\s:]*\n", "liability_coverage"),
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
        (r"(?:^|\n)(?:CLAIM (?:NUMBER|ID|INFORMATION)|CLAIM DETAILS?)[\s:]*\n", "claim_info"),
        (r"(?:^|\n)(?:INSURED|POLICYHOLDER|CLAIMANT)[\s:]*\n", "insured_info"), 
        (r"(?:^|\n)(?:POLICY (?:NUMBER|ID|INFORMATION)|POLICY DETAILS?)[\s:]*\n", "policy_info"),
        (r"(?:^|\n)(?:DATE (?:OF )?LOSS|LOSS DATE|INCIDENT DATE)[\s:]*\n", "loss_date"),
        (r"(?:^|\n)(?:LOSS DESCRIPTION|DESCRIPTION OF LOSS|INCIDENT DESCRIPTION)[\s:]*\n", "loss_description"),
        (r"(?:^|\n)(?:ADJUSTER NOTES?|ADJUSTER COMMENTS?|INVESTIGATION)[\s:]*\n", "adjuster_notes"),
        (r"(?:^|\n)(?:COVERAGE DECISION|COVERAGE DETERMINATION|DECISION)[\s:]*\n", "coverage_decision"),
        (r"(?:^|\n)(?:SETTLEMENT|PAYMENT|PAYOUT)[\s:]*\n", "settlement"),
        (r"(?:^|\n)(?:ATTACHMENTS?|DOCUMENTS?|SUPPORTING DOCS?)[\s:]*\n", "attachments"),
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
    
    # Split by logical boundaries
    sections = []
    
    # Look for coverage items
    coverage_pattern = r"([A-Za-z\s]{5,50}(?:Coverage|Limit)[^$]*\$[\d,]+[^\\n]*)"
    coverage_items = re.findall(coverage_pattern, text, re.IGNORECASE)
    
    # Look for bulleted lists
    bullet_pattern = r"([-•]\s*[A-Za-z][^\\n]{20,})"
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


# Update the main chunking functions to use the improved versions
def chunk_policy_text(text: str) -> List[Dict[str, Any]]:
    """Main entry point for policy chunking - now uses improved logic."""
    return smart_chunk_policy_text(text)


def chunk_claim_text(text: str) -> List[Dict[str, Any]]:
    """Main entry point for claim chunking - now uses improved logic."""
    return smart_chunk_claim_text(text)