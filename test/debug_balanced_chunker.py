#!/usr/bin/env python3
"""
Debug BalancedChunker specifically
"""

import sys
import os
import logging

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_balanced_chunker():
    """Test the BalancedChunker directly"""
    
    sample_text = """
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
    This policy does not cover damage caused by racing or speed contests, commercial use of the vehicle, intentional damage, normal wear and tear, or mechanical or electrical breakdown.
    
    POLICY CONDITIONS
    You must notify us within 24 hours of any accident or claim.
    All repairs must be authorized by the insurance company.
    You have the right to choose your repair facility.
    
    PREMIUM INFORMATION
    Your monthly premium is $125.00.
    Payment is due on the 15th of each month.
    Late payments may result in policy cancellation.
    """
    
    try:
        from app.utils.balanced_chunker import BalancedChunker
        
        # Create chunker with smaller target size to force multiple chunks
        chunker = BalancedChunker(
            target_chunk_size=400,  # Smaller than default
            max_chunk_size=600,
            min_chunk_size=100,
            overlap_ratio=0.15
        )
        
        logger.info(f"Testing BalancedChunker with text of {len(sample_text)} characters")
        logger.info(f"Chunker settings: target={chunker.target_chunk_size}, max={chunker.max_chunk_size}")
        
        chunks = chunker.chunk_document(sample_text, "policy")
        
        if chunks:
            logger.info(f"✅ BalancedChunker created {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                content = chunk.get('content', '')
                metadata = chunk.get('metadata', {})
                logger.info(f"  Chunk {i+1}: {len(content)} chars - {metadata.get('chunk_type', 'unknown')} - {content[:60]}...")
        else:
            logger.error("❌ BalancedChunker created no chunks")
            
    except Exception as e:
        logger.error(f"❌ Error testing BalancedChunker: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_balanced_chunker()