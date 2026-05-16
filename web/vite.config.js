import { defineConfig } from "vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
    plugins: [
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
                id: "/",
                orientation: "portrait",
                lang: "en-US",
                scope: "/",
                start_url: "/",
                categories: ["finance", "productivity"],
                screenshots: [
                    {
                        src: "/screenshots/dashboard-01.png",
                        sizes: "464x952",
                        type: "image/png",
                        form_factor: "narrow",
                        label: "Dashboard overview with portfolio summary",
                    },
                    {
                        src: "/screenshots/portfolio.png",
                        sizes: "464x752",
                        type: "image/png",
                        form_factor: "narrow",
                        label: "Portfolio holdings view",
                    },
                    {
                        src: "/screenshots/trades-01.png",
                        sizes: "464x952",
                        type: "image/png",
                        form_factor: "narrow",
                        label: "Trade history and activity",
                    },
                    {
                        src: "/screenshots/analytics-01.png",
                        sizes: "464x952",
                        type: "image/png",
                        form_factor: "narrow",
                        label: "Analytics and performance charts",
                    },
                    {
                        src: "/screenshots/dashboard-desktop.png",
                        sizes: "464x952",
                        type: "image/png",
                        form_factor: "wide",
                        label: "Desktop dashboard overview with portfolio summary",
                    },
                ],
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
                    {
                        src: "/icon-maskable-512.png",
                        sizes: "512x512",
                        type: "image/png",
                        purpose: "maskable",
                    },
                ],
            },
            injectRegister: "script",
            devOptions: {
                enabled: true,
                type: "module",
                navigateFallback: "/",
            },
        }),
        sveltekit(),
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
        allowedHosts: ["situated-enjoyably-omen.ngrok-free.dev"],
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
