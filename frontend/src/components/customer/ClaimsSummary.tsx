import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export const ClaimsSummary: React.FC = () => {
  const claims = [
    { id: 'CLM-2024001', title: 'Auto accident claim - minor collision', value: 15000, status: 'Approved' },
    { id: 'CLM-2024002', title: 'Home damage claim - water damage', value: 25000, status: 'Under Review' },
    { id: 'CLM-2024003', title: 'Personal injury claim document', value: 12000, status: 'Processing' },
  ];

  return (
    <div className="p-6 space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">Total Claims</div><div className="text-2xl font-semibold">3</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">Approved</div><div className="text-2xl font-semibold">1</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">Under Review</div><div className="text-2xl font-semibold">2</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">Total Value</div><div className="text-2xl font-semibold">$52,000</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">My Claims</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {claims.map(c => (
            <div key={c.id} className="flex items-center justify-between border rounded p-3 text-sm">
              <div>
                <div className="font-medium">{c.id} <span className="ml-2 text-xs text-muted-foreground">{c.status}</span></div>
                <div className="text-muted-foreground text-xs">{c.title}</div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-xs">${c.value.toLocaleString()}</div>
                <Button variant="outline" size="sm">View Details</Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

export default ClaimsSummary;


