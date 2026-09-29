/**
 * RoboAssistant Agent Engine — Core Orchestration Entrypoint
 * Transplanted from Paperclip open architecture into RoboAssistant OS.
 *
 * Exposes:
 * - HeartbeatCoordinator & HeartbeatPolicy
 * - SessionStateMachine (PRP Reducer)
 * - DelegationEngine
 * - AdapterRegistry & Builtin Model Adapters
 * - Centralized ConfigManager
 */

export * from "./types/index.js";
export * from "./config/config-manager.js";
export * from "./state-machine/session-reducer.js";
export * from "./heartbeat/heartbeat-policy.js";
export * from "./heartbeat/heartbeat-loop.js";
export * from "./delegation/delegation-engine.js";
export * from "./adapters/adapter-interface.js";
export * from "./adapters/builtin-adapters.js";
export * from "./adapters/adapter-registry.js";

import { HeartbeatCoordinator } from "./heartbeat/heartbeat-loop.js";
import { DelegationEngine } from "./delegation/delegation-engine.js";
import { adapterRegistry, AdapterRegistry } from "./adapters/adapter-registry.js";
import { configManager, ConfigManager } from "./config/config-manager.js";

export class AgentEngine {
  public readonly heartbeat: HeartbeatCoordinator;
  public readonly delegation: DelegationEngine;
  public readonly adapters: AdapterRegistry;
  public readonly config: ConfigManager;

  constructor() {
    this.heartbeat = new HeartbeatCoordinator();
    this.delegation = new DelegationEngine();
    this.adapters = adapterRegistry;
    this.config = configManager;
  }
}

export const agentEngine = new AgentEngine();
