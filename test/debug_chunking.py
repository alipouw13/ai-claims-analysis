#!/usr/bin/env python3
"""
Debug chunking issue - test smart_chunk_policy_text directly
"""

import asyncio
import sys
import os
import logging

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_policy_chunking():
    """Test the policy chunking directly with sample text"""
    
    # Sample policy text that should generate multiple chunks
    sample_policy_text = """
    INSURANCE POLICY

    COVERAGE DETAILS
    This policy provides comprehensive coverage for your vehicle including collision, comprehensive, and liability protection.
    The coverage limits are $100,000 per person and $300,000 per incident for bodily injury liability.
    Property damage liability is covered up to $50,000 per incident.
    
    DEDUCTIBLE INFORMATION
    Your collision deductible is $500 per claim.
    Your comprehensive deductible is $250 per claim.
    Glass repair may be covered without a deductible depending on your state.
    
    EXCLUSIONS
    This policy does not cover damage caused by:
    - Racing or speed contests
    - Commercial use of the vehicle
    - Intentional damage
    - Normal wear and tear
    - Mechanical or electrical breakdown
    
    POLICY CONDITIONS
    You must notify us within 24 hours of any accident or claim.
    All repairs must be authorized by the insurance company.
    You have the right to choose your repair facility.
    
    PREMIUM INFORMATION
    Your monthly premium is $125.00.
    Payment is due on the 15th of each month.
    Late payments may result in policy cancellation.
    
    DEFINITIONS
    "You" and "your" refer to the named insured.
    "We," "us," and "our" refer to the insurance company.
    "Vehicle" means the automobile described in the declarations.
    """
    
    try:
        from app.utils.policy_claim_chunker import smart_chunk_policy_text
        
        logger.info(f"Testing with sample text of {len(sample_policy_text)} characters")
        
        # Test the chunking function
        chunks = smart_chunk_policy_text(sample_policy_text)
        
        if chunks:
            logger.info(f"✅ Chunking successful: {len(chunks)} chunks created")
            for i, chunk in enumerate(chunks):
                content_preview = chunk.get('content', '')[:100] + '...'
                logger.info(f"  Chunk {i+1}: {len(chunk.get('content', ''))} chars - {content_preview}")
        else:
            logger.error("❌ Chunking failed: No chunks returned")
            
            # Test fallback method
            logger.info("Testing fallback chunking...")
            from app.utils.policy_claim_chunker import chunk_policy_text
            fallback_chunks = chunk_policy_text(sample_policy_text)
            if fallback_chunks:
                logger.info(f"✅ Fallback chunking successful: {len(fallback_chunks)} chunks")
            else:
                logger.error("❌ Fallback chunking also failed")
                
    except Exception as e:
        logger.error(f"❌ Error testing chunking: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_policy_chunking())