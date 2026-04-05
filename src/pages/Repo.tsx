import { motion } from 'motion/react';
import { Download, BookOpen, ListOrdered, History, Settings2, PlusCircle, Link as LinkIcon, Key, ChevronRight } from 'lucide-react';
import repoData from '../repo_data.json';

export default function RepoPage() {
  const changelogLines = repoData.changelog.split('\n').filter(l => l.trim());
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-slate-950 text-slate-100"
    >
      {/* Hero Section */}
      <div className="relative overflow-hidden py-24 px-6">
        <div className="absolute inset-0 bg-[url('fanart.jpg')] bg-cover bg-center opacity-20 grayscale"></div>
        <div className="absolute inset-0 bg-gradient-to-b from-slate-950/50 via-slate-950 to-slate-950"></div>
        
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
              className="text-xl text-slate-400 max-w-2xl mx-auto"
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
            <a href="#install" className="bg-slate-900 hover:bg-slate-800 text-white px-8 py-4 rounded-2xl font-bold transition-all border border-white/5 flex items-center gap-3">
              <BookOpen className="w-5 h-5" />
              Návod k instalaci
            </a>
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
                { step: 1, title: 'Přidat zdroj', desc: 'V Kodi jděte do Správce souborů -> Přidat zdroj a zadejte adresu:', code: 'https://lawkcornieur.github.io/StreamContinuum/' },
                { step: 2, title: 'Instalovat ze ZIP', desc: 'Jděte do Doplňky -> Instalovat ze souboru zip a vyberte přidaný zdroj.' },
                { step: 3, title: 'Instalovat doplněk', desc: 'Jděte do Instalovat z repozitáře -> StreamContinuum Repo -> Doplňky videí -> StreamContinuum.' }
              ].map((item) => (
                <div key={item.step} className="flex gap-6 p-6 bg-slate-900/50 rounded-3xl border border-white/5 hover:border-blue-500/30 transition-all group">
                  <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-xl flex-shrink-0 shadow-lg shadow-blue-900/20 group-hover:scale-110 transition-transform">
                    {item.step}
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-xl font-bold">{item.title}</h3>
                    <p className="text-slate-400 leading-relaxed">{item.desc}</p>
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
            
            <div className="bg-slate-900/50 rounded-3xl border border-white/5 p-8 space-y-8 max-h-[600px] overflow-y-auto custom-scrollbar">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-blue-400">Verze {repoData.latestPluginVersion}</h3>
                  <span className="text-sm text-slate-500">{new Date(repoData.updatedAt).toLocaleDateString('cs-CZ')}</span>
                </div>
                <ul className="space-y-3">
                  {changelogLines.map((line, i) => (
                    <li key={i} className="flex gap-3 text-slate-400">
                      <ChevronRight className="w-4 h-4 text-blue-500 flex-shrink-0 mt-1" />
                      {line.replace(/^\*\*(.*?)\*\*/, '$1')}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        </div>

        {/* Trakt Config */}
        <section className="space-y-12">
          <div className="text-center space-y-4">
            <div className="inline-flex p-3 bg-amber-500/10 rounded-2xl mb-4">
              <Settings2 className="w-8 h-8 text-amber-400" />
            </div>
            <h2 className="text-4xl font-bold">Konfigurace Trakt.tv</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">Pro plnou funkčnost doplňku je nutné propojit váš Trakt.tv účet.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: PlusCircle, title: 'Vytvořit aplikaci', desc: 'Na Trakt.tv v sekci API Apps vytvořte novou aplikaci.' },
              { icon: LinkIcon, title: 'Redirect URI', desc: 'Jako Redirect URI použijte:', code: 'urn:ietf:wg:oauth:2.0:oob' },
              { icon: Key, title: 'Client ID & Secret', desc: 'Zkopírujte údaje do nastavení doplňku a aktivujte zařízení.' }
            ].map((item, i) => (
              <div key={i} className="p-8 bg-slate-900/50 rounded-3xl border border-white/5 space-y-4 hover:bg-slate-900 transition-all">
                <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center">
                  <item.icon className="w-6 h-6 text-blue-400" />
                </div>
                <h3 className="text-xl font-bold">{item.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{item.desc}</p>
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
        <p className="text-slate-500 text-sm">&copy; 2026 StreamContinuum Repository. Všechna práva vyhrazena.</p>
        <p className="text-slate-700 text-xs">Aktualizováno: 5. 4. 2026</p>
      </footer>
    </motion.div>
  );
}
