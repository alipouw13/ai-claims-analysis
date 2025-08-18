import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';

const StatCard: React.FC<{ title: string; value: string | number; subtitle?: string }> = ({ title, value, subtitle }) => (
  <div className="border rounded-md p-4 bg-card">
    <div className="text-xs text-muted-foreground">{title}</div>
    <div className="text-2xl font-semibold mt-1 text-black">{value}</div>
    {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
  </div>
);

const InsuranceDashboard: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [recentClaims, setRecentClaims] = useState<any[]>([]);
  const [recentPolicies, setRecentPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load dashboard stats
      const statsResponse = await apiService.getDashboardStats();
      if (statsResponse.status === 'success') {
        setStats(statsResponse.stats);
      }

      // Load recent claims
      const claimsResponse = await apiService.getRecentClaims(4);
      if (claimsResponse.status === 'success') {
        setRecentClaims(claimsResponse.claims);
      }

      // Load recent policies
      const policiesResponse = await apiService.getRecentPolicies(6);
      if (policiesResponse.status === 'success') {
        setRecentPolicies(policiesResponse.policies);
      }

    } catch (err: any) {
      console.error('Error loading dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <div className="text-center py-8">Loading dashboard data...</div>
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
      {/* Top stats */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
        <StatCard title="Total Policies" value={stats?.total_policies || 0} subtitle="(uploaded for analysis)" />
        <StatCard title="Total Claims" value={stats?.total_claims || 0} subtitle="(pending review)" />
        <StatCard title="Avg Risk Score" value={stats?.avg_risk_score || 0} />
        <StatCard title="Auto Approval" value={`${stats?.auto_approval_percentage || 0}%`} subtitle="Eligible for auto-approval" />
      </div>

      {/* Portfolio summary */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-3">
        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3 text-black">Portfolio Summary</div>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-muted-foreground">Number of Policy Types</div>
              <div className="text-xl font-semibold text-black">{Object.keys(stats?.policy_types || {}).length}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Total Coverage Amount</div>
              <div className="text-xl font-semibold text-black">$26,250,000</div>
            </div>
          </div>
        </div>

        <div className="border rounded-md p-4 bg-card md:col-span-2">
          <div className="text-sm font-medium mb-3 text-black">AI Risk Distribution</div>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1"><span>Low Risk</span><span>{stats?.risk_distribution?.low_risk || 0} policies</span></div>
              <div className="h-2 bg-muted rounded"><div className="h-2 bg-green-500 rounded" style={{width:`${stats?.total_policies ? (stats.risk_distribution?.low_risk / stats.total_policies * 100) : 0}%`}}/></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span>Medium Risk</span><span>{stats?.risk_distribution?.medium_risk || 0} policies</span></div>
              <div className="h-2 bg-muted rounded"><div className="h-2 bg-yellow-500 rounded" style={{width:`${stats?.total_policies ? (stats.risk_distribution?.medium_risk / stats.total_policies * 100) : 0}%`}}/></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span>High Risk</span><span>{stats?.risk_distribution?.high_risk || 0} policies</span></div>
              <div className="h-2 bg-muted rounded"><div className="h-2 bg-red-500 rounded" style={{width:`${stats?.total_policies ? (stats.risk_distribution?.high_risk / stats.total_policies * 100) : 0}%`}}/></div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent claims for review */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3 text-black">Recent Claims for Review</div>
          <ul className="space-y-2 text-sm">
            {recentClaims.length > 0 ? (
              recentClaims.map((claim, i) => (
                <li key={i} className="flex items-center justify-between border rounded p-2">
                  <div>
                    <div className="font-medium text-blue-600">{claim.filename} - {claim.type}</div>
                    <div className="text-xs text-muted-foreground">Amount: {claim.amount} • status: {claim.status}</div>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-800">{claim.status}</span>
                </li>
              ))
            ) : (
              <li className="text-center py-4 text-muted-foreground">No recent claims found</li>
            )}
          </ul>
        </div>

        <div className="border rounded-md p-4 bg-card">
          <div className="text-sm font-medium mb-3 text-black">Policy Types Analyzed</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {Object.keys(stats?.policy_types || {}).length > 0 ? (
              Object.entries(stats.policy_types).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between border rounded p-2">
                  <span>{type}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-muted">analyzed ({count as number})</span>
                </div>
              ))
            ) : (
              <div className="col-span-2 text-center py-4 text-muted-foreground">No policy types found</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InsuranceDashboard;


