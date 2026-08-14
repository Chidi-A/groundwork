import type { ReactNode } from 'react';

type BadgeTone =
  | 'pain'
  | 'feature'
  | 'opportunity'
  | 'quote'
  | 'jtbd'
  | 'completed'
  | 'processing'
  | 'queued'
  | 'failed'
  | 'needsReview'
  | 'unreviewed'
  | 'confirmed'
  | 'edited'
  | 'rejected'
  | 'flagged';

interface BadgeProps {
  kind?: 'taxonomy' | 'status' | 'review';
  tone: BadgeTone;
  children?: ReactNode;
}

const toneMap: Record<BadgeTone, { bg: string; fg: string }> = {
  pain: { bg: 'var(--pain-bg)', fg: 'var(--pain-fg)' },
  feature: { bg: 'var(--feature-bg)', fg: 'var(--feature-fg)' },
  opportunity: { bg: 'var(--opportunity-bg)', fg: 'var(--opportunity-fg)' },
  quote: { bg: 'var(--quote-bg)', fg: 'var(--quote-fg)' },
  jtbd: { bg: 'var(--jtbd-bg)', fg: 'var(--jtbd-fg)' },
  completed: {
    bg: 'var(--status-completed-bg)',
    fg: 'var(--status-completed-fg)',
  },
  processing: {
    bg: 'var(--status-processing-bg)',
    fg: 'var(--status-processing-fg)',
  },
  queued: { bg: 'var(--status-queued-bg)', fg: 'var(--status-queued-fg)' },
  failed: { bg: 'var(--status-failed-bg)', fg: 'var(--status-failed-fg)' },
  needsReview: {
    bg: 'var(--review-needs-review-bg)',
    fg: 'var(--review-needs-review-fg)',
  },
  unreviewed: {
    bg: 'var(--review-unreviewed-bg)',
    fg: 'var(--review-unreviewed-fg)',
  },
  confirmed: {
    bg: 'var(--review-confirmed-bg)',
    fg: 'var(--review-confirmed-fg)',
  },
  edited: { bg: 'var(--review-edited-bg)', fg: 'var(--review-edited-fg)' },
  rejected: {
    bg: 'var(--review-rejected-bg)',
    fg: 'var(--review-rejected-fg)',
  },
  flagged: { bg: 'var(--review-flagged-bg)', fg: 'var(--review-flagged-fg)' },
};

export function Badge({ tone, children }: BadgeProps) {
  const t = toneMap[tone] ?? toneMap.unreviewed;
  return (
    <span
      style={{
        background: t.bg,
        color: t.fg,
        font: '700 11px var(--font-family-body)',
        padding: '4px 10px',
        borderRadius: 'var(--ds-radius-sm)',
        whiteSpace: 'nowrap',
        display: 'inline-block',
      }}
    >
      {children}
    </span>
  );
}
