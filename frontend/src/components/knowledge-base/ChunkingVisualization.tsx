import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { apiService } from '@/services/api';

import { 
  FileText, 
  Layers, 
  BarChart3, 
  Table, 
  Hash, 
  Eye, 
  Download,
  ChevronRight,
  ChevronDown,
  MapPin,
  Zap,
  ArrowLeft,
  Calendar,
  Building,
  RefreshCw
} from 'lucide-react';

interface ChunkMetadata {
  id: string;
  content: string;
  startPage: number;
  endPage: number;
  section: string;
  subsection?: string;
  chunkType: 'text' | 'table' | 'chart' | 'footnote' | 'header';
  size: number;
  overlap: number;
  confidence: number;
  citations: string[];
}

interface DocumentStructure {
  id: string;
  filename: string;
  totalPages: number;
  sections: {
    name: string;
    startPage: number;
    endPage: number;
    subsections: {
      name: string;
      startPage: number;
      endPage: number;
      chunks: ChunkMetadata[];
    }[];
  }[];
  processingStatus: 'processing' | 'completed' | 'failed';
  processingProgress: number;
}

interface ChunkingVisualizationProps {
  initialDocumentId?: string;
  index?: 'policy' | 'claims';
  onBack?: () => void; // Add callback to communicate with parent
}

