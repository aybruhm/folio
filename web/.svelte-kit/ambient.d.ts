
// this file is generated — do not edit it


/// <reference types="@sveltejs/kit" />

/**
 * This module provides access to environment variables that are injected _statically_ into your bundle at build time and are limited to _private_ access.
 * 
 * |         | Runtime                                                                    | Build time                                                               |
 * | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
 * | Private | [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private) | [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private) |
 * | Public  | [`$env/dynamic/public`](https://svelte.dev/docs/kit/$env-dynamic-public)   | [`$env/static/public`](https://svelte.dev/docs/kit/$env-static-public)   |
 * 
 * Static environment variables are [loaded by Vite](https://vitejs.dev/guide/env-and-mode.html#env-files) from `.env` files and `process.env` at build time and then statically injected into your bundle at build time, enabling optimisations like dead code elimination.
 * 
 * **_Private_ access:**
 * 
 * - This module cannot be imported into client-side code
 * - This module only includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured)
 * 
 * For example, given the following build time environment:
 * 
 * ```env
 * ENVIRONMENT=production
 * PUBLIC_BASE_URL=http://site.com
 * ```
 * 
 * With the default `publicPrefix` and `privatePrefix`:
 * 
 * ```ts
 * import { ENVIRONMENT, PUBLIC_BASE_URL } from '$env/static/private';
 * 
 * console.log(ENVIRONMENT); // => "production"
 * console.log(PUBLIC_BASE_URL); // => throws error during build
 * ```
 * 
 * The above values will be the same _even if_ different values for `ENVIRONMENT` or `PUBLIC_BASE_URL` are set at runtime, as they are statically replaced in your code with their build time values.
 */
declare module '$env/static/private' {
	export const NODE_ENV: string;
	export const VITE_API_BASE_URL: string;
	export const VITE_HOST: string;
	export const CHOKIDAR_USEPOLLING: string;
	export const WDS_SOCKET_HOST: string;
	export const WATCHPACK_POLLING: string;
	export const npm_command: string;
	export const npm_config_userconfig: string;
	export const npm_config_cache: string;
	export const HOSTNAME: string;
	export const NODE: string;
	export const NODE_EXTRA_CA_CERTS: string;
	export const COLOR: string;
	export const npm_config_local_prefix: string;
	export const npm_config_globalconfig: string;
	export const EDITOR: string;
	export const PWD: string;
	export const NPM_CONFIG_UPDATE_NOTIFIER: string;
	export const npm_config_init_module: string;
	export const HOME: string;
	export const GIT_SSL_CAINFO: string;
	export const npm_package_version: string;
	export const SSL_CERT_DIR: string;
	export const YARN_HTTP_PROXY: string;
	export const CARGO_HTTP_CAINFO: string;
	export const https_proxy: string;
	export const INIT_CWD: string;
	export const npm_lifecycle_script: string;
	export const npm_config_npm_version: string;
	export const npm_package_name: string;
	export const npm_config_prefix: string;
	export const GIT_PROXY_SSL_CAINFO: string;
	export const npm_lifecycle_event: string;
	export const SHLVL: string;
	export const HTTPS_PROXY: string;
	export const HTTP_PROXY: string;
	export const http_proxy: string;
	export const npm_config_user_agent: string;
	export const npm_execpath: string;
	export const SSL_CERT_FILE: string;
	export const PIP_CERT: string;
	export const npm_package_json: string;
	export const npm_config_noproxy: string;
	export const PATH: string;
	export const npm_config_node_gyp: string;
	export const YARN_HTTPS_PROXY: string;
	export const CARGO_HTTP_PROXY: string;
	export const npm_config_global_prefix: string;
	export const NODE_VERSION: string;
	export const YARN_HTTPS_CA_FILE_PATH: string;
	export const DEBIAN_FRONTEND: string;
	export const npm_node_execpath: string;
	export const _: string;
	export const VITE_USER_NODE_ENV: string;
}

