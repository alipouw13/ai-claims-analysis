"""
Azure Form Recognizer Enhanced Document Processing
Combines Azure Document Intelligence with improved chunking strategies
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import re

logger = logging.getLogger(__name__)

@dataclass
class FormRecognizerResult:
    """Structured result from Azure Form Recognizer analysis."""
    content: str
    tables: List[Dict[str, Any]]
    key_value_pairs: Dict[str, str]
    pages: int
    confidence_scores: Dict[str, float]
    document_type: str
    structured_sections: Dict[str, str]


class EnhancedDocumentProcessor:
    """
    Enhanced document processor that combines Azure Form Recognizer
    with intelligent chunking strategies for insurance documents.
    """
    
    def __init__(self, azure_manager):
        self.azure_manager = azure_manager
        self.insurance_patterns = self._initialize_insurance_patterns()
        
    def _initialize_insurance_patterns(self) -> Dict[str, List[str]]:
        """Initialize insurance-specific extraction patterns."""
        return {
            "policy_fields": [
                "Policy Number", "Policy ID", "Policyholder", "Insured",
                "Coverage Type", "Policy Term", "Premium", "Deductible",
                "Property Address", "Effective Date", "Expiration Date"
            ],
            "claim_fields": [
                "Claim Number", "Claim ID", "Date of Loss", "Claimant", 
                "Policy Number", "Loss Description", "Claim Amount",
                "Adjuster", "Status", "Settlement Amount"
            ],
            "coverage_patterns": [
                r"([A-Z][A-Za-z\s]+Coverage[^:]*):?\s*\$?([\d,]+)",
                r"([A-Z][A-Za-z\s]+Limit[^:]*):?\s*\$?([\d,]+)",
                r"(Dwelling|Property|Liability|Medical)\s+Coverage[^:]*\$?([\d,]+)"
            ]
        }
    
    async def analyze_with_form_recognizer(self, content: bytes, content_type: str) -> FormRecognizerResult:
        """
        Analyze document using Azure Form Recognizer with enhanced processing.
        """
        try:
            logger.info("🔍 Starting Azure Form Recognizer analysis...")
            
            # Use Azure Document Intelligence if available
            if hasattr(self.azure_manager, 'form_recognizer_client') and self.azure_manager.form_recognizer_client:
                result = await self._analyze_with_azure_di(content, content_type)
            else:
                # Fallback to local processing with PyPDF2
                result = await self._analyze_with_local_processing(content, content_type)
            
            # Enhance the result with insurance-specific processing
            enhanced_result = await self._enhance_with_insurance_analysis(result)
            
            logger.info(f"✅ Document analysis complete: {enhanced_result.document_type}")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error in form recognizer analysis: {e}")
            # Return minimal result
            from app.utils.policy_claim_chunker import extract_text_from_bytes
            text = extract_text_from_bytes(content, content_type)
            return FormRecognizerResult(
                content=text,
                tables=[],
                key_value_pairs={},
                pages=1,
                confidence_scores={},
                document_type="unknown",
                structured_sections={"main": text}
            )
    
    async def _analyze_with_azure_di(self, content: bytes, content_type: str) -> FormRecognizerResult:
        """Analyze using Azure Document Intelligence."""
        logger.info("📄 Using Azure Document Intelligence...")
        
        try:
            # Use the existing Azure DI integration
            di_result = await self.azure_manager.analyze_document(content, content_type)
            
            # Extract structured information
            text_content = di_result.get("content", "")
            tables = di_result.get("tables", [])
            key_value_pairs = di_result.get("key_value_pairs", {})
            pages = di_result.get("pages", 1)
            
            # Process tables into structured format
            processed_tables = []
            for table in tables:
                if hasattr(table, 'cells'):
                    table_data = self._process_azure_di_table(table)
                    processed_tables.append(table_data)
            
            # Extract key-value pairs with confidence
            structured_kvp = {}
            confidence_scores = {}
            
            if isinstance(key_value_pairs, dict):
                for key, value in key_value_pairs.items():
                    if isinstance(value, dict) and 'content' in value:
                        structured_kvp[key] = value['content']
                        confidence_scores[key] = value.get('confidence', 0.0)
                    else:
                        structured_kvp[key] = str(value)
                        confidence_scores[key] = 1.0
            
            # Detect document type
            document_type = self._detect_document_type(text_content, structured_kvp)
            
            # Create structured sections
            structured_sections = self._create_structured_sections(text_content, document_type)
            
            return FormRecognizerResult(
                content=text_content,
                tables=processed_tables,
                key_value_pairs=structured_kvp,
                pages=pages,
                confidence_scores=confidence_scores,
                document_type=document_type,
                structured_sections=structured_sections
            )
            
        except Exception as e:
            logger.error(f"Azure DI analysis failed: {e}")
            # Fallback to local processing
            return await self._analyze_with_local_processing(content, content_type)
    
    async def _analyze_with_local_processing(self, content: bytes, content_type: str) -> FormRecognizerResult:
        """Fallback local processing using PyPDF2."""
        logger.info("📄 Using local PDF processing (fallback)...")
        
        from app.utils.policy_claim_chunker import extract_text_from_bytes
        text_content = extract_text_from_bytes(content, content_type)
        
        # Extract key-value pairs using patterns
        key_value_pairs = self._extract_kvp_with_patterns(text_content)
        
        # Detect document type
        document_type = self._detect_document_type(text_content, key_value_pairs)
        
        # Create structured sections
        structured_sections = self._create_structured_sections(text_content, document_type)
        
        # Extract simple tables (basic pattern matching)
        tables = self._extract_simple_tables(text_content)
        
        return FormRecognizerResult(
            content=text_content,
            tables=tables,
            key_value_pairs=key_value_pairs,
            pages=len(text_content) // 3000 + 1,  # Rough page estimation
            confidence_scores={k: 0.8 for k in key_value_pairs.keys()},
            document_type=document_type,
            structured_sections=structured_sections
        )
    
    def _process_azure_di_table(self, table) -> Dict[str, Any]:
        """Process Azure DI table into structured format."""
        table_data = {
            "rows": [],
            "headers": [],
            "row_count": 0,
            "column_count": 0
        }
        
        try:
            if hasattr(table, 'cells'):
                # Group cells by row
                cells_by_row = {}
                max_col = 0
                
                for cell in table.cells:
                    row_idx = cell.row_index
                    col_idx = cell.column_index
                    
                    if row_idx not in cells_by_row:
                        cells_by_row[row_idx] = {}
                    
                    cells_by_row[row_idx][col_idx] = cell.content
                    max_col = max(max_col, col_idx)
                
                # Extract headers (first row)
                if 0 in cells_by_row:
                    table_data["headers"] = [
                        cells_by_row[0].get(col, "") 
                        for col in range(max_col + 1)
                    ]
                
                # Extract all rows
                for row_idx in sorted(cells_by_row.keys()):
                    row_data = [
                        cells_by_row[row_idx].get(col, "") 
                        for col in range(max_col + 1)
                    ]
                    table_data["rows"].append(row_data)
                
                table_data["row_count"] = len(cells_by_row)
                table_data["column_count"] = max_col + 1
        
        except Exception as e:
            logger.warning(f"Error processing table: {e}")
        
        return table_data
    
    def _extract_kvp_with_patterns(self, text: str) -> Dict[str, str]:
        """Extract key-value pairs using pattern matching."""
        kvp = {}
        
        # Enhanced patterns for insurance documents
        patterns = [
            (r"Policy\s*(?:Number|ID)[\s:]+([A-Z0-9\-]+)", "policy_number"),
            (r"Claim\s*(?:Number|ID)[\s:]+([A-Z0-9\-]+)", "claim_number"),
            (r"Policyholder[\s:]+([A-Za-z\s]+?)(?:\n|$)", "policyholder"),
            (r"Insured[\s:]+([A-Za-z\s]+?)(?:\n|$)", "insured"),
            (r"(?:Property\s+)?Address[\s:]+([^\n]+?)(?:\n|$)", "address"),
            (r"Policy\s+Term[\s:]+([^\n]+?)(?:\n|$)", "policy_term"),
            (r"Coverage\s+Type[\s:]+([^\n]+?)(?:\n|$)", "coverage_type"),
            (r"Deductible[\s:]+\$?([\d,]+)", "deductible"),
            (r"Premium[\s:]+\$?([\d,]+)", "premium"),
            (r"Date\s+of\s+Loss[\s:]+([^\n]+?)(?:\n|$)", "loss_date"),
            (r"Effective\s+Date[\s:]+([^\n]+?)(?:\n|$)", "effective_date"),
            (r"Expiration\s+Date[\s:]+([^\n]+?)(?:\n|$)", "expiration_date"),
        ]
        
        for pattern, key in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                kvp[key] = matches[0].strip()
        
        # Extract coverage amounts
        coverage_patterns = [
            (r"Dwelling\s+Coverage[^$]*\$?([\d,]+)", "dwelling_coverage"),
            (r"Personal\s+Property[^$]*\$?([\d,]+)", "personal_property"),
            (r"Liability[^$]*\$?([\d,]+)", "liability_coverage"),
            (r"Medical\s+Payments?[^$]*\$?([\d,]+)", "medical_coverage"),
        ]
        
        for pattern, key in coverage_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                kvp[key] = matches[0]
        
        return kvp
    
    def _detect_document_type(self, text: str, kvp: Dict[str, str]) -> str:
        """Detect the type of insurance document."""
        text_lower = text.lower()
        
        # Check for specific document indicators
        if "claim" in kvp or "claim_number" in kvp:
            return "claim"
        elif "policy" in kvp or "policy_number" in kvp:
            return "policy"
        elif "claim" in text_lower and ("loss" in text_lower or "incident" in text_lower):
            return "claim"
        elif "coverage" in text_lower and ("premium" in text_lower or "deductible" in text_lower):
            return "policy"
        elif "faq" in text_lower or "frequently asked" in text_lower:
            return "faq"
        else:
            return "unknown"
    
    def _create_structured_sections(self, text: str, document_type: str) -> Dict[str, str]:
        """Create structured sections based on document type."""
        sections = {}
        
        if document_type == "policy":
            sections = self._extract_policy_sections(text)
        elif document_type == "claim":
            sections = self._extract_claim_sections(text)
        else:
            # Generic section extraction
            sections = self._extract_generic_sections(text)
        
        return sections
    
    def _extract_policy_sections(self, text: str) -> Dict[str, str]:
        """Extract policy-specific sections."""
        sections = {}
        
        # Policy section patterns
        patterns = [
            (r"(?:COVERAGE|INSURING AGREEMENT|WHAT (?:WE|IS) COVER)[\s:]*([^\\n]*(?:\\n(?!(?:EXCLUSION|CONDITION|LIMIT))[^\\n]*)*)", "coverage"),
            (r"(?:EXCLUSIONS?|WHAT (?:WE|IS) (?:DON'T|NOT) COVER)[\s:]*([^\\n]*(?:\\n(?!(?:COVERAGE|CONDITION|LIMIT))[^\\n]*)*)", "exclusions"),
            (r"(?:CONDITIONS?|POLICY CONDITIONS?)[\s:]*([^\\n]*(?:\\n(?!(?:COVERAGE|EXCLUSION|LIMIT))[^\\n]*)*)", "conditions"),
            (r"(?:DEDUCTIBLES?|YOUR DEDUCTIBLE)[\s:]*([^\\n]*(?:\\n(?!(?:COVERAGE|EXCLUSION|CONDITION))[^\\n]*)*)", "deductible"),
            (r"(?:DEFINITIONS?|DEFINED TERMS?)[\s:]*([^\\n]*(?:\\n(?!(?:COVERAGE|EXCLUSION|CONDITION))[^\\n]*)*)", "definitions"),
        ]
        
        for pattern, section_name in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if matches:
                sections[section_name] = matches[0][:2000]  # Limit section size
        
        return sections
    
    def _extract_claim_sections(self, text: str) -> Dict[str, str]:
        """Extract claim-specific sections."""
        sections = {}
        
        # Claim section patterns
        patterns = [
            (r"(?:CLAIM (?:INFORMATION|DETAILS?)|CLAIM SUMMARY)[\s:]*([^\\n]*(?:\\n(?!(?:LOSS|SETTLEMENT|ADJUSTER))[^\\n]*)*)", "claim_info"),
            (r"(?:LOSS (?:DESCRIPTION|DETAILS?)|INCIDENT DESCRIPTION)[\s:]*([^\\n]*(?:\\n(?!(?:CLAIM|SETTLEMENT|ADJUSTER))[^\\n]*)*)", "loss_description"),
            (r"(?:ADJUSTER (?:NOTES?|COMMENTS?)|INVESTIGATION)[\s:]*([^\\n]*(?:\\n(?!(?:CLAIM|LOSS|SETTLEMENT))[^\\n]*)*)", "adjuster_notes"),
            (r"(?:SETTLEMENT|PAYMENT|PAYOUT)[\s:]*([^\\n]*(?:\\n(?!(?:CLAIM|LOSS|ADJUSTER))[^\\n]*)*)", "settlement"),
        ]
        
        for pattern, section_name in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if matches:
                sections[section_name] = matches[0][:1500]  # Limit section size
        
        return sections
    
    def _extract_generic_sections(self, text: str) -> Dict[str, str]:
        """Extract generic document sections."""
        sections = {}
        
        # Split by common section markers
        lines = text.split('\n')
        current_section = "introduction"
        current_content = []
        
        section_markers = [
            r"^([A-Z][A-Z\s]{10,})\s*$",  # All caps headers
            r"^\d+\.\s*([A-Z][A-Za-z\s,&]+)$",  # Numbered sections
            r"^([A-Z][A-Za-z\s,&]{5,}):?\s*$",  # Title case headers
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a section header
            is_header = False
            for pattern in section_markers:
                match = re.match(pattern, line)
                if match and len(line) < 100:  # Reasonable header length
                    # Save previous section
                    if current_content:
                        sections[current_section] = '\n'.join(current_content)
                    
                    # Start new section
                    current_section = re.sub(r'[^a-zA-Z0-9]+', '_', match.group(1).lower())
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_simple_tables(self, text: str) -> List[Dict[str, Any]]:
        """Extract simple tables using pattern matching."""
        tables = []
        
        # Look for tabular data patterns
        lines = text.split('\n')
        table_lines = []
        in_table = False
        
        for line in lines:
            # Detect table-like content (multiple dollar amounts, or consistent separators)
            if re.search(r'\$[\d,]+.*\$[\d,]+', line) or line.count('|') >= 2 or line.count('\t') >= 2:
                table_lines.append(line)
                in_table = True
            elif in_table and line.strip():
                table_lines.append(line)
            elif in_table:
                # End of table
                if len(table_lines) >= 2:
                    table_data = self._parse_simple_table(table_lines)
                    if table_data:
                        tables.append(table_data)
                table_lines = []
                in_table = False
        
        # Handle table at end of document
        if table_lines and len(table_lines) >= 2:
            table_data = self._parse_simple_table(table_lines)
            if table_data:
                tables.append(table_data)
        
        return tables
    
    def _parse_simple_table(self, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Parse simple table from lines."""
        if not lines:
            return None
        
        try:
            # Try to split on common separators
            separators = ['|', '\t', '  ']  # Multiple spaces
            
            for sep in separators:
                if all(sep in line for line in lines[:2]):  # Check first 2 lines
                    rows = []
                    for line in lines:
                        row = [cell.strip() for cell in line.split(sep) if cell.strip()]
                        if row:
                            rows.append(row)
                    
                    if rows:
                        return {
                            "headers": rows[0] if len(rows) > 1 else [],
                            "rows": rows[1:] if len(rows) > 1 else rows,
                            "row_count": len(rows),
                            "column_count": len(rows[0]) if rows else 0
                        }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing simple table: {e}")
            return None
    
    async def _enhance_with_insurance_analysis(self, result: FormRecognizerResult) -> FormRecognizerResult:
        """Enhance result with insurance-specific analysis."""
        try:
            # Add insurance-specific confidence scoring
            enhanced_confidence = {}
            
            for key, value in result.key_value_pairs.items():
                # Calculate confidence based on pattern matching and completeness
                confidence = self._calculate_field_confidence(key, value, result.content)
                enhanced_confidence[key] = confidence
            
            # Update confidence scores
            result.confidence_scores.update(enhanced_confidence)
            
            # Extract additional insurance metrics
            insurance_metrics = self._extract_insurance_metrics(result.content)
            result.key_value_pairs.update(insurance_metrics)
            
            return result
            
        except Exception as e:
            logger.error(f"Error enhancing with insurance analysis: {e}")
            return result
    
    def _calculate_field_confidence(self, key: str, value: str, content: str) -> float:
        """Calculate confidence score for extracted field."""
        try:
            base_confidence = 0.7
            
            # Higher confidence for complete values
            if len(value) > 5:
                base_confidence += 0.1
            
            # Higher confidence for expected formats
            if key in ["policy_number", "claim_number"] and re.match(r'^[A-Z0-9\-]{6,}$', value):
                base_confidence += 0.2
            
            # Higher confidence for monetary values with proper format
            if key.endswith("_coverage") or key == "premium" and re.match(r'^\d{1,3}(,\d{3})*$', value):
                base_confidence += 0.1
            
            # Lower confidence if value appears multiple times (might be wrong extraction)
            if content.count(value) > 3:
                base_confidence -= 0.1
            
            return min(1.0, max(0.0, base_confidence))
            
        except Exception:
            return 0.5
    
    def _extract_insurance_metrics(self, content: str) -> Dict[str, str]:
        """Extract additional insurance-specific metrics."""
        metrics = {}
        
        # Extract coverage amounts with more sophisticated patterns
        coverage_patterns = [
            (r"Total\s+Coverage[^$]*\$?([\d,]+)", "total_coverage"),
            (r"Annual\s+Premium[^$]*\$?([\d,]+)", "annual_premium"),
            (r"Claim\s+Amount[^$]*\$?([\d,]+)", "claim_amount"),
            (r"Settlement\s+Amount[^$]*\$?([\d,]+)", "settlement_amount"),
            (r"Deductible[^$]*\$?([\d,]+)", "deductible_amount"),
        ]
        
        for pattern, key in coverage_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                metrics[key] = matches[0]
        
        return metrics