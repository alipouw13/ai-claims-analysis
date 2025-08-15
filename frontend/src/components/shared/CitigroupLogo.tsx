import React from 'react';
import msftLogo from '@/assets/msft-logo.png';

interface CitigroupLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  domain?: 'insurance' | 'banking';
}

export const CitigroupLogo: React.FC<CitigroupLogoProps> = ({ 
  className = '', 
  size = 'md',
  domain = 'insurance',
}) => {
  const sizeClasses = {
    sm: 'h-8 w-auto',
    md: 'h-10 w-auto',
    lg: 'h-14 w-auto'
  };

  const title = domain === 'banking' ? 'MSFT Banking' : 'MSFT Insurance';

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Microsoft Logo */}
      <img 
        src={msftLogo} 
        alt="Microsoft" 
        className={`${sizeClasses[size]} object-contain`}
      />
      
      {/* Text Content */}
      <div className="flex flex-col">
        <span className="text-xl font-bold text-foreground leading-tight">
          {title}
        </span>
        <span className="text-sm font-medium text-muted-foreground leading-tight">
          AI Assistant
        </span>
      </div>
    </div>
  );
};
