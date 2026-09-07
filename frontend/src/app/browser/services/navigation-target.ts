const DUCKDUCKGO_SEARCH_URL = "https://duckduckgo.com/?q=";
const SCHEME_PATTERN = /^[a-z][a-z\d+.-]*:/i;

export function resolveNavigationTarget(value: string): string {
  const input = value.trim();
  if (isHostname(input)) return input.startsWith("//") ? `https:${input}` : `https://${input}`;
  if (SCHEME_PATTERN.test(input)) return input;
  return `${DUCKDUCKGO_SEARCH_URL}${encodeURIComponent(input)}`;
}

export function isAddress(value: string): boolean {
  const input = value.trim();
  return isHostname(input) || SCHEME_PATTERN.test(input);
}

function isHostname(value: string): boolean {
  if (!value || /\s/.test(value)) return false;
  try {
    const url = new URL(value.startsWith("//") ? `https:${value}` : `https://${value}`);
    const hostname = url.hostname.toLowerCase();
    return (
      !url.username &&
      !url.password &&
      (hostname === "localhost" || hostname.includes(".") || /^\[[\da-f:]+\]$/i.test(hostname))
    );
  } catch {
    return false;
  }
}
