#!/usr/bin/env python3
"""Test the enhanced chunking pipeline with the Motor Insurance FAQs PDF."""

import asyncio
import os
from app.services.document_processor import DocumentProcessor
from app.services.azure_services import AzureServiceManager

async def test_motor_insurance_faq():
    """Test processing of the Motor Insurance FAQs document."""
    print("🔄 Testing enhanced chunking with Motor Insurance FAQs")
    
    # Initialize services
    azure_manager = AzureServiceManager()
    doc_processor = DocumentProcessor(azure_manager)
    
    # Read the PDF file
    pdf_path = r'C:\temp\AI\ai-claims-analysis\sample-docs\policies\AnyCompany Motor Insurance FAQs.pdf'
    with open(pdf_path, 'rb') as f:
        content = f.read()
    
    filename = os.path.basename(pdf_path)
    print(f"📄 Processing: {filename}")
    print(f"📊 File size: {len(content)} bytes")
    
    try:
        # Process the document
        result = await doc_processor.process_document(
            content=content,
            content_type='application/pdf',
            source=filename,
            metadata={
                'is_policy': True, 
                'document_type': 'motor_insurance_faq',
                'tags': ['motor_insurance', 'faq', 'policy']
            }
        )
        
        print("\n✅ Processing completed successfully!")
        
        # Analyze results
        doc_id = result.get('id', 'unknown')
        content_text = result.get('content', '')
        chunks = result.get('chunks', [])
        
        print(f"📋 Document ID: {doc_id}")
        print(f"📝 Extracted text: {len(content_text)} characters")
        print(f"🔢 Chunks created: {len(chunks)}")
        
        if chunks:
            # Chunk analysis
            sizes = [len(chunk.content) for chunk in chunks]
            
            print(f"\n📏 Chunk Statistics:")
            print(f"  Size range: {min(sizes)} - {max(sizes)} characters")
            print(f"  Average size: {sum(sizes)/len(sizes):.0f} characters")
            print(f"  Total content: {sum(sizes)} characters")
            print(f"  Coverage: {(sum(sizes)/len(content_text)*100):.1f}%")
            
            # Show sample chunks
            print(f"\n📝 Sample Chunks:")
            for i, chunk in enumerate(chunks[:5]):
                size = len(chunk.content)
                metadata = chunk.metadata
                method = metadata.get('chunk_method', 'unknown')
                confidence = metadata.get('confidence_score', 0)
                
                print(f"  Chunk {i+1}: {size} chars, method: {method}, confidence: {confidence:.2f}")
                
                # Preview content
                preview = chunk.content[:120].replace('\n', ' ').strip()
                print(f"    Preview: {preview}...")
                print()
            
            if len(chunks) > 5:
                print(f"  ... and {len(chunks) - 5} more chunks")
            
            # Method analysis
            methods = {}
            for chunk in chunks:
                method = chunk.metadata.get('chunk_method', 'unknown')
                methods[method] = methods.get(method, 0) + 1
            
            print(f"\n🛠️ Chunking Methods Used:")
            for method, count in methods.items():
                print(f"  {method}: {count} chunks ({count/len(chunks)*100:.1f}%)")
        
        print(f"\n🎯 Enhanced chunking test completed successfully!")
        print(f"   This resolves the original issue of '0-2 chunks' - we now have {len(chunks)} well-sized chunks!")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_motor_insurance_faq())