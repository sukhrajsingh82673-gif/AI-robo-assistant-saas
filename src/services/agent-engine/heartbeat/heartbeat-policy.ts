/**
 * RoboAssistant Agent Engine — Heartbeat Scheduling & Execution Policy
 * Uses centralized ConfigManager instead of direct environment reads.
 */

import { configManager } from "../config/config-manager.js";

export interface AgentHeartbeatConfig {
  wakeOnDemand?: boolean;
  wakeOnAssignment?: boolean;
  wakeOnAutomation?: boolean;
  wakeIntervalMs?: number;
  maxConsecutiveFailures?: number;
  cooldownPeriodMs?: number;
}

export class HeartbeatPolicy {
  /**
   * Evaluates whether an agent should wake immediately upon an external event.
   */
  public static isWakeOnDemandEnabled(config?: AgentHeartbeatConfig): boolean {
    if (!config) return true;
    return Boolean(
      config.wakeOnDemand ??
      config.wakeOnAssignment ??
      config.wakeOnAutomation ??
      true
    );
  }

  /**
   * Calculates the next wake interval in milliseconds with random jitter
   * and exponential backoff on consecutive failures.
   */
  public static calculateNextWakeInterval(
    consecutiveFailures: number = 0,
    customIntervalMs?: number
  ): number {
    const baseInterval = customIntervalMs ?? configManager.get("heartbeatIntervalMs", 30000);
    const jitterRange = configManager.get("heartbeatJitterMs", 2500);

    // Apply exponential backoff: base * 2^failures, capped at 10 minutes
    const backoffMultiplier = Math.min(Math.pow(2, consecutiveFailures), 20);
    const intervalWithBackoff = baseInterval * backoffMultiplier;

    // Apply symmetric jitter: +/- jitterRange
    const jitter = (Math.random() * 2 - 1) * jitterRange;
    const finalInterval = Math.max(1000, Math.floor(intervalWithBackoff + jitter));

    return finalInterval;
  }

  /**
   * Determines if the agent has exceeded max allowable retries before requiring
   * operator intervention.
   */
  public static shouldPauseAgent(consecutiveFailures: number): boolean {
    const maxRetries = configManager.get("heartbeatMaxRetries", 5);
    return consecutiveFailures >= maxRetries;
  }
}
