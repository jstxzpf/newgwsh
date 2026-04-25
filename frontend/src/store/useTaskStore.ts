import { create } from 'zustand';

interface TaskState {
  progress: number;
  status: string;
  result: any;
}

interface TaskStore {
  activeTasks: Record<string, TaskState>;
  addTask: (id: string) => void;
  updateTask: (id: string, updates: Partial<TaskState>) => void;
  removeTask: (id: string) => void;
}

export const useTaskStore = create<TaskStore>((set) => ({
  activeTasks: {},
  addTask: (id) => set(state => ({
    activeTasks: { ...state.activeTasks, [id]: { progress: 0, status: 'QUEUED', result: null } }
  })),
  updateTask: (id, updates) => set(state => ({
    activeTasks: { 
      ...state.activeTasks, 
      [id]: { ...state.activeTasks[id], ...updates } 
    }
  })),
  removeTask: (id) => set(state => {
    const next = { ...state.activeTasks };
    delete next[id];
    return { activeTasks: next };
  }),
}));
