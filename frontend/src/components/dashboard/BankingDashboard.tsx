import React from 'react';

const StatCard: React.FC<{ title: string; value: string | number; subtitle?: string }> = ({ title, value, subtitle }) => (
  <div className="border rounded-md p-4 bg-card">
    <div className="text-xs text-muted-foreground">{title}</div>
    <div className="text-2xl font-semibold mt-1">{value}</div>
    {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
  </div>
);

const BankingDashboard: React.FC = () => {
  return (
    <div className="p-6 space-y-4">
      <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
        <StatCard title="Filings Indexed" value={8} subtitle="(sample data)" />
        <StatCard title="Companies" value={6} />
        <StatCard title="Avg Chunks/Doc" value={148.62} />
        <StatCard title="Most Recent Filing" value={'7/29/2025'} />
      </div>

      <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3">Recent SEC Analysis</div>
          <ul className="space-y-2 text-sm">
            {['PNC Financial Services','JPMorgan Chase & Co','Meta Platforms, Inc.','NVIDIA Corp','Microsoft Corp'].map((name, i) => (
              <li key={i} className="flex items-center justify-between border rounded p-2">
                <div>
                  <div className="font-medium">{name}</div>
                  <div className="text-xs text-muted-foreground">Form: 10-K • status: completed</div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded bg-muted">completed</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3">Form Types Distribution</div>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1"><span>10-K</span><span>100%</span></div>
              <div className="h-2 bg-muted rounded"><div className="h-2 bg-blue-500 rounded" style={{width:'100%'}}/></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BankingDashboard;


