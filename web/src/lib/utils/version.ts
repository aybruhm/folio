export const RELEASES_REPO = 'aybruhm/folio';

// "v1.26.0" or "1.26.0" to [1, 26, 0]; null for anything else. A suffix such
// as "-rc.1" is not a release we offer, so it doesn't parse.
export function parseVersion(tag: string): [number, number, number] | null {
  const match = /^v?(\d+)\.(\d+)\.(\d+)$/.exec(tag.trim());
  return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : null;
}

// True only when `latest` is a higher version than `current`, compared number by
// number so 1.10.0 is newer than 1.9.0. Unparseable input is never "newer".
export function isNewerVersion(latest: string, current: string): boolean {
  const a = parseVersion(latest);
  const b = parseVersion(current);
  if (!a || !b) return false;
  for (let i = 0; i < 3; i++) {
    if (a[i] !== b[i]) return a[i] > b[i];
  }
  return false;
}

// "v<tag>" for a version or tag, e.g. "1.27.0" or "v1.27.0" gives "v1.27.0".
export function toTag(version: string): string {
  return `v${version.trim().replace(/^v/, '')}`;
}

export function releaseUrl(version: string): string {
  return `https://github.com/${RELEASES_REPO}/releases/tag/${toTag(version)}`;
}
