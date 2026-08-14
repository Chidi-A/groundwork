import { Avatar } from '../core/Avatar';
import { Icon } from '../icons';

interface AccountMenuProps {
  name?: string;
  email?: string;
  open: boolean;
  onToggle?: () => void;
  onNavigate?: (key: string) => void;
}

const menuItems = [
  { key: 'settings', icon: Icon.settings, label: 'Settings' },
  { key: 'help', icon: Icon.help, label: 'Help & support' },
] as const;

export function AccountMenu({
  name = 'Chidi Anyanwu',
  email = 'chidi.anyanwu@example.com',
  open,
  onToggle,
  onNavigate,
}: AccountMenuProps) {
  return (
    <div style={{ position: 'relative', flexShrink: 0 }}>
      <Avatar onClick={onToggle} />
      {open && (
        <div
          style={{
            position: 'absolute',
            top: 44,
            right: 0,
            width: 230,
            background: '#fff',
            borderRadius: 'var(--ds-radius-2xl)',
            boxShadow: 'var(--shadow-popover)',
            padding: 8,
            zIndex: 20,
          }}
        >
          <div
            style={{
              padding: '12px 14px 10px',
              borderBottom: '1px solid var(--border-subtle)',
              marginBottom: 6,
            }}
          >
            <div
              style={{
                font: '700 13.5px var(--font-family-body)',
                color: 'var(--text-heading)',
              }}
            >
              {name}
            </div>
            <div
              style={{
                font: '400 11.5px var(--font-family-body)',
                color: 'var(--text-muted)',
              }}
            >
              {email}
            </div>
          </div>
          {menuItems.map((it) => (
            <div
              key={it.key}
              onClick={() => onNavigate?.(it.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 14px',
                borderRadius: 10,
                font: '600 13px var(--font-family-body)',
                color: 'var(--text-body)',
                cursor: 'pointer',
              }}
            >
              {it.icon()} {it.label}
            </div>
          ))}
          <div
            style={{
              borderTop: '1px solid var(--border-subtle)',
              margin: '6px 0',
            }}
          />
          <div
            onClick={() => onNavigate?.('logout')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 14px',
              borderRadius: 10,
              font: '600 13px var(--font-family-body)',
              color: 'var(--text-body)',
              cursor: 'pointer',
            }}
          >
            <Icon.logout /> Log out
          </div>
        </div>
      )}
    </div>
  );
}
