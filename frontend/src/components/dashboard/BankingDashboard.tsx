import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';

const StatCard: React.FC<{ title: string; value: string | number; subtitle?: string }> = ({ title, value, subtitle }) => (
  <div className="border rounded-md p-4 bg-card">
    <div className="text-xs text-muted-foreground">{title}</div>
    <div className="text-2xl font-semibold mt-1 text-black">{value}</div>
    {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
  </div>
);

const BankingDashboard: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load banking dashboard stats
      const statsResponse = await apiService.getBankingDashboardStats();
      if (statsResponse.status === 'success') {
        setStats(statsResponse.stats);
      }

    } catch (err: any) {
      console.error('Error loading banking dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <div className="text-center py-8">Loading banking dashboard data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 space-y-4">
        <div className="text-center py-8 text-red-600">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
        <StatCard title="Filings Indexed" value={stats?.total_filings || 0} subtitle="(from SEC database)" />
        <StatCard title="Companies" value={Object.keys(stats?.companies || {}).length} />
        <StatCard title="Avg Chunks/Doc" value={stats?.avg_chunks_per_doc || 0} />
        <StatCard title="Most Recent Filing" value={stats?.most_recent_filing || 'N/A'} />
      </div>

      <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3 text-black">Recent SEC Analysis</div>
          <ul className="space-y-2 text-sm">
            {Object.keys(stats?.companies || {}).length > 0 ? (
              Object.keys(stats.companies).slice(0, 5).map((company, i) => (
                <li key={i} className="flex items-center justify-between border rounded p-2">
                  <div>
                    <div className="font-medium text-blue-600">{company}</div>
                    <div className="text-xs text-muted-foreground">Form: 10-K • status: completed</div>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded bg-muted">completed</span>
                </li>
              ))
            ) : (
              <li className="text-center py-4 text-muted-foreground">No companies found</li>
            )}
          </ul>
        </div>
        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3 text-black">Form Types Distribution</div>
          <div className="space-y-3">
            {Object.keys(stats?.form_types || {}).length > 0 ? (
              Object.entries(stats.form_types).map(([formType, count]) => (
                <div key={formType}>
                  <div className="flex justify-between text-xs mb-1">
                    <span>{formType}</span>
                    <span>{count as number}</span>
                  </div>
                  <div className="h-2 bg-muted rounded">
                    <div className="h-2 bg-blue-600 rounded" style={{
                      width: `${stats.total_filings ? ((count as number) / stats.total_filings * 100) : 0}%`
                    }}/>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-4 text-muted-foreground">No form types found</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BankingDashboard;


