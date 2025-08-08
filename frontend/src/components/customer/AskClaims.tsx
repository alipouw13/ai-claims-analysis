import React from 'react';
import { ChatContainer } from '@/components/chat/ChatContainer';
import { ModelSettings } from '@/components/shared/ModelConfiguration';

export const AskClaims: React.FC<{ settings: ModelSettings }> = ({ settings }) => {
  return (
    <div className="p-6">
      <ChatContainer modelSettings={settings} />
    </div>
  );
};

export default AskClaims;


