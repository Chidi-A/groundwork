interface Tab {
  key: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  active: string;
  onChange: (key: string) => void;
}

export function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 22,
        borderBottom: '1px solid var(--border-subtle)',
        margin: '18px 0 20px',
      }}
    >
      {tabs.map((t) => (
        <div
          key={t.key}
          onClick={() => onChange(t.key)}
          style={{
            padding: '0 0 10px',
            font: '700 13.5px var(--font-family-body)',
            cursor: 'pointer',
            color:
              active === t.key ? 'var(--text-body)' : 'var(--text-secondary)',
            borderBottom:
              active === t.key
                ? '2px solid var(--accent-500)'
                : '2px solid transparent',
          }}
        >
          {t.label}
        </div>
      ))}
    </div>
  );
}
