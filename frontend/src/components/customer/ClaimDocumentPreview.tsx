import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, Download, Eye, RefreshCw, CheckCircle, AlertCircle, X } from 'lucide-react';
import { apiService } from '@/services/api';

interface ClaimDocumentPreviewProps {
  documentId: string;
  filename: string;
  onClose: () => void;
}

interface ExtractedData {
  policy_claim_info?: {
    first_name?: string;
    last_name?: string;
    telephone_number?: string;
    policy_number?: string;
    coverage_type?: string;
    claim_number?: string;
    policy_effective_date?: string;
    policy_expiration_date?: string;
    damage_deductible?: number;
    date_of_damage_loss?: string;
    time_of_loss?: string;
    date_prepared?: string;
  };
  property_address?: {
    street?: string;
    city?: string;
    state?: string;
    postal_code?: string;
    country?: string;
  };
  mailing_address?: {
    street?: string;
    city?: string;
    state?: string;
    postal_code?: string;
    country?: string;
  };
  claim_details?: {
    cause_of_loss?: string;
    estimated_loss?: number;
    items_damaged?: Array<{
      item?: string;
      description?: string;
      date_acquired?: string;
      cost_new?: number;
      repair_cost?: number;
    }>;
  };
  processing_metadata?: {
    entity_score?: number;
    schema_score?: number;
    confidence_score?: number;
    processing_time_seconds?: number;
    extraction_model?: string;
    schema_version?: string;
  };
}

interface ProcessingSteps {
  step: string;
  status: 'completed' | 'processing' | 'failed';
  message: string;
  timestamp: string;
  duration_seconds?: number;
}

