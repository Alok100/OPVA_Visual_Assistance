import { cn } from "cn";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  type LucideIcon,
} from "lucide-react";

export type StatusTone = "success" | "warning" | "danger" | "neutral" | "info";

const TONE_STYLES: Record<StatusTone, string> = {
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  danger: "bg-red-50 text-red-700 border-red-200",
  neutral: "bg-slate-100 text-slate-600 border-slate-200",
  info: "bg-blue-50 text-blue-700 border-blue-200",
};

const TONE_ICON: Record<StatusTone, LucideIcon> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  neutral: Clock,
  info: Clock,
};

interface StatusBadgeProps {
  tone: StatusTone;
  children: React.ReactNode;
  icon?: boolean;
  className?: string;
}

export function StatusBadge({ tone, children, icon = true, className }: StatusBadgeProps) {
  const Icon = TONE_ICON[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        TONE_STYLES[tone],
        className,
      )}
    >
      {icon && <Icon className="size-3.5" />}
      {children}
    </span>
  );
}
