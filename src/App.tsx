import { HashRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { LayoutDashboard, Search, History, Settings, Monitor } from 'lucide-react';
import { Toaster } from 'react-hot-toast';
import { useEffect } from 'react';
import { setTraktAuth } from './lib/trakt';

import Dashboard from './pages/Dashboard';
import SearchPage from './pages/Search';
import HistoryPage from './pages/History';
import SettingsPage from './pages/Settings';
import RepoPage from './pages/Repo';

function Navigation() {
  const location = useLocation();
  
  const links = [
    { to: '/', icon: LayoutDashboard, label: 'Repozitář' },
    { to: '/dashboard', icon: Monitor, label: 'Dashboard' },
    { to: '/search', icon: Search, label: 'Hledat' },
    { to: '/history', icon: History, label: 'Historie' },
    { to: '/settings', icon: Settings, label: 'Nastavení' },
  ];

  return (
    <nav className="fixed left-0 top-0 bottom-0 w-20 md:w-64 bg-zinc-950 border-r border-white/5 flex flex-col items-center md:items-stretch p-4 z-50">
      <div className="flex items-center gap-3 px-2 mb-12">
        <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Monitor className="w-6 h-6 text-white" />
        </div>
        <span className="hidden md:block font-bold text-xl tracking-tighter">
          Stream<span className="text-blue-500">Continuum</span>
        </span>
      </div>

      <div className="flex-grow space-y-2">
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = location.pathname === link.to;
          return (
            <Link
              key={link.to}
              to={link.to}
              className={`flex items-center gap-4 p-4 rounded-2xl transition-all group ${
                isActive 
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' 
                  : 'text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300'
              }`}
            >
              <Icon className={`w-6 h-6 ${isActive ? 'scale-110' : 'group-hover:scale-110'} transition-transform`} />
              <span className="hidden md:block font-medium">{link.label}</span>
            </Link>
          );
        })}
      </div>

      <div className="mt-auto p-4 bg-zinc-900/50 rounded-2xl border border-white/5 hidden md:block">
        <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider mb-1">Status</p>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span className="text-sm font-semibold">Online</span>
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  useEffect(() => {
    const traktId = localStorage.getItem('trakt_client_id');
    const traktToken = localStorage.getItem('trakt_access_token');
    if (traktId) {
      setTraktAuth(traktId, traktToken || undefined);
    }
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex">
        <Navigation />
        
        <main className="flex-grow ml-20 md:ml-64 min-h-screen relative">
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<RepoPage />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </AnimatePresence>
        </main>

        <Toaster 
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#18181b',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.05)',
              borderRadius: '1rem',
            }
          }}
        />
      </div>
    </Router>
  );
}
