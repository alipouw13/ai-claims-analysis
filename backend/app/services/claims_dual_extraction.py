"""
Dual-Extraction Pipeline for Claims Processing

This module implements the Microsoft Content Processing Solution Accelerator approach
with dual extraction: Azure AI Content Understanding + GPT-4o Vision mapping to schema.

The pipeline follows these steps:
1. Extract Pipeline - Azure AI Content Understanding for text extraction
2. Map Pipeline - GPT-4o vision for schema mapping 
3. Evaluate Pipeline - Confidence scoring and comparison
4. Save Pipeline - Store best performing results
"""

import logging
import json
import base64
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.schemas.claim_schema import InsuranceClaim
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from either Azure AI Content Understanding or GPT-4o Vision extraction."""
    extraction_method: str  # "azure_ai_content_understanding" or "gpt4o_vision"
    extracted_data: Dict[str, Any]
    confidence_score: float
    processing_time: float
    error_message: Optional[str] = None
    raw_response: Optional[str] = None


@dataclass
class DualExtractionResult:
    """Combined result from both extraction methods."""
    azure_ai_result: ExtractionResult
    gpt4o_result: ExtractionResult
    final_result: ExtractionResult
    confidence_comparison: Dict[str, Any]
    processing_metadata: Dict[str, Any]


class ClaimsDualExtractionPipeline:
    """
    Implements the dual-extraction pipeline for claims documents following the
    Microsoft Content Processing Solution Accelerator approach.
    """
    
    def __init__(self, azure_manager: AzureServiceManager):
        self.azure_manager = azure_manager
        self.claim_schema = InsuranceClaim
        
    async def process_claim_document(
        self, 
        content: bytes, 
        content_type: str,
        document_images: Optional[List[bytes]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DualExtractionResult:
        """
        Process a claim document using dual extraction pipeline.
        
        Args:
            content: Raw document bytes
            content_type: MIME type of the document  
            document_images: Optional list of document page images
            metadata: Optional additional metadata
            
        Returns:
            DualExtractionResult with both extractions and final result
        """
        logger.info("=== STARTING DUAL EXTRACTION PIPELINE ===")
        
        try:
            # Step 1: Extract Pipeline - Azure AI Content Understanding
            logger.info("Step 1: Azure AI Content Understanding extraction...")
            azure_ai_result = await self._extract_with_azure_ai_content_understanding(
                content, content_type
            )
            logger.info(f"Azure AI extraction complete: confidence={azure_ai_result.confidence_score:.3f}")
            
            # Step 2: Map Pipeline - GPT-4o Vision with schema mapping
            logger.info("Step 2: GPT-4o Vision schema mapping...")
            gpt4o_result = await self._extract_with_gpt4o_vision(
                content, content_type, document_images, azure_ai_result.extracted_data
            )
            logger.info(f"GPT-4o extraction complete: confidence={gpt4o_result.confidence_score:.3f}")
            
            # Step 3: Evaluate Pipeline - Compare and score results
            logger.info("Step 3: Evaluating and comparing results...")
            confidence_comparison = await self._evaluate_extraction_results(
                azure_ai_result, gpt4o_result
            )
            logger.info(f"Evaluation complete: best_method={confidence_comparison['best_method']}")
            
            # Step 4: Save Pipeline - Choose best result and prepare final output
            logger.info("Step 4: Selecting best extraction result...")
            final_result = await self._select_best_extraction(
                azure_ai_result, gpt4o_result, confidence_comparison
            )
            logger.info(f"Final result selected: method={final_result.extraction_method}, confidence={final_result.confidence_score:.3f}")
            
            # Create combined result
            dual_result = DualExtractionResult(
                azure_ai_result=azure_ai_result,
                gpt4o_result=gpt4o_result,
                final_result=final_result,
                confidence_comparison=confidence_comparison,
                processing_metadata={
                    "processed_at": datetime.utcnow().isoformat(),
                    "content_type": content_type,
                    "content_size": len(content),
                    "has_images": document_images is not None and len(document_images) > 0,
                    "total_processing_time": azure_ai_result.processing_time + gpt4o_result.processing_time
                }
            )
            
            logger.info("=== DUAL EXTRACTION PIPELINE COMPLETE ===")
            return dual_result
            
        except Exception as e:
            logger.error(f"Error in dual extraction pipeline: {e}")
            # Return a fallback result
            return self._create_fallback_result(str(e))
    
    async def _extract_with_azure_ai_content_understanding(
        self, 
        content: bytes, 
        content_type: str
    ) -> ExtractionResult:
        """
        Extract text and structure using Azure AI Content Understanding Service.
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("Calling Azure AI Content Understanding Service...")
            
            # Use Azure Document Intelligence for structured extraction
            if (self.azure_manager and 
                getattr(self.azure_manager, 'form_recognizer_client', None) and 
                settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT.startswith("https://")):
                
                # Call Azure Document Intelligence
                azure_result = await self.azure_manager.analyze_document(content, content_type)
                
                # Convert Azure result to claim schema format
                claim_data = await self._convert_azure_ai_to_claim_schema(azure_result)
                
                # Calculate confidence based on completeness and quality
                confidence = self._calculate_azure_ai_confidence(azure_result, claim_data)
                
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                return ExtractionResult(
                    extraction_method="azure_ai_content_understanding",
                    extracted_data=claim_data,
                    confidence_score=confidence,
                    processing_time=processing_time,
                    raw_response=json.dumps(azure_result, default=str)
                )
            else:
                # Fallback when Azure Document Intelligence not available
                logger.warning("Azure Document Intelligence not configured, using fallback extraction")
                
                # Use basic text extraction as fallback
                from app.utils.policy_claim_chunker import extract_text_from_bytes
                text = extract_text_from_bytes(content, content_type)
                
                # Basic pattern-based extraction
                claim_data = await self._extract_basic_claim_data(text)
                
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                return ExtractionResult(
                    extraction_method="azure_ai_content_understanding_fallback",
                    extracted_data=claim_data,
                    confidence_score=0.4,  # Lower confidence for fallback
                    processing_time=processing_time,
                    raw_response=text[:1000]  # First 1000 chars as raw response
                )
                
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Error in Azure AI Content Understanding extraction: {e}")
            
            return ExtractionResult(
                extraction_method="azure_ai_content_understanding",
                extracted_data={},
                confidence_score=0.0,
                processing_time=processing_time,
                error_message=str(e)
            )
    
    async def _extract_with_gpt4o_vision(
        self,
        content: bytes,
        content_type: str, 
        document_images: Optional[List[bytes]],
        azure_context: Dict[str, Any]
    ) -> ExtractionResult:
        """
        Extract claim data using GPT-4o vision capabilities with schema mapping.
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("Starting GPT-4o vision extraction with schema mapping...")
            
            # Get the schema definition for the prompt
            schema_definition = self._get_claim_schema_definition()
            
            # Create extraction prompt
            extraction_prompt = self._create_gpt4o_extraction_prompt(schema_definition, azure_context)
            
            # Prepare images for vision analysis
            image_data = await self._prepare_images_for_vision(content, content_type, document_images)
            
            # Call GPT-4o vision
            gpt4o_response = await self._call_gpt4o_vision(extraction_prompt, image_data)
            
            # Parse the response into claim schema format
            claim_data = await self._parse_gpt4o_response(gpt4o_response)
            
            # Calculate confidence based on completeness and consistency
            confidence = self._calculate_gpt4o_confidence(claim_data, gpt4o_response)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ExtractionResult(
                extraction_method="gpt4o_vision",
                extracted_data=claim_data,
                confidence_score=confidence,
                processing_time=processing_time,
                raw_response=gpt4o_response
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Error in GPT-4o vision extraction: {e}")
            
            return ExtractionResult(
                extraction_method="gpt4o_vision",
                extracted_data={},
                confidence_score=0.0,
                processing_time=processing_time,
                error_message=str(e)
            )
    
    async def _convert_azure_ai_to_claim_schema(self, azure_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Azure AI Content Understanding result to claim schema format.
        """
        try:
            claim_data = {}
            
            # Extract key-value pairs from Azure result
            key_value_pairs = azure_result.get("key_value_pairs", {})
            content = azure_result.get("content", "")
            
            # Map common fields from key-value pairs
            field_mappings = {
                "claim_number": ["claim number", "claim_number", "claim id", "claim_id"],
                "policy_number": ["policy number", "policy_number", "policy id", "policy_id"],
                "insured_name": ["insured", "insured name", "policyholder", "claimant"],
                "loss_date": ["date of loss", "loss date", "incident date", "date_of_loss"],
                "report_date": ["report date", "reported date", "claim date"],
                "loss_description": ["description", "loss description", "incident description"],
                "cause_of_loss": ["cause of loss", "peril", "cause"],
                "claim_amount_requested": ["amount", "claim amount", "requested amount"],
                "deductible": ["deductible"],
                "adjuster_name": ["adjuster", "adjuster name"],
                "claim_status": ["status", "claim status"]
            }
            
            # Extract mapped fields
            for schema_field, azure_keys in field_mappings.items():
                for azure_key in azure_keys:
                    if azure_key in key_value_pairs:
                        value = key_value_pairs[azure_key]
                        # Clean and format the value
                        claim_data[schema_field] = self._clean_extracted_value(value, schema_field)
                        break
            
            # Extract financial amounts using patterns
            financial_patterns = {
                "claim_amount_requested": [r"amount[:\s]*\$?([\d,]+(?:\.\d{2})?)", r"claim[:\s]*\$?([\d,]+(?:\.\d{2})?)"],
                "deductible": [r"deductible[:\s]*\$?([\d,]+(?:\.\d{2})?)", r"ded[:\s]*\$?([\d,]+(?:\.\d{2})?)"],
                "claim_amount_paid": [r"paid[:\s]*\$?([\d,]+(?:\.\d{2})?)", r"payment[:\s]*\$?([\d,]+(?:\.\d{2})?)"]
            }
            
            for field, patterns in financial_patterns.items():
                if field not in claim_data:
                    for pattern in patterns:
                        import re
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            try:
                                # Clean and convert to float
                                amount_str = matches[0].replace(",", "")
                                claim_data[field] = float(amount_str)
                                break
                            except ValueError:
                                continue
            
            # Extract addresses from text
            address_patterns = {
                "insured_address": [r"(?:insured|policyholder|claimant)\s+address[:\s]*([^\n]+)", r"mailing\s+address[:\s]*([^\n]+)"],
                "loss_location": [r"(?:loss|incident|property)\s+(?:location|address)[:\s]*([^\n]+)", r"premises[:\s]*([^\n]+)"]
            }
            
            for field, patterns in address_patterns.items():
                for pattern in patterns:
                    import re
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        # Parse address into components
                        address_str = matches[0].strip()
                        address_dict = self._parse_address_string(address_str)
                        if address_dict:
                            claim_data[field] = address_dict
                        break
            
            logger.info(f"Converted Azure AI result to claim schema: {len(claim_data)} fields extracted")
            return claim_data
            
        except Exception as e:
            logger.error(f"Error converting Azure AI result: {e}")
            return {}
    
    async def _extract_basic_claim_data(self, text: str) -> Dict[str, Any]:
        """
        Extract basic claim data using pattern matching as fallback.
        """
        try:
            import re
            claim_data = {}
            
            # Basic patterns for key claim fields
            patterns = {
                "claim_number": [r"claim\s*(?:number|id|#)[:\s]*([A-Z0-9\-]+)", r"claim[:\s]*([A-Z0-9\-]+)"],
                "policy_number": [r"policy\s*(?:number|id|#)[:\s]*([A-Z0-9\-]+)", r"policy[:\s]*([A-Z0-9\-]+)"],
                "insured_name": [r"insured[:\s]*([A-Za-z\s]+?)(?:\n|$)", r"policyholder[:\s]*([A-Za-z\s]+?)(?:\n|$)"],
                "loss_date": [r"(?:date\s+of\s+loss|loss\s+date)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", r"incident\s+date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"],
                "loss_description": [r"(?:description|details)[:\s]*([^\n]{20,200})", r"what\s+happened[:\s]*([^\n]{20,200})"],
                "claim_amount_requested": [r"(?:amount|total)[:\s]*\$?([\d,]+(?:\.\d{2})?)", r"claim[:\s]*\$?([\d,]+(?:\.\d{2})?)"]
            }
            
            for field, field_patterns in patterns.items():
                for pattern in field_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        value = matches[0].strip()
                        claim_data[field] = self._clean_extracted_value(value, field)
                        break
            
            logger.info(f"Basic claim data extraction: {len(claim_data)} fields found")
            return claim_data
            
        except Exception as e:
            logger.error(f"Error in basic claim data extraction: {e}")
            return {}
    
    def _clean_extracted_value(self, value: str, field_type: str) -> Any:
        """
        Clean and format extracted values based on field type.
        """
        try:
            if not value:
                return None
                
            value = value.strip()
            
            # Handle financial amounts
            if field_type in ["claim_amount_requested", "claim_amount_paid", "claim_amount_reserved", "deductible", "policy_limits"]:
                # Remove currency symbols and convert to float
                import re
                numeric_value = re.sub(r'[^\d.]', '', value)
                if numeric_value:
                    return float(numeric_value)
                return None
            
            # Handle dates
            if field_type in ["loss_date", "report_date", "date_closed"]:
                # Try to normalize date format
                import re
                from datetime import datetime
                
                # Common date patterns
                date_patterns = [
                    r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',  # MM/DD/YYYY
                    r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})',  # YYYY/MM/DD
                    r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})'   # MM/DD/YY
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, value)
                    if match:
                        try:
                            if len(match.group(3)) == 4:  # Full year
                                if '/' in value and value.index('/') < 3:  # MM/DD/YYYY format
                                    parsed_date = datetime.strptime(f"{match.group(1)}/{match.group(2)}/{match.group(3)}", "%m/%d/%Y")
                                else:  # YYYY/MM/DD format
                                    parsed_date = datetime.strptime(f"{match.group(1)}/{match.group(2)}/{match.group(3)}", "%Y/%m/%d")
                            else:  # 2-digit year
                                parsed_date = datetime.strptime(f"{match.group(1)}/{match.group(2)}/{match.group(3)}", "%m/%d/%y")
                            return parsed_date.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
                
                return value  # Return original if no pattern matches
            
            # Handle names - capitalize properly
            if field_type in ["insured_name", "adjuster_name"]:
                return value.title()
            
            # Handle status fields - normalize
            if field_type == "claim_status":
                status_value = value.lower()
                status_mappings = {
                    "open": "open",
                    "closed": "closed", 
                    "pending": "pending",
                    "denied": "denied",
                    "settled": "closed",
                    "approved": "open"
                }
                return status_mappings.get(status_value, value)
            
            return value
            
        except Exception as e:
            logger.warning(f"Error cleaning value '{value}' for field '{field_type}': {e}")
            return value
    
    def _parse_address_string(self, address_str: str) -> Optional[Dict[str, str]]:
        """
        Parse an address string into components.
        """
        try:
            import re
            
            # Simple address parsing
            address_dict = {
                "street": None,
                "city": None, 
                "state": None,
                "postal_code": None,
                "country": "USA"  # Default
            }
            
            # Try to extract ZIP code
            zip_pattern = r'(\d{5}(?:-\d{4})?)\s*$'
            zip_match = re.search(zip_pattern, address_str)
            if zip_match:
                address_dict["postal_code"] = zip_match.group(1)
                address_str = address_str[:zip_match.start()].strip()
            
            # Try to extract state (2-letter abbreviation)
            state_pattern = r'\b([A-Z]{2})\s*$'
            state_match = re.search(state_pattern, address_str)
            if state_match:
                address_dict["state"] = state_match.group(1)
                address_str = address_str[:state_match.start()].strip()
            
            # Split remaining into street and city
            parts = address_str.split(',')
            if len(parts) >= 2:
                address_dict["street"] = parts[0].strip()
                address_dict["city"] = parts[1].strip()
            elif len(parts) == 1:
                # Assume it's all street address
                address_dict["street"] = parts[0].strip()
            
            # Return only if we got meaningful data
            if any(address_dict.values()):
                return address_dict
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing address '{address_str}': {e}")
            return None
    
    def _get_claim_schema_definition(self) -> str:
        """
        Get the claim schema definition for GPT-4o prompt.
        """
        return """
        You are extracting data from an insurance claim document into this JSON schema:
        
        {
            "claim_number": "Unique claim identifier (e.g., CLM-2024-001234)",
            "policy_number": "Insurance policy number (e.g., POL-987654321)",
            "insured_name": "Name of the insured party",
            "insured_address": {
                "street": "Street address",
                "city": "City name", 
                "state": "State abbreviation",
                "postal_code": "ZIP code",
                "country": "Country"
            },
            "loss_date": "Date when loss occurred (YYYY-MM-DD format)",
            "report_date": "Date when claim was reported (YYYY-MM-DD format)",
            "loss_location": {
                "street": "Where loss occurred",
                "city": "City",
                "state": "State", 
                "postal_code": "ZIP",
                "country": "Country"
            },
            "loss_description": "Detailed description of what happened",
            "cause_of_loss": "Primary cause (e.g., fire, theft, water damage)",
            "claim_amount_requested": 25000.00,
            "claim_amount_paid": 15000.00,
            "deductible": 1000.00,
            "coverage_type": "Type of coverage (e.g., dwelling, auto, liability)",
            "adjuster_name": "Name of assigned adjuster",
            "claim_status": "Status (open, closed, pending, denied)",
            "investigation_notes": "Adjuster notes and findings"
        }
        
        Extract ONLY the data that is clearly visible in the document. 
        If a field is not present or unclear, set it to null.
        Return ONLY valid JSON with the extracted data.
        """
    
    def _create_gpt4o_extraction_prompt(self, schema_definition: str, azure_context: Dict[str, Any]) -> str:
        """
        Create the extraction prompt for GPT-4o vision.
        """
        context_info = ""
        if azure_context:
            context_info = f"\nAdditional context from text extraction:\n{json.dumps(azure_context, indent=2)[:500]}"
        
        return f"""
        {schema_definition}
        
        Analyze the insurance claim document image(s) and extract the information according to the schema above.
        
        Important instructions:
        1. Look carefully at forms, tables, and handwritten text
        2. Extract exact values as they appear in the document
        3. For dates, use YYYY-MM-DD format
        4. For monetary amounts, use decimal format (e.g., 15000.00)
        5. If text is unclear or missing, use null instead of guessing
        6. Return ONLY the JSON object, no additional text
        
        {context_info}
        
        JSON:
        """
    
    async def _prepare_images_for_vision(
        self, 
        content: bytes, 
        content_type: str,
        document_images: Optional[List[bytes]]
    ) -> List[str]:
        """
        Prepare document images for GPT-4o vision analysis.
        """
        try:
            images = []
            
            # If images are provided directly, use them
            if document_images:
                for img_bytes in document_images:
                    b64_image = base64.b64encode(img_bytes).decode('utf-8')
                    images.append(b64_image)
                logger.info(f"Using {len(images)} provided document images")
                return images
            
            # If it's a PDF, try to convert pages to images
            if content_type and "pdf" in content_type.lower():
                try:
                    import fitz  # PyMuPDF
                    
                    pdf_doc = fitz.open(stream=content, filetype="pdf")
                    
                    # Convert first few pages to images (limit to 5 for performance)
                    max_pages = min(5, len(pdf_doc))
                    
                    for page_num in range(max_pages):
                        page = pdf_doc[page_num]
                        # Convert to image
                        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x zoom for clarity
                        img_data = pix.tobytes("png")
                        
                        b64_image = base64.b64encode(img_data).decode('utf-8')
                        images.append(b64_image)
                    
                    pdf_doc.close()
                    logger.info(f"Converted {len(images)} PDF pages to images")
                    
                except ImportError:
                    logger.warning("PyMuPDF not available, cannot convert PDF to images")
                except Exception as e:
                    logger.warning(f"Error converting PDF to images: {e}")
            
            # If it's already an image, use it directly
            elif content_type and any(img_type in content_type.lower() for img_type in ["image", "png", "jpg", "jpeg"]):
                b64_image = base64.b64encode(content).decode('utf-8')
                images.append(b64_image)
                logger.info("Using document as single image")
            
            return images
            
        except Exception as e:
            logger.error(f"Error preparing images for vision: {e}")
            return []
    
    async def _call_gpt4o_vision(self, prompt: str, images: List[str]) -> str:
        """
        Call GPT-4o vision API with document images.
        """
        try:
            if not images:
                logger.warning("No images available for GPT-4o vision analysis")
                return "{}"
            
            # Prepare messages for vision API
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert insurance claims processor. Extract data accurately from claim documents and return only valid JSON."
                },
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt}
                    ] + [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img}",
                                "detail": "high"
                            }
                        } for img in images[:4]  # Limit to 4 images for API limits
                    ]
                }
            ]
            
            # Get deployment name from settings
            deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
            if not deployment_name:
                logger.error("No Azure OpenAI deployment configured")
                return "{}"
            
            # Call Azure OpenAI
            logger.info(f"Calling GPT-4o vision with {len(images)} images...")
            response = await self.azure_manager.openai_client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                temperature=0.1,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"GPT-4o vision response received: {len(result)} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling GPT-4o vision: {e}")
            return "{}"
    
    async def _parse_gpt4o_response(self, response: str) -> Dict[str, Any]:
        """
        Parse GPT-4o response into structured claim data.
        """
        try:
            # Clean up the response
            response = response.strip()
            
            # Remove any markdown formatting
            if response.startswith("```json"):
                response = response[7:-3]
            elif response.startswith("```"):
                response = response[3:-3]
            
            # Parse JSON
            claim_data = json.loads(response)
            
            logger.info(f"Parsed GPT-4o response: {len(claim_data)} fields extracted")
            return claim_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing GPT-4o JSON response: {e}")
            logger.error(f"Problematic response: {response[:500]}...")
            return {}
        except Exception as e:
            logger.error(f"Error processing GPT-4o response: {e}")
            return {}
    
    def _calculate_azure_ai_confidence(self, azure_result: Dict[str, Any], claim_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score for Azure AI extraction.
        """
        try:
            confidence = 0.5  # Base confidence
            
            # Boost for having key-value pairs
            if azure_result.get("key_value_pairs"):
                confidence += 0.2
            
            # Boost for structured data extraction
            if azure_result.get("tables"):
                confidence += 0.1
            
            # Boost based on extracted claim fields
            important_fields = ["claim_number", "policy_number", "insured_name", "loss_date", "loss_description"]
            found_fields = sum(1 for field in important_fields if field in claim_data and claim_data[field])
            confidence += (found_fields / len(important_fields)) * 0.2
            
            return min(1.0, confidence)
            
        except Exception as e:
            logger.warning(f"Error calculating Azure AI confidence: {e}")
            return 0.5
    
    def _calculate_gpt4o_confidence(self, claim_data: Dict[str, Any], raw_response: str) -> float:
        """
        Calculate confidence score for GPT-4o extraction.
        """
        try:
            confidence = 0.6  # Base confidence (higher for vision)
            
            # Boost based on completeness
            total_fields = 15  # Important fields we expect
            filled_fields = sum(1 for value in claim_data.values() if value is not None and value != "")
            completeness_score = filled_fields / total_fields
            confidence += completeness_score * 0.3
            
            # Boost for critical fields
            critical_fields = ["claim_number", "policy_number", "insured_name", "loss_date"]
            critical_found = sum(1 for field in critical_fields if field in claim_data and claim_data[field])
            confidence += (critical_found / len(critical_fields)) * 0.1
            
            return min(1.0, confidence)
            
        except Exception as e:
            logger.warning(f"Error calculating GPT-4o confidence: {e}")
            return 0.6
    
    async def _evaluate_extraction_results(
        self, 
        azure_result: ExtractionResult, 
        gpt4o_result: ExtractionResult
    ) -> Dict[str, Any]:
        """
        Compare and evaluate both extraction results.
        """
        try:
            # Compare confidence scores
            confidence_comparison = {
                "azure_ai_confidence": azure_result.confidence_score,
                "gpt4o_confidence": gpt4o_result.confidence_score,
                "confidence_difference": abs(azure_result.confidence_score - gpt4o_result.confidence_score),
                "best_method": "gpt4o_vision" if gpt4o_result.confidence_score > azure_result.confidence_score else "azure_ai_content_understanding"
            }
            
            # Compare field completeness
            azure_fields = len([v for v in azure_result.extracted_data.values() if v is not None and v != ""])
            gpt4o_fields = len([v for v in gpt4o_result.extracted_data.values() if v is not None and v != ""])
            
            confidence_comparison.update({
                "azure_ai_fields_count": azure_fields,
                "gpt4o_fields_count": gpt4o_fields,
                "field_count_winner": "gpt4o_vision" if gpt4o_fields > azure_fields else "azure_ai_content_understanding"
            })
            
            # Overall recommendation
            if confidence_comparison["confidence_difference"] < 0.1:
                # Close confidence scores - prefer the one with more fields
                confidence_comparison["recommendation"] = confidence_comparison["field_count_winner"]
            else:
                # Clear confidence winner
                confidence_comparison["recommendation"] = confidence_comparison["best_method"]
            
            return confidence_comparison
            
        except Exception as e:
            logger.error(f"Error evaluating extraction results: {e}")
            return {
                "best_method": "gpt4o_vision",
                "recommendation": "gpt4o_vision",
                "error": str(e)
            }
    
    async def _select_best_extraction(
        self,
        azure_result: ExtractionResult,
        gpt4o_result: ExtractionResult, 
        confidence_comparison: Dict[str, Any]
    ) -> ExtractionResult:
        """
        Select the best extraction result based on evaluation.
        """
        try:
            recommended_method = confidence_comparison.get("recommendation", "gpt4o_vision")
            
            if recommended_method == "gpt4o_vision":
                logger.info("Selected GPT-4o vision result as final extraction")
                return gpt4o_result
            else:
                logger.info("Selected Azure AI Content Understanding result as final extraction")
                return azure_result
                
        except Exception as e:
            logger.error(f"Error selecting best extraction: {e}")
            # Default to GPT-4o result
            return gpt4o_result
    
    def _create_fallback_result(self, error_message: str) -> DualExtractionResult:
        """
        Create a fallback result when the pipeline fails.
        """
        fallback_extraction = ExtractionResult(
            extraction_method="fallback",
            extracted_data={},
            confidence_score=0.0,
            processing_time=0.0,
            error_message=error_message
        )
        
        return DualExtractionResult(
            azure_ai_result=fallback_extraction,
            gpt4o_result=fallback_extraction,
            final_result=fallback_extraction,
            confidence_comparison={"error": error_message},
            processing_metadata={
                "processed_at": datetime.utcnow().isoformat(),
                "pipeline_failed": True,
                "error": error_message
            }
        )