/// <reference types="vite/client" />

declare module "$env/dynamic/public" {
    export const env: {
        PUBLIC_API_BASE_URL: string;
        PUBLIC_ENABLE_REGISTRATION: string;
        [key: string]: string | undefined;
    };
}

declare module "$env/dynamic/private" {
    export const env: {
        SECRET_KEY: string;
        [key: string]: string | undefined;
    };
}
