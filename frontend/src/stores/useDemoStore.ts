import { create } from 'zustand';

type Mode = 'slides' | 'manual' | 'auto' | 'lab' | 'dashboard' | 'governance';
type StepStatus = 'idle' | 'running' | 'done';

interface DemoStore {
  mode: Mode;
  slide: number;
  actIndex: number;
  dashPage: string;

  ingestStatus: StepStatus;
  baselineStatus: StepStatus;
  nanoStatus: StepStatus;
  microStatus: StepStatus;
  macroStatus: StepStatus;
  cascadeStatus: StepStatus;
  loopStatus: StepStatus;

  // Fleet-specific step statuses
  costStatus: StepStatus;
  eventProfileStatus: StepStatus;
  fleetNanoStatus: StepStatus;
  forecastStatus: StepStatus;
  blastRadiusStatus: StepStatus;
  intentStatus: StepStatus;
  ledgerStatus: StepStatus;

  detail: {
    open: boolean;
    title: string;
    content: Record<string, unknown> | null;
    type: 'agent' | 'evidence' | 'baseline' | 'action' | 'learning' | 'intent' | 'ledger';
  };

  setMode: (mode: Mode) => void;
  setSlide: (slide: number | ((prev: number) => number)) => void;
  setActIndex: (index: number) => void;
  setDashPage: (page: string) => void;
  setStepStatus: (step: string, status: StepStatus) => void;
  openDetail: (title: string, content: Record<string, unknown>, type: DemoStore['detail']['type']) => void;
  closeDetail: () => void;
}

const initialState = {
  mode: 'slides' as const,
  slide: 0,
  actIndex: 0,
  dashPage: 'overview',
  ingestStatus: 'idle' as const,
  baselineStatus: 'idle' as const,
  nanoStatus: 'idle' as const,
  microStatus: 'idle' as const,
  macroStatus: 'idle' as const,
  cascadeStatus: 'idle' as const,
  loopStatus: 'idle' as const,
  costStatus: 'idle' as const,
  eventProfileStatus: 'idle' as const,
  fleetNanoStatus: 'idle' as const,
  forecastStatus: 'idle' as const,
  blastRadiusStatus: 'idle' as const,
  intentStatus: 'idle' as const,
  ledgerStatus: 'idle' as const,
  detail: { open: false, title: '', content: null, type: 'agent' as const },
};

export const useDemoStore = create<DemoStore>((set) => ({
  mode: 'slides',
  slide: 0,
  actIndex: 0,
  dashPage: 'overview',

  ingestStatus: 'idle',
  baselineStatus: 'idle',
  nanoStatus: 'idle',
  microStatus: 'idle',
  macroStatus: 'idle',
  cascadeStatus: 'idle',
  loopStatus: 'idle',
  costStatus: 'idle',
  eventProfileStatus: 'idle',
  fleetNanoStatus: 'idle',
  forecastStatus: 'idle',
  blastRadiusStatus: 'idle',
  intentStatus: 'idle',
  ledgerStatus: 'idle',

  detail: { open: false, title: '', content: null, type: 'agent' },

  setMode: (mode) => set({ mode }),
  setDashPage: (dashPage) => set({ dashPage }),
  setSlide: (slide) => set((state) => ({
    slide: typeof slide === 'function' ? slide(state.slide) : slide,
  })),
  setActIndex: (actIndex) => set({ actIndex }),
  setStepStatus: (step, status) => set({ [`${step}Status`]: status } as Partial<DemoStore>),
  openDetail: (title, content, type) => set({ detail: { open: true, title, content, type } }),
  closeDetail: () => set((state) => ({ detail: { ...state.detail, open: false } })),
}));

export const resetDemoStore = () => useDemoStore.setState(initialState);
