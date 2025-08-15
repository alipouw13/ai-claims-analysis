import React from 'react';

const StatCard: React.FC<{ title: string; value: string | number; subtitle?: string }> = ({ title, value, subtitle }) => (
  <div className="border rounded-md p-4 bg-card">
    <div className="text-xs text-muted-foreground">{title}</div>
    <div className="text-2xl font-semibold mt-1 text-black">{value}</div>
    {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
  </div>
);

const InsuranceDashboard: React.FC = () => {
  return (
    <div className="p-6 space-y-4">
      {/* Top stats */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
        <StatCard title="Total Documents" value={6} subtitle="(sample data)" />
        <StatCard title="Processing" value={0} subtitle="Documents in queue" />
        <StatCard title="Avg Risk Score" value={46} />
        <StatCard title="Auto Approval" value={'50%'} subtitle="Eligible for auto-approval" />
      </div>

      {/* Portfolio summary */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-3">
        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3 text-black">Portfolio Summary</div>
          <div className="grid grid-cols-3 text-center">
            <div>
              <div className="text-xs text-muted-foreground">Total Coverage</div>
              <div className="text-xl font-semibold text-black">$26,250,000</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Policy Types</div>
              <div className="text-xl font-semibold text-black">6</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">AI Analyzed</div>
              <div className="text-xl font-semibold text-black">6</div>
            </div>
          </div>
        </div>

        <div className="border rounded-md p-4 bg-card md:col-span-2">
          <div className="text-sm font-medium mb-3 text-black">AI Risk Distribution</div>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1"><span>Low Risk</span><span>2 policies</span></div>
              <div className="h-2 bg-muted rounded"><div className="h-2 bg-green-500 rounded" style={{width:'33%'}}/></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span>Medium Risk</span><span>3 policies</span></div>
              <div className="h-2 bg-muted rounded"><div className="h-2 bg-yellow-500 rounded" style={{width:'50%'}}/></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span>High Risk</span><span>1 policies</span></div>
              <div className="h-2 bg-muted rounded"><div className="h-2 bg-red-500 rounded" style={{width:'17%'}}/></div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent AI analysis */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3 text-black">Recent AI Analysis</div>
          <ul className="space-y-2 text-sm">
            {['Umbrella Insurance','Commercial Property','Life Insurance','Commercial Liability','Home Insurance'].map((name, i) => (
              <li key={i} className="flex items-center justify-between border rounded p-2">
                <div>
                  <div className="font-medium text-blue-600">{name} Analysis Complete</div>
                  <div className="text-xs text-muted-foreground">risk level: MEDIUM • completed</div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded bg-muted">completed</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3 text-black">Policy Types Analyzed</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {['Auto Insurance','Life Insurance','Home Insurance','Commercial Property','Commercial Liability','Umbrella Insurance'].map((p) => (
              <div key={p} className="flex items-center justify-between border rounded p-2">
                <span>{p}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-muted">sample</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InsuranceDashboard;


