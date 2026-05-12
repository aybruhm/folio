import { defineConfig } from "vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
    plugins: [
        sveltekit(),
        VitePWA({
            registerType: "autoUpdate",
            workbox: {
                globPatterns: [
                    "client/**/*.{js,css,html,svg,ico,png,webp,woff,woff2,ttf,eot}",
                ],
                runtimeCaching: [
                    {
                        urlPattern: /^https:\/\/api\./,
                        handler: "StaleWhileRevalidate",
                        options: {
                            cacheName: "api-cache",
                            expiration: {
                                maxEntries: 100,
                                maxAgeSeconds: 24 * 60 * 60,
                            },
                        },
                    },
                    {
                        urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/,
                        handler: "CacheFirst",
                        options: {
                            cacheName: "google-fonts-cache",
                            expiration: {
                                maxEntries: 20,
                                maxAgeSeconds: 365 * 24 * 60 * 60,
                            },
                        },
                    },
                    {
                        urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/,
                        handler: "CacheFirst",
                        options: {
                            cacheName: "gstatic-fonts-cache",
                            expiration: {
                                maxEntries: 20,
                                maxAgeSeconds: 365 * 24 * 60 * 60,
                            },
                        },
                    },
                ],
            },
            manifest: {
                name: "Folio - Investment Portfolio Tracker",
                short_name: "Folio",
                description:
                    "Track, analyze, and optimize your investment portfolio",
                theme_color: "#0f172a",
                background_color: "#0f172a",
                display: "standalone",
                scope: "/",
                start_url: "/",
                icons: [
                    {
                        src: "/icon-192.png",
                        sizes: "192x192",
                        type: "image/png",
                        purpose: "any",
                    },
                    {
                        src: "/icon-512.png",
                        sizes: "512x512",
                        type: "image/png",
                        purpose: "any",
                    },
                ],
            },
            injectRegister: "script",
            injectManifest: {
                globPatterns: ["client/**/*.{js,css,html,svg,ico,png}"],
                maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
            },
        }),
    ],
    server: {
        host: "0.0.0.0",
        port: 3000,
        proxy: {
            "/api": {
                target: "http://api:8000",
                changeOrigin: true,
            },
        },
        hmr: {
            host: "localhost",
            port: 3000,
        },
        watch: {
            ignored: [
                "**/node_modules/**",
                "**/.svelte-kit/**",
                "**/build/**",
                "**/dist/**",
                "**/.git/**",
                "**/.cache/**",
                "**/.vscode/**",
                "**/.idea/**",
                "**/logs/**",
                "**/tmp/**",
                "**/temp/**",
            ],
        },
    },
});
