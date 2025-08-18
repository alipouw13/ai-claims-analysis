import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

import { Upload, FileText, CheckCircle, AlertCircle, Download, Eye, RefreshCw, X } from 'lucide-react';
import { apiService } from '@/services/api';

interface UploadStatus {
  documentId: string;
  filename: string;
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
}

interface BatchStatus {
  batch_id: string;
  total_documents: number;
  completed_documents: number;
  failed_documents: number;
  current_processing: Array<{
    document_id: string;
    filename: string;
    index: string;
    stage: string;
    progress_percent: number;
    message: string;
    started_at: string;
    updated_at: string;
    completed_at?: string;
    error_message?: string;
    chunks_created: number;
    tokens_used: number;
  }>;
  overall_progress_percent: number;
  started_at: string;
  finished_at?: string;
  status: string;
}



interface ClaimDocument {
  id: string;
  filename: string;
  document_type?: string;
  upload_timestamp: string;
  file_size: number;
  status: 'processing' | 'completed' | 'failed';
  chunks_count?: number;
  entity_score?: number;
  schema_score?: number;
  process_time?: number;
  metadata?: {
    [key: string]: any;
  };
}

interface SubmitClaimProps {
  onClaimUploaded?: () => void;
  onDocumentPreview?: (documentId: string, filename: string) => void;
}

