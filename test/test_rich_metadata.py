#!/usr/bin/env python3
"""
Test enhanced metadata extraction for policies and claims
"""
import sys
import os

# Add the backend directory to the Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from app.utils.insurance_metadata_extractor import InsuranceMetadataExtractor
from app.utils.policy_claim_chunker import smart_chunk_policy_text, smart_chunk_claim_text

def test_policy_metadata():
    """Test policy metadata extraction"""
    print("=== Testing Policy Metadata Extraction ===")
    
    sample_policy_text = """
    HOMEOWNERS INSURANCE POLICY
    
    Policy Number: HO-2024-123456
    Insured: John Smith
    Property Address: 123 Main Street, Anytown, CA 90210
    
    Coverage A - Dwelling: $500,000
    Coverage B - Other Structures: $50,000
    Coverage C - Personal Property: $250,000
    Coverage D - Loss of Use: $100,000
    
    Deductible: $2,500
    Policy Period: 01/01/2024 to 01/01/2025
    Premium: $2,400 annually
    
    Agent: Jane Doe Insurance Agency
    """
    
    # Test metadata extraction
    extractor = InsuranceMetadataExtractor()
    metadata = extractor.extract_policy_metadata(sample_policy_text, "test_policy.pdf")
    
    print("Extracted Policy Metadata:")
    for key, value in metadata.__dict__.items():
        print(f"  {key}: {value}")
    
    # Test enhanced chunking
    chunks = smart_chunk_policy_text(sample_policy_text, "test_policy.pdf")
    print(f"\nGenerated {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        # Handle both dict and object formats
        if isinstance(chunk, dict):
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
        else:
            content = getattr(chunk, 'content', '')
            metadata = getattr(chunk, 'metadata', {})
            
        print(f"  Content: {content[:100]}...")
        print(f"  Metadata keys: {list(metadata.keys())}")
        if 'policy_number' in metadata:
            print(f"  Policy Number: {metadata['policy_number']}")
        if 'coverage_limits' in metadata:
            print(f"  Coverage Limits: {metadata['coverage_limits']}")

def test_claim_metadata():
    """Test claim metadata extraction"""
    print("\n=== Testing Claim Metadata Extraction ===")
    
    sample_claim_text = """
    INSURANCE CLAIM REPORT
    
    Claim Number: CLM-2024-789012
    Policy Number: HO-2024-123456
    Claimant: John Smith
    
    Date of Loss: March 15, 2024
    Reported Date: March 16, 2024
    Cause of Loss: Water damage from burst pipe
    
    Location: 123 Main Street, Anytown, CA 90210
    
    Adjuster: Mike Johnson
    Status: Open
    
    Settlement Amount: $15,000
    Coverage Decision: Covered under Coverage A
    
    Notes: Kitchen flooding caused damage to flooring and cabinets.
    Property damage includes hardwood floors and lower kitchen cabinets.
    """
    
    # Test metadata extraction
    extractor = InsuranceMetadataExtractor()
    metadata = extractor.extract_claim_metadata(sample_claim_text, "test_claim.pdf")
    
    print("Extracted Claim Metadata:")
    for key, value in metadata.__dict__.items():
        print(f"  {key}: {value}")
    
    # Test enhanced chunking
    chunks = smart_chunk_claim_text(sample_claim_text, "test_claim.pdf")
    print(f"\nGenerated {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        # Handle both dict and object formats
        if isinstance(chunk, dict):
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
        else:
            content = getattr(chunk, 'content', '')
            metadata = getattr(chunk, 'metadata', {})
            
        print(f"  Content: {content[:100]}...")
        print(f"  Metadata keys: {list(metadata.keys())}")
        if 'claim_id' in metadata:
            print(f"  Claim ID: {metadata['claim_id']}")
        if 'loss_cause' in metadata:
            print(f"  Loss Cause: {metadata['loss_cause']}")
        if 'payout_amount' in metadata:
            print(f"  Payout Amount: {metadata['payout_amount']}")

if __name__ == "__main__":
    test_policy_metadata()
    test_claim_metadata()
    print("\n=== Metadata extraction test completed ===")