/**
 * RoboAssistant Enterprise UI/UX Data Types & Contracts
 */

export type ThemeMode = 'dark' | 'light';

export type AuthorityCeiling = 
  | 'SANDBOXED_READ_ONLY' 
  | 'AUTOMATIC_IDEMPOTENT' 
  | 'ASK_ME' 
  | 'NEVER_ALLOWED';

export interface AIEmployee {
  id: number;
  name: string;
  role: string;
  department: string;
  manager: string;
  missions: number;
  status: 'Online' | 'Idle' | 'Offline';
  authorityLevel: AuthorityCeiling;
  monthlyBudget: number;
  incurredCost: number;
  tokensUsed: number;
  tokenLimit: number;
  gradient: string;
  initials: string;
}

export interface BusinessMission {
  id: string;
  title: string;
  assignedAgent: string;
  department: string;
  targetOutcome: string;
  progress: number;
  status: 'In Progress' | 'Completed' | 'Pending' | 'Blocked';
  dueTime: string;
  verifiedDigest?: string;
}

export interface ConnectedHost {
  id: string;
  name: string;
  os: string;
  isPrimary?: boolean;
  status: 'Online' | 'Offline' | 'Standby';
  connectedAgents: number;
  cpuLoadPercentage: number;
  latencyMs: number;
}

export interface PortfolioKPI {
  totalRevenue: number;
  revenueChangePct: number;
  activeEmployees: number;
  newEmployeesProvisioned: number;
  runningMissions: number;
  systemHealthPct: number;
  policyViolations: number;
}
