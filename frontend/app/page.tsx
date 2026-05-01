"use client";
import { useState } from "react";
import { useSSE, createTask } from "@/hooks/useSSE";
import { AGENT_PIPELINE, Task, TaskStatus } from "@/types";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getActiveAgent(status: TaskStatus): string | null {
  const map: Partial<Record<TaskStatus, string>> = {
    planning: "planning",
    researching: "researching",
    writing: "writing",
    reviewing: "reviewing",
    revision: "writing",
  };
  return map[status] ?? null;
}

function statusLabel(status: TaskStatus): string {
  const labels: Record<TaskStatus, string> = {
    pending: "Waiting to start...",
    planning: "Planner is breaking down your request...",
    researching: "Researcher is gathering information in parallel...",
    writing: "Writer is drafting the report...",
    reviewing: "Reviewer is evaluating the draft...",
    revision: "Writer is revising based on reviewer feedback...",
    done: "Complete! Your report is ready.",
    failed: "Something went wrong.",
  };
  return labels[status] ?? status;
}

function isAgentComplete(agentKey: string, status: TaskStatus): boolean {
  const order = ["planning", "researching", "writing", "reviewing"];
  const active = getActiveAgent(status);
  const currentIdx = order.indexOf(active ?? "");
  const agentIdx = order.indexOf(agentKey);
  if (status === "done") return true;
  if (status === "revision" && agentKey === "writing") return false;
  if (status === "revision" && agentKey === "reviewing") return false;
  return agentIdx < currentIdx;
}

function renderMarkdown(text: string) {
  return text.split("\n").map((line, i) => {
    if (line.startsWith("# "))   return <h1 key={i}>{line.slice(2)}</h1>;
    if (line.startsWith("## "))  return <h2 key={i}>{line.slice(3)}</h2>;
    if (line.startsWith("### ")) return <h3 key={i}>{line.slice(4)}</h3>;
    if (line.startsWith("- "))   return <li key={i}>{line.slice(2)}</li>;
    if (line.startsWith("---"))  return <hr key={i} />;
    if (line.startsWith("> "))   return <blockquote key={i}>{line.slice(2)}</blockquote>;
    if (line.trim() === "")      return <br key={i} />;
    return <p key={i}>{line}</p>;
  });
}

// ─── Pipeline Visualizer ─────────────────────────────────────────────────────

