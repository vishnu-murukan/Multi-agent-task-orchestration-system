export type TaskStatus =
  | "pending"
  | "planning"
  | "researching"
  | "writing"
  | "reviewing"
  | "revision"
  | "done"
  | "failed";

export interface AgentStep {
  agent: string;
  status: "running" | "done" | "failed";
  input_summary: string;
  output_summary: string;
  timestamp: string;
}

export interface Task {
  id: string;
  user_request: string;
  status: TaskStatus;
  steps: AgentStep[];
  sub_tasks: string[];
  draft_report: string | null;
  reviewer_feedback: string | null;
  revision_count: number;
  final_report: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export const AGENT_PIPELINE = [
  { key: "planning",    label: "Planner",    icon: "🧠", description: "Breaks request into sub-tasks" },
  { key: "researching", label: "Researcher", icon: "🔍", description: "Gathers information per sub-task" },
  { key: "writing",     label: "Writer",     icon: "✍️",  description: "Synthesizes research into draft" },
  { key: "reviewing",   label: "Reviewer",   icon: "🔎", description: "Evaluates quality and approves" },
];

export const STATUS_ORDER: TaskStatus[] = [
  "pending", "planning", "researching", "writing", "reviewing", "revision", "done", "failed"
];
