interface ToggleGroupOption {
  value: string;
  label: string;
}

interface ToggleGroupProps {
  options: ToggleGroupOption[];
  value: string;
  onChange?: (value: string) => void;
}

export function ToggleGroup({ options, value, onChange }: ToggleGroupProps) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 4,
        background: 'var(--bg-surface-muted)',
        borderRadius: 'var(--ds-radius-md)',
        padding: 3,
      }}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange?.(opt.value)}
            style={{
              border: 'none',
              cursor: 'pointer',
              font: '700 12px var(--font-family-body)',
              padding: '6px 12px',
              borderRadius: 'var(--ds-radius-md)',
              background: active ? '#fff' : 'transparent',
              color: active ? 'var(--text-body)' : 'var(--text-secondary)',
              boxShadow: active ? 'var(--shadow-card)' : 'none',
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
