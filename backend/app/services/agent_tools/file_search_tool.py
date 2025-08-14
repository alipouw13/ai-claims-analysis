"""
File Search Tool for Azure AI Foundry Agents

This tool provides file search and retrieval capabilities to agents, allowing them to:
- Search for files in the knowledge base
- Retrieve file contents and metadata
- Search within file contents
- Manage file operations for insurance documents
"""

import logging
import json
import os
import glob
from typing import Dict, List, Any, Optional
from datetime import datetime
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)

class FileSearchTool:
    """
    File Search tool for Azure AI Foundry agents
    
    This tool can be attached to agents to provide:
    - File search capabilities
    - File content retrieval
    - File metadata extraction
    - Insurance document management
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.getcwd()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the File Search tool"""
        try:
            # Ensure base path exists
            if not os.path.exists(self.base_path):
                os.makedirs(self.base_path, exist_ok=True)
            
            self._initialized = True
            logger.info(f"File Search tool initialized with base path: {self.base_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize File Search tool: {e}")
            raise
    
    async def search_files(
        self, 
        query: str,
        file_types: List[str] = None,
        max_results: int = 10,
        search_in_content: bool = True
    ) -> Dict[str, Any]:
        """
        Search for files by name and optionally content
        
        Args:
            query: Search query
            file_types: List of file extensions to search (e.g., ['.pdf', '.txt'])
            max_results: Maximum number of results to return
            search_in_content: Whether to search within file contents
            
        Returns:
            Search results with file information
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            results = []
            search_pattern = os.path.join(self.base_path, "**", "*")
            
            # Filter by file types if specified
            if file_types:
                search_patterns = []
                for ext in file_types:
                    search_patterns.append(os.path.join(self.base_path, "**", f"*{ext}"))
            else:
                search_patterns = [search_pattern]
            
            for pattern in search_patterns:
                for file_path in glob.glob(pattern, recursive=True):
                    if os.path.isfile(file_path):
                        file_info = await self._get_file_info(file_path)
                        
                        # Check if file matches query
                        matches = False
                        if query.lower() in file_info['name'].lower():
                            matches = True
                        elif search_in_content and query.lower() in file_info.get('content_preview', '').lower():
                            matches = True
                        
                        if matches:
                            results.append(file_info)
                            
                            if len(results) >= max_results:
                                break
                
                if len(results) >= max_results:
                    break
            
            return {
                "query": query,
                "total_results": len(results),
                "results": results,
                "search_in_content": search_in_content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"File search failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "results": [],
                "total_results": 0
            }
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed information about a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            File information and metadata
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            return await self._get_file_info(file_path)
            
        except Exception as e:
            logger.error(f"Get file info failed: {e}")
            return {
                "error": str(e),
                "file_path": file_path
            }
    
    async def read_file_content(
        self, 
        file_path: str,
        max_length: int = 10000
    ) -> Dict[str, Any]:
        """
        Read file content
        
        Args:
            file_path: Path to the file
            max_length: Maximum content length to return
            
        Returns:
            File content and metadata
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            file_info = await self._get_file_info(file_path)
            
            if "error" in file_info:
                return file_info
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Truncate if too long
                if len(content) > max_length:
                    content = content[:max_length] + "... [truncated]"
                
                file_info["content"] = content
                file_info["content_length"] = len(content)
                
            except UnicodeDecodeError:
                # Try binary read for non-text files
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read(max_length)
                    file_info["content"] = f"[Binary file - {len(content)} bytes]"
                    file_info["content_length"] = len(content)
                except Exception as e:
                    file_info["error"] = f"Could not read file content: {str(e)}"
            
            return file_info
            
        except Exception as e:
            logger.error(f"Read file content failed: {e}")
            return {
                "error": str(e),
                "file_path": file_path
            }
    
    async def list_files(
        self, 
        directory: str = None,
        file_types: List[str] = None,
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        List files in a directory
        
        Args:
            directory: Directory to list (relative to base path)
            file_types: List of file extensions to include
            recursive: Whether to search recursively
            
        Returns:
            List of files with metadata
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            search_dir = os.path.join(self.base_path, directory) if directory else self.base_path
            
            if not os.path.exists(search_dir):
                return {
                    "error": f"Directory not found: {search_dir}",
                    "files": [],
                    "total_files": 0
                }
            
            files = []
            if recursive:
                search_pattern = os.path.join(search_dir, "**", "*")
            else:
                search_pattern = os.path.join(search_dir, "*")
            
            for file_path in glob.glob(search_pattern, recursive=recursive):
                if os.path.isfile(file_path):
                    # Filter by file type if specified
                    if file_types:
                        file_ext = os.path.splitext(file_path)[1].lower()
                        if file_ext not in file_types:
                            continue
                    
                    file_info = await self._get_file_info(file_path)
                    files.append(file_info)
            
            return {
                "directory": search_dir,
                "total_files": len(files),
                "files": files,
                "file_types": file_types,
                "recursive": recursive,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"List files failed: {e}")
            return {
                "error": str(e),
                "files": [],
                "total_files": 0
            }
    
    async def search_insurance_documents(
        self, 
        document_type: str = None,
        query: str = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search specifically for insurance documents
        
        Args:
            document_type: "policy", "claims", "reports", or None for all
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            Insurance document search results
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Define insurance document patterns
            insurance_patterns = {
                "policy": ["*policy*", "*coverage*", "*terms*"],
                "claims": ["*claim*", "*damage*", "*incident*"],
                "reports": ["*report*", "*assessment*", "*evaluation*"]
            }
            
            if document_type and document_type in insurance_patterns:
                patterns = insurance_patterns[document_type]
            else:
                # Search all insurance patterns
                patterns = []
                for pattern_list in insurance_patterns.values():
                    patterns.extend(pattern_list)
            
            results = []
            for pattern in patterns:
                search_pattern = os.path.join(self.base_path, "**", pattern)
                
                for file_path in glob.glob(search_pattern, recursive=True):
                    if os.path.isfile(file_path):
                        file_info = await self._get_file_info(file_path)
                        
                        # Additional filtering by query if provided
                        if query:
                            if (query.lower() in file_info['name'].lower() or 
                                query.lower() in file_info.get('content_preview', '').lower()):
                                results.append(file_info)
                        else:
                            results.append(file_info)
                        
                        if len(results) >= max_results:
                            break
                
                if len(results) >= max_results:
                    break
            
            return {
                "document_type": document_type,
                "query": query,
                "total_results": len(results),
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Insurance document search failed: {e}")
            return {
                "error": str(e),
                "document_type": document_type,
                "query": query,
                "results": [],
                "total_results": 0
            }
    
    async def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information and metadata"""
        try:
            stat = os.stat(file_path)
            
            # Get file type
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Read content preview for text files
            content_preview = ""
            try:
                if mime_type and mime_type.startswith('text/'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_preview = f.read(500)  # First 500 characters
            except:
                pass
            
            return {
                "name": os.path.basename(file_path),
                "path": file_path,
                "relative_path": os.path.relpath(file_path, self.base_path),
                "size": stat.st_size,
                "size_formatted": self._format_size(stat.st_size),
                "mime_type": mime_type,
                "extension": os.path.splitext(file_path)[1].lower(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "content_preview": content_preview,
                "is_text": mime_type and mime_type.startswith('text/') if mime_type else False
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "path": file_path
            }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """Get the tool schema for Azure AI Foundry agent configuration"""
        return {
            "name": "file_search_tool",
            "description": "Search and retrieve files from the knowledge base",
            "type": "file_search",
            "capabilities": [
                "search_files",
                "get_file_info",
                "read_file_content",
                "list_files",
                "search_insurance_documents"
            ],
            "supported_file_types": ["pdf", "txt", "doc", "docx", "json", "csv"],
            "insurance_document_types": ["policy", "claims", "reports"]
        }
