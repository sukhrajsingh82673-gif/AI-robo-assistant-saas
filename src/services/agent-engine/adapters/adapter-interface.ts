/**
 * RoboAssistant Agent Engine — Multi-Model Adapter Interface
 * Unified contract for LLM provider adapters.
 */

import type {
  ModelPrompt,
  ModelResponse,
  ModelDelta,
} from "../types/index.js";

export interface ModelAdapter {
  readonly adapterType: string;
  readonly defaultModel: string;

  /**
   * Generates a non-streaming completion with optional tool calls.
   */
  generate(prompt: ModelPrompt): Promise<ModelResponse>;

  /**
   * Generates a streaming completion yielding deltas.
   */
  stream?(prompt: ModelPrompt): AsyncIterable<ModelDelta>;

  /**
   * Returns whether this adapter supports function/tool execution.
   */
  supportsTools(): boolean;
}
