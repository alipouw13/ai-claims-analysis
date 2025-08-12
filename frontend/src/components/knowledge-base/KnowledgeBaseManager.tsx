import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Upload, FileText, CheckCircle, AlertCircle, Clock, Trash2, Eye, Download, RefreshCw } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import ChunkingVisualization from './ChunkingVisualization';
import { ModelSettings } from '../shared/ModelConfiguration';
import { apiService, DocumentInfo, ConflictInfo, KnowledgeBaseMetrics } from '@/services/api';
import { KnowledgeBaseAgentServiceStatus } from './KnowledgeBaseAgentServiceStatus';



interface KnowledgeBaseManagerProps {
  modelSettings: ModelSettings;
  role: 'admin' | 'underwriter' | 'customer';
}

const KnowledgeBaseManager: React.FC<KnowledgeBaseManagerProps> = ({ modelSettings, role }) => {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([]);
  const [metrics, setMetrics] = useState<KnowledgeBaseMetrics | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [activeTab, setActiveTab] = useState('upload');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchText, setSearchText] = useState<string>('');
  const [indexFilter, setIndexFilter] = useState<string>(role === 'customer' ? 'claims' : 'policy');
  const [previewOpen, setPreviewOpen] = useState<boolean>(false);
  const [previewDoc, setPreviewDoc] = useState<{ id: string; index: 'policy' | 'claims' } | null>(null);
  const [previewChunks, setPreviewChunks] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [inlineNotice, setInlineNotice] = useState<{ type: 'success' | 'error'; message: string; latestDocId?: string } | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  // Live polling for status updates when viewing library or during upload
  useEffect(() => {
    const shouldPoll = activeTab === 'documents' || isUploading;
    if (!shouldPoll) return;
    const id = setInterval(() => {
      loadData({ silent: true });
    }, 3000);
    return () => clearInterval(id);
  }, [activeTab, isUploading]);

  const loadData = async (opts: { silent?: boolean } = {}) => {
    if (!opts.silent) setLoading(true);
    setError(null);
    
    try {
      const [documentsResponse, conflictsResponse, metricsResponse] = await Promise.all([
        apiService.listDocuments(indexFilter !== 'all' ? { index: indexFilter } as any : undefined as any),
        apiService.getConflicts(),
        apiService.getKnowledgeBaseMetrics()
      ]);
      
      setDocuments(documentsResponse.documents);
      setConflicts(conflictsResponse.conflicts);
      setMetrics(metricsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
      console.error('Error loading data:', err);
    } finally {
      if (!opts.silent) setLoading(false);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      const filesArray = Array.from(selectedFiles);
      
      const uploadResponse = await apiService.uploadDocuments({
        files: filesArray,
        embedding_model: modelSettings.embeddingModel,
        search_type: modelSettings.searchType,
        temperature: modelSettings.temperature,
        document_type: undefined,
        company_name: undefined,
        filing_date: undefined,
        is_claim: role === 'customer'
      });

      console.log('Upload successful:', uploadResponse);
      setSelectedFiles(null);
      // Notify success with in-app banner and CTA to open chunk visualization for the new doc
      setInlineNotice({
        type: 'success',
        message: `${filesArray.length} file(s) uploaded. Click View Analysis to open Chunk Visualization.`,
        latestDocId: (uploadResponse && uploadResponse[0] && uploadResponse[0].document_id) || undefined,
      });
      
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            setIsUploading(false);
            loadData(); // Refresh data after upload
            return 100;
          }
          return prev + 10;
        });
      }, 200);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      console.error('Upload error:', err);
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteDocument = async (documentId: string) => {
    try {
      await apiService.deleteDocument(documentId);
      await loadData(); // Refresh data after deletion
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
      console.error('Delete failed:', err);
    }
  };

  const handleResolveConflict = async (conflictId: string, resolution: 'resolve' | 'ignore') => {
    try {
      const status = resolution === 'resolve' ? 'resolved' : 'ignored';
      await apiService.resolveConflict(conflictId, status);
      await loadData(); // Refresh data after conflict resolution
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resolve conflict');
      console.error('Conflict resolution failed:', err);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      completed: 'default',
      processing: 'secondary',
      failed: 'destructive',
      pending: 'outline'
    } as const;

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{role === 'customer' ? 'Claims Documents' : 'Policy Documents'} Management</h1>
          <p className="text-muted-foreground text-sm">
            {role === 'customer'
              ? 'Upload and manage claim documents for AI analysis'
              : 'Upload and manage policy documents and applications for AI analysis'}
          </p>
        </div>
        <Button onClick={loadData} variant="outline" disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="upload">{role === 'customer' ? 'Upload Claims' : 'Upload Policies'}</TabsTrigger>
          <TabsTrigger value="documents">Document Library</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="chunking">Chunk Visualization</TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-4">
          <Card className={`border-dashed ${isDragging ? 'border-blue-500 bg-blue-50/40' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              const files = e.dataTransfer.files;
              if (files && files.length > 0) {
                setSelectedFiles(files);
              }
            }}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Upload className="h-4 w-4" />
                {role === 'customer' ? 'Upload Claim Documents' : 'Upload Policy Documents'}
              </CardTitle>
              <CardDescription className="text-xs">Drag and drop files here, or click to browse. Supports PDF, DOC, DOCX files up to 10MB.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {inlineNotice && (
                <div className={`p-3 rounded border ${inlineNotice.type==='success' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{inlineNotice.message}</span>
                    {inlineNotice.latestDocId && (
                      <Button size="sm" variant="outline" onClick={() => { setActiveTab('chunking'); setPreviewDoc({ id: inlineNotice.latestDocId!, index: (role==='customer' ? 'claims':'policy') }); setInlineNotice(null); }}>
                        View Analysis
                      </Button>
                    )}
                  </div>
                </div>
              )}
              <div className="grid w-full max-w-sm items-center gap-1.5">
                <Label htmlFor="documents">Select {role === 'customer' ? 'Claim' : 'Policy'} Documents</Label>
                <Input
                  id="documents"
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => setSelectedFiles(e.target.files)}
                  disabled={isUploading}
                />
                <p className="text-xs text-muted-foreground">Supported formats: PDF, DOCX, TXT (Max 10MB per file)</p>
              </div>

              {selectedFiles && selectedFiles.length > 0 && (
                <div className="space-y-2">
                  <Label>Selected Files:</Label>
                  {Array.from(selectedFiles).map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-2 border rounded">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        <span className="text-sm">{file.name}</span>
                        <span className="text-xs text-muted-foreground">
                          ({formatFileSize(file.size)})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {isUploading && (
                <div className="space-y-2">
                  <Label>Upload Progress</Label>
                  <Progress value={uploadProgress} className="w-full" />
                  <p className="text-sm text-muted-foreground">{uploadProgress}% complete</p>
                </div>
              )}

              <div className="flex gap-2 items-center">
                <Button onClick={handleFileUpload} disabled={!selectedFiles || selectedFiles.length === 0 || isUploading}>
                  {isUploading ? 'Uploading…' : (selectedFiles && selectedFiles.length > 0 ? 'Upload' : 'Select Files')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="documents" className="space-y-4">
          {/* Quick Stats */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Total Documents</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-semibold">{documents.length}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Completed</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-semibold">{documents.filter(d => d.status === 'completed').length}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Processing</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-semibold">{documents.filter(d => d.status === 'processing').length}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Failed</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-semibold">{documents.filter(d => d.status === 'failed').length}</div></CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Document Library</CardTitle>
              <CardDescription>
                Manage uploaded documents and their processing status
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Filters */}
              <div className="flex flex-wrap gap-2 items-center mb-4">
                <input
                  className="border rounded px-2 py-1 text-sm"
                  placeholder="Search filename…"
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                />
                <select className="border rounded px-2 py-1 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                  <option value="all">All Statuses</option>
                  <option value="completed">Completed</option>
                  <option value="processing">Processing</option>
                  <option value="failed">Failed</option>
                </select>
                <select className="border rounded px-2 py-1 text-sm" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                  <option value="all">All Types</option>
                  {[...new Set(documents.map(d => d.type))].map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <select className="border rounded px-2 py-1 text-sm" value={indexFilter} onChange={(e) => { setIndexFilter(e.target.value); loadData({ silent: true }); }}>
                  <option value="all">All Indexes</option>
                  <option value="policy">Policy</option>
                  <option value="claims">Claims</option>
                </select>
                <Button variant="outline" size="sm" onClick={() => { setStatusFilter('all'); setTypeFilter('all'); setSearchText(''); }}>Clear</Button>
              </div>

              <Table>
                <TableHeader>
                   <TableRow>
                    <TableHead>Document</TableHead>
                    <TableHead>Type</TableHead>
                     <TableHead>Index</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Upload Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Chunks</TableHead>
                    <TableHead>Conflicts</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents
                    .filter(d => (statusFilter === 'all' ? true : d.status === statusFilter))
                    .filter(d => (typeFilter === 'all' ? true : d.type === typeFilter))
                    .filter(d => (searchText ? d.filename.toLowerCase().includes(searchText.toLowerCase()) : true))
                    .map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4" />
                          {doc.filename}
                        </div>
                      </TableCell>
                      <TableCell>{doc.type}</TableCell>
                      <TableCell>{(doc as any).index || 'policy'}</TableCell>
                      <TableCell>{formatFileSize(doc.size)}</TableCell>
                      <TableCell>{formatDate(doc.uploadDate)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(doc.status)}
                          {getStatusBadge(doc.status)}
                          {doc.status === 'processing' && (
                            <div className="flex items-center gap-2 min-w-[120px]">
                              <Progress value={doc.processingProgress || 5} className="w-24" />
                              <span className="text-xs text-muted-foreground">{doc.processingProgress || 5}%</span>
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{doc.chunks}</TableCell>
                      <TableCell>
                        {doc.conflicts ? (
                          <Badge variant="destructive">{doc.conflicts}</Badge>
                        ) : (
                          <Badge variant="outline">0</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Button variant="outline" size="sm" onClick={() => {
                            // Route to Chunk Visualization tab instead of opening the side preview
                            const idx = ((doc as any).index || 'policy') as 'policy' | 'claims';
                            setPreviewDoc({ id: doc.id, index: idx });
                            setActiveTab('chunking');
                            setPreviewOpen(false);
                          }}>
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button variant="outline" size="sm">
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteDocument(doc.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Preview Drawer */}
          {previewOpen && (
            <div className="fixed inset-0 bg-black/30 z-40" onClick={() => setPreviewOpen(false)} />
          )}
          <div className={`fixed right-0 top-0 h-full w-full sm:w-[560px] z-50 bg-background border-l transition-transform ${previewOpen ? 'translate-x-0' : 'translate-x-full'}`}>
            <div className="p-4 border-b flex items-center justify-between">
              <div className="text-sm font-medium">Document Chunks {previewDoc ? `(${previewDoc.index})` : ''}</div>
              <Button variant="outline" size="sm" onClick={() => setPreviewOpen(false)}>Close</Button>
            </div>
            <div className="p-4 overflow-y-auto h-[calc(100%-56px)]">
              {previewLoading ? (
                <div className="text-sm text-muted-foreground">Loading chunks…</div>
              ) : (
                <div className="space-y-3">
                  {previewChunks.map((c, i) => (
                    <div key={i} className="border rounded p-3 text-xs">
                      <div className="text-muted-foreground mb-1">Chunk ID: {c.chunk_id || c.id}</div>
                      <div className="whitespace-pre-wrap">{c.content}</div>
                      {c.metadata && (
                        <div className="mt-2 text-muted-foreground">Meta: {JSON.stringify(c.metadata)}</div>
                      )}
                    </div>
                  ))}
                  {previewChunks.length === 0 && <div className="text-xs text-muted-foreground">No chunks found.</div>}
                </div>
              )}
            </div>
          </div>
        </TabsContent>

          <TabsContent value="chunking" className="space-y-4">
            <ChunkingVisualization initialDocumentId={previewDoc?.id} index={(previewDoc?.index ?? indexFilter) as any} />
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="space-y-4">
            <KnowledgeBaseAgentServiceStatus onRefresh={loadData} />
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics?.total_documents || documents.length}</div>
                <p className="text-xs text-muted-foreground">
                  Total documents
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Chunks</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.total_chunks || documents.reduce((sum, doc) => sum + (doc.chunks || 0), 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  Processed chunks
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Conflicts</CardTitle>
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.active_conflicts || conflicts.filter(c => c.status === 'pending').length}
                </div>
                <p className="text-xs text-muted-foreground">
                  Require attention
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Processing Rate</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics?.processing_rate || 94}%</div>
                <p className="text-xs text-muted-foreground">
                  Success rate
                </p>
              </CardContent>
            </Card>
          </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default KnowledgeBaseManager;
