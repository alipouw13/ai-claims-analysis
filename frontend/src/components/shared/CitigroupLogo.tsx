import React from 'react';

interface CitigroupLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const CitigroupLogo: React.FC<CitigroupLogoProps> = ({ 
  className = '', 
  size = 'md' 
}) => {
  const sizeClasses = {
    sm: 'h-6 w-24',
    md: 'h-8 w-32',
    lg: 'h-12 w-48'
  };

  return (
    <div className={`${sizeClasses[size]} ${className}`}>
      <svg
        viewBox="0 0 240 50"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full"
      >
        {/* MSFT Insurance wordmark (simple, neutral) */}
        <text x="0" y="28" fontSize="20" fontWeight="700" fill="#1F2937" fontFamily="Segoe UI, Arial, sans-serif">
          MSFT Insurance
        </text>
        <text x="0" y="45" fontSize="12" fontWeight="500" fill="#6B7280" fontFamily="Segoe UI, Arial, sans-serif">
          AI Assistant
        </text>
      </svg>
    </div>
  );
};
