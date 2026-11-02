import { writable } from 'svelte/store';
import { browser } from '$app/env';
import { PUBLIC_UPDATE_CHECK } from '$app/env/public';
import { APP_VERSION } from '#lib/version.js';
import { RELEASES_REPO, isNewerVersion } from '#lib/utils/version.js';

// A newer release than this build, not yet dismissed; null otherwise.
export const availableUpdate = writable<{ tag: string } | null>(null);

const LATEST_KEY = 'folio.latestRelease';
const DISMISSED_KEY = 'folio.dismissedUpdate';
// GitHub allows 60 unauthenticated requests an hour per IP, so look at most
// every few hours, and back off after a failure.
const FRESH_MS = 6 * 60 * 60 * 1000;
const RETRY_MS = 60 * 60 * 1000;

interface LatestRelease {
    tag: string | null; // last tag we saw, kept through failed checks
    checkedAt: number;
    ok: boolean;
}

function readLatest(): LatestRelease | null {
    try {
        return JSON.parse(localStorage.getItem(LATEST_KEY) ?? 'null');
    } catch {
        return null;
    }
}

async function fetchLatestTag(): Promise<string | null> {
    const response = await fetch(`https://api.github.com/repos/${RELEASES_REPO}/releases/latest`, {
        headers: { Accept: 'application/vnd.github+json' },
        signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) throw new Error(`GitHub answered ${response.status}`);
    const body = await response.json();
    return typeof body.tag_name === 'string' ? body.tag_name : null;
}

let checked = false;

// Looks for a newer GitHub release, at most once per page load and rarely over
// the network. Silent on failure: this is a courtesy, never an error.
// Set PUBLIC_UPDATE_CHECK=false to turn it off (no request to GitHub is made).
export async function checkForUpdate(): Promise<void> {
    if (!browser || checked || PUBLIC_UPDATE_CHECK === 'false') return;
    checked = true;

    const cached = readLatest();
    const age = cached ? Date.now() - cached.checkedAt : Infinity;
    let tag = cached?.tag ?? null;

    const needsCheck = !cached || age >= (cached.ok ? FRESH_MS : RETRY_MS);
    if (needsCheck && navigator.onLine) {
        let record: LatestRelease;
        try {
            tag = (await fetchLatestTag()) ?? tag;
            record = { tag, checkedAt: Date.now(), ok: true };
        } catch {
            record = { tag, checkedAt: Date.now(), ok: false };
        }
        try {
            localStorage.setItem(LATEST_KEY, JSON.stringify(record));
        } catch {
            // storage full or blocked: just check again next time
        }
    }

    if (tag && isNewerVersion(tag, APP_VERSION) && localStorage.getItem(DISMISSED_KEY) !== tag) {
        availableUpdate.set({ tag });
    }
}

// Hides the notice for this release; a newer one shows it again.
export function dismissUpdate(): void {
    availableUpdate.update((current) => {
        if (current) {
            try {
                localStorage.setItem(DISMISSED_KEY, current.tag);
            } catch {
                // dismissal just won't persist
            }
        }
        return null;
    });
}
