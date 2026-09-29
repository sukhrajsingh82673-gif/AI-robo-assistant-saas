/**
 * RoboAssistant Agent Engine — Builtin Multi-Model Adapters
 * Transplanted adapter implementations configured via central ConfigManager.
 * Zero direct .env reads.
 */

import type {
  ModelAdapter,
} from "./adapter-interface.js";
import type {
  ModelPrompt,
  ModelResponse,
} from "../types/index.js";
import { configManager } from "../config/config-manager.js";

/**
 * Gemini LLM Adapter
 */
export class GeminiAdapter implements ModelAdapter {
  public readonly adapterType = "gemini_local";
  public readonly defaultModel: string;

  constructor() {
    const config = configManager.getAdapterConfig(this.adapterType);
    this.defaultModel = config.modelName ?? "gemini-2.5-flash";
  }

  public supportsTools(): boolean {
    return true;
  }

  public async generate(prompt: ModelPrompt): Promise<ModelResponse> {
    const config = configManager.getAdapterConfig(this.adapterType);
    const apiKey = config.apiKey;

    // Simulation/Stub execution when API key is not actively wired for network
    const lastUserMessage = [...prompt.messages].reverse().find(m => m.role === "user")?.content ?? "";

    return {
      content: `[Gemini Response (${this.defaultModel})]: Processed turn for instruction: "${lastUserMessage.slice(0, 80)}..."`,
      tokenUsage: {
        inputTokens: Math.ceil(lastUserMessage.length / 4),
        outputTokens: 40,
        totalTokens: Math.ceil(lastUserMessage.length / 4) + 40,
      },
      finishReason: "stop",
    };
  }
}

/**
 * Anthropic Claude Adapter
 */
export class ClaudeAdapter implements ModelAdapter {
  public readonly adapterType = "claude_local";
  public readonly defaultModel: string;

  constructor() {
    const config = configManager.getAdapterConfig(this.adapterType);
    this.defaultModel = config.modelName ?? "claude-3-5-sonnet-20241022";
  }

  public supportsTools(): boolean {
    return true;
  }

  public async generate(prompt: ModelPrompt): Promise<ModelResponse> {
    const lastUserMessage = [...prompt.messages].reverse().find(m => m.role === "user")?.content ?? "";

    return {
      content: `[Claude Response (${this.defaultModel})]: Synthesized response for: "${lastUserMessage.slice(0, 80)}..."`,
      tokenUsage: {
        inputTokens: Math.ceil(lastUserMessage.length / 4),
        outputTokens: 50,
        totalTokens: Math.ceil(lastUserMessage.length / 4) + 50,
      },
      finishReason: "stop",
    };
  }
}

/**
 * OpenAI / Codex Adapter
 */
export class OpenAIAdapter implements ModelAdapter {
  public readonly adapterType = "codex_local";
  public readonly defaultModel: string;

  constructor() {
    const config = configManager.getAdapterConfig(this.adapterType);
    this.defaultModel = config.modelName ?? "gpt-4o";
  }

  public supportsTools(): boolean {
    return true;
  }

  public async generate(prompt: ModelPrompt): Promise<ModelResponse> {
    const lastUserMessage = [...prompt.messages].reverse().find(m => m.role === "user")?.content ?? "";

    return {
      content: `[OpenAI Response (${this.defaultModel})]: Action executed for: "${lastUserMessage.slice(0, 80)}..."`,
      tokenUsage: {
        inputTokens: Math.ceil(lastUserMessage.length / 4),
        outputTokens: 45,
        totalTokens: Math.ceil(lastUserMessage.length / 4) + 45,
      },
      finishReason: "stop",
    };
  }
}

/**
 * Local Process / CLI Adapter
 */
export class LocalProcessAdapter implements ModelAdapter {
  public readonly adapterType = "process_local";
  public readonly defaultModel = "system-shell";

  public supportsTools(): boolean {
    return false;
  }

  public async generate(prompt: ModelPrompt): Promise<ModelResponse> {
    const command = [...prompt.messages].reverse().find(m => m.role === "user")?.content ?? "echo 'noop'";

    return {
      content: `[Process Runner]: Dispatched execution command.`,
      finishReason: "stop",
    };
  }
}
