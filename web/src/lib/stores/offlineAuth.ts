import { writable } from 'svelte/store';

export interface StoredAuthToken {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
  userId?: string;
  email?: string;
}

const STORAGE_KEY = 'folio-auth-offline';
const TOKEN_BUFFER = 5 * 60 * 1000; // 5 minutes buffer

// Create a store for offline auth tokens
export const offlineAuthStore = writable<StoredAuthToken | null>(null);

/**
 * Initialize auth store from localStorage
 */
export function initializeAuthStore() {
  if (typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const token = JSON.parse(stored) as StoredAuthToken;
        // Check if token is still valid
        if (token.expiresAt > Date.now() - TOKEN_BUFFER) {
          offlineAuthStore.set(token);
          return true;
        } else {
          // Token expired, clear it
          localStorage.removeItem(STORAGE_KEY);
          offlineAuthStore.set(null);
          return false;
        }
      }
    } catch (error) {
      console.error('Error loading auth token:', error);
    }
  }
  return false;
}

/**
 * Store auth token for offline use
 */
export function storeAuthToken(token: StoredAuthToken): void {
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(token));
      offlineAuthStore.set(token);
    } catch (error) {
      console.error('Error storing auth token:', error);
    }
  }
}

/**
 * Clear stored auth token
 */
export function clearAuthToken(): void {
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.removeItem(STORAGE_KEY);
      offlineAuthStore.set(null);
    } catch (error) {
      console.error('Error clearing auth token:', error);
    }
  }
}

/**
 * Get the current auth token
 */
export function getAuthToken(): StoredAuthToken | null {
  if (typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const token = JSON.parse(stored) as StoredAuthToken;
        // Check if token is still valid
        if (token.expiresAt > Date.now() - TOKEN_BUFFER) {
          return token;
        } else {
          // Token expired
          localStorage.removeItem(STORAGE_KEY);
          offlineAuthStore.set(null);
          return null;
        }
      }
    } catch (error) {
      console.error('Error retrieving auth token:', error);
    }
  }
  return null;
}

/**
 * Check if there's a valid offline auth token
 */
export function isAuthTokenValid(): boolean {
  const token = getAuthToken();
  if (!token) return false;
  return token.expiresAt > Date.now() - TOKEN_BUFFER;
}

/**
 * Update token expiration time (useful after token refresh)
 */
export function updateTokenExpiration(expiresAt: number): void {
  if (typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const token = JSON.parse(stored) as StoredAuthToken;
        token.expiresAt = expiresAt;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(token));
        offlineAuthStore.set(token);
      }
    } catch (error) {
      console.error('Error updating token expiration:', error);
    }
  }
}

/**
 * Migrate token format between versions
 */
export function migrateAuthToken(oldFormat: unknown): StoredAuthToken | null {
  try {
    // Handle old string format (raw JWT)
    if (typeof oldFormat === 'string') {
      return {
        accessToken: oldFormat,
        expiresAt: Date.now() + 24 * 60 * 60 * 1000 // assume 24h expiry
      };
    }
    // Handle object format
    if (typeof oldFormat === 'object' && oldFormat !== null) {
      const obj = oldFormat as Record<string, unknown>;
      if (typeof obj.accessToken === 'string' && typeof obj.expiresAt === 'number') {
        return {
          accessToken: obj.accessToken,
          refreshToken: typeof obj.refreshToken === 'string' ? obj.refreshToken : undefined,
          expiresAt: obj.expiresAt,
          userId: typeof obj.userId === 'string' ? obj.userId : undefined,
          email: typeof obj.email === 'string' ? obj.email : undefined
        };
      }
    }
  } catch (error) {
    console.error('Error migrating auth token:', error);
  }
  return null;
}
