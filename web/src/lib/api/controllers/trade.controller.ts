import type { AxiosInstance } from 'axios';
import type {
  Trade,
  CreateTradeRequest,
  ListTradesQuery,
  ListTradesResponse,
  ValidateCsvResponse,
  ConfirmImportResponse,
} from '../types';

export class TradeController {
  constructor(private client: AxiosInstance) {}

  async listTrades(params: ListTradesQuery): Promise<ListTradesResponse> {
    const response = await this.client.get('/trades/', {
      params: {
        portfolio_id: params.portfolio_id,
        ticker: params.ticker,
        trade_type: params.trade_type,
        start_date: params.start_date,
        end_date: params.end_date,
        skip: params.skip || 0,
        limit: params.limit || 100,
      },
    });
    return response.data;
  }

  async createTrade(data: CreateTradeRequest): Promise<Trade> {
    const response = await this.client.post('/trades/', data);
    return response.data;
  }

  async getTrade(tradeId: string): Promise<Trade> {
    const response = await this.client.get(`/trades/${tradeId}`);
    return response.data;
  }

  async updateTrade(tradeId: string, data: CreateTradeRequest): Promise<Trade> {
    const response = await this.client.put(`/trades/${tradeId}`, data);
    return response.data;
  }

  async deleteTrade(tradeId: string): Promise<void> {
    await this.client.delete(`/trades/${tradeId}`);
  }

  async validateCsv(
    file: File,
    mapping: Record<string, unknown>,
    dateFormat: string
  ): Promise<ValidateCsvResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mapping', JSON.stringify(mapping));
    formData.append('date_format', dateFormat);

    const response = await this.client.post('/trades/import/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async confirmImport(
    file: File,
    mapping: Record<string, unknown>,
    portfolioId: string,
    dateFormat: string,
    profileName?: string | null
  ): Promise<ConfirmImportResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mapping', JSON.stringify(mapping));
    formData.append('portfolio_id', portfolioId);
    formData.append('date_format', dateFormat);
    if (profileName) formData.append('profile_name', profileName);

    const response = await this.client.post('/trades/import/confirm', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }
}
