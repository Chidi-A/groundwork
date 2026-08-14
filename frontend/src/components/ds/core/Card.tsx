import type { ReactNode, CSSProperties } from 'react';

interface CardProps {
  children?: ReactNode;
  padding?: string;
  style?: CSSProperties;
}

export function Card({ children, padding = '20px', style = {} }: CardProps) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        borderRadius: 'var(--ds-radius-2xl)',
        boxShadow: 'var(--shadow-card)',
        padding,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
