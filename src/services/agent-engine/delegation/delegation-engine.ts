/**
 * RoboAssistant Agent Engine — Task Delegation & Orchestration Engine
 * Transplanted and adapted from Paperclip Board-Operator Delegation Model.
 *
 * Provides:
 * 1. Goal decomposition into specialized subtasks
 * 2. Role-based agent dispatch (CEO -> CTO / Lead / Specialist)
 * 3. Dependency DAG tracking & cascading completion
 * 4. Cycle detection (preventing hot-potato infinite loops)
 * 5. Board/Owner approval gates for high-impact plans
 */

import { randomUUID } from "node:crypto";
import type {
  DelegationPlan,
  DelegationSubtask,
  DelegationTaskStatus,
} from "../types/index.js";
import { configManager } from "../config/config-manager.js";

export interface AgentDescriptor {
  agentId: string;
  role: string;
  department: string;
  capabilities: string[];
}

export class DelegationEngine {
  private plans: Map<string, DelegationPlan> = new Map();
  private agentRegistry: Map<string, AgentDescriptor> = new Map();

  public registerAgent(agent: AgentDescriptor): void {
    this.agentRegistry.set(agent.agentId, agent);
  }

  /**
   * Decomposes a high-level goal into a structured delegation plan.
   */
  public createDelegationPlan(
    goalId: string,
    goalTitle: string,
    leadAgentId: string,
    rawSubtasks: Array<{
      title: string;
      description: string;
      targetRole: string;
      priority: "urgent" | "high" | "medium" | "low";
      dependencies?: string[];
    }>,
    requiresBoardApproval: boolean = false
  ): DelegationPlan {
    const maxDepth = configManager.get("delegationMaxDepth", 5);

    const subtasks: DelegationSubtask[] = rawSubtasks.map((st) => {
      const subtaskId = `subtask_${randomUUID()}`;
      const deps = st.dependencies ?? [];
      const initialStatus: DelegationTaskStatus = requiresBoardApproval
        ? "pending_approval"
        : (deps.length > 0 ? "blocked" : "assigned");

      return {
        id: subtaskId,
        parentId: goalId,
        title: st.title,
        description: st.description,
        targetRole: st.targetRole,
        priority: st.priority,
        dependencies: deps,
        status: initialStatus,
        assignedAgentId: this.findBestAgentForRole(st.targetRole)?.agentId,
      };
    });

    // Detect dependency cycles before finalizing
    this.validateNoCycles(subtasks);

    const plan: DelegationPlan = {
      goalId,
      goalTitle,
      leadAgentId,
      requiresBoardApproval,
      approvalStatus: requiresBoardApproval ? "pending" : "approved",
      subtasks,
      createdAt: new Date().toISOString(),
    };

    this.plans.set(goalId, plan);
    return plan;
  }

  /**
   * Resolves the best matching agent for a target role or capability.
   */
  public findBestAgentForRole(role: string): AgentDescriptor | undefined {
    const normalized = role.toLowerCase();
    for (const agent of this.agentRegistry.values()) {
      if (agent.role.toLowerCase() === normalized || agent.capabilities.some(c => c.toLowerCase() === normalized)) {
        return agent;
      }
    }
    // Return any agent in registry if exact match not found, or undefined
    return this.agentRegistry.values().next().value;
  }

  /**
   * Approves a pending delegation plan, unlocking all root subtasks.
   */
  public approvePlan(goalId: string): boolean {
    const plan = this.plans.get(goalId);
    if (!plan) return false;

    plan.approvalStatus = "approved";
    for (const subtask of plan.subtasks) {
      if (subtask.status === "pending_approval") {
        subtask.status = subtask.dependencies.length === 0 ? "assigned" : "blocked";
      }
    }
    return true;
  }

  /**
   * Marks a subtask as complete and unblocks downstream dependent tasks.
   */
  public completeSubtask(goalId: string, subtaskId: string, result: string): {
    unblockedTasks: DelegationSubtask[];
    isGoalComplete: boolean;
  } {
    const plan = this.plans.get(goalId);
    if (!plan) throw new Error(`Plan for goal ${goalId} not found`);

    const subtask = plan.subtasks.find((s) => s.id === subtaskId);
    if (!subtask) throw new Error(`Subtask ${subtaskId} not found`);

    subtask.status = "completed";
    subtask.result = result;

    const unblockedTasks: DelegationSubtask[] = [];
    const completedIds = new Set(
      plan.subtasks.filter((s) => s.status === "completed").map((s) => s.id)
    );

    for (const pending of plan.subtasks) {
      if (pending.status === "blocked") {
        const allResolved = pending.dependencies.every((depId) => completedIds.has(depId));
        if (allResolved) {
          pending.status = "assigned";
          unblockedTasks.push(pending);
        }
      }
    }

    const isGoalComplete = plan.subtasks.every((s) => s.status === "completed");
    return { unblockedTasks, isGoalComplete };
  }

  /**
   * Topological DAG cycle validation.
   */
  private validateNoCycles(subtasks: DelegationSubtask[]): void {
    const adj = new Map<string, string[]>();
    for (const st of subtasks) {
      adj.set(st.id, st.dependencies);
    }

    const visited = new Set<string>();
    const inStack = new Set<string>();

    const dfs = (id: string) => {
      visited.add(id);
      inStack.add(id);
      for (const dep of adj.get(id) ?? []) {
        if (!visited.has(dep)) {
          if (dfs(dep)) return true;
        } else if (inStack.has(dep)) {
          return true; // Cycle detected
        }
      }
      inStack.delete(id);
      return false;
    };

    for (const st of subtasks) {
      if (!visited.has(st.id)) {
        if (dfs(st.id)) {
          throw new Error(`Circular dependency detected in delegation plan around task: ${st.title}`);
        }
      }
    }
  }

  public getPlan(goalId: string): DelegationPlan | undefined {
    return this.plans.get(goalId);
  }
}
