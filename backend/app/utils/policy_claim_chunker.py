import io
import re
from typing import List, Dict, Any

from PyPDF2 import PdfReader
from docx import Document as DocxDocument


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
    """Chunk policy documents using insurance-specific headings and bullets."""
    heading_patterns = [
        r"^definitions\b.*$",
        r"^insuring\s+agreement\b.*$",
        r"^coverage\b.*$",
        r"^exclusions\b.*$",
        r"^conditions\b.*$",
        r"^endorsements\b.*$",
        r"^limits\b.*$",
        r"^deductible\b.*$",
        r"^declarations\b.*$",
        r"^schedule\b.*$",
    ]
    sections = _split_on_headings(text, heading_patterns)

    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    for section_name, section_text in sections.items():
        # Further split on bullets/numbering to keep chunks focused
        parts = re.split(r"\n\s*(?:[-•\d]+[.)\-:]\s+)", section_text)
        for i, part in enumerate(parts):
            cleaned = part.strip()
            if len(cleaned) < 40:
                continue
            chunks.append({
                "chunk_id": f"policy_chunk_{chunk_index}",
                "content": cleaned,
                "metadata": {
                    "chunk_index": chunk_index,
                    "section_key": section_name,
                    "section_type": "policy",
                    "chunk_type": "text",
                }
            })
            chunk_index += 1
    if not chunks:
        chunks.append({
            "chunk_id": f"policy_chunk_{chunk_index}",
            "content": text,
            "metadata": {"chunk_index": 0, "section_type": "policy", "chunk_type": "text"}
        })
    return chunks


def chunk_claim_text(text: str) -> List[Dict[str, Any]]:
    """Chunk claim documents with typical structure: identifiers, loss details, notes, assessment, settlement."""
    heading_patterns = [
        r"^claim\s*(?:number|id)\b.*$",
        r"^insured\b.*$",
        r"^policy\s*(?:number|id)\b.*$",
        r"^date\s+of\s+loss\b.*$",
        r"^loss\s+description\b.*$",
        r"^adjuster\s+notes\b.*$",
        r"^coverage\s+decision\b.*$",
        r"^settlement\s+summary\b.*$",
        r"^payout\s+summary\b.*$",
        r"^attachments\b.*$",
    ]
    sections = _split_on_headings(text, heading_patterns)

    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    for section_name, section_text in sections.items():
        # Keep smaller logical chunks; split by paragraph while preserving signal
        parts = re.split(r"\n{2,}", section_text)
        for i, part in enumerate(parts):
            cleaned = part.strip()
            if len(cleaned) < 40:
                continue
            chunks.append({
                "chunk_id": f"claim_chunk_{chunk_index}",
                "content": cleaned,
                "metadata": {
                    "chunk_index": chunk_index,
                    "section_key": section_name,
                    "section_type": "claim",
                    "chunk_type": "text",
                }
            })
            chunk_index += 1
    if not chunks:
        chunks.append({
            "chunk_id": f"claim_chunk_{chunk_index}",
            "content": text,
            "metadata": {"chunk_index": 0, "section_type": "claim", "chunk_type": "text"}
        })
    return chunks


