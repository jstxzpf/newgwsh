import { create } from 'zustand';

interface TaskState {
  activeTaskIds: string[];
  addTask: (taskId: string) => void;
  removeTask: (taskId: string) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  activeTaskIds: [],
  addTask: (taskId) => set((state) => ({ 
    activeTaskIds: state.activeTaskIds.includes(taskId) 
      ? state.activeTaskIds 
      : [...state.activeTaskIds, taskId] 
  })),
  removeTask: (taskId) => set((state) => ({ 
    activeTaskIds: state.activeTaskIds.filter(id => id !== taskId) 
  })),
}));
