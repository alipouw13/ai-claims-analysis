"""
Traditional RAG Service Implementation
Based on Azure AI Search RAG best practices
https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview
"""

import logging
import time
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI

from app.services.azure_services import AzureServiceManager
from app.services.token_usage_tracker import TokenUsageTracker
from app.services.credibility_assessor import CredibilityAssessor
from app.models.schemas import VerificationLevel
from app.core.config import settings

logger = logging.getLogger(__name__)

class TraditionalRAGService:
    """
    Traditional RAG implementation following Azure AI Search best practices.
    Simple and direct: Search → Retrieve → Generate response
    """
    
    def __init__(self, azure_manager: AzureServiceManager):
        self.azure_manager = azure_manager
        self.openai_client = None
        self.credibility_assessor = CredibilityAssessor(azure_manager)
    
    async def initialize(self):
        """Initialize the service"""
        try:
            # Initialize OpenAI client for direct LLM calls
            if not self.openai_client:
                self.openai_client = AzureOpenAI(
                    api_version="2024-06-01",
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY
                )
            logger.info("Traditional RAG service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Traditional RAG service: {e}")
            raise
    
    async def process_question(
        self,
        question: str,
        session_id: str,
        model_config: Dict[str, Any],
        verification_level: VerificationLevel = VerificationLevel.BASIC,
        token_tracker: Optional[TokenUsageTracker] = None,
        tracking_id: Optional[str] = None,
        credibility_check_enabled: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a question using Traditional RAG pattern:
        1. Convert question to embeddings
        2. Search knowledge base
        3. Format results for LLM
        4. Generate response with citations
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting Traditional RAG processing for question: {question[:100]}...")
            
            if not self.openai_client:
                await self.initialize()
            
            # Step 1: Search the knowledge base
            logger.info(f"🔍 Traditional RAG: Step 1 - Searching knowledge base for: '{question[:100]}...'")
            search_results = await self._search_knowledge_base(
                question, 
                top_k=10 if verification_level == VerificationLevel.BASIC else 15,
                token_tracker=token_tracker,
                tracking_id=tracking_id
            )
            
            logger.info(f"🔍 Traditional RAG: Search completed, found {len(search_results)} results")
            
            if not search_results:
                logger.warning("🔍 Traditional RAG: No relevant documents found in knowledge base")
                # Let's also try a broader search without any filtering
                logger.info("🔍 Traditional RAG: Attempting broader search...")
                broad_results = await self.azure_manager.hybrid_search(
                    query=question,
                    top_k=20,
                    min_score=0.0
                )
                logger.info(f"🔍 Traditional RAG: Broad search found {len(broad_results)} total results")
                
                return {
                    "answer": "I couldn't find relevant information in the knowledge base to answer your question. This might be because the question doesn't match available documents or the relevance threshold is too high.",
                    "confidence_score": 0.1,
                    "sources": [],
                    "citations": [],
                    "metadata": {
                        "rag_method": "traditional",
                        "sources_found": 0,
                        "broad_search_found": len(broad_results),
                        "processing_time": time.time() - start_time
                    }
                }
            
            # Step 2: Format sources for LLM prompt
            logger.info(f"Step 2: Formatting {len(search_results)} sources for LLM...")
            formatted_sources = self._format_sources_for_llm(search_results)
            
            # Step 3: Generate response using LLM
            logger.info("Step 3: Generating response with LLM...")
            response = await self._generate_response(
                question=question,
                sources=formatted_sources,
                model_config=model_config,
                token_tracker=token_tracker,
                tracking_id=tracking_id
            )
            
            # Step 4: Format citations with credibility assessment if enabled
            citations = await self._format_citations(search_results, credibility_check_enabled, token_tracker, tracking_id)
            
            # Step 5: Calculate verification details if credibility checking is enabled
            verification_details = self._calculate_verification_details(citations, credibility_check_enabled, verification_level)
            
            processing_time = time.time() - start_time
            logger.info(f"Traditional RAG processing completed in {processing_time:.2f}s")
            
            return {
                "answer": response.get("answer", ""),
                "confidence_score": response.get("confidence_score", 0.7),
                "sources": search_results,
                "citations": citations,
                "verification_details": verification_details,
                "metadata": {
                    "rag_method": "traditional",
                    "sources_found": len(search_results),
                    "processing_time": processing_time,
                    "model_used": model_config.get("chat_model", "unknown"),
                    "tokens_used": response.get("token_usage", {})
                }
            }
            
        except Exception as e:
            logger.error(f"Error in Traditional RAG processing: {e}")
            raise
    
    async def _search_knowledge_base(
        self, 
        query: str, 
        top_k: int = 10,
        token_tracker: Optional[TokenUsageTracker] = None,
        tracking_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base using hybrid search (vector + keyword)
        Following Azure AI Search RAG best practices
        """
        try:
            logger.info(f"🔍 Traditional RAG: Searching knowledge base with query: '{query[:100]}...'")
            
            # First, let's test if the search service is accessible at all
            logger.info("🔍 Traditional RAG: Testing search service connectivity...")
            
            # Use hybrid search for maximum recall as recommended by Azure
            # Start with no minimum score to see all results
            results = await self.azure_manager.hybrid_search(
                query=query,
                top_k=top_k,
                min_score=0.0,  # No minimum initially
                token_tracker=token_tracker,
                tracking_id=tracking_id
            )
            
            logger.info(f"🔍 Traditional RAG: Raw search returned {len(results)} results")
            
            # If we got results, analyze and filter them
            if results:
                scores = [r.get('search_score', 0) for r in results]
                logger.info(f"🔍 Traditional RAG: Search scores: min={min(scores):.3f}, max={max(scores):.3f}, avg={sum(scores)/len(scores):.3f}")
                
                # Log details of top 3 results for debugging
                for i, result in enumerate(results[:3]):
                    logger.info(f"🔍 Traditional RAG: Result {i+1}: score={result.get('search_score', 0):.3f}, "
                              f"company={result.get('company', 'N/A')}, "
                              f"doc_type={result.get('form_type', 'N/A')}, "
                              f"content_len={len(result.get('content', ''))}")
                
                # Apply a more reasonable minimum score filter (0.2 instead of 0.7)
                # But first try without any filtering to see if we get any results
                if max(scores) < 0.2:
                    logger.warning(f"🔍 Traditional RAG: All scores below 0.2, returning top results anyway")
                    filtered_results = results[:min(5, len(results))]  # Take top 5 regardless of score
                else:
                    filtered_results = [r for r in results if r.get('search_score', 0) >= 0.2]
                    logger.info(f"🔍 Traditional RAG: After score filtering (>=0.2): {len(filtered_results)} results")
                
                return filtered_results
            else:
                logger.warning("🔍 Traditional RAG: No results returned from hybrid search")
                
                # Try a simple keyword search as fallback
                logger.info("🔍 Traditional RAG: Trying simple keyword search fallback...")
                try:
                    # Use the search client directly for a simple text search
                    search_results = self.azure_manager.search_client.search(
                        search_text=query,
                        top=5,
                        select=["id", "content", "company", "form_type", "filing_date", "document_id", 
                               "source", "document_title", "credibility_score"]
                    )
                    
                    fallback_results = []
                    async for result in search_results:
                        result_dict = dict(result)
                        result_dict['search_score'] = 0.5  # Assign a default score
                        fallback_results.append(result_dict)
                    
                    logger.info(f"🔍 Traditional RAG: Fallback search found {len(fallback_results)} results")
                    return fallback_results
                    
                except Exception as fallback_error:
                    logger.error(f"🔍 Traditional RAG: Fallback search also failed: {fallback_error}")
                    return []
            
        except Exception as e:
            logger.error(f"🔍 Traditional RAG: Error searching knowledge base: {e}")
            logger.error(f"🔍 Traditional RAG: Query was: '{query}'")
            logger.error(f"🔍 Traditional RAG: Azure manager initialized: {self.azure_manager is not None}")
            return []
    
    def _format_sources_for_llm(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Format search results into a structured format for the LLM prompt
        Following Azure's recommended source formatting
        """
        if not search_results:
            return "No sources available."
        
        formatted_sources = []
        for i, result in enumerate(search_results, 1):
            # Extract key information
            content = result.get('content', '').strip()
            company = result.get('company', 'Unknown Company')
            form_type = result.get('form_type', 'Unknown Document')
            filing_date = result.get('filing_date', 'Unknown Date')
            document_id = result.get('document_id', 'Unknown ID')
            
            # Format source with clear attribution
            source_text = f"Source {i}:\n"
            source_text += f"Company: {company}\n"
            source_text += f"Document: {form_type} (Filed: {filing_date})\n"
            source_text += f"Content: {content}\n"
            source_text += f"Document ID: {document_id}\n"
            source_text += "---\n"
            
            formatted_sources.append(source_text)
        
        return "\n".join(formatted_sources)
    
    async def _generate_response(
        self,
        question: str,
        sources: str,
        model_config: Dict[str, Any],
        token_tracker: Optional[TokenUsageTracker] = None,
        tracking_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response using Azure OpenAI following Traditional RAG pattern
        """
        try:
            # Construct the grounded prompt following Azure's recommended pattern
            system_prompt = self._get_system_prompt()
            user_prompt = self._get_user_prompt(question, sources)
            
            # Extract deployment name from model config (handle "gpt-4o (chat4o)" format)
            chat_model_full = model_config.get("chat_model", "chat4omini")
            chat_model = self._extract_deployment_name(chat_model_full)
            temperature = model_config.get("temperature", 0.1)
            
            logger.info(f"Calling Azure OpenAI with deployment: {chat_model} (from: {chat_model_full})")
            
            # Call Azure OpenAI directly
            response = self.openai_client.chat.completions.create(
                model=chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=4000
            )
            
            answer = response.choices[0].message.content
            
            # Track token usage if tracker provided
            if token_tracker and tracking_id:
                token_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                
                # Update token tracker
                await token_tracker.update_usage(
                    tracking_id=tracking_id,
                    prompt_tokens=token_usage["prompt_tokens"],
                    completion_tokens=token_usage["completion_tokens"],
                    model_name=chat_model
                )
            else:
                token_usage = {}
            
            # Estimate confidence based on response quality
            confidence_score = self._estimate_confidence(answer, sources)
            
            return {
                "answer": answer,
                "confidence_score": confidence_score,
                "token_usage": token_usage
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _get_system_prompt(self) -> str:
        """
        System prompt following Azure's RAG best practices
        """
        return """You are a helpful financial analyst assistant. Your role is to provide accurate, well-researched answers to financial questions using only the provided source documents.

IMPORTANT GUIDELINES:
- Answer ONLY using the facts and information provided in the sources below
- If the sources don't contain enough information to answer the question, say so clearly
- Always cite your sources using the document information provided
- Be precise and factual - avoid speculation or information not found in the sources
- Provide comprehensive answers when sources allow, but stay grounded in the provided information
- Include relevant financial figures, dates, and company details when available in the sources

Remember: You must base your response entirely on the provided sources. Do not add external knowledge or speculation."""
    
    def _get_user_prompt(self, question: str, sources: str) -> str:
        """
        User prompt with question and formatted sources
        Following Azure's recommended prompt structure
        """
        return f"""Question: {question}

Sources:
{sources}

Please provide a comprehensive answer to the question using only the information from the sources above. Include specific citations to the relevant sources in your response."""
    
    def _estimate_confidence(self, answer: str, sources: str) -> float:
        """
        Estimate confidence in the answer based on response quality
        Simple heuristic - could be enhanced with more sophisticated analysis
        """
        if not answer or "don't know" in answer.lower() or "not enough information" in answer.lower():
            return 0.3
        
        if len(answer) < 100:
            return 0.5
        
        # Check if answer references sources
        if "source" in answer.lower() or any(word in answer.lower() for word in ["according", "based on", "as stated"]):
            return 0.8
        
        return 0.7
    
    async def _format_citations(self, search_results: List[Dict[str, Any]], 
                               credibility_check_enabled: bool = False,
                               token_tracker: Optional[TokenUsageTracker] = None,
                               tracking_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Format search results as citations for the response
        Optionally assess credibility if enabled
        """
        citations = []
        
        for i, result in enumerate(search_results, 1):
            # Get base credibility score
            base_credibility = result.get('credibility_score', 0.5)
            
            # Assess credibility if enabled
            if credibility_check_enabled:
                try:
                    assessed_credibility = await self.credibility_assessor.assess_credibility(
                        processed_doc=result,
                        source=result.get('source', ''),
                        token_tracker=token_tracker,
                        tracking_id=tracking_id
                    )
                    # Use the assessed credibility
                    final_credibility = assessed_credibility
                    logger.info(f"Traditional RAG: Assessed credibility for source {i}: {final_credibility:.3f}")
                except Exception as e:
                    logger.warning(f"Traditional RAG: Credibility assessment failed for source {i}: {e}")
                    final_credibility = base_credibility
            else:
                final_credibility = base_credibility
            
            citation = {
                "id": f"citation_{i}",
                "content": result.get('content', '')[:500] + "...",  # Truncate for display
                "source": f"{result.get('company', 'Unknown')} - {result.get('form_type', 'Document')}",
                "document_id": result.get('document_id', ''),
                "document_title": f"{result.get('form_type', 'Document')} - {result.get('company', 'Unknown')}",
                "page_number": result.get('page_number'),
                "section_title": result.get('section_type'),
                "confidence": "high" if result.get('search_score', 0) > 0.8 else "medium",
                "url": result.get('document_url', ''),
                "credibility_score": final_credibility
            }
            citations.append(citation)
        
        return citations
    
    async def diagnose_knowledge_base(self) -> Dict[str, Any]:
        """
        Diagnostic method to check the state of the knowledge base
        """
        try:
            # Try a very broad search to see if there are any documents at all
            all_docs = await self.azure_manager.hybrid_search(
                query="*",
                top_k=50,
                min_score=0.0
            )
            
            # Try a simple search for common financial terms
            financial_docs = await self.azure_manager.hybrid_search(
                query="revenue earnings financial",
                top_k=10,
                min_score=0.0
            )
            
            # Try searching for specific companies
            company_docs = await self.azure_manager.hybrid_search(
                query="Apple Microsoft Tesla",
                top_k=10,
                min_score=0.0
            )
            
            return {
                "total_documents_found": len(all_docs),
                "financial_search_results": len(financial_docs),
                "company_search_results": len(company_docs),
                "sample_document_types": [doc.get('document_type', 'unknown') for doc in all_docs[:5]],
                "sample_companies": [doc.get('company', 'unknown') for doc in all_docs[:5]]
            }
            
        except Exception as e:
            logger.error(f"Error diagnosing knowledge base: {e}")
            return {"error": str(e)}

    def _extract_deployment_name(self, model_config_value: str) -> str:
        """Extract deployment name from model config value, handling combined strings like 'gpt-4o (chat4o)'"""
        if not model_config_value:
            return "chat4omini"  # Default deployment
        
        # Handle combined strings like "gpt-4o (chat4o)" -> extract "chat4o"
        if '(' in model_config_value and ')' in model_config_value:
            try:
                deployment_name = model_config_value.split('(')[1].split(')')[0].strip()
                logger.debug(f"Extracted deployment name '{deployment_name}' from combined string '{model_config_value}'")
                return deployment_name
            except (IndexError, AttributeError):
                logger.warning(f"Failed to parse deployment name from '{model_config_value}', using as-is")
                return model_config_value
        
        # Return as-is if no parentheses (already just deployment name)
        return model_config_value

    def _calculate_verification_details(self, citations: List[Dict[str, Any]], 
                                       credibility_check_enabled: bool, 
                                       verification_level: VerificationLevel) -> Dict[str, Any]:
        """Calculate verification details based on citations and credibility scores"""
        
        if not credibility_check_enabled or not citations:
            return {
                "overall_credibility_score": 0.5,
                "verified_sources_count": 0,
                "total_sources_count": len(citations),
                "verification_summary": "Credibility checking disabled or no sources available",
                "verification_level": verification_level.value if hasattr(verification_level, 'value') else str(verification_level)
            }
        
        # Calculate overall credibility score
        credibility_scores = [citation.get('credibility_score', 0.5) for citation in citations]
        overall_credibility = sum(credibility_scores) / len(credibility_scores) if credibility_scores else 0.5
        
        # Count verified sources (credibility >= 0.6)
        verified_sources = [c for c in citations if c.get('credibility_score', 0) >= 0.6]
        verified_count = len(verified_sources)
        total_count = len(citations)
        
        # Generate verification summary
        if verified_count == total_count:
            verification_summary = f"All {total_count} sources verified as credible"
        elif verified_count > 0:
            verification_summary = f"{verified_count} of {total_count} sources verified as credible"
        else:
            verification_summary = f"None of {total_count} sources met credibility threshold"
        
        logger.info(f"Traditional RAG verification: {verified_count}/{total_count} sources verified, "
                   f"overall credibility: {overall_credibility:.3f}")
        
        return {
            "overall_credibility_score": overall_credibility,
            "verified_sources_count": verified_count,
            "total_sources_count": total_count,
            "verification_summary": verification_summary,
            "verification_level": verification_level.value if hasattr(verification_level, 'value') else str(verification_level),
            "credibility_method": "traditional_rag"
        }
