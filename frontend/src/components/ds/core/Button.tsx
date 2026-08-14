import type { ReactNode } from 'react';

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  children?: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
}

export function Button({
  variant = 'primary',
  size = 'md',
  children,
  disabled,
  onClick,
}: ButtonProps) {
  const sizes = {
    sm: { padding: '8px 14px', font: '700 12px var(--font-family-body)' },
    md: { padding: '11px 18px', font: '700 13.5px var(--font-family-body)' },
    lg: { padding: '13px 22px', font: '700 14px var(--font-family-body)' },
  };
  const variants = {
    primary: {
      background: 'var(--accent-500)',
      color: '#fff',
      boxShadow: 'var(--shadow-accent-glow)',
      border: 'none',
    },
    secondary: {
      background: '#fff',
      color: 'var(--text-body)',
      boxShadow: 'var(--shadow-raised)',
      border: 'none',
    },
    ghost: {
      background: 'var(--bg-surface-muted)',
      color: 'var(--text-body)',
      border: 'none',
    },
    outline: {
      background: '#fff',
      color: 'var(--text-body)',
      border: '1px solid var(--border-default)',
    },
  };
  return (
    <button
      style={{
        ...sizes[size],
        ...variants[variant],
        borderRadius: 'var(--ds-radius-lg)',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
