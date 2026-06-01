"use client";

import { TaskContent } from "@/app/page";

interface TaskPanelProps {
  tasks: TaskContent[];
  onTaskClick: (taskId: string) => void;
}

export function TaskPanel({ tasks, onTaskClick }: TaskPanelProps) {
  return (
    <div className="task-panel">
      <h2>Tasks</h2>
      <div className="task-list">
        {tasks.map((task) => (
          <button
            key={task.task_id}
            onClick={() => onTaskClick(task.task_id)}
            className="task-item"
          >
            <span className="task-title">{task.title}</span>
            <span className={`task-lane lane-${task.lane}`}>{task.lane_label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
