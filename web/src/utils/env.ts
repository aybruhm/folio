class EnvUtils {
    private static instance: EnvUtils;
    private env: {
        API_BASE_URL: string;
    };

    private constructor() {
        this.env = {
            API_BASE_URL:
                import.meta.env.VITE_API_BASE_URL ||
                "http://localhost:8000/api/v1/",
        };
    }

    public static getInstance(): EnvUtils {
        if (!EnvUtils.instance) {
            EnvUtils.instance = new EnvUtils();
        }
        return EnvUtils.instance;
    }

    public getBaseUrl(): string {
        return this.env.API_BASE_URL;
    }
}

export const envUtils = EnvUtils.getInstance();
