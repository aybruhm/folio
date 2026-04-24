import type { AxiosInstance } from 'axios';
import type { HealthCheck } from '../types';

export class HealthController {
  constructor(private client: AxiosInstance) {}

  async healthCheck(): Promise<HealthCheck> {
    const response = await this.client.get('/health');
    return response.data;
  }
}
