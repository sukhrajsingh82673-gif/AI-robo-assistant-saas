/**
 * RoboAssistant Agent Engine — Unified Protocol & Domain Types
 * Transplanted and adapted from Paperclip specification contracts.
 */

// -------------------------------------------------------------
// Protocol & Replay Types (Paperclip Runner Protocol)
// -------------------------------------------------------------

export interface PrpIdentity {
  companyId: string;
  agentId: string;
  runId: string;
  sessionToken?: string;
  role?: string;
}

export interface PrpCapabilities {
  tools: boolean;
  streaming: boolean;
  maxTurns?: number;
}

export interface PrpCapabilitiesV2 extends PrpCapabilities {
  duplexCodec?: boolean;
  sessionGoals?: boolean;
  dynamicPermissions?: boolean;
}

export interface PrpTerminalState {
  runTerminalState: "succeeded" | "failed" | "cancelled" | "timed_out";
  turnTerminalState: "completed" | "failed" | "interrupted" | "cancelled";
  exitCode?: number;
  reason?: string;
}

export interface PrpStructuredRunResult {
  summary: string;
  deliverables?: Array<{ path: string; description: string }>;
  metrics?: Record<string, number | string>;
  disposition?: "done" | "needs_approval" | "blocked" | "delegated";
}

export interface PrpEvent {
  sourceKind: string;
  sourceInstanceId: string;
  sourceEventId: string;
  sourceSeq: number;
  eventType: string;
  emittedAt: string;
  itemId?: string;
  turnId?: string;
  payload: Record<string, unknown>;
}

export interface PrpFixture {
  name: string;
  identity: PrpIdentity;
  capabilities: PrpCapabilities | PrpCapabilitiesV2;
  events: PrpEvent[];
}

// -------------------------------------------------------------
// State Machine Types
// -------------------------------------------------------------

export interface SessionTimelineEntry {
  position: number;
  sourceEventId: string;
  sourceSeq: number;
  eventType: string;
  emittedAt: string;
  itemId?: string;
  summary: string;
}

export interface SessionItemSnapshot {
  itemId: string;
  kind: string;
  status: "running" | "completed" | "failed";
  text: string;
}

export interface SessionRequestSnapshot {
  requestId: string;
  requestKind: string;
  type: string;
  status: string;
  prompt: string;
}

export interface SequenceGap {
  sourceKey: string;
  expected: number;
  received: number;
  missingCount: number;
  missing: number[];
  truncated: boolean;
}

export interface SessionSnapshot {
  schema: "paperclip.prp.session-snapshot.v1";
  fixtureName: string;
  identity: PrpIdentity;
  capabilities: PrpCapabilities | PrpCapabilitiesV2;
  runPhase: string;
  sessionState: "not_started" | "running" | "closed" | "failed";
  turnState:
    | "not_started"
    | "running"
    | "completed"
    | "failed"
    | "interrupted"
    | "cancelled";
  activeTurnId: string | null;
  items: SessionItemSnapshot[];
  requests: SessionRequestSnapshot[];
  proposedResult: PrpStructuredRunResult | null;
  terminal: PrpTerminalState | null;
  timeline: SessionTimelineEntry[];
  sourceCursors: Record<string, number>;
  processedEventIds: string[];
  duplicateEventIds: string[];
  outOfOrderEventIds: string[];
  gaps: SequenceGap[];
  integrity: "complete" | "gap_detected";
}

// -------------------------------------------------------------
// Heartbeat & Lifecycle Types
// -------------------------------------------------------------

export type HeartbeatRunStatus =
  | "queued"
  | "running"
  | "waiting_for_approval"
  | "completed"
  | "failed"
  | "cancelled";

export interface HeartbeatWakePayload {
  agentId: string;
  companyId: string;
  trigger: "manual" | "schedule" | "assignment" | "approval_resolved" | "comment_mention";
  taskId?: string;
  approvalId?: string;
  commentId?: string;
  metadata?: Record<string, unknown>;
}

export interface HeartbeatRun {
  runId: string;
  companyId: string;
  agentId: string;
  status: HeartbeatRunStatus;
  startedAt: string;
  finishedAt?: string;
  activeTaskId?: string;
  lastHeartbeatTime: string;
  stepCount: number;
}

// -------------------------------------------------------------
// Delegation Types
// -------------------------------------------------------------

export type DelegationTaskStatus =
  | "pending_approval"
  | "approved"
  | "assigned"
  | "in_progress"
  | "in_review"
  | "completed"
  | "blocked"
  | "failed";

export interface DelegationSubtask {
  id: string;
  parentId: string;
  title: string;
  description: string;
  targetRole: string;
  assignedAgentId?: string;
  priority: "urgent" | "high" | "medium" | "low";
  dependencies: string[];
  status: DelegationTaskStatus;
  result?: string;
}

export interface DelegationPlan {
  goalId: string;
  goalTitle: string;
  leadAgentId: string;
  requiresBoardApproval: boolean;
  approvalStatus: "pending" | "approved" | "rejected";
  subtasks: DelegationSubtask[];
  createdAt: string;
}

// -------------------------------------------------------------
// Adapter Types
// -------------------------------------------------------------

export interface ModelPromptMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  name?: string;
  toolCallId?: string;
}

export interface ModelToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ModelPrompt {
  messages: ModelPromptMessage[];
  systemInstruction?: string;
  tools?: ModelToolDefinition[];
  temperature?: number;
  maxTokens?: number;
}

export interface ModelToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

export interface ModelResponse {
  content: string;
  toolCalls?: ModelToolCall[];
  tokenUsage?: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
  };
  finishReason: "stop" | "tool_calls" | "length" | "error";
}

export interface ModelDelta {
  textChunk?: string;
  toolCallChunk?: Partial<ModelToolCall>;
  isFinal: boolean;
}
