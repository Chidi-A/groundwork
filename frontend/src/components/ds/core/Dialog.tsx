import type { ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  width?: number;
  children?: ReactNode;
}

export function Dialog({ open, width = 440, children }: DialogProps) {
  if (!open) return null;
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'oklch(30% 0.02 150 / 0.35)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 30,
      }}
    >
      <div
        style={{
          width,
          background: '#fff',
          borderRadius: 'var(--ds-radius-4xl)',
          padding: 28,
          boxShadow: 'var(--shadow-modal)',
        }}
      >
        {children}
      </div>
    </div>
  );
}