/**
 * This module provides access to environment variables that are injected _statically_ into your bundle at build time and are _publicly_ accessible.
 * 
 * |         | Runtime                                                                    | Build time                                                               |
 * | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
 * | Private | [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private) | [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private) |
 * | Public  | [`$env/dynamic/public`](https://svelte.dev/docs/kit/$env-dynamic-public)   | [`$env/static/public`](https://svelte.dev/docs/kit/$env-static-public)   |
 * 
 * Static environment variables are [loaded by Vite](https://vitejs.dev/guide/env-and-mode.html#env-files) from `.env` files and `process.env` at build time and then statically injected into your bundle at build time, enabling optimisations like dead code elimination.
 * 
 * **_Public_ access:**
 * 
 * - This module _can_ be imported into client-side code
 * - **Only** variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`) are included
 * 
 * For example, given the following build time environment:
 * 
 * ```env
 * ENVIRONMENT=production
 * PUBLIC_BASE_URL=http://site.com
 * ```
 * 
 * With the default `publicPrefix` and `privatePrefix`:
 * 
 * ```ts
 * import { ENVIRONMENT, PUBLIC_BASE_URL } from '$env/static/public';
 * 
 * console.log(ENVIRONMENT); // => throws error during build
 * console.log(PUBLIC_BASE_URL); // => "http://site.com"
 * ```
 * 
 * The above values will be the same _even if_ different values for `ENVIRONMENT` or `PUBLIC_BASE_URL` are set at runtime, as they are statically replaced in your code with their build time values.
 */
declare module '$env/static/public' {
	export const PUBLIC_API_BASE_URL: string;
}

/**
 * This module provides access to environment variables set _dynamically_ at runtime and that are limited to _private_ access.
 * 
 * |         | Runtime                                                                    | Build time                                                               |
 * | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
 * | Private | [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private) | [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private) |
 * | Public  | [`$env/dynamic/public`](https://svelte.dev/docs/kit/$env-dynamic-public)   | [`$env/static/public`](https://svelte.dev/docs/kit/$env-static-public)   |
 * 
 * Dynamic environment variables are defined by the platform you're running on. For example if you're using [`adapter-node`](https://github.com/sveltejs/kit/tree/main/packages/adapter-node) (or running [`vite preview`](https://svelte.dev/docs/kit/cli)), this is equivalent to `process.env`.
 * 
 * **_Private_ access:**
 * 
 * - This module cannot be imported into client-side code
 * - This module includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured)
 * 
 * > [!NOTE] In `dev`, `$env/dynamic` includes environment variables from `.env`. In `prod`, this behavior will depend on your adapter.
 * 
 * > [!NOTE] To get correct types, environment variables referenced in your code should be declared (for example in an `.env` file), even if they don't have a value until the app is deployed:
 * >
 * > ```env
 * > MY_FEATURE_FLAG=
 * > ```
 * >
 * > You can override `.env` values from the command line like so:
 * >
 * > ```sh
 * > MY_FEATURE_FLAG="enabled" npm run dev
 * > ```
 * 
 * For example, given the following runtime environment:
 * 
 * ```env
 * ENVIRONMENT=production
 * PUBLIC_BASE_URL=http://site.com
 * ```
 * 
 * With the default `publicPrefix` and `privatePrefix`:
 * 
 * ```ts
 * import { env } from '$env/dynamic/private';
 * 
 * console.log(env.ENVIRONMENT); // => "production"
 * console.log(env.PUBLIC_BASE_URL); // => undefined
 * ```
 */
