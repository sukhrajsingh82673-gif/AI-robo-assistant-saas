/**
 * RoboAssistant Agent Engine — Centralized Configuration Manager
 * Replaces direct ad-hoc .env reads across transplanted modules with a
 * single governed configuration plane and secret isolation boundary.
 */

export interface AgentEngineConfig {
  heartbeatIntervalMs: number;
  heartbeatMaxRetries: number;
  heartbeatJitterMs: number;
  defaultModelAdapter: string;
  delegationMaxDepth: number;
  delegationTimeoutMs: number;
  workspaceRootDir: string;
  enableDebugLogs: boolean;
  adapterConfigs: Record<string, AdapterRuntimeConfig>;
}

export interface AdapterRuntimeConfig {
  apiKey?: string;
  baseUrl?: string;
  modelName?: string;
  timeoutMs?: number;
  maxTokens?: number;
  temperature?: number;
}

export class ConfigManager {
  private static instance: ConfigManager | null = null;
  private overrides: Map<string, unknown> = new Map();
  private secretStore: Map<string, string> = new Map();

  private defaults: AgentEngineConfig = {
    heartbeatIntervalMs: 30000,
    heartbeatMaxRetries: 5,
    heartbeatJitterMs: 2500,
    defaultModelAdapter: "gemini_local",
    delegationMaxDepth: 5,
    delegationTimeoutMs: 300000,
    workspaceRootDir: "/root/roboassistant/storage",
    enableDebugLogs: false,
    adapterConfigs: {
      gemini_local: {
        modelName: "gemini-2.5-flash",
        timeoutMs: 60000,
        temperature: 0.2,
      },
      claude_local: {
        modelName: "claude-3-5-sonnet-20241022",
        timeoutMs: 60000,
        temperature: 0.2,
      },
      codex_local: {
        modelName: "gpt-4o",
        timeoutMs: 60000,
        temperature: 0.2,
      },
    },
  };

  private constructor() {
    this.hydrateFromProcessEnv();
  }

  public static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }

  /**
   * Hydrates initial settings safely from environment without exposing raw secrets.
   */
  private hydrateFromProcessEnv(): void {
    if (typeof process === "undefined" || !process.env) return;

    if (process.env.AGENT_HEARTBEAT_INTERVAL_MS) {
      this.defaults.heartbeatIntervalMs = parseInt(process.env.AGENT_HEARTBEAT_INTERVAL_MS, 10);
    }
    if (process.env.AGENT_HEARTBEAT_MAX_RETRIES) {
      this.defaults.heartbeatMaxRetries = parseInt(process.env.AGENT_HEARTBEAT_MAX_RETRIES, 10);
    }
    if (process.env.DEFAULT_MODEL_ADAPTER) {
      this.defaults.defaultModelAdapter = process.env.DEFAULT_MODEL_ADAPTER;
    }
    if (process.env.AGENT_WORKSPACE_ROOT) {
      this.defaults.workspaceRootDir = process.env.AGENT_WORKSPACE_ROOT;
    }
    if (process.env.AGENT_ENGINE_DEBUG) {
      this.defaults.enableDebugLogs = process.env.AGENT_ENGINE_DEBUG === "true" || process.env.AGENT_ENGINE_DEBUG === "1";
    }

    // Register known API key credentials into the secret isolation store
    const keyMappings: Record<string, string> = {
      GEMINI_API_KEY: "gemini_api_key",
      OPENAI_API_KEY: "openai_api_key",
      ANTHROPIC_API_KEY: "anthropic_api_key",
      GROK_API_KEY: "grok_api_key",
    };

    for (const [envVar, secretName] of Object.entries(keyMappings)) {
      const val = process.env[envVar];
      if (val) {
        this.secretStore.set(secretName, val);
      }
    }
  }

  public get<T>(key: keyof AgentEngineConfig, fallback?: T): T {
    if (this.overrides.has(key as string)) {
      return this.overrides.get(key as string) as T;
    }
    if (key in this.defaults) {
      return (this.defaults as unknown as Record<string, unknown>)[key as string] as T;
    }
    return fallback as T;
  }

  public getSecret(secretName: string): string | undefined {
    return this.secretStore.get(secretName);
  }

  public setSecret(secretName: string, value: string): void {
    this.secretStore.set(secretName, value);
  }

  public setOverride(key: string, value: unknown): void {
    this.overrides.set(key, value);
  }

  public clearOverrides(): void {
    this.overrides.clear();
  }

  public getAdapterConfig(adapterType: string): AdapterRuntimeConfig {
    const config = this.defaults.adapterConfigs[adapterType] ?? {};
    // Automatically bind secret if present
    const secretKey = `${adapterType.split("_")[0]}_api_key`;
    const secretVal = this.getSecret(secretKey);
    return {
      ...config,
      ...(secretVal ? { apiKey: secretVal } : {}),
    };
  }
}

export const configManager = ConfigManager.getInstance();
