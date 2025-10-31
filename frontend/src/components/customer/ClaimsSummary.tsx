import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { FileText, Download, Eye, AlertCircle, RefreshCw, X } from 'lucide-react';
import { apiService } from '@/services/api';

interface ClaimDocument {
  id: string;
  filename: string;
  document_type?: string;
  upload_timestamp: string;
  file_size: number;
  status: 'processing' | 'completed' | 'failed';
  chunks_count?: number;
  metadata?: {
    company_name?: string;
    filing_date?: string;
    [key: string]: any;
  };
}

interface ClaimsMetrics {
  total_claims: number;
  approved: number;
  under_review: number;
  total_value: number;
}

export const ClaimsSummary: React.FC = () => {
  const [claimDocuments, setClaimDocuments] = useState<ClaimDocument[]>([]);
  const [metrics, setMetrics] = useState<ClaimsMetrics>({
    total_claims: 0,
    approved: 0,
    under_review: 0,
    total_value: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Add these new state variables for document preview/download functionality
  const [previewDocument, setPreviewDocument] = useState<ClaimDocument | null>(null);
  const [documentContent, setDocumentContent] = useState<string>('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const loadClaimDocuments = async () => {
    try {
      setError(null);
      
      // Fetch documents from claims index
      const documentsResponse = await apiService.listDocuments({ index: 'claims' });
      const documents = documentsResponse.documents || [];
      
      // Transform documents to claim format
      const claimDocs: ClaimDocument[] = documents.map((doc: any) => ({
        id: doc.id,
        filename: doc.filename || doc.metadata?.filename || 'Unknown',
        document_type: doc.document_type || doc.metadata?.document_type,
        upload_timestamp: doc.upload_timestamp || doc.metadata?.upload_timestamp,
        file_size: doc.file_size || doc.metadata?.file_size || 0,
        status: doc.status || 'completed',
        chunks_count: doc.chunks_count,
        metadata: doc.metadata || {}
      }));

      setClaimDocuments(claimDocs);

      // Calculate metrics
      const totalClaims = claimDocs.length;
      const completedClaims = claimDocs.filter(doc => doc.status === 'completed').length;
      const processingClaims = claimDocs.filter(doc => doc.status === 'processing').length;
      
      // Estimate total value based on document types (this would be more sophisticated in real app)
      const totalValue = claimDocs.reduce((sum, doc) => {
        const baseValue = doc.document_type === 'auto_claim' ? 15000 :
                         doc.document_type === 'home_claim' ? 25000 :
                         doc.document_type === 'medical_claim' ? 12000 : 10000;
        return sum + baseValue;
      }, 0);

      setMetrics({
        total_claims: totalClaims,
        approved: completedClaims,
        under_review: processingClaims,
        total_value: totalValue
      });

    } catch (err) {
      console.error('Failed to load claim documents:', err);
      setError(err instanceof Error ? err.message : 'Failed to load claim documents');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadClaimDocuments();
  }, []);

  // Refresh claims list when component becomes visible (e.g., when switching tabs)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        loadClaimDocuments();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadClaimDocuments();
  };

  // Function to handle document viewing
  const handleViewDocument = async (claim: ClaimDocument) => {
    try {
      setPreviewLoading(true);
      setPreviewError(null);
      setPreviewDocument(claim);
      setShowPreviewModal(true);
      
      const response = await apiService.getDocumentContent(claim.id);
      setDocumentContent(response.content);
      
    } catch (error) {
      console.error('Failed to load document content:', error);
      setPreviewError(error instanceof Error ? error.message : 'Failed to load document');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Function to close the preview modal
  const handleClosePreview = () => {
    setShowPreviewModal(false);
    setPreviewDocument(null);
    setDocumentContent('');
    setPreviewError(null);
  };

  // Function to handle document downloading
  const handleDownloadDocument = async (claim: ClaimDocument) => {
    try {
      const response = await apiService.getDocumentContent(claim.id);
      
      // Create a blob and download the document
      const blob = new Blob([response.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = claim.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Failed to download document:', error);
      // You could show an error message to the user here
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-100 text-green-800">Approved</Badge>;
      case 'processing':
        return <Badge variant="secondary">Under Review</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Unknown date';
    }
  };

  const getClaimType = (documentType?: string) => {
    switch (documentType) {
      case 'auto_claim':
        return 'Auto Accident';
      case 'home_claim':
        return 'Home Damage';
      case 'medical_claim':
        return 'Medical';
      case 'personal_injury':
        return 'Personal Injury';
      default:
        return 'General Claim';
    }
  };

  const estimateClaimValue = (documentType?: string) => {
    switch (documentType) {
      case 'auto_claim':
        return 15000;
      case 'home_claim':
        return 25000;
      case 'medical_claim':
        return 12000;
      case 'personal_injury':
        return 20000;
      default:
        return 10000;
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-6 bg-gray-200 rounded w-1/2"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">My Claims</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="animate-pulse space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-200 rounded"></div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Metrics Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Total Claims</div>
            <div className="text-2xl font-semibold">{metrics.total_claims}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Approved</div>
            <div className="text-2xl font-semibold text-green-600">{metrics.approved}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Under Review</div>
            <div className="text-2xl font-semibold text-blue-600">{metrics.under_review}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Total Value</div>
            <div className="text-2xl font-semibold">${metrics.total_value.toLocaleString()}</div>
          </CardContent>
        </Card>
      </div>

      {/* Claims List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">My Claims</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {previewError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>Preview Error: {previewError}</AlertDescription>
            </Alert>
          )}

          {claimDocuments.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                             <p>No claim documents uploaded yet.</p>
               <p className="text-sm">Upload your first claim document to get started.</p>
            </div>
          ) : (
            claimDocuments.map((claim) => (
              <div key={claim.id} className="flex items-center justify-between border rounded p-3 text-sm">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <FileText className="h-4 w-4 text-gray-500" />
                    <span className="font-medium truncate">{claim.filename}</span>
                    {getStatusBadge(claim.status)}
                  </div>
                  <div className="text-muted-foreground text-xs space-y-1">
                    <div>Type: {getClaimType(claim.document_type)}</div>
                    <div>Uploaded: {formatDate(claim.upload_timestamp)}</div>
                    <div>Size: {formatFileSize(claim.file_size)}</div>
                    {claim.chunks_count && (
                      <div>Chunks: {claim.chunks_count}</div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 ml-4">
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground">Estimated Value</div>
                    <div className="font-medium">
                      ${estimateClaimValue(claim.document_type).toLocaleString()}
                    </div>
                  </div>
                                     <div className="flex space-x-2">
                                           <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleViewDocument(claim)}
                        disabled={previewLoading && previewDocument?.id === claim.id}
                      >
                       <Eye className="h-4 w-4 mr-1" />
                       {previewLoading && previewDocument?.id === claim.id ? 'Loading...' : 'View'}
                     </Button>
                     <Button 
                       variant="outline" 
                       size="sm"
                       onClick={() => handleDownloadDocument(claim)}
                     >
                       <Download className="h-4 w-4 mr-1" />
                       Download
                     </Button>
                   </div>
                </div>
              </div>
            ))
          )}
                 </CardContent>
       </Card>

       {/* Document Preview Modal */}
       <Dialog open={showPreviewModal} onOpenChange={setShowPreviewModal}>
         <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
           <DialogHeader>
             <DialogTitle className="flex items-center space-x-2">
               <FileText className="h-5 w-5" />
               <span>{previewDocument?.filename || 'Document Preview'}</span>
             </DialogTitle>
             <DialogDescription>
               {previewDocument && (
                 <div className="text-sm text-gray-600 space-y-1">
                   <div>Type: {getClaimType(previewDocument.document_type)}</div>
                   <div>Uploaded: {formatDate(previewDocument.upload_timestamp)}</div>
                   <div>Size: {formatFileSize(previewDocument.file_size)}</div>
                 </div>
               )}
             </DialogDescription>
           </DialogHeader>
           
           <div className="flex-1 overflow-y-auto max-h-[60vh] p-4 border border-gray-200 rounded-md bg-gray-50">
             {previewLoading ? (
               <div className="flex items-center justify-center h-32">
                 <RefreshCw className="h-6 w-6 animate-spin text-blue-500 mr-2" />
                 <span>Loading document content...</span>
               </div>
             ) : previewError ? (
               <div className="text-center py-8">
                 <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                 <p className="text-red-600">{previewError}</p>
                 <Button 
                   variant="outline" 
                   onClick={() => previewDocument && handleViewDocument(previewDocument)}
                   className="mt-2"
                 >
                   Retry
                 </Button>
               </div>
             ) : documentContent ? (
               <div className="whitespace-pre-wrap text-sm font-mono">
                 {documentContent}
               </div>
             ) : (
               <div className="text-center py-8 text-gray-500">
                 No content available
               </div>
             )}
           </div>
           
           <div className="flex justify-between items-center pt-4">
             <Button 
               variant="outline"
               onClick={() => previewDocument && handleDownloadDocument(previewDocument)}
             >
               <Download className="h-4 w-4 mr-2" />
               Download
             </Button>
             <Button 
               variant="outline"
               onClick={handleClosePreview}
             >
               <X className="h-4 w-4 mr-2" />
               Close
             </Button>
           </div>
         </DialogContent>
       </Dialog>

       
     </div>
   );
 };

export default ClaimsSummary;


