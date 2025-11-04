"""
Test script for the new dual-extraction pipeline for claims processing.

This script tests the implementation that replaces placeholder values like 
"$10,000, general claim and invalid date" with actual extracted data from claim documents.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.claims_dual_extraction import ClaimsDualExtractionPipeline
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_dual_extraction_pipeline():
    """
    Test the dual-extraction pipeline with a sample claim document.
    """
    logger.info("=== TESTING DUAL-EXTRACTION PIPELINE ===")
    
    try:
        # Initialize Azure service manager
        azure_manager = AzureServiceManager()
        
        # Initialize dual extraction pipeline
        dual_extractor = ClaimsDualExtractionPipeline(azure_manager)
        
        # Create a sample claim document text (simulating extracted text)
        sample_claim_text = """
        INSURANCE CLAIM FORM
        
        Claim Number: CLM-2024-12345
        Policy Number: POL-987654321
        
        INSURED INFORMATION:
        Name: John and Mary Smith
        Address: 123 Main Street, Springfield, IL 62701
        Phone: (555) 123-4567
        
        LOSS INFORMATION:
        Date of Loss: 10/15/2024
        Time of Loss: 2:30 PM
        Location of Loss: 123 Main Street, Springfield, IL 62701
        
        DESCRIPTION OF LOSS:
        Water damage occurred in the kitchen due to a burst pipe under the sink. 
        The water damaged the kitchen cabinets, flooring, and some appliances.
        The homeowner noticed water pooling on the floor and immediately shut off 
        the main water supply.
        
        CAUSE OF LOSS: Water Damage - Burst Pipe
        
        ESTIMATED DAMAGE:
        Kitchen Cabinets: $5,000
        Flooring Replacement: $3,500
        Appliance Damage: $2,000
        Total Estimated: $10,500
        
        ADJUSTER INFORMATION:
        Adjuster: Sarah Johnson
        Phone: (555) 987-6543
        Email: s.johnson@insurance.com
        
        STATUS: Open
        DEDUCTIBLE: $1,000
        """
        
        # Convert text to bytes (simulating file upload)
        content = sample_claim_text.encode('utf-8')
        content_type = "text/plain"
        
        logger.info("Testing with sample claim document...")
        logger.info(f"Sample content preview: {sample_claim_text[:200]}...")
        
        # Process the document with dual extraction
        result = await dual_extractor.process_claim_document(
            content=content,
            content_type=content_type,
            document_images=None,
            metadata={"is_claim": True, "test_document": True}
        )
        
        # Display results
        logger.info("\n=== EXTRACTION RESULTS ===")
        logger.info(f"Azure AI Method: {result.azure_ai_result.extraction_method}")
        logger.info(f"Azure AI Confidence: {result.azure_ai_result.confidence_score:.3f}")
        logger.info(f"Azure AI Fields: {len(result.azure_ai_result.extracted_data)}")
        
        logger.info(f"\nGPT-4o Method: {result.gpt4o_result.extraction_method}")
        logger.info(f"GPT-4o Confidence: {result.gpt4o_result.confidence_score:.3f}")
        logger.info(f"GPT-4o Fields: {len(result.gpt4o_result.extracted_data)}")
        
        logger.info(f"\nFinal Selected Method: {result.final_result.extraction_method}")
        logger.info(f"Final Confidence: {result.final_result.confidence_score:.3f}")
        
        # Display extracted data
        logger.info("\n=== EXTRACTED CLAIM DATA ===")
        extracted_data = result.final_result.extracted_data
        
        if extracted_data:
            for field, value in extracted_data.items():
                if value is not None and value != "":
                    logger.info(f"{field}: {value}")
        else:
            logger.warning("No data extracted!")
        
        # Check for specific fields that should NOT be placeholder values
        logger.info("\n=== VALIDATION CHECKS ===")
        
        # Check claim number
        claim_number = extracted_data.get("claim_number")
        if claim_number and "CLM-2024-12345" in str(claim_number):
            logger.info("✅ Claim number correctly extracted")
        else:
            logger.warning(f"❌ Claim number issue: {claim_number}")
        
        # Check amount (should not be generic $10,000)
        claim_amount = extracted_data.get("claim_amount_requested")
        if claim_amount and claim_amount != 10000.0:
            logger.info(f"✅ Claim amount correctly extracted: ${claim_amount:,.2f}")
        else:
            logger.warning(f"❌ Claim amount may be placeholder: {claim_amount}")
        
        # Check date (should not be "invalid date")
        loss_date = extracted_data.get("loss_date")
        if loss_date and "2024" in str(loss_date):
            logger.info(f"✅ Loss date correctly extracted: {loss_date}")
        else:
            logger.warning(f"❌ Loss date issue: {loss_date}")
        
        # Check description (should not be "general claim")
        loss_description = extracted_data.get("loss_description")
        if loss_description and "water" in loss_description.lower() and "pipe" in loss_description.lower():
            logger.info("✅ Loss description correctly extracted")
        else:
            logger.warning(f"❌ Loss description may be generic: {loss_description}")
        
        logger.info("\n=== TEST COMPLETE ===")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in dual extraction test: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_basic_extraction_comparison():
    """
    Test to compare old vs new extraction methods.
    """
    logger.info("\n=== COMPARING OLD VS NEW EXTRACTION ===")
    
    try:
        # Test old method (basic regex patterns)
        from app.utils.policy_claim_chunker import _extract_key_value_pairs
        
        sample_text = """
        Claim Number: CLM-2024-12345
        Policy Number: POL-987654321
        Insured: John and Mary Smith
        Date of Loss: 10/15/2024
        Amount: $10,500
        Description: Water damage from burst pipe
        """
        
        old_extraction = _extract_key_value_pairs(sample_text)
        logger.info("Old extraction method results:")
        for key, value in old_extraction.items():
            logger.info(f"  {key}: {value}")
        
        # Test new method (dual extraction)
        azure_manager = AzureServiceManager()
        dual_extractor = ClaimsDualExtractionPipeline(azure_manager)
        
        # Use just the Azure AI basic extraction for comparison
        from app.services.claims_dual_extraction import ExtractionResult
        new_extraction = await dual_extractor._extract_basic_claim_data(sample_text)
        
        logger.info("\nNew extraction method results:")
        for key, value in new_extraction.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("\n=== COMPARISON COMPLETE ===")
        
    except Exception as e:
        logger.error(f"Error in comparison test: {e}")


def main():
    """
    Main test function.
    """
    logger.info("Starting claims dual-extraction pipeline tests...")
    
    # Check if required environment variables are set
    required_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        logger.warning("Some tests may fallback to basic extraction")
    
    # Run tests
    asyncio.run(test_dual_extraction_pipeline())
    asyncio.run(test_basic_extraction_comparison())
    
    logger.info("\n✅ All tests completed!")
    logger.info("\nNext steps:")
    logger.info("1. Upload a real claim document through the web interface")
    logger.info("2. Check if the extracted data shows real values instead of placeholders")
    logger.info("3. Look for 'has_real_claim_data': True in the chunk metadata")


if __name__ == "__main__":
    main()