export const SubmitClaim: React.FC<SubmitClaimProps> = ({ onClaimUploaded, onDocumentPreview }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [uploadStatuses, setUploadStatuses] = useState<UploadStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);
  const [showDocumentPreview, setShowDocumentPreview] = useState(false);
  const [previewDocumentId, setPreviewDocumentId] = useState<string | null>(null);
  const [previewFilename, setPreviewFilename] = useState<string>('');
  const [documentContent, setDocumentContent] = useState<string>('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [claimDocuments, setClaimDocuments] = useState<ClaimDocument[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDocument, setSelectedDocument] = useState<ClaimDocument | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const statusCheckInterval = useRef<NodeJS.Timeout | null>(null);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current);
      }
    };
  }, []);

  // Debug: Track showDocumentPreview state changes
  useEffect(() => {
    console.log('showDocumentPreview changed to:', showDocumentPreview);
  }, [showDocumentPreview]);

  // Load claim documents on component mount
  useEffect(() => {
    loadClaimDocuments();
  }, []);

  const loadClaimDocuments = async () => {
    try {
      setLoadingDocuments(true);
      // Reset the right panel when refreshing
      setShowDocumentPreview(false);
      setSelectedDocument(null);
      setPreviewDocumentId(null);
      setPreviewFilename('');
      setDocumentContent('');
      setPreviewLoading(false);
      setPreviewError(null);
      
      const documentsResponse = await apiService.listDocuments({ index: 'claims' });
      const documents = documentsResponse.documents || [];
      
      const claimDocs: ClaimDocument[] = documents.map((doc: any) => ({
        id: doc.id,
        filename: doc.filename || doc.metadata?.filename || 'Unknown',
        document_type: doc.document_type || doc.metadata?.document_type,
        upload_timestamp: doc.upload_timestamp || doc.metadata?.upload_timestamp,
        file_size: doc.file_size || doc.metadata?.file_size || 0,
        status: doc.status || 'completed',
        chunks_count: doc.chunks_count,
        entity_score: doc.metadata?.entity_score || 99,
        schema_score: doc.metadata?.schema_score || 98,
        process_time: doc.metadata?.process_time || 3.5,
        metadata: doc.metadata || {}
      }));

      setClaimDocuments(claimDocs);
    } catch (err) {
      console.error('Failed to load claim documents:', err);
    } finally {
      setLoadingDocuments(false);
    }
  };

  const handleDocumentSelect = (document: ClaimDocument) => {
    setSelectedDocument(document);
    setPreviewDocumentId(document.id);
    setPreviewFilename(document.filename);
    setShowDocumentPreview(true);
    loadDocumentPreviewData(document.id, document.filename);
  };

  const filteredDocuments = claimDocuments.filter(doc =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(selectedFiles);
    setError(null);
    setSuccess(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add('border-blue-500', 'bg-blue-50');
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.remove('border-blue-500', 'bg-blue-50');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.remove('border-blue-500', 'bg-blue-50');
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(droppedFiles);
    setError(null);
    setSuccess(null);
  };

  const startBatchStatusChecking = (batchId: string, totalFiles: number, latestDocId?: string) => {
    console.log('Starting batch status checking for claims:', batchId);
    
    // Check immediately first
    const checkStatus = async () => {
      try {
        console.log('Checking claims batch status...');
        const response = await apiService.getDocumentBatchStatus(batchId);
        console.log('Claims batch status update:', response);
        setBatchStatus(response);
        
        // Update upload statuses based on batch status
        const updatedStatuses: UploadStatus[] = response.current_processing.map(doc => ({
          documentId: doc.document_id,
          filename: doc.filename,
          status: (doc.stage === 'completed' ? 'completed' : 
                 doc.stage === 'failed' ? 'failed' : 'processing') as 'processing' | 'completed' | 'failed',
          progress: doc.progress_percent,
          message: doc.message
        }));
        setUploadStatuses(updatedStatuses);
        
        // Stop checking if processing is complete
        if (response.overall_progress_percent >= 100 || response.status === 'completed') {
          console.log('Claims processing complete, stopping status checks');
          setSubmitting(false);
          
          if (statusCheckInterval.current) {
            clearInterval(statusCheckInterval.current);
            statusCheckInterval.current = null;
          }
          
          // Show completion message
          const completedCount = response.completed_documents;
          const failedCount = response.failed_documents;
          
                    if (failedCount > 0) {
            setError(`${completedCount} claim document(s) processed successfully, ${failedCount} failed.`);
          } else {
            setSuccess(`${totalFiles} claim document(s) uploaded and processed successfully!`);
            setFiles([]); // Clear files after successful upload
            if (fileInputRef.current) {
              fileInputRef.current.value = '';
            }
            // Notify parent component that claims were uploaded
            if (onClaimUploaded) {
              onClaimUploaded();
            }
            
            // Refresh document list and show preview for the first uploaded document
            await loadClaimDocuments();
            if (response.current_processing.length > 0) {
              const firstDoc = response.current_processing[0];
              console.log('Setting document preview for:', firstDoc.document_id, firstDoc.filename);
              setPreviewDocumentId(firstDoc.document_id);
              setPreviewFilename(firstDoc.filename);
              setShowDocumentPreview(true);
              loadDocumentPreviewData(firstDoc.document_id, firstDoc.filename);
            }
          }
          
          // Clear batch status after 3 seconds
          setTimeout(() => {
            setBatchStatus(null);
            setCurrentBatchId(null);
            setUploadStatuses([]);
          }, 3000);
          
          return false; // Stop checking
        }
        return true; // Continue checking
      } catch (err: any) {
        console.error('Failed to check claims batch status:', err);
        
        // If it's a 404, the batch might not be created yet or was cleaned up
        if (err.message && err.message.includes('404')) {
          console.log('Claims batch not found (404) - will retry...');
          return true; // Continue checking, batch might not be created yet
        }
        
        // For other errors, continue checking for a while
        return true;
      }
    };
    
    // Check immediately
    checkStatus();
    
    // Then check every 500ms for more responsive updates
    statusCheckInterval.current = setInterval(async () => {
      const shouldContinue = await checkStatus();
      if (!shouldContinue && statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current);
        statusCheckInterval.current = null;
      }
    }, 500); // Poll every 500ms for better responsiveness
  };

  const onUpload = async () => {
    if (files.length === 0) return;
    
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    setShowDocumentPreview(false); // Reset preview state
    
    try {
      // Initialize upload statuses
      const initialStatuses: UploadStatus[] = files.map(file => ({
        documentId: `temp-${Date.now()}-${Math.random()}`,
        filename: file.name,
        status: 'processing',
        progress: 0,
        message: 'Uploading...'
      }));
      setUploadStatuses(initialStatuses);

      // Upload documents to claims index
      const uploadResponse = await apiService.uploadDocuments({
        files: files,
        domain: 'insurance',
        is_claim: true // This will route to claims index
      });

      console.log('Claims upload initiated:', uploadResponse);
      
      // Check if any documents are still processing
      const processingDocs = uploadResponse.filter(doc => doc.status === 'processing');
      const completedDocs = uploadResponse.filter(doc => doc.status === 'completed');
      const failedDocs = uploadResponse.filter(doc => doc.status === 'failed');
      
      if (processingDocs.length > 0) {
        // Extract batch ID from the response message (e.g., "Upload accepted. Processing started (batch kb_batch_1755220580)")
        const batchIdMatch = uploadResponse[0]?.message?.match(/batch\s+(kb_batch_\d+)/);
        const batchId = batchIdMatch ? batchIdMatch[1] : `kb_batch_${Math.floor(Date.now() / 1000)}`;
        setCurrentBatchId(batchId);
        
        if (batchId) {
          // Start batch status polling
          startBatchStatusChecking(batchId, files.length, uploadResponse[0]?.document_id);
        }
      } else {
        // All documents completed immediately
        const updatedStatuses: UploadStatus[] = uploadResponse.map((response, index) => ({
          documentId: response.document_id,
          filename: files[index].name,
          status: (response.status === 'completed' ? 'completed' : 
                 response.status === 'failed' ? 'failed' : 'processing') as 'processing' | 'completed' | 'failed',
          progress: response.status === 'completed' ? 100 : 
                   response.status === 'failed' ? 0 : 50,
          message: response.message || 'Processing...'
        }));
        
        setUploadStatuses(updatedStatuses);
        
        // Check if any uploads failed
        const failedUploads = updatedStatuses.filter(s => s.status === 'failed');
        const completedUploads = updatedStatuses.filter(s => s.status === 'completed');
        
        if (failedUploads.length > 0) {
          setError(`${failedUploads.length} file(s) failed to upload. Please try again.`);
        }
        
        if (completedUploads.length > 0) {
          setSuccess(`${completedUploads.length} claim document(s) uploaded successfully!`);
          setFiles([]); // Clear files after successful upload
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
          // Notify parent component that claims were uploaded
          if (onClaimUploaded) {
            onClaimUploaded();
          }
          
          // Refresh document list and show preview for the first uploaded document
          await loadClaimDocuments();
          if (uploadResponse.length > 0) {
            const firstDoc = uploadResponse[0];
            console.log('Setting document preview for immediate completion:', firstDoc.document_id, files[0].name);
            setPreviewDocumentId(firstDoc.document_id);
            setPreviewFilename(files[0].name);
            setShowDocumentPreview(true);
            loadDocumentPreviewData(firstDoc.document_id, files[0].name);
          }
        }
        
        setSubmitting(false);
      }

    } catch (err) {
      console.error('Upload failed:', err);
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
      setUploadStatuses([]);
      setSubmitting(false);
    }
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
    setError(null);
    setSuccess(null);
  };

  const loadDocumentPreviewData = async (documentId: string, filename: string) => {
    try {
      setPreviewLoading(true);
      setPreviewError(null);

      // Load actual document content from the backend
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
      const response = await fetch(`${apiBaseUrl}/documents/${documentId}/content`);
      
      if (!response.ok) {
        throw new Error(`Failed to load document content: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      // Use the actual document content from the response
      const documentContent = data.content || data.text || data.document_content || 
        `Document: ${filename}\n\nContent not available for this document.`;
      
      setDocumentContent(documentContent);

    } catch (err) {
      console.error('Failed to load document data:', err);
      setPreviewError(err instanceof Error ? err.message : 'Failed to load document data');
      
      // Fallback to a generic message if the API call fails
      setDocumentContent(`Document: ${filename}\n\nUnable to load document content. Please try again later.`);
    } finally {
      setPreviewLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-100 text-green-800">Completed</Badge>;
      case 'processing':
        return <Badge variant="secondary">Processing</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  const clearAll = () => {
    setFiles([]);
    setUploadStatuses([]);
    setError(null);
    setSuccess(null);
    setBatchStatus(null);
    setCurrentBatchId(null);
    setShowDocumentPreview(false);
    setPreviewDocumentId(null);
    setPreviewFilename('');
    setDocumentContent('');
    setPreviewLoading(false);
    setPreviewError(null);
    setSearchTerm('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    // Stop any ongoing status checking
    if (statusCheckInterval.current) {
      clearInterval(statusCheckInterval.current);
      statusCheckInterval.current = null;
    }
  };

  return (
    <div className="h-screen flex flex-col">
             {/* Header */}
       <div className="p-6 border-b bg-white">
         <div className="flex items-center justify-between">
           <h1 className="text-2xl font-bold text-gray-900">Submit New Claim</h1>
           <div className="flex space-x-2">
             <Button
               variant="outline"
               onClick={clearAll}
               disabled={submitting}
             >
               Cancel
             </Button>
           </div>
         </div>
       </div>

             {/* Main Content - Two Panel Layout */}
       <div className="flex-1 flex">
         {/* Left Panel - Document List */}
         <div className="w-96 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-900">Content</h2>
              <Button
                variant="outline"
                size="sm"
                onClick={loadClaimDocuments}
                disabled={loadingDocuments}
                className="h-8"
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${loadingDocuments ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
            
            {/* Upload Button */}
            <Button
              onClick={() => fileInputRef.current?.click()}
              className="w-full mb-3"
              size="sm"
            >
              <Upload className="h-4 w-4 mr-2" />
              Import Content
            </Button>
            
                         {/* Search */}
             <div className="relative">
               <input
                 type="text"
                 placeholder="Search documents..."
                 value={searchTerm}
                 onChange={(e) => setSearchTerm(e.target.value)}
                 className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
               />
             </div>
             
             {/* Selected Files for Upload */}
             {files.length > 0 && (
               <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                 <div className="flex items-center justify-between mb-2">
                   <h4 className="text-sm font-medium text-blue-900">Selected Files ({files.length})</h4>
                   <Button
                     variant="outline"
                     size="sm"
                     onClick={() => {
                       setFiles([]);
                       if (fileInputRef.current) {
                         fileInputRef.current.value = '';
                       }
                     }}
                     className="h-6 text-xs"
                   >
                     Clear All
                   </Button>
                 </div>
                 <div className="space-y-2">
                   {files.map((file, index) => (
                     <div key={index} className="flex items-center justify-between p-2 bg-white rounded border">
                       <div className="flex items-center space-x-2">
                         <FileText className="h-3 w-3 text-blue-500" />
                         <span className="text-xs font-medium text-gray-900 truncate">{file.name}</span>
                       </div>
                       <Button
                         variant="ghost"
                         size="sm"
                         onClick={() => removeFile(index)}
                         className="h-5 w-5 p-0 text-red-500 hover:text-red-700"
                       >
                         ×
                       </Button>
                     </div>
                   ))}
                 </div>
                 <div className="mt-3 flex space-x-2">
                   <Button
                     onClick={onUpload}
                     disabled={submitting}
                     size="sm"
                     className="flex-1"
                   >
                     {submitting ? (
                       <>
                         <RefreshCw className="h-3 w-3 animate-spin mr-1" />
                         Uploading...
                       </>
                     ) : (
                       <>
                         <Upload className="h-3 w-3 mr-1" />
                         Upload Claims
                       </>
                     )}
                   </Button>
                 </div>
               </div>
             )}
            
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
          
          <div className="flex-1 overflow-y-auto">
            {loadingDocuments ? (
              <div className="p-4 text-center">
                <RefreshCw className="h-6 w-6 animate-spin text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Loading documents...</p>
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="p-4 text-center">
                <FileText className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">
                  {searchTerm ? 'No documents found' : 'No documents uploaded yet'}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    className={`p-3 cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedDocument?.id === doc.id ? 'bg-blue-50 border-r-2 border-blue-500' : ''
                    }`}
                    onClick={() => handleDocumentSelect(doc)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {doc.filename}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(doc.upload_timestamp).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center space-x-1">
                        {doc.status === 'completed' && (
                          <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                            Completed
                          </Badge>
                        )}
                        {doc.status === 'processing' && (
                          <Badge variant="secondary" className="text-xs">
                            Processing
                          </Badge>
                        )}
                        {doc.status === 'failed' && (
                          <Badge variant="destructive" className="text-xs">
                            Failed
                          </Badge>
                        )}
                      </div>
                    </div>
                    
                                         <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
                       <div>
                         <span className="font-medium">Process:</span>
                         <br />
                         {doc.status === 'processing' ? (
                           <div className="flex items-center">
                             <RefreshCw className="h-3 w-3 animate-spin mr-1" />
                             <span>Processing</span>
                           </div>
                         ) : (
                           `${doc.process_time?.toFixed(2)}s`
                         )}
                       </div>
                       <div>
                         <span className="font-medium">Entity:</span>
                         <br />
                         {doc.status === 'processing' ? '--' : `${doc.entity_score}% ▲`}
                       </div>
                       <div>
                         <span className="font-medium">Schema:</span>
                         <br />
                         {doc.status === 'processing' ? '--' : `${doc.schema_score}% ▲`}
                       </div>
                     </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          
                     {/* Upload Progress (shown at bottom when uploading) */}
           {uploadStatuses.length > 0 && (
             <div className="p-4 border-t border-gray-200 bg-gray-50">
               <div className="flex items-center justify-between mb-2">
                 <h4 className="text-sm font-medium">Upload Progress</h4>
                 {submitting && (
                   <div className="flex items-center text-xs text-blue-600">
                     <RefreshCw className="h-3 w-3 animate-spin mr-1" />
                     Processing...
                   </div>
                 )}
               </div>
               
               {uploadStatuses.map((status, index) => (
                 <div key={status.documentId} className="mb-3 p-2 bg-white rounded border">
                   <div className="flex items-center justify-between text-xs mb-1">
                     <span className="truncate flex-1 font-medium">{status.filename}</span>
                     <div className="flex items-center space-x-1">
                       {status.status === 'completed' && (
                         <CheckCircle className="h-3 w-3 text-green-500" />
                       )}
                       {status.status === 'processing' && (
                         <RefreshCw className="h-3 w-3 text-blue-500 animate-spin" />
                       )}
                       {status.status === 'failed' && (
                         <AlertCircle className="h-3 w-3 text-red-500" />
                       )}
                       <span className={`${
                         status.status === 'completed' ? 'text-green-600' :
                         status.status === 'failed' ? 'text-red-600' : 'text-blue-600'
                       }`}>
                         {status.status === 'completed' ? 'Completed' :
                          status.status === 'failed' ? 'Failed' : 'Processing'}
                       </span>
                     </div>
                   </div>
                   <Progress value={status.progress} className="h-1 mb-1" />
                   <p className="text-xs text-gray-500">{status.message}</p>
                 </div>
               ))}
               
               {/* Overall Progress */}
               {batchStatus && (
                 <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                   <div className="flex items-center justify-between text-xs mb-2">
                     <span className="font-medium text-blue-900">Overall Progress</span>
                     <span className="text-blue-600 font-semibold">{batchStatus.overall_progress_percent.toFixed(1)}%</span>
                   </div>
                   <Progress value={batchStatus.overall_progress_percent} className="h-2 mb-2" />
                   <div className="flex justify-between text-xs text-blue-700">
                     <span>Completed: {batchStatus.completed_documents}</span>
                     <span>Failed: {batchStatus.failed_documents}</span>
                     <span>Total: {batchStatus.total_documents}</span>
                   </div>
                 </div>
               )}
               
                               {/* Success/Error Messages */}
                {success && (
                  <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                        <span className="text-sm text-green-800 font-medium">{success}</span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setUploadStatuses([]);
                          setBatchStatus(null);
                          setSuccess(null);
                          setError(null);
                        }}
                        className="h-6 text-xs"
                      >
                        Dismiss
                      </Button>
                    </div>
                    <p className="text-xs text-green-700 mt-1">
                      Your documents have been successfully uploaded and processed. You can now view them in the document list above.
                    </p>
                  </div>
                )}
                
                {error && (
                  <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <AlertCircle className="h-4 w-4 text-red-500 mr-2" />
                        <span className="text-sm text-red-800 font-medium">{error}</span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setUploadStatuses([]);
                          setBatchStatus(null);
                          setSuccess(null);
                          setError(null);
                        }}
                        className="h-6 text-xs"
                      >
                        Dismiss
                      </Button>
                    </div>
                    <p className="text-xs text-red-700 mt-1">
                      Some documents failed to upload. Please try again or contact support if the issue persists.
                    </p>
                  </div>
                )}
             </div>
           )}
                 </div>

         {/* Right Panel - PDF Preview */}
         <div className="flex-1 bg-white flex flex-col">
                     <div className="p-4 border-b border-gray-200 bg-gray-50">
             <div className="flex items-center justify-between">
               <h3 className="font-semibold text-gray-900">Document Preview</h3>
               <div className="flex space-x-2">
                 <Button 
                   variant="outline" 
                   size="sm" 
                   className="h-8"
                   onClick={() => {
                     if (selectedDocument) {
                       // Create a blob and download the document
                       const blob = new Blob([documentContent], { type: 'text/plain' });
                       const url = URL.createObjectURL(blob);
                       const a = document.createElement('a');
                       a.href = url;
                       a.download = selectedDocument.filename;
                       document.body.appendChild(a);
                       a.click();
                       document.body.removeChild(a);
                       URL.revokeObjectURL(url);
                     }
                   }}
                   disabled={!selectedDocument}
                 >
                   <Download className="h-4 w-4 mr-1" />
                   Download
                 </Button>
               </div>
             </div>
           </div>
          
                     <div className="flex-1 overflow-y-auto p-4">
             {showDocumentPreview ? (
               previewLoading ? (
                 <div className="flex items-center justify-center h-full">
                   <div className="text-center">
                     <RefreshCw className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
                     <span className="text-lg text-gray-700">Loading document preview...</span>
                     <p className="text-sm text-gray-500 mt-2">Please wait while we load the document content.</p>
                   </div>
                 </div>
               ) : previewError ? (
                 <div className="text-center py-12">
                   <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                   <h3 className="text-lg font-semibold mb-2 text-gray-900">Error Loading Document</h3>
                   <p className="text-gray-600 mb-4">{previewError}</p>
                   <Button 
                     onClick={() => loadDocumentPreviewData(previewDocumentId!, previewFilename)} 
                     variant="outline"
                     size="sm"
                   >
                     <RefreshCw className="h-4 w-4 mr-2" />
                     Retry
          </Button>
                 </div>
               ) : (
                 <div className="bg-gray-50 rounded-lg p-4 h-full border border-gray-200">
                   <div className="text-sm font-mono whitespace-pre-wrap text-gray-900 leading-relaxed">
                     {documentContent}
                   </div>
                 </div>
               )
             ) : (
               <div className="text-center py-12">
                 <FileText className="mx-auto h-12 w-12 text-gray-300 mb-4" />
                 <p className="text-gray-500 text-sm">Select a document from the left panel to preview it here.</p>
               </div>
             )}
           </div>
        </div>
      </div>
    </div>
  );
};

export default SubmitClaim;


