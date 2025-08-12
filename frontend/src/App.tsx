import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MessageSquare, BarChart3, HelpCircle, FileText, Building2, LayoutDashboard } from 'lucide-react';
import { ChatContainer } from '@/components/chat/ChatContainer';
import { AdminDashboard } from '@/components/admin/AdminDashboard';
import KnowledgeBaseManager from '@/components/knowledge-base/KnowledgeBaseManager';
import SECDocumentsManager from '@/components/sec-documents/SECDocumentsManager';
import InsuranceDashboard from '@/components/dashboard/InsuranceDashboard';
import BankingDashboard from '@/components/dashboard/BankingDashboard';
import { QAContainer } from '@/components/qa/QAContainer';
import { ModelConfiguration, ModelSettings } from '@/components/shared/ModelConfiguration';
import { CitigroupLogo } from '@/components/shared/CitigroupLogo';
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext';
import './App.css';
import ClaimsSummary from '@/components/customer/ClaimsSummary';
import SubmitClaim from '@/components/customer/SubmitClaim';
import AskClaims from '@/components/customer/AskClaims';
// (already imported above)

type Role = 'admin' | 'underwriter' | 'customer' | 'analyst';

const AppContent = () => {
  const [activeTab, setActiveTab] = useState('documents');
  const [role, setRole] = useState<Role>('admin');
  const [domain, setDomain] = useState<'insurance' | 'banking'>((localStorage.getItem('domain') as any) || 'insurance');
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [globalModelSettings, setGlobalModelSettings] = useState<ModelSettings>({
    selectedModel: 'gpt-4',
    embeddingModel: 'text-embedding-ada-002',
    searchType: 'hybrid',
    temperature: 0.0,
    maxTokens: 2000,
  });

  const { theme, setTheme } = useTheme();

  const handleModelSettingsChange = (settings: Partial<ModelSettings>) => {
    setGlobalModelSettings(prev => ({ ...prev, ...settings }));
  };

  const visibleTabs = (
    role === 'customer'
      ? ['dashboard', 'claims', 'submit', 'ask']
      : domain === 'banking'
        ? ['dashboard', 'chat', 'qa', 'sec-docs', 'admin']
        : ['dashboard', 'chat', 'qa', 'documents', 'admin']
  );

  return (
    <div className={`min-h-screen transition-colors duration-200 ${
      theme === 'dark' ? 'dark bg-background text-foreground' : 
      theme === 'customer' ? 'customer bg-background text-foreground' :
      'bg-background text-foreground'
    }`}>
      <div className="border-b bg-background">
        <div className="flex h-16 items-center px-4">
          {/* Left: Brand and product name */}
          <div className="flex items-center gap-2">
            <CitigroupLogo size="md" domain={domain} />
            <span className="ml-2 text-xs rounded bg-secondary px-2 py-0.5">
              {role.charAt(0).toUpperCase() + role.slice(1)} Access
            </span>
          </div>

          {/* Center nav removed per request */}

          {/* Right: Domain + Persona segmented controls */}
          <div className="ml-auto flex items-center gap-4">
            {/* Domain toggle */}
            <div className="inline-flex rounded-md border p-0.5 bg-background">
              {(['insurance','banking'] as const).map(d => (
                <button
                  key={d}
                  className={`px-3 py-1 text-xs rounded-sm ${domain===d ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-muted'}`}
                  onClick={() => {
                    setDomain(d);
                    localStorage.setItem('domain', d);
                    if (role !== 'customer') setActiveTab(d==='banking' ? 'sec-docs' : 'documents');
                  }}
                >
                  {d.charAt(0).toUpperCase()+d.slice(1)}
                </button>
              ))}
            </div>
            <div className="inline-flex rounded-md border p-0.5 bg-background">
              {(domain==='banking' ? (['admin','analyst','customer'] as Role[]) : (['admin','underwriter','customer'] as Role[])).map(r => (
                <button
                  key={r}
                  className={`px-3 py-1 text-xs rounded-sm ${role===r ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-muted'}`}
                  onClick={() => {
                    setRole(r);
                    setTheme(r==='customer' ? 'customer' : 'light');
                    setActiveTab(r==='customer' ? 'claims' : 'dashboard');
                  }}
                >
                  {r.charAt(0).toUpperCase()+r.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Below header: main nav tabs similar to previous layout for desktop */}
        <div className="flex items-center px-4 pb-2">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-6">
                {visibleTabs.includes('dashboard') && (
                  <TabsTrigger value="dashboard" className="flex items-center gap-2">
                    <LayoutDashboard className="h-4 w-4" />
                    Dashboard
                  </TabsTrigger>
                )}
                {visibleTabs.includes('chat') && (
                  <TabsTrigger value="chat" className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    Chat
                  </TabsTrigger>
                )}
                {visibleTabs.includes('qa') && (
                  <TabsTrigger value="qa" className="flex items-center gap-2">
                    <HelpCircle className="h-4 w-4" />
                    Q&A
                  </TabsTrigger>
                )}
                {visibleTabs.includes('documents') && (
                  <TabsTrigger value="documents" className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Documents
                  </TabsTrigger>
                )}
                {visibleTabs.includes('sec-docs') && (
                  <TabsTrigger value="sec-docs" className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    SEC Docs
                  </TabsTrigger>
                )}
                {visibleTabs.includes('admin') && (
                  <TabsTrigger value="admin" className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    Admin
                  </TabsTrigger>
                )}
                {visibleTabs.includes('claims') && (
                  <TabsTrigger value="claims" className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    My Claims
                  </TabsTrigger>
                )}
                {visibleTabs.includes('submit') && (
                  <TabsTrigger value="submit" className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Submit Claim
                  </TabsTrigger>
                )}
                {visibleTabs.includes('ask') && (
                  <TabsTrigger value="ask" className="flex items-center gap-2">
                    <HelpCircle className="h-4 w-4" />
                    Ask Questions
                  </TabsTrigger>
                )}
              </TabsList>
            </Tabs>
        </div>
      </div>

      {/* Global Model Configuration */}
      {role !== 'customer' && (
        <ModelConfiguration
        settings={globalModelSettings}
        onSettingsChange={handleModelSettingsChange}
        showAdvanced={showAdvancedSettings}
        onToggleAdvanced={() => setShowAdvancedSettings(!showAdvancedSettings)}
        theme={theme}
        onThemeChange={setTheme}
        />
      )}

      <main className="flex-1 bg-background">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsContent value="dashboard" className="m-0 bg-background">
            {domain==='banking' ? <BankingDashboard /> : <InsuranceDashboard />}
          </TabsContent>
          <TabsContent value="chat" className="m-0 bg-background">
            <ChatContainer modelSettings={globalModelSettings} role={role} domain={domain} />
          </TabsContent>
          
          <TabsContent value="qa" className="m-0 bg-background">
            <QAContainer modelSettings={globalModelSettings} domain={domain} />
          </TabsContent>
          
          <TabsContent value="documents" className="m-0 bg-background">
            <KnowledgeBaseManager modelSettings={globalModelSettings} role={role} />
          </TabsContent>
          <TabsContent value="sec-docs" className="m-0 bg-background">
            <SECDocumentsManager />
          </TabsContent>
          
          
          
          <TabsContent value="admin" className="m-0 bg-background">
            <AdminDashboard isActive={activeTab === 'admin'} />
          </TabsContent>

          {/* Customer persona */}
          <TabsContent value="claims" className="m-0 bg-background">
            <ClaimsSummary />
          </TabsContent>
          <TabsContent value="submit" className="m-0 bg-background">
            <SubmitClaim />
          </TabsContent>
          <TabsContent value="ask" className="m-0 bg-background">
            <AskClaims settings={globalModelSettings} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
