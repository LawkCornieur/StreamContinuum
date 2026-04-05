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
      className="min-h-screen bg-zinc-950 text-zinc-100"
    >
      {/* Hero Section */}
      <div className="relative overflow-hidden py-24 px-6">
        <div className="absolute inset-0 bg-[url('fanart.jpg')] bg-cover bg-center opacity-20 grayscale"></div>
        <div className="absolute inset-0 bg-gradient-to-b from-zinc-950/50 via-zinc-950 to-zinc-950"></div>
        
        <div className="relative max-w-5xl mx-auto text-center space-y-8">
          <motion.img 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            src="icon.png" 
            alt="StreamContinuum Logo" 
            className="w-32 h-32 mx-auto rounded-3xl shadow-2xl border-4 border-blue-500/20"
          />
          <div className="space-y-4">
            <motion.h1 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-6xl font-bold tracking-tighter bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent"
            >
              StreamContinuum
            </motion.h1>
            <motion.p 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-xl text-zinc-400 max-w-2xl mx-auto"
            >
              Moderní doplněk pro Kodi s integrací Trakt.tv a Webshare.cz. 
              Vše, co potřebujete pro dokonalý filmový zážitek.
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
            <a href="#install" className="bg-zinc-900 hover:bg-zinc-800 text-white px-8 py-4 rounded-2xl font-bold transition-all border border-white/5 flex items-center gap-3">
              <BookOpen className="w-5 h-5" />
              Návod k instalaci
            </a>
          </motion.div>

          {/* Development Warning */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="max-w-2xl mx-auto p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-center gap-4 text-left"
          >
            <AlertTriangle className="w-8 h-8 text-amber-500 flex-shrink-0" />
            <div>
              <p className="text-amber-500 font-bold text-sm uppercase tracking-wider">Upozornění</p>
              <p className="text-zinc-400 text-sm">Doplněk je v aktivním vývoji. Může obsahovat chyby nebo nedokončené funkce. Pravidelně aktualizujte repozitář pro nejnovější opravy.</p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Kodi Style Info Section */}
      <section className="max-w-6xl mx-auto px-6 py-12">
        <div className="bg-zinc-900/80 backdrop-blur-xl rounded-[2.5rem] border border-white/5 overflow-hidden shadow-2xl">
          {/* Header */}
          <div className="p-12 space-y-12">
            <div className="flex flex-col md:flex-row gap-12 items-start">
              {/* Logo & Basic Info */}
              <div className="w-full md:w-1/3 space-y-6">
                <div className="aspect-square bg-zinc-950 rounded-[2rem] p-8 shadow-inner border border-white/5 relative group">
                  <img src="icon.png" alt="Logo" className="w-full h-full object-contain" />
                  <div className="absolute inset-0 bg-blue-600/10 opacity-0 group-hover:opacity-100 transition-opacity rounded-[2rem]"></div>
                </div>
                <div className="text-center md:text-left">
                  <h2 className="text-4xl font-bold tracking-tight">StreamContinuum</h2>
                  <p className="text-zinc-500 font-medium">{repoData.latestPluginVersion} od LawkCornieur</p>
                </div>
              </div>

              {/* Screenshots & Description */}
              <div className="flex-1 space-y-8">
                {/* Screenshots Grid */}
                <div className="grid grid-cols-3 gap-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="aspect-video bg-zinc-950 rounded-2xl border border-white/5 overflow-hidden relative group cursor-zoom-in">
                      <img 
                        src={`https://picsum.photos/seed/streamcontinuum-${i}/800/450`} 
                        alt={`Screenshot ${i}`} 
                        className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-all group-hover:scale-105" 
                      />
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                        <Play className="w-8 h-8 text-white fill-white" />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Description Box */}
                <div className="flex gap-8">
                  <div className="flex-1 bg-zinc-950/50 p-8 rounded-3xl border border-white/5 space-y-4">
                    <h3 className="text-xl font-bold text-blue-400">Jednoduchý stream doplněk s integrací Trakt.tv a Webshare.</h3>
                    <p className="text-zinc-400 leading-relaxed">
                      StreamContinuum umožňuje prohlížet a přehrávat obsah z Webshare.cz s plnou synchronizací Trakt.tv a lokální historií. 
                      Doplněk je navržen pro maximální rychlost a přehlednost v prostředí Kodi.
                    </p>
                    <p className="text-zinc-600 text-xs italic">
                      This addon does not host any content. It is a tool to access third-party services.
                    </p>
                  </div>

                  {/* Metadata */}
                  <div className="w-48 space-y-6 text-sm">
                    <div className="space-y-1">
                      <p className="text-blue-400 font-medium">Kategorie:</p>
                      <p className="text-zinc-300">Zdroje médií</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-blue-400 font-medium">Původ:</p>
                      <p className="text-zinc-300">Repozitář</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-blue-400 font-medium">Stav:</p>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                        <p className="text-zinc-300">Aktivní</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Kodi Style Buttons */}
            <div className="flex flex-wrap justify-center gap-4 pt-8 border-t border-white/5">
              {[
                { icon: Play, label: 'Otevřít' },
                { icon: SettingsIcon, label: 'Konfigurovat' },
                { icon: RefreshCw, label: 'Aktualizovat' },
                { icon: Info, label: 'Závislosti' },
                { icon: Package, label: 'Verze' },
                { icon: Trash2, label: 'Odinstalovat', color: 'text-red-400' }
              ].map((btn, i) => (
                <button key={i} className="flex flex-col items-center gap-2 px-6 py-4 rounded-2xl bg-zinc-950 hover:bg-zinc-800 border border-white/5 transition-all min-w-[120px] group">
                  <btn.icon className={`w-6 h-6 ${btn.color || 'text-zinc-400'} group-hover:scale-110 transition-transform`} />
                  <span className="text-xs font-bold uppercase tracking-widest text-zinc-500 group-hover:text-zinc-300">{btn.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

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
                { step: 1, title: 'Přidat zdroj', desc: 'V Kodi jděte do Správce souborů -> Přidat zdroj a zadejte adresu:', code: 'https://lawkcornieur.github.io/StreamContinuum/' },
                { step: 2, title: 'Instalovat ze ZIP', desc: 'Jděte do Doplňky -> Instalovat ze souboru zip a vyberte přidaný zdroj.' },
                { step: 3, title: 'Instalovat doplněk', desc: 'Jděte do Instalovat z repozitáře -> StreamContinuum Repo -> Doplňky videí -> StreamContinuum.' }
              ].map((item) => (
                <div key={item.step} className="flex gap-6 p-6 bg-zinc-900/50 rounded-3xl border border-white/5 hover:border-blue-500/30 transition-all group">
                  <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-xl flex-shrink-0 shadow-lg shadow-blue-900/20 group-hover:scale-110 transition-transform">
                    {item.step}
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-xl font-bold">{item.title}</h3>
                    <p className="text-zinc-400 leading-relaxed">{item.desc}</p>
                    {item.code && (
                      <code className="block bg-black/40 p-3 rounded-xl text-blue-300 text-sm font-mono break-all border border-white/5">
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
                <History className="w-8 h-8 text-indigo-400" />
              </div>
              <h2 className="text-3xl font-bold">Seznam změn</h2>
            </div>
            
            <div className="bg-zinc-900/50 rounded-3xl border border-white/5 p-8 space-y-8 max-h-[600px] overflow-y-auto custom-scrollbar">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-blue-400">Verze {repoData.latestPluginVersion}</h3>
                  <span className="text-sm text-zinc-500">{new Date(repoData.updatedAt).toLocaleDateString('cs-CZ')}</span>
                </div>
                <ul className="space-y-3">
                  {changelogLines.map((line, i) => (
                    <li key={i} className="flex gap-3 text-zinc-400">
                      <ChevronRight className="w-4 h-4 text-blue-500 flex-shrink-0 mt-1" />
                      {line.replace(/^\*\*(.*?)\*\*/, '$1')}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        </div>

        {/* Features Section */}
        <section className="space-y-12">
          <div className="text-center space-y-4">
            <div className="inline-flex p-3 bg-blue-500/10 rounded-2xl mb-4">
              <Layers className="w-8 h-8 text-blue-400" />
            </div>
            <h2 className="text-4xl font-bold">Klíčové vlastnosti</h2>
            <p className="text-zinc-400 max-w-2xl mx-auto">Všechny funkce, které očekáváte od moderního doplňku.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { title: 'Trakt.tv Synchronizace', desc: 'Sledujte svou historii, watchlist a hodnocení napříč všemi zařízeními.' },
              { title: 'Webshare.cz Integrace', desc: 'Přímý přístup k tisícům streamů ve vysoké kvalitě.' },
              { title: 'Chytrá Historie', desc: 'Rychlý přístup k naposledy sledovaným dílům s funkcí "Další epizoda".' },
              { title: 'Moderní UI', desc: 'Čisté a přehledné rozhraní optimalizované pro dálkové ovládání.' },
              { title: 'Rychlé Hledání', desc: 'Pokročilé vyhledávání s podporou různých oddělovačů a formátů.' },
              { title: 'Automatické Aktualizace', desc: 'Repozitář se stará o to, abyste měli vždy nejnovější verzi.' }
            ].map((feature, i) => (
              <div key={i} className="p-8 bg-zinc-900/50 rounded-3xl border border-white/5 hover:bg-zinc-900 transition-all">
                <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Trakt Config */}
        <section className="space-y-12">
          <div className="text-center space-y-4">
            <div className="inline-flex p-3 bg-amber-500/10 rounded-2xl mb-4">
              <Settings2 className="w-8 h-8 text-amber-400" />
            </div>
            <h2 className="text-4xl font-bold">Konfigurace Trakt.tv</h2>
            <p className="text-zinc-400 max-w-2xl mx-auto">Pro plnou funkčnost doplňku je nutné propojit váš Trakt.tv účet.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: PlusCircle, title: 'Vytvořit aplikaci', desc: 'Na Trakt.tv v sekci API Apps vytvořte novou aplikaci.' },
              { icon: LinkIcon, title: 'Redirect URI', desc: 'Jako Redirect URI použijte:', code: 'urn:ietf:wg:oauth:2.0:oob' },
              { icon: Key, title: 'Client ID & Secret', desc: 'Zkopírujte údaje do nastavení doplňku a aktivujte zařízení.' }
            ].map((item, i) => (
              <div key={i} className="p-8 bg-zinc-900/50 rounded-3xl border border-white/5 space-y-4 hover:bg-zinc-900 transition-all">
                <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center">
                  <item.icon className="w-6 h-6 text-blue-400" />
                </div>
                <h3 className="text-xl font-bold">{item.title}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">{item.desc}</p>
                {item.code && (
                  <code className="block bg-black/40 p-2 rounded-lg text-blue-300 text-xs font-mono break-all border border-white/5">
                    {item.code}
                  </code>
                )}
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-white/5 py-16 text-center space-y-4">
        <p className="text-zinc-500 text-sm">&copy; 2026 StreamContinuum Repository. Všechna práva vyhrazena.</p>
        <p className="text-zinc-700 text-xs">Aktualizováno: {new Date(repoData.updatedAt).toLocaleDateString('cs-CZ')}</p>
      </footer>
    </motion.div>
  );
}
