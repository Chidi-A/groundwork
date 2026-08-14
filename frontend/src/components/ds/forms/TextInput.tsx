import type { ChangeEvent } from 'react';

interface TextInputProps {
  label?: string;
  placeholder?: string;
  value?: string;
  type?: 'text' | 'email' | 'password';
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void;
}

export function TextInput({
  label,
  placeholder,
  value,
  onChange,
  type = 'text',
}: TextInputProps) {
  return (
    <div>
      {label && (
        <div
          style={{
            font: '700 12.5px var(--font-family-body)',
            color: 'var(--text-body)',
            marginBottom: 7,
          }}
        >
          {label}
        </div>
      )}
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        style={{
          width: '100%',
          boxSizing: 'border-box',
          background: 'var(--bg-surface-muted)',
          border: 'none',
          borderRadius: 'var(--ds-radius-md)',
          padding: '12px 16px',
          font: '400 14px var(--font-family-body)',
          color: 'var(--text-heading)',
        }}
      />
    </div>
  );
}
