import { useState, FormEvent } from 'react';
import { motion } from 'motion/react';
import { Search as SearchIcon, Loader2, Play, Plus } from 'lucide-react';
import { traktService } from '../lib/trakt';
import { localDB } from '../lib/db';
import toast from 'react-hot-toast';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [type, setType] = useState<'movie' | 'show'>('movie');

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    const data = await traktService.search(query, type);
    setResults(data);
    setLoading(false);
  };

  const addToHistory = async (item: any) => {
    const media = item.movie || item.show;
    await localDB.addToHistory({
      id: media.ids.trakt.toString(),
      type: item.type,
      title: media.title,
      lastWatched: Date.now(),
      poster: `https://picsum.photos/seed/${media.ids.trakt}/400/600`
    });
    toast.success(`${media.title} přidán do historie`);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 max-w-7xl mx-auto space-y-8"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <h1 className="text-4xl font-bold tracking-tight">Hledat</h1>
        
        <div className="flex bg-zinc-900 p-1 rounded-xl border border-white/5">
          <button
            onClick={() => setType('movie')}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              type === 'movie' ? 'bg-blue-600 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            Filmy
          </button>
          <button
            onClick={() => setType('show')}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              type === 'show' ? 'bg-blue-600 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            Seriály
          </button>
        </div>
      </div>

      <form onSubmit={handleSearch} className="relative group">
        <SearchIcon className="absolute left-6 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-blue-500 transition-colors" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`Hledat ${type === 'movie' ? 'filmy' : 'seriály'}...`}
          className="w-full bg-zinc-900 border border-white/5 rounded-2xl py-6 pl-16 pr-6 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all text-xl"
        />
        {loading && (
          <Loader2 className="absolute right-6 top-1/2 -translate-y-1/2 animate-spin text-blue-500" />
        )}
      </form>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-8">
        {results.map((item) => {
          const media = item.movie || item.show;
          return (
            <motion.div
              key={media.ids.trakt}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-3 group"
            >
              <div className="aspect-[2/3] bg-zinc-900 rounded-2xl overflow-hidden relative border border-white/5 group-hover:border-blue-500/50 transition-all">
                <img
                  src={`https://picsum.photos/seed/${media.ids.trakt}/400/600`}
                  alt={media.title}
                  className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
                />
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-3">
                  <button 
                    onClick={() => addToHistory(item)}
                    className="w-12 h-12 bg-white text-black rounded-full flex items-center justify-center hover:scale-110 transition-transform"
                  >
                    <Plus className="w-6 h-6" />
                  </button>
                  <button className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center hover:scale-110 transition-transform">
                    <Play className="w-6 h-6 fill-current" />
                  </button>
                </div>
              </div>
              <div>
                <h3 className="font-semibold truncate">{media.title}</h3>
                <p className="text-xs text-zinc-500">{media.year}</p>
              </div>
            </motion.div>
          );
        })}
      </div>

      {!loading && query && results.length === 0 && (
        <div className="text-center py-20 space-y-4">
          <p className="text-zinc-500 text-lg">Nebyly nalezeny žádné výsledky pro "{query}"</p>
          <button 
            onClick={() => setQuery('')}
            className="text-blue-500 hover:underline"
          >
            Zkusit jiné hledání
          </button>
        </div>
      )}
    </motion.div>
  );
}
