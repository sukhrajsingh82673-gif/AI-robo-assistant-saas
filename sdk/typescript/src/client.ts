export interface ZonataClientConfig {
  apiKey: string;
  baseUrl?: string;
}

export class ZonataClient {
  private apiKey: string;
  private baseUrl: string;

  constructor(config: ZonataClientConfig) {
    this.apiKey = config.apiKey;
    this.baseUrl = (config.baseUrl || 'https://api.zonata.ai/api/public/v1').replace(/\/$/, '');
  }

  public async getPlans(): Promise<any> {
    return { status: 200, plans: [] };
  }
}
