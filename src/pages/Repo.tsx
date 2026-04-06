import { motion } from 'motion/react';
import { Download, BookOpen, ListOrdered, History, Settings2, PlusCircle, Link as LinkIcon, Key, ChevronRight, AlertTriangle, Info, Play, Settings as SettingsIcon, Package, Trash2, RefreshCw, Layers } from 'lucide-react';
import repoData from '../repo_data.json';

export default function RepoPage() {
  const changelogLines = repoData.changelog.split('\n').filter(l => l.trim());
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors duration-300"
    >
      {/* Hero Section */}
      <div className="relative overflow-hidden py-24 px-6">
        <div 
          className="absolute inset-0 bg-cover bg-center opacity-10 dark:opacity-20 grayscale"
          style={{ backgroundImage: "url('./fanart-v0.0.1.jpg')" }}
        ></div>
        <div className="absolute inset-0 bg-gradient-to-b from-white/50 via-white to-white dark:from-zinc-950/50 dark:via-zinc-950 dark:to-zinc-950"></div>
        
        <div className="relative max-w-5xl mx-auto text-center space-y-8">
          <motion.img 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            src="./icon-v0.0.1.png" 
            alt="StreamContinuum Logo" 
            className="w-32 h-32 mx-auto rounded-3xl shadow-2xl border-4 border-blue-500/20"
          />
          <div className="space-y-4">
            <motion.h1 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-6xl font-bold tracking-tighter bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent"
            >
              StreamContinuum
            </motion.h1>
            <motion.p 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-xl text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto"
            >
              Jednoduchý stream doplněk pro Kodi s integrací Trakt.tv a Webshare.cz.
            </motion.p>
          </div>
          
          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="flex flex-wrap justify-center gap-4"
          >
            <a href={`repository.streamcontinuum-${repoData.latestRepoVersion}.zip`} className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-4 rounded-2xl font-bold transition-all shadow-xl shadow-blue-900/20 flex items-center gap-3 group">
              <Download className="w-5 h-5 group-hover:bounce" />
              Stáhnout Repozitář (v{repoData.latestRepoVersion})
            </a>
            <a href="#install" className="bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-900 dark:text-white px-8 py-4 rounded-2xl font-bold transition-all border border-black/5 dark:border-white/5 flex items-center gap-3">
              <BookOpen className="w-5 h-5" />
              Návod k instalaci
            </a>
          </motion.div>

          {/* Development Warning */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="max-w-2xl mx-auto p-4 bg-amber-100 dark:bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-center gap-4 text-left"
          >
            <AlertTriangle className="w-8 h-8 text-amber-600 dark:text-amber-500 flex-shrink-0" />
            <div>
              <p className="text-amber-700 dark:text-amber-500 font-bold text-sm uppercase tracking-wider">Upozornění</p>
              <p className="text-amber-900/70 dark:text-zinc-400 text-sm">Doplněk je v aktivním vývoji. Může obsahovat chyby nebo nedokončené funkce. Pravidelně aktualizujte repozitář pro nejnovější opravy.</p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Content Section */}
      <main className="max-w-6xl mx-auto px-6 py-20 space-y-32">
        <div className="grid lg:grid-cols-2 gap-12">
          {/* Installation Guide */}
          <section id="install" className="space-y-8">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-500/10 rounded-2xl">
                <ListOrdered className="w-8 h-8 text-blue-400" />
              </div>
              <h2 className="text-3xl font-bold">Instalace</h2>
            </div>
            
            <div className="space-y-6">
              {[
                { step: 1, title: 'Přidat zdroj repozitáře', desc: 'V Kodi jděte do Nastavení -> Správce souborů -> Přidat zdroj. Jako cestu zadejte:', code: 'https://lawkcornieur.github.io/StreamContinuum/' },
                { step: 2, title: 'Nainstalovat repozitář', desc: 'Jděte do Doplňky -> Instalovat ze souboru zip. Vyberte přidaný zdroj a nainstalujte soubor repository.streamcontinuum.zip.' },
                { step: 3, title: 'Nainstalovat doplněk', desc: 'Jděte do Instalovat z repozitáře -> StreamContinuum Repository -> Doplňky videí -> StreamContinuum a klikněte na Instalovat.' }
              ].map((item) => (
                <div key={item.step} className="flex gap-6 p-6 bg-zinc-50 dark:bg-zinc-900/50 rounded-3xl border border-black/5 dark:border-white/5 hover:border-blue-500/30 transition-all group shadow-sm">
                  <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-xl flex-shrink-0 shadow-lg shadow-blue-900/20 group-hover:scale-110 transition-transform">
                    {item.step}
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-xl font-bold">{item.title}</h3>
                    <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">{item.desc}</p>
                    {item.code && (
                      <code className="block bg-zinc-200 dark:bg-black/40 p-3 rounded-xl text-blue-700 dark:text-blue-300 text-sm font-mono break-all border border-black/5 dark:border-white/5">
                        {item.code}
                      </code>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Changelog */}
          <section className="space-y-8">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-indigo-500/10 rounded-2xl">
                <History className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
              </div>
              <h2 className="text-3xl font-bold">Seznam změn</h2>
            </div>
            
            <div className="bg-zinc-50 dark:bg-zinc-900/50 rounded-3xl border border-black/5 dark:border-white/5 p-8 space-y-8 max-h-[600px] overflow-y-auto custom-scrollbar shadow-sm">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-blue-600 dark:text-blue-400">Verze {repoData.latestPluginVersion}</h3>
                  <span className="text-sm text-zinc-500">{new Date(repoData.updatedAt).toLocaleDateString('cs-CZ')}</span>
                </div>
                <ul className="space-y-3">
                  {changelogLines.map((line, i) => {
                    const cleanLine = line.replace(/^[-*•]\s*/, '').replace(/^\*\*(.*?)\*\*/, '$1').trim();
                    if (!cleanLine) return null;
                    return (
                      <li key={i} className="flex gap-3 text-zinc-700 dark:text-zinc-400">
                        <ChevronRight className="w-4 h-4 text-blue-500 flex-shrink-0 mt-1" />
                        <span>{cleanLine}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </section>
        </div>

        {/* Configuration Section */}
        <section className="space-y-12">
          <div className="text-center space-y-4">
            <div className="inline-flex p-3 bg-amber-500/10 rounded-2xl mb-4">
              <Settings2 className="w-8 h-8 text-amber-600 dark:text-amber-400" />
            </div>
            <h2 className="text-4xl font-bold">Konfigurace</h2>
            <p className="text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">Pro plnou funkčnost doplňku je nutné nastavit Webshare a Trakt.tv.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="p-8 bg-zinc-50 dark:bg-zinc-900/50 rounded-3xl border border-black/5 dark:border-white/5 space-y-4 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-all shadow-sm">
              <div className="w-12 h-12 rounded-2xl bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center">
                <Key className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-xl font-bold">1. Webshare.cz</h3>
              <p className="text-zinc-600 dark:text-zinc-400 text-sm leading-relaxed">
                Po instalaci přejděte do nastavení doplňku. V sekci <strong>Webshare</strong> zadejte své uživatelské jméno a heslo.
              </p>
            </div>

            <div className="p-8 bg-zinc-50 dark:bg-zinc-900/50 rounded-3xl border border-black/5 dark:border-white/5 space-y-4 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-all shadow-sm">
              <div className="w-12 h-12 rounded-2xl bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center">
                <LinkIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-xl font-bold">2. Trakt.tv (API Nastavení)</h3>
              <p className="text-zinc-600 dark:text-zinc-400 text-sm leading-relaxed">
                Pro fungování Trakt.tv integrace si musí každý uživatel vytvořit vlastní API aplikaci na Trakt.tv.
              </p>
              <ul className="text-zinc-600 dark:text-zinc-400 text-sm leading-relaxed list-disc list-inside space-y-1">
                <li>Přihlaste se na Trakt.tv a přejděte do Settings -&gt; API Apps.</li>
                <li>Klikněte na New Application a vyplňte libovolný název.</li>
                <li>Do pole Redirect URI zadejte: <code className="bg-zinc-200 dark:bg-black/40 px-1 rounded">urn:ietf:wg:oauth:2.0:oob</code></li>
                <li>Uložte aplikaci a zkopírujte si Client ID a Client Secret do nastavení doplňku.</li>
                <li>Poté klikněte na Aktivovat zařízení a zadejte kód na trakt.tv/activate.</li>
              </ul>
              <a 
                href="https://trakt.tv/oauth/applications/new" 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-block text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-sm font-medium underline underline-offset-4 mt-2"
              >
                Otevřít Trakt API →
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-black/5 dark:border-white/5 py-16 text-center space-y-4">
        <p className="text-zinc-500 text-sm">&copy; 2026 StreamContinuum Repository. Všechna práva vyhrazena.</p>
        <p className="text-zinc-400 dark:text-zinc-700 text-xs">Aktualizováno: {new Date(repoData.updatedAt).toLocaleDateString('cs-CZ')}</p>
      </footer>
    </motion.div>
  );
}
