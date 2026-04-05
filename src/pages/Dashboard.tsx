import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Play, Clock, ChevronRight, Star } from 'lucide-react';
import { localDB } from '../lib/db';
import { traktService } from '../lib/trakt';
import { WatchedItem } from '../types';
import { formatDistanceToNow } from 'date-fns';
import { cs } from 'date-fns/locale';

export default function Dashboard() {
  const [history, setHistory] = useState<WatchedItem[]>([]);
  const [trending, setTrending] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [localHistory, trendingMovies] = await Promise.all([
          localDB.getHistory(),
          traktService.getTrending('movies').catch(() => [])
        ]);
        setHistory(localHistory.slice(0, 5));
        setTrending(trendingMovies);
      } catch (err) {
        console.error('Chyba při načítání dat dashboardu:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="p-6 max-w-7xl mx-auto space-y-12"
    >
      {/* Hero Section / Banner */}
      <section className="relative h-[400px] rounded-3xl overflow-hidden group">
        <img
          src="fanart.jpg" 
          alt="StreamContinuum Banner"
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
          onError={(e) => {
            (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1626814026160-2237a95fc5a0?q=80&w=2070&auto=format&fit=crop';
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent" />
        <div className="absolute bottom-8 left-8 right-8 space-y-4">
          <h1 className="text-5xl font-bold tracking-tighter md:text-7xl">
            Stream<span className="text-blue-500">Continuum</span>
          </h1>
          <p className="text-zinc-400 max-w-xl text-lg">
            Váš nekonečný proud zábavy. Plynule navazujte na své oblíbené seriály a objevujte nové světy.
          </p>
          <div className="flex gap-4">
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-full font-semibold flex items-center gap-2 transition-all hover:scale-105">
              <Play className="w-5 h-5 fill-current" />
              Pokračovat ve sledování
            </button>
          </div>
        </div>
      </section>

      {/* Continue Watching / History */}
      {history.length > 0 && (
        <section className="space-y-6">
          <div className="flex justify-between items-end">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Clock className="w-6 h-6 text-blue-500" />
              Nedávno sledované
            </h2>
            <button className="text-zinc-500 hover:text-zinc-300 text-sm font-medium flex items-center gap-1">
              Zobrazit vše <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
            {history.map((item) => (
              <motion.div
                key={item.id}
                whileHover={{ y: -8 }}
                className="bg-zinc-900/50 rounded-2xl p-4 border border-white/5 hover:border-blue-500/30 transition-all cursor-pointer group"
              >
                <div className="aspect-[2/3] rounded-xl overflow-hidden bg-zinc-800 mb-4 relative">
                  {item.poster ? (
                    <img src={item.poster} alt={item.title} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-zinc-600">
                      <Play className="w-12 h-12" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center scale-75 group-hover:scale-100 transition-transform">
                      <Play className="w-6 h-6 fill-current" />
                    </div>
                  </div>
                </div>
                <h3 className="font-semibold truncate">{item.title}</h3>
                <p className="text-xs text-zinc-500 mt-1">
                  {item.season && `S${item.season}E${item.episode} • `}
                  {formatDistanceToNow(item.lastWatched, { addSuffix: true, locale: cs })}
                </p>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* Trending Section */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Star className="w-6 h-6 text-yellow-500" />
          Populární nyní
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="aspect-[2/3] bg-zinc-900 animate-pulse rounded-2xl" />
            ))
          ) : (
            trending.map((item: any) => (
              <div key={item.movie?.ids.trakt || item.show?.ids.trakt} className="space-y-2 group cursor-pointer">
                <div className="aspect-[2/3] bg-zinc-900 rounded-2xl overflow-hidden border border-white/5 group-hover:border-blue-500/50 transition-all">
                  <img 
                    src={`https://picsum.photos/seed/${item.movie?.ids.trakt || item.show?.ids.trakt}/400/600`}
                    alt={item.movie?.title || item.show?.title}
                    className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
                  />
                </div>
                <p className="font-medium text-sm truncate">{item.movie?.title || item.show?.title}</p>
                <p className="text-xs text-zinc-500">{item.movie?.year || item.show?.year}</p>
              </div>
            ))
          )}
        </div>
      </section>
    </motion.div>
  );
}
