import { create } from 'zustand';

interface InfraData {
  runtime: Record<string, unknown>;
  inference: Record<string, unknown>;
  agents: Record<string, unknown>;
  pipeline: Record<string, unknown>;
  framework: Record<string, unknown>;
}

interface InfraStore {
  data: InfraData | null;
  health: { status: string } | null;
  loading: boolean;

  setData: (data: InfraData) => void;
  setHealth: (health: { status: string }) => void;
  setLoading: (loading: boolean) => void;
  fetchInfra: () => Promise<void>;
}

export const useInfraStore = create<InfraStore>((set) => ({
  data: null,
  health: null,
  loading: false,

  setData: (data) => set({ data }),
  setHealth: (health) => set({ health }),
  setLoading: (loading) => set({ loading }),
  fetchInfra: async () => {
    set({ loading: true });
    try {
      const res = await fetch('/api/v1/demo/infrastructure');
      const data = await res.json();
      set({ data, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
