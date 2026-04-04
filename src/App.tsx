import { motion } from 'motion/react';
import { Download, Github, Terminal, Smartphone, Monitor, Info } from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans p-8">
      <div className="max-w-4xl mx-auto space-y-12">
        {/* Header */}
        <header className="text-center space-y-4">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-32 h-32 bg-blue-600 rounded-3xl mx-auto flex items-center justify-center shadow-2xl shadow-blue-500/20"
          >
            <Monitor className="w-16 h-16 text-white" />
          </motion.div>
          <h1 className="text-5xl font-bold tracking-tighter">
            Stream<span className="text-blue-500">Continuum</span>
          </h1>
          <p className="text-zinc-400 text-xl">
            Další generace Kodi doplňku pro Webshare a Trakt.tv
          </p>
        </header>

        {/* Main Info */}
        <div className="grid md:grid-cols-2 gap-8">
          <section className="bg-zinc-900/50 border border-white/5 p-8 rounded-3xl space-y-4">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Terminal className="w-6 h-6 text-blue-500" />
              Stav projektu
            </h2>
            <p className="text-zinc-400 leading-relaxed">
              Projekt je nyní připraven ve formátu **Kodi Addon (Python)**. 
              Všechny soubory byly vygenerovány podle standardu Kodi 19/20 (Matrix/Nexus).
            </p>
            <ul className="space-y-2 text-sm text-zinc-300">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                Plná integrace Trakt.tv Device Auth
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                Opravené přihlašování na Webshare (SHA1 hash)
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                Opravené nastavení a lokalizace do češtiny
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                Vizuální identita (ikona a fanart) integrována
              </li>
            </ul>
          </section>

          <section className="bg-zinc-900/50 border border-white/5 p-8 rounded-3xl space-y-6">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Download className="w-6 h-6 text-emerald-500" />
              Instalace
            </h2>
            <div className="space-y-4">
              <div className="bg-black/40 p-4 rounded-xl border border-white/5">
                <p className="text-xs text-zinc-500 uppercase font-bold mb-2">GitHub Repozitář</p>
                <a 
                  href="https://github.com/LawkCornieur/StreamContinuum" 
                  target="_blank"
                  className="text-blue-400 hover:underline flex items-center gap-2"
                >
                  <Github className="w-4 h-4" />
                  LawkCornieur/StreamContinuum
                </a>
              </div>
              <p className="text-sm text-zinc-400">
                Pro instalaci do Kodi stáhněte složku <code className="text-blue-400">plugin.video.streamcontinuum</code> jako ZIP a nainstalujte skrze menu doplňků.
              </p>
            </div>
          </section>
        </div>

        {/* Remote Control Preview */}
        <section className="bg-blue-600/10 border border-blue-500/20 p-8 rounded-3xl text-center space-y-4">
          <Smartphone className="w-12 h-12 text-blue-500 mx-auto" />
          <h3 className="text-2xl font-bold">Optimalizováno pro ovladače</h3>
          <p className="text-zinc-400 max-w-2xl mx-auto">
            Nastavení doplňku využívá nativní Kodi dialogy, které jsou plně ovladatelné dálkovým ovladačem. 
            Trakt.tv aktivace probíhá skrze jednoduchý 8-místný kód bez nutnosti psát heslo na TV.
          </p>
        </section>

        <footer className="text-center text-zinc-600 text-sm pt-8">
          Vytvořeno pro komunitu Kodi & StreamContinuum
        </footer>
      </div>
    </div>
  );
}
