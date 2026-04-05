import { useState, useEffect, FormEvent } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Search as SearchIcon, Loader2, Play, Plus, Info, ChevronRight, LayoutGrid, List } from 'lucide-react';
import { traktService } from '../lib/trakt';
import { webshareService } from '../lib/webshare';
import { localDB } from '../lib/db';
import { useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';

export default function SearchPage() {
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [type, setType] = useState<'movie' | 'show'>('movie');
  const [selectedMedia, setSelectedMedia] = useState<any>(null);
  const [seasons, setSeasons] = useState<any[]>([]);
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [webshareResults, setWebshareResults] = useState<any[]>([]);
  const [searchingWebshare, setSearchingWebshare] = useState(false);
  const [separator, setSeparator] = useState(' ');

  const handleSearch = async (e?: FormEvent, forcedQuery?: string) => {
    if (e) e.preventDefault();
    const searchQuery = forcedQuery || query;
    if (!searchQuery.trim()) return [];

    setLoading(true);
    const data = await traktService.search(searchQuery, type);
    setResults(data);
    setLoading(false);
    return data;
  };

  const handleWebshareSearch = async (media: any, episode?: any) => {
    let searchQuery = '';
    
    if (episode) {
      searchQuery = `${media.title} S${episode.season.toString().padStart(2, '0')}E${episode.number.toString().padStart(2, '0')}`;
    } else if (media.title && media.year) {
      // If it's a movie/show object with title and year
      searchQuery = `${media.title} ${media.year}`;
    } else if (media.title) {
      // If it's a raw title (e.g. from history auto-search)
      searchQuery = media.title;
    }
    
    // Apply separator if not space
    if (separator !== ' ') {
      searchQuery = searchQuery.replace(/\s+/g, separator);
    }
    
    setSearchingWebshare(true);
    setWebshareResults([]);
    toast.loading(`Hledám "${searchQuery}" na Webshare...`, { id: 'webshare-search' });
    
    try {
      // We'll use a mock or real search if token is available
      // For now, let's assume we search without token or with a dummy one
      const data = await webshareService.search(searchQuery);
      if (data && data.status === 'OK' && data.files) {
        setWebshareResults(data.files);
        toast.success(`Nalezeno ${data.files.length} souborů`, { id: 'webshare-search' });
      } else {
        toast.error('Na Webshare nebylo nic nalezeno', { id: 'webshare-search' });
      }
    } catch (error) {
      toast.error('Chyba při hledání na Webshare', { id: 'webshare-search' });
    } finally {
      setSearchingWebshare(false);
    }
  };

  useEffect(() => {
    const state = location.state as { query?: string; autoSearch?: boolean; type?: 'movie' | 'show'; webshare?: boolean };
    if (state?.query) {
      setQuery(state.query);
      if (state.type) setType(state.type);
      if (state.autoSearch) {
        handleSearch(undefined, state.query).then(async (data) => {
          if (state.webshare && data && data.length > 0) {
            const firstResult = data[0];
            await handleMediaClick(firstResult);
            // Use the original query from state for the webshare search
            handleWebshareSearch({ title: state.query });
          }
        });
      }
    }
  }, [location.state]);

  const handleMediaClick = async (item: any) => {
    const media = item.movie || item.show;
    setSelectedMedia(item);
    setSelectedSeason(null);
    setEpisodes([]);
    
    if (item.type === 'show') {
      setLoadingDetails(true);
      const seasonsData = await traktService.getShowSeasons(media.ids.trakt);
      setSeasons(seasonsData);
      setLoadingDetails(false);
    }
  };

  const handleSeasonClick = async (seasonNumber: number) => {
    if (!selectedMedia) return;
    const media = selectedMedia.show;
    setSelectedSeason(seasonNumber);
    setLoadingDetails(true);
    const episodesData = await traktService.getSeasonEpisodes(media.ids.trakt, seasonNumber);
    setEpisodes(episodesData);
    setLoadingDetails(false);
  };

  const addToHistory = async (item: any, episode?: any) => {
    const media = item.movie || item.show;
    const id = episode ? `${media.ids.trakt}_s${episode.season}_e${episode.number}` : media.ids.trakt.toString();
    
    await localDB.addToHistory({
      id,
      type: item.type,
      title: media.title,
      lastWatched: Date.now(),
      poster: `https://picsum.photos/seed/${media.ids.trakt}/400/600`,
      season: episode?.season,
      episode: episode?.number
    });
    toast.success(`${media.title}${episode ? ` S${episode.season}E${episode.number}` : ''} přidán do historie`);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 max-w-7xl mx-auto space-y-8 flex flex-col lg:flex-row gap-8"
    >
      <div className="flex-grow space-y-8">
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

        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
          {results.map((item) => {
            const media = item.movie || item.show;
            const isSelected = selectedMedia?.ids?.trakt === media.ids.trakt;
            return (
              <motion.div
                key={media.ids.trakt}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                onClick={() => handleMediaClick(item)}
                className={`space-y-3 group cursor-pointer p-2 rounded-3xl transition-all ${
                  isSelected ? 'bg-blue-600/10 ring-2 ring-blue-500' : 'hover:bg-zinc-900/50'
                }`}
              >
                <div className="aspect-[2/3] bg-zinc-900 rounded-2xl overflow-hidden relative border border-white/5 group-hover:border-blue-500/50 transition-all">
                  <img
                    src={`https://picsum.photos/seed/${media.ids.trakt}/400/600`}
                    alt={media.title}
                    className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
                  />
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-3">
                    <button 
                      onClick={(e) => { e.stopPropagation(); addToHistory(item); }}
                      className="w-12 h-12 bg-white text-black rounded-full flex items-center justify-center hover:scale-110 transition-transform"
                    >
                      <Plus className="w-6 h-6" />
                    </button>
                  </div>
                </div>
                <div className="px-2">
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
      </div>

      {/* Details Sidebar */}
      <AnimatePresence>
        {selectedMedia && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="w-full lg:w-96 bg-zinc-900/50 border border-white/5 rounded-3xl p-6 h-fit sticky top-6 space-y-6"
          >
            <div className="aspect-[2/3] rounded-2xl overflow-hidden bg-zinc-800">
              <img
                src={`https://picsum.photos/seed/${(selectedMedia.movie || selectedMedia.show).ids.trakt}/400/600`}
                alt="Selected Poster"
                className="w-full h-full object-cover"
              />
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl font-bold">{(selectedMedia.movie || selectedMedia.show).title}</h2>
              <p className="text-zinc-400 text-sm leading-relaxed">
                {(selectedMedia.movie || selectedMedia.show).overview || 'Žádný popis k dispozici.'}
              </p>
            </div>

            {selectedMedia.type === 'show' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold flex items-center gap-2">
                    <List className="w-4 h-4 text-blue-500" />
                    Série
                  </h3>
                  <div className="flex gap-1 bg-black/20 p-1 rounded-lg">
                    {[' ', '.', '_', '-'].map(s => (
                      <button
                        key={s}
                        onClick={() => setSeparator(s)}
                        className={`w-8 h-8 rounded flex items-center justify-center text-xs font-mono transition-all ${
                          separator === s ? 'bg-blue-600 text-white' : 'text-zinc-500 hover:text-zinc-300'
                        }`}
                      >
                        {s === ' ' ? '␣' : s}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {seasons.map((s) => (
                    <button
                      key={s.number}
                      onClick={() => handleSeasonClick(s.number)}
                      className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                        selectedSeason === s.number ? 'bg-blue-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                      }`}
                    >
                      S{s.number}
                    </button>
                  ))}
                </div>

                {selectedSeason !== null && (
                  <div className="space-y-2 max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                    <h3 className="font-bold text-sm text-zinc-500 uppercase tracking-wider">Díly série {selectedSeason}</h3>
                    {loadingDetails ? (
                      <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
                    ) : (
                      episodes.map((ep) => (
                        <div
                          key={ep.number}
                          className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-xl hover:bg-zinc-800 transition-all group"
                        >
                          <div className="min-w-0">
                            <p className="font-medium text-sm truncate">{ep.number}. {ep.title}</p>
                            <p className="text-[10px] text-zinc-500">Premiéra: {ep.first_aired ? new Date(ep.first_aired).toLocaleDateString('cs-CZ') : 'Neznámo'}</p>
                          </div>
                          <div className="flex gap-1">
                            <button 
                              onClick={() => addToHistory(selectedMedia, ep)}
                              className="p-2 text-zinc-500 hover:text-white transition-colors"
                              title="Přidat do historie"
                            >
                              <Plus className="w-4 h-4" />
                            </button>
                            <button 
                              onClick={() => handleWebshareSearch(selectedMedia.show, ep)}
                              className="p-2 text-zinc-500 hover:text-blue-500 transition-colors"
                              title="Hledat na Webshare"
                            >
                              <SearchIcon className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}

            {selectedMedia.type === 'movie' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500 uppercase font-bold tracking-wider">Oddělovač</span>
                  <div className="flex gap-1 bg-black/20 p-1 rounded-lg">
                    {[' ', '.', '_', '-'].map(s => (
                      <button
                        key={s}
                        onClick={() => setSeparator(s)}
                        className={`w-8 h-8 rounded flex items-center justify-center text-xs font-mono transition-all ${
                          separator === s ? 'bg-blue-600 text-white' : 'text-zinc-500 hover:text-zinc-300'
                        }`}
                      >
                        {s === ' ' ? '␣' : s}
                      </button>
                    ))}
                  </div>
                </div>
                <button 
                  onClick={() => handleWebshareSearch(selectedMedia.movie)}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all"
                >
                  <SearchIcon className="w-5 h-5" />
                  Hledat na Webshare
                </button>
              </div>
            )}

            {/* Webshare Results */}
            <AnimatePresence>
              {webshareResults.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-4 pt-6 border-t border-white/5"
                >
                  <h3 className="font-bold flex items-center gap-2 text-blue-400">
                    <LayoutGrid className="w-4 h-4" />
                    Výsledky Webshare
                  </h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
                    {webshareResults.map((file: any, i: number) => (
                      <div key={i} className="p-3 bg-zinc-800/30 rounded-xl border border-white/5 hover:border-blue-500/30 transition-all group">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-xs font-medium truncate group-hover:text-blue-400 transition-colors">{file.name}</p>
                            <p className="text-[10px] text-zinc-500">Velikost: {(file.size / (1024 * 1024 * 1024)).toFixed(2)} GB</p>
                          </div>
                          <button className="p-1.5 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600 hover:text-white transition-all">
                            <Play className="w-3 h-3 fill-current" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
