/// <reference types="vite/client" />

declare module "$env/dynamic/public" {
    export const env: {
        PUBLIC_API_BASE_URL: string;
        [key: string]: string | undefined;
    };
}
