import { SECRET_KEY } from "$env/static/private";
import type { Handle } from "@sveltejs/kit";
import { redirect } from "@sveltejs/kit";
import { jwtVerify } from "jose";
import { envUtils } from "@/utils/env";

const PUBLIC_ROUTES = ["/login", "/register"];

export const handle: Handle = async ({ event, resolve }) => {
    const token = event.cookies.get("access_token");
    event.locals.user = null;

    if (token) {
        try {
            const secret = new TextEncoder().encode(SECRET_KEY);
            const { payload } = await jwtVerify(token, secret);
            if (payload.sub && payload.email) {
                event.locals.user = {
                    id: payload.sub,
                    email: payload.email as string,
                };
            }
        } catch {
            // expired or invalid — treat as unauthenticated
        }
    }

    const isPublic = PUBLIC_ROUTES.some((r) =>
        event.url.pathname.startsWith(r),
    );

    if (!isPublic && !event.locals.user) {
        throw redirect(
            302,
            `/login?redirect=${encodeURIComponent(event.url.pathname)}`,
        );
    }

    return resolve(event);
};
