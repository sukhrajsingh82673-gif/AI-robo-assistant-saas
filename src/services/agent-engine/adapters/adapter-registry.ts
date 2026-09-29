/**
 * RoboAssistant Agent Engine — Adapter Registry
 * Manages discovery, registration, and selection of model harnesses.
 */

import type { ModelAdapter } from "./adapter-interface.js";
import {
  GeminiAdapter,
  ClaudeAdapter,
  OpenAIAdapter,
  LocalProcessAdapter,
} from "./builtin-adapters.js";
import { configManager } from "../config/config-manager.js";

export class AdapterRegistry {
  private adapters: Map<string, ModelAdapter> = new Map();

  constructor() {
    this.registerBuiltins();
  }

  private registerBuiltins(): void {
    this.register(new GeminiAdapter());
    this.register(new ClaudeAdapter());
    this.register(new OpenAIAdapter());
    this.register(new LocalProcessAdapter());
  }

  public register(adapter: ModelAdapter): void {
    this.adapters.set(adapter.adapterType, adapter);
  }

  public get(adapterType?: string): ModelAdapter {
    const targetType = adapterType ?? configManager.get("defaultModelAdapter", "gemini_local");
    const adapter = this.adapters.get(targetType);
    if (!adapter) {
      // Fallback to first available or default gemini
      return this.adapters.get("gemini_local") ?? Array.from(this.adapters.values())[0];
    }
    return adapter;
  }

  public listAdapters(): string[] {
    return Array.from(this.adapters.keys());
  }
}

export const adapterRegistry = new AdapterRegistry();