export const ClaimDocumentPreview: React.FC<ClaimDocumentPreviewProps> = ({
  documentId,
  filename,
  onClose
}) => {
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [processingSteps, setProcessingSteps] = useState<ProcessingSteps[]>([]);
  const [documentContent, setDocumentContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('extracted');

  useEffect(() => {
    loadDocumentData();
  }, [documentId]);

  const loadDocumentData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load extracted data from the API
      const [extractedDataResponse, processingStepsResponse] = await Promise.all([
        apiService.getDocumentExtractedData(documentId),
        apiService.getDocumentProcessingSteps(documentId)
      ]);

      setExtractedData(extractedDataResponse.extracted_data);
      setProcessingSteps(processingStepsResponse.processing_steps.map(step => ({
        step: step.step,
        status: step.status as 'completed' | 'processing' | 'failed',
        message: step.message,
        timestamp: step.timestamp,
        duration_seconds: step.duration_seconds
      })));

      // Mock document content (in real implementation, this would come from the document content endpoint)
      const mockDocumentContent = `
CONTOSO CLAIM FORM
Property Loss or Damage Claim

1. POLICY & CLAIM INFORMATION
Policyholder: Emma Martinez
Policy Number: PH789012
Coverage Type: Homeowners
Claim Number: CL456789
Date of Loss: 2021-07-25
Time of Loss: 16:45

Property Address:
9101 Oak St
Brooklyn, NY 11201

2. CLAIM DETAILS
Cause of Loss: A tree fell on the roof during a storm, causing structural damage and water leakage into the attic.

Estimated Loss: $25,000

Items Damaged:
- Samsung Galaxy S20 (Water damage)
- Dell XPS 15 Laptop (Falling debris damage)
- Various household items

3. CONTACT INFORMATION
Phone: 718-555-0321
Email: emma.martinez@email.com

Date Prepared: 2021-07-26
      `;

      setDocumentContent(mockDocumentContent);

    } catch (err) {
      console.error('Failed to load document data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load document data');
    } finally {
      setLoading(false);
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

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
          <div className="flex items-center space-x-3">
            <RefreshCw className="h-6 w-6 animate-spin text-blue-500" />
            <span className="text-lg">Loading document preview...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Error Loading Document</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <div className="flex space-x-2 justify-center">
              <Button onClick={loadDocumentData} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
              <Button onClick={onClose} variant="outline">
                Close
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[9999] flex" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 9999 }}>
      {/* Left Panel - Document List */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Content</h2>
            <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-3">
            <div className="p-4 border border-gray-200 rounded-lg bg-blue-50">
              <div className="flex items-center space-x-2 mb-3">
                <FileText className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-sm text-gray-900">{filename}</span>
                {getStatusBadge('completed')}
              </div>
              <div className="space-y-1 text-xs text-gray-600">
                <div className="flex justify-between">
                  <span>Entity Score:</span>
                  <span className="font-medium text-green-600">99% ↗</span>
                </div>
                <div className="flex justify-between">
                  <span>Schema Score:</span>
                  <span className="font-medium text-green-600">98% ↗</span>
                </div>
                <div className="flex justify-between">
                  <span>Processed:</span>
                  <span className="font-medium">2.3s</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Panel - Extracted Results */}
      <div className="flex-1 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="extracted">Extracted Results</TabsTrigger>
              <TabsTrigger value="steps">Process Steps</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          <TabsContent value="extracted" className="mt-0">
            <div className="space-y-6">
              {/* Policy & Claim Information */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h3 className="font-semibold text-gray-900 mb-3">Policy & Claim Information</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {extractedData?.policy_claim_info && Object.entries(extractedData.policy_claim_info).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center">
                      <span className="text-gray-600 font-medium">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span>
                      <span className="text-gray-900 font-semibold">{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Property Address */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h3 className="font-semibold text-gray-900 mb-3">Property Address</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {extractedData?.property_address && Object.entries(extractedData.property_address).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center">
                      <span className="text-gray-600 font-medium">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span>
                      <span className="text-gray-900 font-semibold">{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Claim Details */}
              {extractedData?.claim_details && (
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <h3 className="font-semibold text-gray-900 mb-3">Claim Details</h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <span className="text-gray-600 font-medium">Cause of Loss:</span>
                      <p className="text-gray-900 font-semibold mt-1">{extractedData.claim_details.cause_of_loss}</p>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 font-medium">Estimated Loss:</span>
                      <span className="text-gray-900 font-semibold">${extractedData.claim_details.estimated_loss?.toLocaleString()}</span>
                    </div>
                  </div>
                  
                  {extractedData.claim_details.items_damaged && extractedData.claim_details.items_damaged.length > 0 && (
                    <div className="mt-4">
                      <h4 className="font-medium text-gray-900 mb-3">Items Damaged</h4>
                      <div className="space-y-3">
                        {extractedData.claim_details.items_damaged.map((item, index) => (
                          <div key={index} className="border border-gray-200 rounded p-3 bg-white">
                            <div className="font-semibold text-gray-900">{item.item}</div>
                            <div className="text-xs text-gray-600 mt-1">{item.description}</div>
                            <div className="text-xs text-gray-500 mt-2 flex justify-between">
                              <span>Cost: ${item.cost_new?.toLocaleString()}</span>
                              <span>Repair: ${item.repair_cost?.toLocaleString()}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Processing Metadata */}
              {extractedData?.processing_metadata && (
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <h3 className="font-semibold text-gray-900 mb-3">Processing Metadata</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {Object.entries(extractedData.processing_metadata).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center">
                        <span className="text-gray-600 font-medium">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span>
                        <span className="text-gray-900 font-semibold">
                          {typeof value === 'number' && key.includes('score') ? `${value}%` : value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="steps" className="mt-0">
            <div className="space-y-4">
              {processingSteps.map((step, index) => (
                <div key={index} className="flex items-start space-x-4 p-4 border border-gray-200 rounded-lg bg-gray-50">
                  {getStatusIcon(step.status)}
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900">{step.step}</div>
                    <div className="text-sm text-gray-600 mt-1">{step.message}</div>
                    <div className="text-xs text-gray-500 mt-2 flex justify-between">
                      <span>{new Date(step.timestamp).toLocaleString()}</span>
                      {step.duration_seconds && (
                        <span>Duration: {step.duration_seconds}s</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>
        </div>
      </div>

      {/* Right Panel - Source Content */}
      <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Source Content</h3>
            <div className="flex space-x-2">
              <Button variant="outline" size="sm" className="h-8">
                <Eye className="h-4 w-4 mr-1" />
                View
              </Button>
              <Button variant="outline" size="sm" className="h-8">
                <Download className="h-4 w-4 mr-1" />
                Download
              </Button>
            </div>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <div className="bg-gray-50 rounded-lg p-4 h-full border border-gray-200">
            <div className="text-sm font-mono whitespace-pre-wrap text-gray-900 leading-relaxed">
              {documentContent}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClaimDocumentPreview;