declare module '$env/dynamic/private' {
	export const env: {
		NODE_ENV: string;
		VITE_API_BASE_URL: string;
		VITE_HOST: string;
		CHOKIDAR_USEPOLLING: string;
		WDS_SOCKET_HOST: string;
		WATCHPACK_POLLING: string;
		npm_command: string;
		npm_config_userconfig: string;
		npm_config_cache: string;
		HOSTNAME: string;
		NODE: string;
		NODE_EXTRA_CA_CERTS: string;
		COLOR: string;
		npm_config_local_prefix: string;
		npm_config_globalconfig: string;
		EDITOR: string;
		PWD: string;
		NPM_CONFIG_UPDATE_NOTIFIER: string;
		npm_config_init_module: string;
		HOME: string;
		GIT_SSL_CAINFO: string;
		npm_package_version: string;
		SSL_CERT_DIR: string;
		YARN_HTTP_PROXY: string;
		CARGO_HTTP_CAINFO: string;
		https_proxy: string;
		INIT_CWD: string;
		npm_lifecycle_script: string;
		npm_config_npm_version: string;
		npm_package_name: string;
		npm_config_prefix: string;
		GIT_PROXY_SSL_CAINFO: string;
		npm_lifecycle_event: string;
		SHLVL: string;
		HTTPS_PROXY: string;
		HTTP_PROXY: string;
		http_proxy: string;
		npm_config_user_agent: string;
		npm_execpath: string;
		SSL_CERT_FILE: string;
		PIP_CERT: string;
		npm_package_json: string;
		npm_config_noproxy: string;
		PATH: string;
		npm_config_node_gyp: string;
		YARN_HTTPS_PROXY: string;
		CARGO_HTTP_PROXY: string;
		npm_config_global_prefix: string;
		NODE_VERSION: string;
		YARN_HTTPS_CA_FILE_PATH: string;
		DEBIAN_FRONTEND: string;
		npm_node_execpath: string;
		_: string;
		VITE_USER_NODE_ENV: string;
		[key: `PUBLIC_${string}`]: undefined;
		[key: `${string}`]: string | undefined;
	}
}

/**
 * This module provides access to environment variables set _dynamically_ at runtime and that are _publicly_ accessible.
 * 
 * |         | Runtime                                                                    | Build time                                                               |
 * | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
 * | Private | [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private) | [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private) |
 * | Public  | [`$env/dynamic/public`](https://svelte.dev/docs/kit/$env-dynamic-public)   | [`$env/static/public`](https://svelte.dev/docs/kit/$env-static-public)   |
 * 
 * Dynamic environment variables are defined by the platform you're running on. For example if you're using [`adapter-node`](https://github.com/sveltejs/kit/tree/main/packages/adapter-node) (or running [`vite preview`](https://svelte.dev/docs/kit/cli)), this is equivalent to `process.env`.
 * 
 * **_Public_ access:**
 * 
 * - This module _can_ be imported into client-side code
 * - **Only** variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`) are included
 * 
 * > [!NOTE] In `dev`, `$env/dynamic` includes environment variables from `.env`. In `prod`, this behavior will depend on your adapter.
 * 
 * > [!NOTE] To get correct types, environment variables referenced in your code should be declared (for example in an `.env` file), even if they don't have a value until the app is deployed:
 * >
 * > ```env
 * > MY_FEATURE_FLAG=
 * > ```
 * >
 * > You can override `.env` values from the command line like so:
 * >
 * > ```sh
 * > MY_FEATURE_FLAG="enabled" npm run dev
 * > ```
 * 
 * For example, given the following runtime environment:
 * 
 * ```env
 * ENVIRONMENT=production
 * PUBLIC_BASE_URL=http://example.com
 * ```
 * 
 * With the default `publicPrefix` and `privatePrefix`:
 * 
 * ```ts
 * import { env } from '$env/dynamic/public';
 * console.log(env.ENVIRONMENT); // => undefined, not public
 * console.log(env.PUBLIC_BASE_URL); // => "http://example.com"
 * ```
 * 
 * ```
 * 
 * ```
 */
declare module '$env/dynamic/public' {
	export const env: {
		PUBLIC_API_BASE_URL: string;
		[key: `PUBLIC_${string}`]: string | undefined;
	}
}