const ChunkingVisualization: React.FC<ChunkingVisualizationProps> = ({ initialDocumentId, index = 'policy', onBack }) => {
  const [selectedDocument, setSelectedDocument] = useState<string>(initialDocumentId || '');
  const [domain, setDomain] = useState<'insurance' | 'banking'>(() => (localStorage.getItem('domain') as any) || 'insurance');
  const [libraryDocs, setLibraryDocs] = useState<Array<{id: string; name: string}>>([]);
  const [documentStructure, setDocumentStructure] = useState<DocumentStructure | null>(null);
  const [analytics, setAnalytics] = useState<{
    total_chunks: number;
    avg_chunk_length: number;
    section_types: string[];
  } | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<ChunkMetadata | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [chunkingStrategy] = useState<'hierarchical' | 'semantic' | 'hybrid'>('hierarchical');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [chunkVisualizationData, setChunkVisualizationData] = useState<any>(null);
  const [manuallyCleared, setManuallyCleared] = useState(false); // Track manual navigation

  // Load document list from corresponding library
  const loadLibrary = async () => {
    try {
      if (domain === 'insurance') {
        const res = await apiService.listDocuments({ index } as any);
        const docs = (res.documents || []).map((d: any) => ({ id: d.id, name: d.filename || d.name || d.id }));
        setLibraryDocs(docs);
      } else {
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
        const secRes = await fetch(`${apiBaseUrl}/sec/library?limit=200`);
        const data = await secRes.json();
        const docs = (data.documents || []).map((d: any) => ({ id: d.document_id || d.id, name: d.filename || d.title || d.document_id }));
        setLibraryDocs(docs);
      }
    } catch (e) {
      setLibraryDocs([]);
    }
  };

  useEffect(() => {
    loadLibrary();
  }, [domain, index]);

  // When parent hints a document, refresh library and select it
  useEffect(() => {
    if (!initialDocumentId || manuallyCleared) return;
    (async () => {
      await loadLibrary();
      setSelectedDocument(initialDocumentId);
    })();
  }, [initialDocumentId, manuallyCleared]);

  // Also handle the case where initialDocumentId is provided on first render
  useEffect(() => {
    if (initialDocumentId && selectedDocument !== initialDocumentId && !manuallyCleared) {
      setSelectedDocument(initialDocumentId);
      setLoading(true); // Set loading when document changes
    }
  }, [initialDocumentId, selectedDocument, manuallyCleared]);

  const mockDocumentStructure: DocumentStructure = {
    id: '1',
    filename: 'AAPL_10K_2023.pdf',
    totalPages: 112,
    processingStatus: 'completed',
    processingProgress: 100,
    sections: [
      {
        name: 'Business Overview',
        startPage: 1,
        endPage: 15,
        subsections: [
          {
            name: 'Company Description',
            startPage: 1,
            endPage: 5,
            chunks: [
              {
                id: 'chunk_1',
                content: 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide...',
                startPage: 1,
                endPage: 2,
                section: 'Business Overview',
                subsection: 'Company Description',
                chunkType: 'text',
                size: 512,
                overlap: 50,
                confidence: 0.95,
                citations: ['Page 1-2, Business Overview']
              },
              {
                id: 'chunk_2',
                content: 'The Company serves consumers and businesses worldwide through its retail and online stores, direct sales force...',
                startPage: 2,
                endPage: 3,
                section: 'Business Overview',
                subsection: 'Company Description',
                chunkType: 'text',
                size: 487,
                overlap: 50,
                confidence: 0.92,
                citations: ['Page 2-3, Business Overview']
              }
            ]
          },
          {
            name: 'Products and Services',
            startPage: 6,
            endPage: 15,
            chunks: [
              {
                id: 'chunk_3',
                content: 'iPhone revenue for fiscal 2023 was $200.6 billion, representing 52% of total net sales...',
                startPage: 8,
                endPage: 8,
                section: 'Business Overview',
                subsection: 'Products and Services',
                chunkType: 'text',
                size: 445,
                overlap: 50,
                confidence: 0.98,
                citations: ['Page 8, Products and Services']
              }
            ]
          }
        ]
      },
      {
        name: 'Financial Information',
        startPage: 16,
        endPage: 45,
        subsections: [
          {
            name: 'Consolidated Statements',
            startPage: 16,
            endPage: 25,
            chunks: [
              {
                id: 'chunk_4',
                content: 'Revenue breakdown by product category and geographic region for fiscal year 2023...',
                startPage: 18,
                endPage: 19,
                section: 'Financial Information',
                subsection: 'Consolidated Statements',
                chunkType: 'table',
                size: 678,
                overlap: 25,
                confidence: 0.89,
                citations: ['Page 18-19, Table 1: Revenue by Product Category']
              }
            ]
          }
        ]
      }
    ]
  };

  useEffect(() => {
    const loadStructure = async () => {
      if (!selectedDocument) return;
      
      setLoading(true);
      setChunkVisualizationData(null); // Clear previous data
      
      try {
        if (domain === 'insurance') {
          // Use SEC-style policy/claims chunk visualization endpoint
          const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
          const res = await fetch(`${apiBaseUrl}/knowledge-base/documents/${selectedDocument}/chunks?index=${index}`);
          const payload = await res.json();
          
          // Store the raw chunk visualization data (matching SEC format)
          setChunkVisualizationData(payload);
          
          // Handle the new ChunkVisualizationResponse format (same as SEC)
          const chunks = payload.chunks || [];
          const docInfo = payload.document_info || {};
          const chunkStats = payload.chunk_stats || {};

          // Build a richer structure from API response
          const structure: DocumentStructure = {
            id: selectedDocument,
            filename: docInfo.title || docInfo.source || selectedDocument,
            totalPages: chunkStats.page_range?.max || 1,
            processingStatus: 'completed',
            processingProgress: 100,
            sections: [
              {
                name: 'Document',
                startPage: chunkStats.page_range?.min || 1,
                endPage: chunkStats.page_range?.max || 1,
                subsections: [{
                  name: 'All Chunks', 
                  startPage: chunkStats.page_range?.min || 1, 
                  endPage: chunkStats.page_range?.max || 1,
                  chunks: chunks.slice(0, 200).map((c: any, idx: number) => ({
                    id: c.chunk_id || c.id || `chunk_${idx}`,
                    content: c.content || '',
                    startPage: c.page_number || 1,
                    endPage: c.page_number || 1,
                    section: c.section_type || 'Document',
                    subsection: 'All Chunks',
                    chunkType: 'text',
                    size: c.content_length || (c.content || '').length,
                    overlap: 0,
                    confidence: c.credibility_score ?? 0.9,
                    citations: c.citation_info ? [c.citation_info] : []
                  }))
                }]
              }
            ]
          };
          setDocumentStructure(structure);
          setAnalytics({
            total_chunks: chunkStats.total_chunks ?? chunks.length,
            avg_chunk_length: chunkStats.avg_chunk_length ?? 0,
            section_types: chunkStats.section_types ?? [],
          });
        } else {
          // Banking: use SEC document chunks endpoint
          const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
          const res = await fetch(`${apiBaseUrl}/sec/documents/${selectedDocument}/chunks`);
          const data = await res.json();
          // Expect data.chunks-like structure; reuse mock for now if missing
          setDocumentStructure(mockDocumentStructure);
        }
      } catch (e) {
        setDocumentStructure(null);
        setChunkVisualizationData(null);
      } finally {
        setLoading(false);
      }
    };
    loadStructure();
  }, [selectedDocument, domain]);

  const toggleSection = (sectionName: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionName)) {
      newExpanded.delete(sectionName);
    } else {
      newExpanded.add(sectionName);
    }
    setExpandedSections(newExpanded);
  };

  // Helper functions for SEC-style formatting
  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString();
  };

  const getCredibilityVariant = (score: number) => {
    if (score >= 0.8) return 'default';
    if (score >= 0.6) return 'secondary';
    return 'destructive';
  };

  const getChunksByPage = () => {
    if (!chunkVisualizationData?.chunks) return {};
    
    const chunksByPage: { [key: number]: any[] } = {};
    chunkVisualizationData.chunks.forEach((chunk: any) => {
      const page = chunk.page_number || 0;
      if (!chunksByPage[page]) {
        chunksByPage[page] = [];
      }
      chunksByPage[page].push(chunk);
    });
    
    return chunksByPage;
  };

  const getChunksBySection = () => {
    if (!chunkVisualizationData?.chunks) return {};
    
    const chunksBySection: { [key: string]: any[] } = {};
    chunkVisualizationData.chunks.forEach((chunk: any) => {
      const section = chunk.section_type || 'Unknown';
      if (!chunksBySection[section]) {
        chunksBySection[section] = [];
      }
      chunksBySection[section].push(chunk);
    });
    
    return chunksBySection;
  };

  // Show loading state
  if (loading) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <div className="text-muted-foreground">Loading chunk visualization...</div>
        </CardContent>
      </Card>
    );
  }

  // Show document selection if no document selected
  if (!selectedDocument) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Document Chunking Visualization</h2>
            <p className="text-muted-foreground">
              Visualize how {index} documents are processed and chunked for RAG analysis
            </p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Document Selection
            </CardTitle>
            <CardDescription>
              Select a document to visualize its chunking structure
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {libraryDocs.map((doc) => (
                <Button
                  key={doc.id}
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => {
                    setSelectedDocument(doc.id);
                    setManuallyCleared(false); // Reset manual flag when selecting a document
                  }}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  {doc.name}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show chunk visualization if we have data
  if (!chunkVisualizationData) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <div className="text-muted-foreground">No chunk data available</div>
          <Button onClick={() => setSelectedDocument('')} className="mt-4">
            Select Different Document
          </Button>
        </CardContent>
      </Card>
    );
  }

  const chunksByPage = getChunksByPage();
  const chunksBySection = getChunksBySection();
  const data = chunkVisualizationData;

  return (
    <div className="space-y-6">
      {/* Header - SEC Style */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  console.log('Back button clicked, clearing selected document');
                  console.log('onBack callback exists:', !!onBack);
                  if (onBack) {
                    console.log('Calling onBack callback');
                    onBack(); // Call parent callback to clear previewDoc
                  } else {
                    console.log('Using fallback state management');
                    // Fallback to local state management
                    setSelectedDocument('');
                    setChunkVisualizationData(null);
                    setManuallyCleared(true);
                  }
                }}
                className="flex items-center gap-2 hover:bg-gray-100"
                style={{ zIndex: 1000 }}
                title="Go back to document selection"
                aria-label="Go back to document selection"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  Chunk Visualization
                </CardTitle>
                <CardDescription>
                  Document analysis and chunk breakdown
                </CardDescription>
              </div>
            </div>
            <Button onClick={() => window.location.reload()} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-semibold text-lg">
                {data.document_info?.title || data.document_info?.source || selectedDocument}
              </h3>
              <p className="text-muted-foreground">
                {index.toUpperCase()} Document
              </p>
              <div className="flex items-center gap-4 text-sm text-muted-foreground mt-2">
                {data.document_info?.processed_at && (
                  <span className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    {formatDate(data.document_info.processed_at)}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Building className="h-4 w-4" />
                  ID: {selectedDocument}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{data.chunk_stats?.total_chunks || 0}</div>
                <div className="text-sm text-muted-foreground">Total Chunks</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{data.chunk_stats?.avg_chunk_length || 0}</div>
                <div className="text-sm text-muted-foreground">Avg Length</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs - SEC Style */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="chunks">Chunks</TabsTrigger>
          <TabsTrigger value="pages">By Page</TabsTrigger>
          <TabsTrigger value="sections">By Section</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Statistics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Document Statistics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span>Total Content Length</span>
                  <span className="font-mono">{data.chunk_stats?.total_content_length || 0} chars</span>
                </div>
                <div className="flex justify-between">
                  <span>Average Chunk Length</span>
                  <span className="font-mono">{data.chunk_stats?.avg_chunk_length || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Page Range</span>
                  <span className="font-mono">
                    {data.chunk_stats?.page_range?.min || 'N/A'} - {data.chunk_stats?.page_range?.max || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Section Types</span>
                  <span className="font-mono">{data.chunk_stats?.section_types?.length || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Average Credibility</span>
                  <span className="font-mono">
                    {data.chunk_stats?.avg_credibility_score ? 
                      `${(data.chunk_stats.avg_credibility_score * 100).toFixed(1)}%` : 
                      'N/A'
                    }
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Section Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Section Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(chunksBySection).map(([section, chunks]) => (
                    <div key={section} className="flex items-center justify-between">
                      <span className="text-sm">{section || 'Unknown'}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-32 bg-muted rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{ 
                              width: `${(chunks.length / (data.chunks?.length || 1)) * 100}%` 
                            }}
                          />
                        </div>
                        <span className="text-sm font-mono w-12 text-right">{chunks.length}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Chunks Tab */}
        <TabsContent value="chunks">
          <Card>
            <CardHeader>
              <CardTitle>All Chunks ({data.chunks?.length || 0})</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="space-y-4">
                  {(data.chunks || []).map((chunk: any, index: number) => (
                    <Card 
                      key={chunk.chunk_id || index}
                      className={`cursor-pointer transition-colors ${
                        selectedChunk?.id === chunk.chunk_id ? 'ring-2 ring-blue-500' : ''
                      }`}
                      onClick={() => setSelectedChunk({
                        id: chunk.chunk_id || `chunk_${index}`,
                        content: chunk.content || '',
                        startPage: chunk.page_number || 1,
                        endPage: chunk.page_number || 1,
                        section: chunk.section_type || 'general',
                        chunkType: 'text',
                        size: chunk.content_length || 0,
                        overlap: 0,
                        confidence: chunk.credibility_score || 0.5,
                        citations: chunk.citation_info ? [chunk.citation_info] : []
                      })}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant="outline">#{index + 1}</Badge>
                              {chunk.page_number && (
                                <Badge variant="secondary">Page {chunk.page_number}</Badge>
                              )}
                              {chunk.section_type && (
                                <Badge variant="outline">{chunk.section_type}</Badge>
                              )}
                              <Badge variant={getCredibilityVariant(chunk.credibility_score || 0.5)}>
                                {((chunk.credibility_score || 0.5) * 100).toFixed(0)}%
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground truncate">
                              {chunk.content || ''}
                            </p>
                            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                              <span>{chunk.content_length || 0} chars</span>
                              {chunk.citation_info && (
                                <span className="truncate">{chunk.citation_info}</span>
                              )}
                            </div>
                          </div>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* By Page Tab */}
        <TabsContent value="pages">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                Chunks by Page
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="space-y-4">
                  {Object.entries(chunksByPage)
                    .sort(([a], [b]) => Number(a) - Number(b))
                    .map(([page, chunks]) => (
                    <Card key={page}>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg">
                          Page {page === '0' ? 'Unknown' : page}
                          <Badge variant="secondary" className="ml-2">
                            {chunks.length} chunks
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {chunks.map((chunk: any, index: number) => (
                            <div key={chunk.chunk_id || index} className="text-sm p-2 bg-muted rounded">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-mono text-xs">#{index + 1}</span>
                                <Badge variant={getCredibilityVariant(chunk.credibility_score || 0.5)} className="text-xs">
                                  {((chunk.credibility_score || 0.5) * 100).toFixed(0)}%
                                </Badge>
                              </div>
                              <p className="text-muted-foreground">
                                {chunk.content && chunk.content.length > 100 
                                  ? `${chunk.content.substring(0, 100)}...` 
                                  : chunk.content || ''
                                }
                              </p>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* By Section Tab */}
        <TabsContent value="sections">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Hash className="h-5 w-5" />
                Chunks by Section
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="space-y-4">
                  {Object.entries(chunksBySection).map(([section, chunks]) => (
                    <Card key={section}>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg">
                          {section || 'Unknown Section'}
                          <Badge variant="secondary" className="ml-2">
                            {chunks.length} chunks
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {chunks.map((chunk: any, index: number) => (
                            <div key={chunk.chunk_id || index} className="text-sm p-2 bg-muted rounded">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-mono text-xs">
                                  #{index + 1} {chunk.page_number ? `(Page ${chunk.page_number})` : ''}
                                </span>
                                <Badge variant={getCredibilityVariant(chunk.credibility_score || 0.5)} className="text-xs">
                                  {((chunk.credibility_score || 0.5) * 100).toFixed(0)}%
                                </Badge>
                              </div>
                              <p className="text-muted-foreground">
                                {chunk.content && chunk.content.length > 100 
                                  ? `${chunk.content.substring(0, 100)}...` 
                                  : chunk.content || ''
                                }
                              </p>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Selected Chunk Detail */}
      {selectedChunk && (
        <Card>
          <CardHeader>
            <CardTitle>Chunk Details</CardTitle>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setSelectedChunk(null)}
              className="w-fit"
            >
              Close
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{selectedChunk.id}</Badge>
                <Badge variant="secondary">Page {selectedChunk.startPage}</Badge>
                <Badge variant="outline">{selectedChunk.section}</Badge>
                <Badge variant={getCredibilityVariant(selectedChunk.confidence)}>
                  Credibility: {(selectedChunk.confidence * 100).toFixed(1)}%
                </Badge>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Content</h4>
                <div className="bg-muted p-4 rounded-lg">
                  <p className="text-sm">{selectedChunk.content}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Length:</span> {selectedChunk.size} characters
                </div>
                <div>
                  <span className="font-medium">Type:</span> {selectedChunk.chunkType}
                </div>
              </div>
              {selectedChunk.citations.length > 0 && (
                <div>
                  <span className="font-medium">Citations:</span> {selectedChunk.citations.join(', ')}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Document Chunking Visualization</h2>
          <p className="text-muted-foreground">
            Visualize how financial documents are processed and chunked for RAG analysis
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="flex items-center gap-1">
            <Zap className="h-3 w-3" />
            {chunkingStrategy.charAt(0).toUpperCase() + chunkingStrategy.slice(1)} Strategy
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Document Selection
            </CardTitle>
            <CardDescription>
              Select a document to visualize its chunking structure
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              {libraryDocs.map((doc) => (
                <Button
                  key={doc.id}
                  variant={selectedDocument === doc.id ? "default" : "outline"}
                  className="w-full justify-start"
                  onClick={() => setSelectedDocument(doc.id)}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  {doc.name}
                </Button>
              ))}
            </div>

            {documentStructure && (
              <div className="space-y-3 pt-4 border-t">
                <div className="flex items-center justify-between text-sm">
                  <span>Processing Status:</span>
                  <Badge variant={documentStructure.processingStatus === 'completed' ? 'default' : 'secondary'}>
                    {documentStructure.processingStatus}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>Progress:</span>
                    <span>{documentStructure.processingProgress}%</span>
                  </div>
                  <Progress value={documentStructure.processingProgress} className="h-2" />
                </div>
                <div className="text-sm text-muted-foreground">
                  {documentStructure.totalPages} pages • {documentStructure.sections.length} sections
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              Document Structure
            </CardTitle>
            <CardDescription>
              Hierarchical view of document sections and chunks
            </CardDescription>
          </CardHeader>
          <CardContent>
            {documentStructure ? (
              <ScrollArea className="h-[600px] pr-4">
                <div className="space-y-4">
                  {analytics && (
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">{analytics.total_chunks}</div>
                        <div className="text-sm text-muted-foreground">Total Chunks</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">{analytics.avg_chunk_length}</div>
                        <div className="text-sm text-muted-foreground">Avg Length</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-muted-foreground">Sections: {analytics.section_types.join(', ')}</div>
                      </div>
                    </div>
                  )}
                  {documentStructure.sections.map((section) => (
                    <div key={section.name} className="border rounded-lg p-4">
                      <div
                        className="flex items-center justify-between cursor-pointer"
                        onClick={() => toggleSection(section.name)}
                      >
                        <div className="flex items-center gap-2">
                          {expandedSections.has(section.name) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                          <h3 className="font-semibold">{section.name}</h3>
                          <Badge variant="outline" className="text-xs">
                            Pages {section.startPage}-{section.endPage}
                          </Badge>
                        </div>
                        <Badge variant="secondary">
                          {section.subsections.reduce((acc, sub) => acc + sub.chunks.length, 0)} chunks
                        </Badge>
                      </div>

                      {expandedSections.has(section.name) && (
                        <div className="mt-4 space-y-3">
                          {section.subsections.map((subsection) => (
                            <div key={subsection.name} className="ml-6 border-l-2 border-gray-200 pl-4">
                              <div className="flex items-center gap-2 mb-2">
                                <h4 className="font-medium text-sm">{subsection.name}</h4>
                                <Badge variant="outline" className="text-xs">
                                  Pages {subsection.startPage}-{subsection.endPage}
                                </Badge>
                              </div>
                              <div className="space-y-2">
                                {subsection.chunks.map((chunk) => (
                                  <div
                                    key={chunk.id}
                                    className={`p-3 rounded border cursor-pointer transition-colors ${
                                      selectedChunk?.id === chunk.id
                                        ? 'border-blue-500 bg-blue-50'
                                        : 'border-gray-200 hover:border-gray-300'
                                    }`}
                                    onClick={() => setSelectedChunk(chunk)}
                                  >
                                    <div className="flex items-center justify-between mb-2">
                                      <div className="flex items-center gap-2">
                                        {getChunkTypeIcon(chunk.chunkType)}
                                        <Badge className={`text-xs ${getChunkTypeColor(chunk.chunkType)}`}>
                                          {chunk.chunkType}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground">
                                          {chunk.size} chars
                                        </span>
                                      </div>
                                      <div className="flex items-center gap-2">
                                        <span className={`text-xs font-medium ${getConfidenceColor(chunk.confidence)}`}>
                                          {(chunk.confidence * 100).toFixed(0)}%
                                        </span>
                                        <Button size="sm" variant="ghost" className="h-6 w-6 p-0">
                                          <Eye className="h-3 w-3" />
                                        </Button>
                                      </div>
                                    </div>
                                    <p className="text-xs text-muted-foreground line-clamp-2">
                                      {chunk.content}
                                    </p>
                                    <div className="flex items-center gap-2 mt-2">
                                      <MapPin className="h-3 w-3 text-muted-foreground" />
                                      <span className="text-xs text-muted-foreground">
                                        Pages {chunk.startPage}-{chunk.endPage}
                                      </span>
                                      {chunk.overlap > 0 && (
                                        <Badge variant="outline" className="text-xs">
                                          {chunk.overlap} char overlap
                                        </Badge>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-muted-foreground">
                <div className="text-center">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Select a document to view its chunking structure</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {selectedChunk && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Chunk Details
            </CardTitle>
            <CardDescription>
              Detailed information about the selected chunk
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="content" className="w-full">
              <TabsList>
                <TabsTrigger value="content">Content</TabsTrigger>
                <TabsTrigger value="metadata">Metadata</TabsTrigger>
                <TabsTrigger value="citations">Citations</TabsTrigger>
              </TabsList>
              
              <TabsContent value="content" className="space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  {getChunkTypeIcon(selectedChunk.chunkType)}
                  <Badge className={getChunkTypeColor(selectedChunk.chunkType)}>
                    {selectedChunk.chunkType}
                  </Badge>
                  <Badge variant="outline">
                    {selectedChunk.size} characters
                  </Badge>
                  <Badge variant="outline" className={getConfidenceColor(selectedChunk.confidence)}>
                    {(selectedChunk.confidence * 100).toFixed(0)}% confidence
                  </Badge>
                </div>
                <ScrollArea className="h-[300px] w-full border rounded p-4">
                  <p className="text-sm leading-relaxed">{selectedChunk.content}</p>
                </ScrollArea>
              </TabsContent>
              
              <TabsContent value="metadata" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Chunk ID</label>
                    <p className="text-sm text-muted-foreground">{selectedChunk.id}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Section</label>
                    <p className="text-sm text-muted-foreground">{selectedChunk.section}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Subsection</label>
                    <p className="text-sm text-muted-foreground">{selectedChunk.subsection || 'N/A'}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Page Range</label>
                    <p className="text-sm text-muted-foreground">
                      {selectedChunk.startPage}-{selectedChunk.endPage}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Chunk Size</label>
                    <p className="text-sm text-muted-foreground">{selectedChunk.size} characters</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Overlap</label>
                    <p className="text-sm text-muted-foreground">{selectedChunk.overlap} characters</p>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="citations" className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Citation References</label>
                  <div className="space-y-2">
                    {selectedChunk.citations.map((citation, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 border rounded">
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{citation}</span>
                        <Button size="sm" variant="ghost" className="ml-auto">
                          <Download className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ChunkingVisualization;
