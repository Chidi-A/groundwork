interface AvatarProps {
  initials?: string;
  size?: number;
  onClick?: () => void;
}

export function Avatar({ initials = 'CA', size = 36, onClick }: AvatarProps) {
  return (
    <div
      onClick={onClick}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: 'oklch(72% 0.09 150)',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        font: `700 ${Math.round(size * 0.36)}px var(--font-family-heading)`,
        cursor: onClick ? 'pointer' : 'default',
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}
