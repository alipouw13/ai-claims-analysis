import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { startIngestion } from '@/services/workflowService';

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(',')[1]);
    reader.onerror = e => reject(e);
    reader.readAsDataURL(file);
  });
}

export const SubmitClaim: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [instanceId, setInstanceId] = useState<string | null>(null);

  const onUpload = async () => {
    if (files.length === 0) return;
    setSubmitting(true);
    try {
      const file = files[0];
      const b64 = await toBase64(file);
      const res = await startIngestion({
        content: b64,
        content_type: file.type || 'application/pdf',
        filename: file.name,
        metadata: { claim: true },
      });
      setInstanceId(res.id || res["id"]);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Submit New Claim</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <input type="file" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
          <Button onClick={onUpload} disabled={submitting || files.length === 0}>
            {submitting ? 'Uploading…' : 'Browse Files'}
          </Button>
          {instanceId && <div className="text-xs text-muted-foreground">Workflow started: {instanceId}</div>}
        </CardContent>
      </Card>
    </div>
  );
};

export default SubmitClaim;


