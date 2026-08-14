import type { ReactNode } from 'react';
import { NavItem } from './NavItem';
import { Icon } from '../icons';

interface SidebarProps {
  active: string;
  onNav?: (key: string) => void;
  userName?: string;
  userSub?: string;
  usage?: ReactNode;
}

const OVERVIEW_ITEMS = [
  { key: 'overview', label: 'Overview', icon: Icon.overview },
  { key: 'inbox', label: 'Inbox', icon: Icon.inbox, badgeCount: 5 },
] as const;

const PROJECT_ITEMS = [
  { key: 'projects', label: 'Projects', icon: Icon.projects },
] as const;

const RESEARCH_ITEMS = [
  { key: 'insights', label: 'Insights', icon: Icon.insights },
  { key: 'search', label: 'Search', icon: Icon.search },
  { key: 'reports', label: 'Reports', icon: Icon.reports },
  { key: 'chat', label: 'Chat', icon: Icon.chat },
] as const;

const ACCOUNT_ITEMS = [
  { key: 'settings', label: 'Settings', icon: Icon.settings },
  { key: 'help', label: 'Help & support', icon: Icon.help },
] as const;

type NavGroup =
  | typeof OVERVIEW_ITEMS
  | typeof PROJECT_ITEMS
  | typeof RESEARCH_ITEMS
  | typeof ACCOUNT_ITEMS;

export function Sidebar({
  active,
  onNav,
  userName = 'Chidi Anyanwu',
  userSub = 'Solo workspace',
  usage,
}: SidebarProps) {
  const renderGroup = (items: NavGroup) =>
    items.map((it) => (
      <NavItem
        key={it.key}
        icon={it.icon()}
        label={it.label}
        active={active === it.key}
        badgeCount={'badgeCount' in it ? it.badgeCount : undefined}
        onClick={() => onNav?.(it.key)}
      />
    ));

  return (
    <div
      style={{
        width: 256,
        flexShrink: 0,
        background: 'var(--bg-sidebar)',
        display: 'flex',
        flexDirection: 'column',
        padding: '26px 18px',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '0 8px 26px',
        }}
      >
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: 10,
            background: 'var(--accent-500)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon.sparkle fill="white" />
        </div>
        <div>
          <div
            style={{
              font: '600 17px var(--font-family-heading)',
              color: 'var(--text-heading)',
            }}
          >
            Groundwork
          </div>
          <div
            style={{
              font: '400 11px var(--font-family-body)',
              color: 'var(--text-secondary)',
            }}
          >
            AI Research Assistant
          </div>
        </div>
      </div>

      <div
        style={{
          font: '600 11px var(--font-family-body)',
          letterSpacing: '0.05em',
          color: 'var(--text-muted)',
          padding: '0 10px 10px',
        }}
      >
        OVERVIEW
      </div>
      {renderGroup(OVERVIEW_ITEMS)}

      <div
        style={{
          font: '600 11px var(--font-family-body)',
          letterSpacing: '0.05em',
          color: 'var(--text-muted)',
          padding: '6px 12px 10px',
        }}
      >
        PROJECTS
      </div>
      {renderGroup(PROJECT_ITEMS)}

      <div
        style={{
          font: '600 11px var(--font-family-body)',
          letterSpacing: '0.05em',
          color: 'var(--text-muted)',
          padding: '6px 12px 10px',
        }}
      >
        RESEARCH
      </div>
      {renderGroup(RESEARCH_ITEMS)}

      <div style={{ marginTop: 10 }}>{renderGroup(ACCOUNT_ITEMS)}</div>
      <div style={{ flex: 1 }} />

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: 10,
          background: '#fff',
          borderRadius: 'var(--ds-radius-xl)',
          boxShadow: 'var(--shadow-raised)',
        }}
      >
        <div
          style={{
            width: 34,
            height: 34,
            borderRadius: '50%',
            background: 'oklch(72% 0.09 150)',
            flexShrink: 0,
          }}
        />
        <div>
          <div
            style={{
              font: '600 13px var(--font-family-body)',
              color: 'var(--text-heading)',
            }}
          >
            {userName}
          </div>
          <div
            style={{
              font: '400 11px var(--font-family-body)',
              color: 'var(--text-muted)',
            }}
          >
            {userSub}
          </div>
        </div>
      </div>
      {usage}
    </div>
  );
}
