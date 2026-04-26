import type { AxiosInstance } from 'axios';
import type {
  Goal,
  CreateGoalRequest,
  ListGoalsResponse,
  GetProjectionResponse,
} from '../types';

export class GoalController {
  constructor(private client: AxiosInstance) {}

  async listGoals(portfolioId: string): Promise<ListGoalsResponse> {
    const response = await this.client.get('/goals/', {
      params: {
        portfolio_id: portfolioId,
      },
    });
    return response.data;
  }

  async createGoal(data: CreateGoalRequest): Promise<Goal> {
    const response = await this.client.post('/goals/', data);
    return response.data;
  }

  async getGoal(goalId: string): Promise<Goal> {
    const response = await this.client.get(`/goals/${goalId}`);
    return response.data;
  }

  async updateGoal(goalId: string, data: CreateGoalRequest): Promise<Goal> {
    const response = await this.client.put(`/goals/${goalId}`, data);
    return response.data;
  }

  async deleteGoal(goalId: string): Promise<void> {
    await this.client.delete(`/goals/${goalId}`);
  }

  async getProjection(goalId: string): Promise<GetProjectionResponse> {
    const response = await this.client.get(`/goals/${goalId}/projection`);
    return response.data;
  }
}
