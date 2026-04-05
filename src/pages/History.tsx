import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { History as HistoryIcon, Trash2, Play, ExternalLink, ChevronRight, Search } from 'lucide-react';
import { localDB } from '../lib/db';
import { traktService } from '../lib/trakt';
import { WatchedItem } from '../types';
import { format } from 'date-fns';
import { cs } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

export default function HistoryPage() {
  const [history, setHistory] = useState<WatchedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadHistory = async () => {
    const data = await localDB.getHistory();
    setHistory(data);
    setLoading(false);
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const removeItem = async (id: string) => {
    await localDB.removeFromHistory(id);
    toast.success('Položka odstraněna z historie');
    loadHistory();
  };

  const clearAll = async () => {
    if (window.confirm('Opravdu chcete smazat celou historii?')) {
      await localDB.clearHistory();
      toast.success('Historie vymazána');
      loadHistory();
    }
  };

  const handleNextEpisode = async (item: WatchedItem) => {
    if (!item.season || !item.episode) return;
    
    setLoading(true);
    const next = await traktService.getNextEpisode(item.id, item.season, item.episode);
    setLoading(false);

    if (next) {
      const nextQuery = `${item.title} S${next.season}E${next.number}`;
      navigate('/search', { state: { query: nextQuery, autoSearch: true } });
    } else {
      toast.error('Další díl nebyl nalezen');
    }
  };

  const handleSearchWebshare = (item: WatchedItem) => {
    const query = item.season 
      ? `${item.title} S${item.season}E${item.episode}`
      : item.title;
    navigate('/search', { state: { query, autoSearch: true, webshare: true } });
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 max-w-5xl mx-auto space-y-8"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-bold tracking-tight flex items-center gap-3">
          <HistoryIcon className="w-10 h-10 text-blue-500" />
          Historie sledování
        </h1>
        {history.length > 0 && (
          <button
            onClick={clearAll}
            className="text-red-500 hover:text-red-400 text-sm font-medium flex items-center gap-2 px-4 py-2 rounded-xl hover:bg-red-500/10 transition-all"
          >
            <Trash2 className="w-4 h-4" />
            Vymazat vše
          </button>
        )}
      </div>

      <div className="space-y-4">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 bg-zinc-900/50 animate-pulse rounded-2xl" />
          ))
        ) : history.length === 0 ? (
          <div className="text-center py-32 bg-zinc-900/30 rounded-3xl border border-dashed border-white/10">
            <HistoryIcon className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
            <p className="text-zinc-500 text-lg">Zatím jste nic nesledovali.</p>
          </div>
        ) : (
          history.map((item) => (
            <motion.div
              key={item.id}
              layout
              className="flex flex-col md:flex-row md:items-center gap-6 p-4 bg-zinc-900/50 rounded-2xl border border-white/5 hover:border-blue-500/30 transition-all group"
            >
              <div className="flex items-center gap-6 flex-grow">
                <div className="w-16 h-24 rounded-lg overflow-hidden bg-zinc-800 flex-shrink-0">
                  <img src={item.poster} alt={item.title} className="w-full h-full object-cover" />
                </div>
                
                <div className="flex-grow min-w-0">
                  <h3 className="font-bold text-lg truncate">{item.title}</h3>
                  <p className="text-zinc-500 text-sm">
                    {item.season && `S${item.season}E${item.episode} • `}
                    Sledováno {format(item.lastWatched, 'd. MMMM yyyy, HH:mm', { locale: cs })}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 md:opacity-0 group-hover:opacity-100 transition-opacity">
                {item.season && (
                  <button
                    onClick={() => handleNextEpisode(item)}
                    className="flex items-center gap-2 px-4 py-2 bg-zinc-800 text-zinc-300 rounded-xl hover:bg-zinc-700 transition-all text-sm font-medium"
                  >
                    <ChevronRight className="w-4 h-4" />
                    Další díl
                  </button>
                )}
                <button
                  onClick={() => handleSearchWebshare(item)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600/20 text-blue-400 rounded-xl hover:bg-blue-600/30 transition-all text-sm font-medium"
                >
                  <Search className="w-4 h-4" />
                  Webshare
                </button>
                <button
                  onClick={() => removeItem(item.id)}
                  className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-all"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  );
}
