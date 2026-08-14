import type { ReactNode } from 'react';

interface NavItemProps {
  icon?: ReactNode;
  label: string;
  active?: boolean;
  badgeCount?: number;
  onClick?: () => void;
}

export function NavItem({
  icon,
  label,
  active = false,
  badgeCount,
  onClick,
}: NavItemProps) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '10px 12px',
        borderRadius: 'var(--ds-radius-lg)',
        background: active ? '#fff' : 'transparent',
        color: active ? 'var(--accent-600)' : 'var(--text-body)',
        font: active
          ? '600 14px var(--font-family-body)'
          : '500 14px var(--font-family-body)',
        boxShadow: active ? 'var(--shadow-raised)' : 'none',
        cursor: 'pointer',
      }}
    >
      {icon}
      <span style={{ flex: 1 }}>{label}</span>
      {badgeCount != null && (
        <span
          style={{
            background: 'var(--accent-500)',
            color: '#fff',
            font: '700 10.5px var(--font-family-body)',
            minWidth: 18,
            height: 18,
            borderRadius: 'var(--ds-radius-pill)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 5px',
          }}
        >
          {badgeCount}
        </span>
      )}
    </div>
  );
}
