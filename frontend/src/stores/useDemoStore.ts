import { create } from 'zustand';

type Mode = 'slides' | 'manual' | 'auto' | 'lab';
type StepStatus = 'idle' | 'running' | 'done';

interface DemoStore {
  mode: Mode;
  slide: number;
  actIndex: number;

  ingestStatus: StepStatus;
  baselineStatus: StepStatus;
  nanoStatus: StepStatus;
  microStatus: StepStatus;
  macroStatus: StepStatus;
  cascadeStatus: StepStatus;
  loopStatus: StepStatus;

  detail: {
    open: boolean;
    title: string;
    content: Record<string, unknown> | null;
    type: 'agent' | 'evidence' | 'baseline' | 'action' | 'learning';
  };

  setMode: (mode: Mode) => void;
  setSlide: (slide: number | ((prev: number) => number)) => void;
  setActIndex: (index: number) => void;
  setStepStatus: (step: string, status: StepStatus) => void;
  openDetail: (title: string, content: Record<string, unknown>, type: DemoStore['detail']['type']) => void;
  closeDetail: () => void;
}

const initialState = {
  mode: 'slides' as const,
  slide: 0,
  actIndex: 0,
  ingestStatus: 'idle' as const,
  baselineStatus: 'idle' as const,
  nanoStatus: 'idle' as const,
  microStatus: 'idle' as const,
  macroStatus: 'idle' as const,
  cascadeStatus: 'idle' as const,
  loopStatus: 'idle' as const,
  detail: { open: false, title: '', content: null, type: 'agent' as const },
};

export const useDemoStore = create<DemoStore>((set) => ({
  mode: 'slides',
  slide: 0,
  actIndex: 0,

  ingestStatus: 'idle',
  baselineStatus: 'idle',
  nanoStatus: 'idle',
  microStatus: 'idle',
  macroStatus: 'idle',
  cascadeStatus: 'idle',
  loopStatus: 'idle',

  detail: { open: false, title: '', content: null, type: 'agent' },

  setMode: (mode) => set({ mode }),
  setSlide: (slide) => set((state) => ({
    slide: typeof slide === 'function' ? slide(state.slide) : slide,
  })),
  setActIndex: (actIndex) => set({ actIndex }),
  setStepStatus: (step, status) => set({ [`${step}Status`]: status } as Partial<DemoStore>),
  openDetail: (title, content, type) => set({ detail: { open: true, title, content, type } }),
  closeDetail: () => set((state) => ({ detail: { ...state.detail, open: false } })),
}));

export const resetDemoStore = () => useDemoStore.setState(initialState);