function PipelineVisualizer({ task }: { task: Task | null }) {
  const activeAgent = task ? getActiveAgent(task.status) : null;
  return (
    <div className="pipeline-container">
      {AGENT_PIPELINE.map((agent, i) => {
        const isActive   = activeAgent === agent.key;
        const isDone     = task ? isAgentComplete(agent.key, task.status) : false;
        const isRevision = task?.status === "revision" && agent.key === "writing";
        return (
          <div key={agent.key} className="pipeline-step">
            <div className={`agent-card ${isActive ? "active" : ""} ${isDone ? "done" : ""} ${isRevision ? "revision" : ""}`}>
              <div className="agent-icon">{agent.icon}</div>
              <div className="agent-info">
                <div className="agent-label">
                  {agent.label}
                  {isRevision && <span className="revision-badge">REVISING</span>}
                </div>
                <div className="agent-desc">{agent.description}</div>
              </div>
              <div className="agent-status-dot">
                {isActive && <span className="pulse-dot" />}
                {isDone   && <span className="check">✓</span>}
              </div>
            </div>
            {i < AGENT_PIPELINE.length - 1 && (
              <div className={`connector ${isDone ? "done" : ""}`}>→</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Sub Task List ────────────────────────────────────────────────────────────

function SubTaskList({ subTasks }: { subTasks: string[] }) {
  if (!subTasks.length) return null;
  return (
    <div className="card">
      <h3 className="card-title">📋 Planner — Sub-Tasks Generated</h3>
      <ol className="subtask-list">
        {subTasks.map((t, i) => <li key={i}>{t}</li>)}
      </ol>
    </div>
  );
}

// ─── Agent IO Card (expandable) ──────────────────────────────────────────────

function AgentIOCard({ step }: { step: Task["steps"][0] }) {
  const [expanded, setExpanded] = useState(false);
  const iconMap:  Record<string, string> = { Planner: "🧠", Researcher: "🔍", Writer: "✍️", Reviewer: "🔎", Orchestrator: "⚙️" };
  const colorMap: Record<string, string> = { Planner: "#7c6af7", Researcher: "#4ecca3", Writer: "#f4a261", Reviewer: "#e76f51", Orchestrator: "#888" };
  const color = colorMap[step.agent] || "#7c6af7";

  const isRejection = step.agent === "Reviewer" && step.output_summary.toUpperCase().includes("REJECTED");
  const isRetry     = step.output_summary.toLowerCase().includes("retrying");
  const isFailed    = step.status === "failed";

  return (
    <div className="chain-node" style={{ borderColor: isFailed ? "var(--failed)" : isRejection ? "var(--revision)" : color }}>
      <div className="chain-node-header" onClick={() => setExpanded(!expanded)}>
        <span className="chain-icon">{iconMap[step.agent] || "🤖"}</span>
        <span className="chain-agent" style={{ color: isFailed ? "var(--failed)" : color }}>{step.agent}</span>
        {isRejection && <span className="badge badge-rejected">REJECTED</span>}
        {isRetry     && <span className="badge badge-retry">RETRY</span>}
        {isFailed    && <span className="badge badge-failed">FAILED</span>}
        {!isRejection && !isRetry && !isFailed && step.status === "done" &&
          <span className="badge badge-done">DONE</span>
        }
        <span className="chain-summary">{step.output_summary}</span>
        <span className="chain-toggle">{expanded ? "▲" : "▼"}</span>
      </div>
      {expanded && (
        <div className="chain-node-body">
          <div className="chain-io">
            <div className="chain-io-block">
              <span className="chain-io-label">📥 Input</span>
              <span className="chain-io-value">{step.input_summary}</span>
            </div>
            <div className="chain-io-arrow">→</div>
            <div className="chain-io-block">
              <span className="chain-io-label">📤 Output</span>
              <span className="chain-io-value">{step.output_summary}</span>
            </div>
          </div>
          <span className="chain-time">🕐 {new Date(step.timestamp).toLocaleTimeString()}</span>
        </div>
      )}
    </div>
  );
}

// ─── Rejection Block — shown inline right after Reviewer rejects ─────────────

function RejectionBlock({ feedback, revisionCount }: { feedback: string; revisionCount: number }) {
  return (
    <div className="rejection-block">
      <div className="rejection-header">
        <span className="rejection-icon">🔄</span>
        <span className="rejection-title">
          Reviewer rejected draft v{revisionCount} — sending feedback to Writer
        </span>
      </div>
      <pre className="rejection-feedback">{feedback}</pre>
      <div className="rejection-footer">↓ Writer is now revising...</div>
    </div>
  );
}

// ─── Chain of Actions + Inline Feedback + Final Report ───────────────────────

function ChainAndReport({ task }: { task: Task }) {
  const { steps, final_report, reviewer_feedback, revision_count, status } = task;

  const rendered: JSX.Element[] = [];

  steps.forEach((step, i) => {
    rendered.push(
      <div key={`step-${i}`}>
        <AgentIOCard step={step} />
      </div>
    );

    // After Reviewer REJECTION — show feedback inline immediately
    const isRejection = step.agent === "Reviewer" && step.output_summary.toUpperCase().includes("REJECTED");
    if (isRejection && reviewer_feedback) {
      rendered.push(
        <div key={`feedback-${i}`}>
          <div className="chain-arrow chain-arrow-rejection">↓</div>
          <RejectionBlock feedback={reviewer_feedback} revisionCount={revision_count} />
          <div className="chain-arrow chain-arrow-revision">↓ Writer revising</div>
        </div>
      );
    }

    // Arrow between steps (not after last)
    if (i < steps.length - 1) {
      rendered.push(<div key={`arrow-${i}`} className="chain-arrow">↓</div>);
    }
  });

  return (
    <div className="card">
      <h3 className="card-title">🗂 Chain of Agent Actions → Final Report</h3>
      <div className="chain-container">
        {rendered}

        {/* Final report connected directly to chain */}
        {final_report && (
          <>
            <div className="chain-arrow chain-arrow-done">↓ Approved</div>
            <div className="chain-final">
              <div className="chain-final-header">
                <span>📄 Final Report</span>
                <span className="badge badge-approved">✅ APPROVED</span>
              </div>
              <div className="report-body chain-final-body">
                {renderMarkdown(final_report)}
              </div>
            </div>
          </>
        )}

        {/* Still running — pulse indicator */}
        {!final_report && status !== "failed" && (
          <div className="chain-arrow">
            <span className="pulse-dot" style={{ display: "inline-block" }} />
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Home() {
  const [input, setInput]             = useState("");
  const [taskId, setTaskId]           = useState<string | null>(null);
  const [submitting, setSubmitting]   = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { task, connected, error: sseError } = useSSE(taskId);

  async function handleSubmit() {
    if (!input.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const { task_id } = await createTask(input.trim());
      setTaskId(task_id);
    } catch (e: any) {
      setSubmitError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleReset() {
    setTaskId(null);
    setInput("");
    setSubmitError(null);
  }

  return (
    <div className="page">

        <header className="header">
          <div className="header-inner">
            <div className="logo">⚙️ AgentFlow</div>
            <div className="subtitle">Multi-Agent Task Orchestration</div>
          </div>
        </header>

        <main className="main">

          {/* ── Task Submission ── */}
          {!taskId && (
            <div className="hero">
              <h1 className="hero-title">What should the agents research?</h1>
              <p className="hero-sub">
                Submit a research or analysis request. Four specialized agents will
                collaborate to produce your report — with real-time progress updates.
              </p>
              <div className="form-area">
                <textarea
                  className="textarea"
                  placeholder='e.g. "Research the pros and cons of microservices vs monoliths"'
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  rows={4}
                />
                <div className="examples">
                  <span>Try: </span>
                  {[
                    "Compare microservices vs monolith architecture",
                    "Research pros and cons of TypeScript",
                    "Analyze benefits of remote work",
                  ].map((ex) => (
                    <button key={ex} className="example-chip" onClick={() => setInput(ex)}>
                      {ex}
                    </button>
                  ))}
                </div>
                {submitError && <div className="error-msg">{submitError}</div>}
                <button
                  className="submit-btn"
                  onClick={handleSubmit}
                  disabled={submitting || !input.trim()}
                >
                  {submitting ? "Starting agents..." : "Run Agent Pipeline →"}
                </button>
              </div>
            </div>
          )}

          {/* ── Pipeline View ── */}
          {taskId && (
            <div className="pipeline-view">

              {/* Status bar */}
              <div className="status-bar">
                <div className={`status-indicator ${task?.status}`} />
                <span className="status-text">
                  {task ? statusLabel(task.status) : "Connecting..."}
                </span>
                {task?.revision_count ? (
                  <span className="revision-count-badge">🔄 Revision {task.revision_count}</span>
                ) : null}
                {connected && <span className="live-badge">● LIVE</span>}
              </div>

              {/* Pipeline visualizer */}
              <PipelineVisualizer task={task ?? null} />

              {task && (
                <>
                  {/* Sub-tasks from Planner */}
                  {task.sub_tasks.length > 0 && (
                    <SubTaskList subTasks={task.sub_tasks} />
                  )}

                  {/* Chain of actions + inline rejection feedback + final report */}
                  {task.steps.length > 0 && (
                    <ChainAndReport task={task} />
                  )}

                  {/* Failed state with retry info */}
                  {task.status === "failed" && (
                    <div className="card error-card">
                      <h3>⚠️ Pipeline Failed</h3>
                      <p>{task.error}</p>
                      <p className="error-hint">
                        The orchestrator retried each agent up to 2 times before failing.
                        Check the chain above to see which step failed.
                      </p>
                    </div>
                  )}
                </>
              )}

              <button className="reset-btn" onClick={handleReset}>
                ← New Request
              </button>
            </div>
          )}
        </main>
      </div>
  );
}