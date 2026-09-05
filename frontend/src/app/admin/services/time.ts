const UNITS: readonly (readonly [Intl.RelativeTimeFormatUnit, number])[] = [
  ["second", 60],
  ["minute", 60],
  ["hour", 24],
  ["day", 7],
];

const RELATIVE = new Intl.RelativeTimeFormat("en-US", { numeric: "auto", style: "narrow" });
const CLOCK = new Intl.DateTimeFormat("en-US", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

/** "3m ago" / "in 8m", so an operator reads age and expiry at a glance. */
export function relativeTime(timestamp: string, now: number = Date.now()): string {
  let value = (new Date(timestamp).getTime() - now) / 1000;
  if (!Number.isFinite(value)) return "unknown";
  for (const [unit, span] of UNITS) {
    if (Math.abs(value) < span) return RELATIVE.format(Math.round(value), unit);
    value /= span;
  }
  return RELATIVE.format(Math.round(value), "week");
}

export function clockTime(date: Date): string {
  return CLOCK.format(date);
}
