"""
Policy and Claims RAG Service

This service handles question-answering for policy and claims documents,
separate from the traditional RAG service used for SEC documents.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.config import settings
from app.services.azure_services import AzureServiceManager
from app.services.token_usage_tracker import TokenUsageTracker, OperationType
from app.models.schemas import QARequest, QAResponse

logger = logging.getLogger(__name__)


class PolicyClaimsRAGService:
    """RAG service specifically for policy and claims documents."""
    
    def __init__(self, azure_manager: AzureServiceManager):
        self.azure_manager = azure_manager
        self.token_tracker = TokenUsageTracker(azure_manager)
        
    async def ask_question(
        self,
        question: str,
        session_id: str,
        request: QARequest
    ) -> QAResponse:
        """
        Answer a question using policy and claims documents.
        
        Args:
            question: The user's question
            session_id: Unique session identifier
            request: The QA request object with model settings
            
        Returns:
            QAResponse with answer and citations
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing policy/claims question for session {session_id}: {question[:100]}...")
            
            # Start token tracking
            tracking_id = await self.token_tracker.start_tracking(
                session_id=session_id,
                operation=OperationType.ANSWER_GENERATION,
                model_name=request.chat_model,
                metadata={
                    "question": question[:200],
                    "rag_method": "policy_claims",
                    "temperature": request.temperature
                }
            )
            
            # Step 1: Search for relevant documents
            logger.info("Searching for relevant policy/claims documents...")
            search_results = await self._search_documents(
                question, 
                request.embedding_model,
                top_k=10
            )
            
            if not search_results:
                logger.warning("No relevant documents found for the question")
                return QAResponse(
                    answer="I couldn't find any relevant policy or claims documents to answer your question.",
                    citations=[],
                    session_id=session_id,
                    token_usage={
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    },
                    metadata={
                        "search_results_count": 0,
                        "processing_time": (datetime.now() - start_time).total_seconds()
                    }
                )
            
            # Step 2: Generate answer using retrieved context
            logger.info(f"Generating answer using {len(search_results)} relevant documents...")
            answer, token_usage = await self._generate_answer(
                question=question,
                context_documents=search_results,
                chat_model=request.chat_model,
                temperature=request.temperature
            )
            
            # Step 3: Create citations
            citations = self._create_citations(search_results)
            
            # Update token tracking
            await self.token_tracker.update_tracking(
                tracking_id=tracking_id,
                tokens_used=token_usage.get("total_tokens", 0),
                prompt_tokens=token_usage.get("prompt_tokens", 0),
                completion_tokens=token_usage.get("completion_tokens", 0)
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Policy/claims question processed successfully in {processing_time:.2f}s")
            
            return QAResponse(
                answer=answer,
                citations=citations,
                session_id=session_id,
                token_usage=token_usage,
                metadata={
                    "search_results_count": len(search_results),
                    "processing_time": processing_time,
                    "rag_method": "policy_claims"
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing policy/claims question for session {session_id}: {e}")
            
            # Finalize token tracking on error
            try:
                await self.token_tracker.finalize_tracking(tracking_id)
            except:
                pass
                
            return QAResponse(
                answer="I encountered an error while processing your question about policy or claims documents. Please try again.",
                citations=[],
                session_id=session_id,
                token_usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                metadata={
                    "error": str(e),
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            )
    
    async def _search_documents(
        self, 
        question: str, 
        embedding_model: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents in policy and claims indexes."""
        
        try:
            # Search both policy and claims indexes
            policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
            claims_index = settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
            
            search_tasks = []
            
            if policy_index:
                search_tasks.append(
                    self._search_single_index(question, policy_index, top_k // 2)
                )
                
            if claims_index:
                search_tasks.append(
                    self._search_single_index(question, claims_index, top_k // 2)
                )
            
            if not search_tasks:
                logger.warning("No policy or claims indexes configured")
                return []
            
            # Execute searches in parallel
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Combine results
            all_results = []
            for result in search_results:
                if isinstance(result, Exception):
                    logger.warning(f"Search error: {result}")
                    continue
                if isinstance(result, list):
                    all_results.extend(result)
            
            # Sort by relevance score and limit to top_k
            all_results.sort(key=lambda x: x.get('@search.score', 0), reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def _search_single_index(
        self, 
        question: str, 
        index_name: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Search a single Azure Search index."""
        
        try:
            search_client = self.azure_manager.get_search_client_for_index(index_name)
            
            # Use simple text search
            search_results = await search_client.search(
                search_text=question,
                top=top_k,
                select=["id", "content", "source", "title", "parent_id"],
                highlight_fields=["content"]
            )
            
            documents = []
            async for result in search_results:
                documents.append({
                    "id": result.get("id"),
                    "content": result.get("content", ""),
                    "source": result.get("source", ""),
                    "title": result.get("title", ""),
                    "parent_id": result.get("parent_id"),
                    "@search.score": result.get("@search.score", 0),
                    "@search.highlights": result.get("@search.highlights", {}),
                    "index": index_name
                })
            
            logger.info(f"Found {len(documents)} results in index {index_name}")
            return documents
            
        except Exception as e:
            logger.error(f"Error searching index {index_name}: {e}")
            return []
    
    async def _generate_answer(
        self,
        question: str,
        context_documents: List[Dict[str, Any]],
        chat_model: str,
        temperature: float
    ) -> Tuple[str, Dict[str, int]]:
        """Generate an answer using the OpenAI chat model."""
        
        try:
            # Build context from retrieved documents
            context_parts = []
            for i, doc in enumerate(context_documents[:5]):  # Limit to top 5 for context
                source = doc.get("source", "Unknown")
                content = doc.get("content", "")[:1000]  # Limit content length
                context_parts.append(f"Source {i+1} ({source}):\n{content}")
            
            context = "\n\n".join(context_parts)
            
            # Create the prompt
            system_prompt = """You are an expert insurance assistant. Answer questions about policy terms, coverage, exclusions, claims, and procedures based on the provided policy and claims documents.

Instructions:
- Provide accurate, specific answers based only on the information in the provided documents
- Include specific section references when possible
- If information is unclear or missing, state this explicitly
- For exclusions, cite the exact policy language and section numbers
- Be thorough but concise
- Use professional insurance terminology appropriately"""

            user_prompt = f"""Question: {question}

Context from Policy and Claims Documents:
{context}

Please provide a comprehensive answer based on the above documents. Include specific references to policy sections and document sources where applicable."""

            # Call OpenAI
            openai_client = self.azure_manager.get_openai_client()
            
            response = openai_client.chat.completions.create(
                model=chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=1500
            )
            
            answer = response.choices[0].message.content
            
            # Extract token usage
            token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            return answer, token_usage
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"I encountered an error while generating the answer: {str(e)}", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
    
    def _create_citations(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create citations from search results."""
        
        citations = []
        seen_sources = set()
        
        for result in search_results:
            source = result.get("source", "Unknown")
            if source in seen_sources:
                continue
                
            seen_sources.add(source)
            
            citation = {
                "source": source,
                "title": result.get("title", source),
                "content_preview": result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", ""),
                "relevance_score": result.get("@search.score", 0),
                "document_id": result.get("id"),
                "parent_id": result.get("parent_id"),
                "index": result.get("index", "policy")
            }
            
            citations.append(citation)
            
            # Limit to top 5 citations
            if len(citations) >= 5:
                break
        
        return citations