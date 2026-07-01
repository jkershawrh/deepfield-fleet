import { lazy, Suspense, useState, useRef, useEffect } from 'react';
import { Routes, Route, NavLink, useLocation } from 'react-router-dom';

const MultimodalEvidence = lazy(() => import('./pages/MultimodalEvidence'));
const BaselineCompiler = lazy(() => import('./pages/BaselineCompiler'));
const ClassificationCascade = lazy(() => import('./pages/ClassificationCascade'));
const AgentLoop = lazy(() => import('./pages/AgentLoop'));

interface NavGroup {
  label: string;
  items: { to: string; label: string }[];
}

function NavDropdown({ group }: { group: NavGroup }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const isGroupActive = group.items.some(i => location.pathname === i.to);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)}
        className={`px-3 py-2 rounded text-sm font-medium transition flex items-center gap-1 ${isGroupActive ? 'bg-white/15 text-white' : 'text-[#6A6E73] hover:text-white hover:bg-white/10'}`}>
        {group.label}
        <span className="text-[10px]">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 bg-[#212121] border border-[#333] rounded-lg shadow-xl py-1 min-w-[160px] z-50">
          {group.items.map(({ to, label }) => (
            <NavLink key={to} to={to} end={to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `block px-4 py-2 text-sm transition ${isActive ? 'text-white bg-white/10' : 'text-[#a0a0a0] hover:text-white hover:bg-white/5'}`
              }>
              {label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const navGroups: NavGroup[] = [
    { label: 'Intelligence', items: [
      { to: '/', label: 'Evidence' },
      { to: '/baselines', label: 'Baselines' },
      { to: '/classification', label: 'Classification' },
      { to: '/agent-loop', label: 'Agent Loop' },
    ]},
  ];

  return (
    <div className="min-h-screen bg-[#151515]">
      <nav className="bg-[#1a1a1a] border-b border-[#333] px-6 py-2 flex items-center gap-4">
        <span className="text-lg font-bold text-white mr-4">DeepField<span className="text-[#0071C5]"> Multimodal</span></span>
        {navGroups.map(g => <NavDropdown key={g.label} group={g} />)}
      </nav>
      <main className="max-w-7xl mx-auto px-6 py-6">
        <Suspense fallback={<div className="text-[#6A6E73]">Loading...</div>}>
          <Routes>
            <Route path="/" element={<MultimodalEvidence />} />
            <Route path="/baselines" element={<BaselineCompiler />} />
            <Route path="/classification" element={<ClassificationCascade />} />
            <Route path="/agent-loop" element={<AgentLoop />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}
