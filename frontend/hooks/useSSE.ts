"use client";
import { useEffect, useRef, useState } from "react";
import { Task } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useSSE(taskId: string | null) {
  const [task, setTask] = useState<Task | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!taskId) return;

    // Clean up any existing connection
    esRef.current?.close();
    setError(null);
    setConnected(false);

    const es = new EventSource(`${API_BASE}/tasks/${taskId}/stream`);
    esRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (event) => {
      try {
        const data: Task = JSON.parse(event.data);
        setTask(data);
        // Close connection once terminal state reached
        if (data.status === "done" || data.status === "failed") {
          es.close();
          setConnected(false);
        }
      } catch {
        setError("Failed to parse server event.");
      }
    };

    es.onerror = () => {
      setError("Connection to server lost. Retrying...");
      setConnected(false);
    };

    return () => {
      es.close();
    };
  }, [taskId]);

  return { task, connected, error };
}

export async function createTask(request: string): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create task.");
  }
  return res.json();
}
