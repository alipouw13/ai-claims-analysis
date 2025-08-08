import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MessageSquare, BarChart3, HelpCircle, FileText } from 'lucide-react';
import { ChatContainer } from '@/components/chat/ChatContainer';
import { AdminDashboard } from '@/components/admin/AdminDashboard';
import KnowledgeBaseManager from '@/components/knowledge-base/KnowledgeBaseManager';
import { QAContainer } from '@/components/qa/QAContainer';
import SECDocumentsManager from '@/components/sec-documents/SECDocumentsManager';
import { ModelConfiguration, ModelSettings } from '@/components/shared/ModelConfiguration';
import { CitigroupLogo } from '@/components/shared/CitigroupLogo';
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext';
import './App.css';
import ClaimsSummary from '@/components/customer/ClaimsSummary';
import SubmitClaim from '@/components/customer/SubmitClaim';
import AskClaims from '@/components/customer/AskClaims';

type Role = 'admin' | 'underwriter' | 'customer';

const AppContent = () => {
  const [activeTab, setActiveTab] = useState('sec-docs');
  const [role, setRole] = useState<Role>('admin');
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
    role === 'customer' ? ['claims', 'submit', 'ask'] : ['chat', 'qa', 'sec-docs', 'admin']
  );

  return (
    <div className={`min-h-screen transition-colors duration-200 ${
      theme === 'dark' ? 'dark bg-background text-foreground' : 
      theme === 'customer' ? 'customer bg-background text-foreground' :
      'bg-background text-foreground'
    }`}>
      <div className="border-b bg-background">
        <div className="flex h-16 items-center px-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <MessageSquare className="h-6 w-6" />
              {theme === 'customer' ? (
                <CitigroupLogo size="md" />
              ) : (
                <h1 className="text-xl font-semibold">RAG Financial Assistant</h1>
              )}
            </div>
          </div>
          
          <div className="ml-auto flex items-center space-x-4">
            <select
              className="border rounded px-2 py-1 text-sm"
              value={role}
              onChange={(e) => {
                const r = e.target.value as Role;
                setRole(r);
                setTheme(r === 'customer' ? 'customer' : theme);
                setActiveTab(r === 'customer' ? 'claims' : 'chat');
              }}
            >
              <option value="admin">Admin</option>
              <option value="underwriter">Underwriter</option>
              <option value="customer">Customer</option>
            </select>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-[1000px]">
              <TabsList className="grid w-full grid-cols-5">
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
          <TabsContent value="chat" className="m-0 bg-background">
            <ChatContainer modelSettings={globalModelSettings} />
          </TabsContent>
          
          <TabsContent value="qa" className="m-0 bg-background">
            <QAContainer modelSettings={globalModelSettings} />
          </TabsContent>
          
          <TabsContent value="sec-docs" className="m-0 bg-background">
            <SECDocumentsManager />
          </TabsContent>
          
          <TabsContent value="knowledge-base" className="m-0 bg-background">
            <KnowledgeBaseManager modelSettings={globalModelSettings} />
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
