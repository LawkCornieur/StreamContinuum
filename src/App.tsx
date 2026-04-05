import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Toaster } from 'react-hot-toast';
import RepoPage from './pages/Repo';

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-zinc-950 text-zinc-100">
        <main className="min-h-screen relative">
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<RepoPage />} />
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
