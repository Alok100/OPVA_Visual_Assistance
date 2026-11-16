interface ReadinessGaugeProps {
  percent: number;
  label: string;
}

export function ReadinessGauge({ percent, label }: ReadinessGaugeProps) {
  const angle = Math.round((percent / 100) * 360);

  return (
    <div className="flex items-center gap-5">
      <div
        className="relative flex size-28 shrink-0 items-center justify-center rounded-full"
        style={{
          background: `conic-gradient(var(--primary) ${angle}deg, var(--muted) ${angle}deg)`,
        }}
      >
        <div className="flex size-[88px] flex-col items-center justify-center rounded-full bg-card">
          <span className="text-2xl font-semibold text-foreground">{percent}%</span>
        </div>
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground">
          Based on image quality, coverage, and annotation completeness
        </p>
      </div>
    </div>
  );
}
