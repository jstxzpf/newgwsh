import { create } from 'zustand'

interface TaskState {
  activeTaskIds: string[];
  taskResults: Record<string, any>;
  addTask: (id: string) => void;
  removeTask: (id: string) => void;
  setTaskResult: (id: string, result: any) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  activeTaskIds: [],
  taskResults: {},
  addTask: (id) => set((state) => ({ activeTaskIds: [...state.activeTaskIds, id] })),
  removeTask: (id) => set((state) => ({ activeTaskIds: state.activeTaskIds.filter(tid => tid !== id) })),
  setTaskResult: (id, result) => set((state) => ({ taskResults: { ...state.taskResults, [id]: result } }))
}))