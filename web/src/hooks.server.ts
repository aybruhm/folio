import { env } from "$env/dynamic/private";
import type { Handle } from "@sveltejs/kit";
import { redirect } from "@sveltejs/kit";
import { jwtVerify } from "jose";

const PUBLIC_ROUTES = ["/login", "/register"];

/**
 * Internal URL of the FastAPI backend.
 * In Docker Compose the api service is reachable at http://api:8000.
 * Set PRIVATE_API_URL=http://localhost:8000 for local dev outside Docker.
 */
const API_BASE = env.PRIVATE_API_URL ?? "http://api:8000";
const API_REFRESH_PATH = `${API_BASE}/api/v1/auth/refresh`;

interface CookieAttributes {
    path: string;
    httpOnly?: boolean;
    secure?: boolean;
    sameSite?: boolean | "lax" | "strict" | "none";
    maxAge?: number;
}

/**
 * Attempt to refresh the access token using the refresh_token cookie.
 * Uses global fetch (not event.fetch) because event.fetch goes through
 * SvelteKit's internal pipeline which has no /api/ routes — the Vite
 * proxy only handles real browser HTTP requests.
 */
async function tryRefreshToken(
    event: Parameters<Handle>[0]["event"],
): Promise<string | null> {
    const refreshToken = event.cookies.get("refresh_token");
    if (!refreshToken) {
        console.log("[hooks] No refresh_token cookie found");
        return null;
    }

    try {
        console.log("[hooks] Attempting token refresh via", API_REFRESH_PATH);
        const response = await fetch(API_REFRESH_PATH, {
            method: "POST",
            headers: {
                cookie: event.request.headers.get("cookie") ?? "",
            },
        });

        if (!response.ok) {
            console.warn(
                "[hooks] Refresh request failed:",
                response.status,
                response.statusText,
            );
            return null;
        }

        // Transfer Set-Cookie headers from the API response to the client
        const setCookieHeaders = response.headers.getSetCookie();
        let newAccessToken: string | null = null;

        for (const cookieStr of setCookieHeaders) {
            const match = cookieStr.match(/^([^=]+)=([^;]*)/);
            if (!match) continue;

            const [, name, value] = match;

            const attrs: CookieAttributes = { path: "/" };
            if (cookieStr.includes("HttpOnly")) attrs.httpOnly = true;
            if (cookieStr.includes("Secure")) attrs.secure = true;
            const sameSiteMatch = cookieStr.match(/SameSite=(\w+)/i);
            if (sameSiteMatch) {
                attrs.sameSite =
                    sameSiteMatch[1].toLowerCase() as CookieAttributes["sameSite"];
            }
            const maxAgeMatch = cookieStr.match(/Max-Age=(\d+)/i);
            if (maxAgeMatch) attrs.maxAge = parseInt(maxAgeMatch[1], 10);

            event.cookies.set(name, value, attrs);

            if (name === "access_token") {
                newAccessToken = value;
            }
        }

        if (newAccessToken) {
            console.log("[hooks] Token refresh succeeded");
        }
        return newAccessToken;
    } catch (err) {
        console.warn("[hooks] Refresh request failed:", err);
        return null;
    }
}

/**
 * Verify a JWT access token and extract the user payload.
 */
async function verifyToken(
    token: string,
): Promise<{ id: string; email: string } | null> {
    if (!env.SECRET_KEY) {
        console.warn("[hooks] SECRET_KEY is not set — cannot verify JWTs");
        return null;
    }

    try {
        const secret = new TextEncoder().encode(env.SECRET_KEY);
        const { payload } = await jwtVerify(token, secret, {
            algorithms: ["HS256"],
        });
        if (payload.sub && payload.email) {
            return {
                id: payload.sub,
                email: payload.email as string,
            };
        }
        console.warn("[hooks] Token payload missing sub or email", payload);
        return null;
    } catch (err) {
        console.warn("[hooks] Token verification failed:", err);
        return null;
    }
}

export const handle: Handle = async ({ event, resolve }) => {
    // Short-circuit: API routes are handled by the FastAPI backend with
    // their own auth. The hook must not redirect these requests to /login.
    if (event.url.pathname.startsWith("/api/")) {
        return resolve(event);
    }

    let token = event.cookies.get("access_token");
    event.locals.user = null;

    // Attempt to verify the existing access token
    if (token) {
        const user = await verifyToken(token);
        if (user) {
            event.locals.user = user;
            console.log(
                "[hooks] User authenticated via access_token:",
                user.email,
            );
        }
    } else {
        console.log("[hooks] No access_token cookie found");
    }

    // If no valid access token, try to refresh using the refresh_token cookie
    if (!event.locals.user) {
        const newToken = await tryRefreshToken(event);
        if (newToken) {
            const user = await verifyToken(newToken);
            if (user) {
                event.locals.user = user;
                token = newToken;
                console.log(
                    "[hooks] User authenticated via refresh:",
                    user.email,
                );
            }
        }
    }

    const isPublic = PUBLIC_ROUTES.some((r) =>
        event.url.pathname.startsWith(r),
    );

    // Authenticated users on public/auth routes should be redirected to the home page
    if (isPublic && event.locals.user) {
        console.log("[hooks] Auth user on public route — redirecting to /");
        throw redirect(302, "/");
    }

    // Unauthenticated users on protected routes should be redirected to login
    if (!isPublic && !event.locals.user) {
        console.log(
            "[hooks] No user on protected route",
            event.url.pathname,
            "— redirecting to /login",
        );
        throw redirect(
            302,
            `/login?redirect=${encodeURIComponent(event.url.pathname)}`,
        );
    }

    return resolve(event);
};
