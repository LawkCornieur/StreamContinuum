import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Settings as SettingsIcon, Key, Database, Globe, Shield, LogOut, Smartphone, Cloud, Loader2, CheckCircle2, AlertCircle, ClipboardPaste } from 'lucide-react';
import toast from 'react-hot-toast';
import { traktService, setTraktAuth } from '../lib/trakt';
import { webshareService } from '../lib/webshare';

export default function SettingsPage() {
  // Trakt State
  const [traktId, setTraktId] = useState(localStorage.getItem('trakt_client_id') || '');
  const [traktSecret, setTraktSecret] = useState(localStorage.getItem('trakt_client_secret') || '');
  const [traktToken, setTraktToken] = useState(localStorage.getItem('trakt_access_token') || '');
  const [deviceCode, setDeviceCode] = useState<{ user_code: string, device_code: string, verification_url: string } | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  // Webshare State
  const [wsUsername, setWsUsername] = useState(localStorage.getItem('ws_username') || '');
  const [wsPassword, setWsPassword] = useState('');
  const [wsToken, setWsToken] = useState(localStorage.getItem('ws_token') || '');
  const [isWsLoading, setIsWsLoading] = useState(false);

  const saveTraktConfig = () => {
    localStorage.setItem('trakt_client_id', traktId);
    localStorage.setItem('trakt_client_secret', traktSecret);
    setTraktAuth(traktId, traktToken);
    toast.success('Konfigurace Trakt.tv uložena');
  };

  const startTraktActivation = async () => {
    if (!traktId) {
      toast.error('Nejdříve vyplňte Trakt Client ID');
      return;
    }
    const data = await traktService.generateDeviceCode(traktId);
    if (data) {
      setDeviceCode(data);
      setIsPolling(true);
      toast.success('Kód vygenerován. Aktivujte na trakt.tv/activate');
    }
  };

  useEffect(() => {
    let pollInterval: NodeJS.Timeout;
    if (isPolling && deviceCode && traktId && traktSecret) {
      pollInterval = setInterval(async () => {
        const result = await traktService.pollForDeviceToken(traktId, traktSecret, deviceCode.device_code);
        if (result.access_token) {
          localStorage.setItem('trakt_access_token', result.access_token);
          setTraktToken(result.access_token);
          setTraktAuth(traktId, result.access_token);
          setIsPolling(false);
          setDeviceCode(null);
          toast.success('Trakt.tv úspěšně propojen!');
        } else if (result.status === 'error') {
          setIsPolling(false);
          setDeviceCode(null);
          toast.error('Chyba při aktivaci: ' + result.message);
        }
      }, 5000);
    }
    return () => clearInterval(pollInterval);
  }, [isPolling, deviceCode, traktId, traktSecret]);

  const handleWebshareLogin = async () => {
    if (!wsUsername || !wsPassword) {
      toast.error('Vyplňte jméno a heslo');
      return;
    }
    setIsWsLoading(true);
    const result = await webshareService.login(wsUsername, wsPassword);
    if (result && result.token) {
      localStorage.setItem('ws_token', result.token);
      localStorage.setItem('ws_username', result.username);
      setWsToken(result.token);
      setWsUsername(result.username);
      setWsPassword('');
      toast.success('Webshare úspěšně přihlášen!');
    } else {
      toast.error('Přihlášení na Webshare selhalo');
    }
    setIsWsLoading(false);
  };

  const logoutTrakt = () => {
    localStorage.removeItem('trakt_access_token');
    setTraktToken('');
    toast.success('Trakt.tv odhlášen');
  };

  const logoutWebshare = () => {
    localStorage.removeItem('ws_token');
    localStorage.removeItem('ws_username');
    setWsToken('');
    setWsUsername('');
    toast.success('Webshare odhlášen');
  };

  const handlePaste = async (setter: (val: string) => void) => {
    try {
      const text = await navigator.clipboard.readText();
      setter(text);
      toast.success('Vloženo ze schránky');
    } catch (err) {
      toast.error('Nepodařilo se číst ze schránky. Ujistěte se, že máte povolen přístup.');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 max-w-4xl mx-auto space-y-12"
    >
      <h1 className="text-4xl font-bold tracking-tight flex items-center gap-3">
        <SettingsIcon className="w-10 h-10 text-blue-500" />
        Nastavení
      </h1>

      <div className="grid gap-8">
        {/* Trakt.tv Integration */}
        <section className="bg-zinc-900/50 rounded-3xl p-8 border border-white/5 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-red-500/10 rounded-xl flex items-center justify-center">
                <Smartphone className="w-6 h-6 text-red-500" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Trakt.tv Aktivace</h2>
                <p className="text-sm text-zinc-500">Propojte zařízení pomocí aktivačního kódu.</p>
              </div>
            </div>
            {traktToken && (
              <span className="flex items-center gap-1 text-emerald-500 text-sm font-medium">
                <CheckCircle2 className="w-4 h-4" /> Propojeno
              </span>
            )}
          </div>

          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">Client ID</label>
                <div className="relative">
                  <input
                    type="password"
                    value={traktId}
                    onChange={(e) => setTraktId(e.target.value)}
                    className="w-full bg-zinc-950 border border-white/10 rounded-xl px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-red-500/50 transition-all"
                  />
                  <button 
                    onClick={() => handlePaste(setTraktId)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-zinc-500 hover:text-white transition-colors"
                    title="Vložit ze schránky"
                  >
                    <ClipboardPaste className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">Client Secret</label>
                <div className="relative">
                  <input
                    type="password"
                    value={traktSecret}
                    onChange={(e) => setTraktSecret(e.target.value)}
                    className="w-full bg-zinc-950 border border-white/10 rounded-xl px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-red-500/50 transition-all"
                  />
                  <button 
                    onClick={() => handlePaste(setTraktSecret)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-zinc-500 hover:text-white transition-colors"
                    title="Vložit ze schránky"
                  >
                    <ClipboardPaste className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={saveTraktConfig}
                className="bg-zinc-800 hover:bg-zinc-700 text-white px-6 py-3 rounded-xl font-semibold transition-all"
              >
                Uložit konfiguraci
              </button>
              {!traktToken ? (
                <button
                  onClick={startTraktActivation}
                  disabled={isPolling}
                  className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2"
                >
                  {isPolling ? <Loader2 className="w-5 h-5 animate-spin" /> : <Smartphone className="w-5 h-5" />}
                  Aktivovat zařízení
                </button>
              ) : (
                <button
                  onClick={logoutTrakt}
                  className="bg-zinc-800 hover:bg-zinc-700 text-red-500 px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2"
                >
                  <LogOut className="w-5 h-5" />
                  Odpojit Trakt
                </button>
              )}
            </div>

            <AnimatePresence>
              {deviceCode && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-zinc-950 border border-red-500/30 rounded-2xl p-6 space-y-4 text-center"
                >
                  <p className="text-zinc-400">Přejděte na <a href={deviceCode.verification_url} target="_blank" className="text-red-500 underline font-bold">{deviceCode.verification_url}</a> a zadejte kód:</p>
                  <div className="text-5xl font-mono font-bold tracking-[0.2em] text-white py-4 bg-white/5 rounded-xl">
                    {deviceCode.user_code}
                  </div>
                  <div className="flex items-center justify-center gap-2 text-zinc-500 text-sm">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Čekám na potvrzení...
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </section>

        {/* Webshare Integration */}
        <section className="bg-zinc-900/50 rounded-3xl p-8 border border-white/5 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center">
                <Cloud className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Webshare.cz</h2>
                <p className="text-sm text-zinc-500">Přihlášení pro přístup k souborům.</p>
              </div>
            </div>
            {wsToken && (
              <span className="flex items-center gap-1 text-emerald-500 text-sm font-medium">
                <CheckCircle2 className="w-4 h-4" /> Přihlášeno ({wsUsername})
              </span>
            )}
          </div>

          {!wsToken ? (
            <div className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-400">Uživatelské jméno</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={wsUsername}
                      onChange={(e) => setWsUsername(e.target.value)}
                      className="w-full bg-zinc-950 border border-white/10 rounded-xl px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                    />
                    <button 
                      onClick={() => handlePaste(setWsUsername)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-zinc-500 hover:text-white transition-colors"
                      title="Vložit ze schránky"
                    >
                      <ClipboardPaste className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-400">Heslo</label>
                  <div className="relative">
                    <input
                      type="password"
                      value={wsPassword}
                      onChange={(e) => setWsPassword(e.target.value)}
                      className="w-full bg-zinc-950 border border-white/10 rounded-xl px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                    />
                    <button 
                      onClick={() => handlePaste(setWsPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-zinc-500 hover:text-white transition-colors"
                      title="Vložit ze schránky"
                    >
                      <ClipboardPaste className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
              <button
                onClick={handleWebshareLogin}
                disabled={isWsLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-semibold transition-all flex items-center gap-2"
              >
                {isWsLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Cloud className="w-5 h-5" />}
                Přihlásit se
              </button>
            </div>
          ) : (
            <div className="flex gap-4">
              <button
                onClick={logoutWebshare}
                className="bg-zinc-800 hover:bg-zinc-700 text-red-500 px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2"
              >
                <LogOut className="w-5 h-5" />
                Odhlásit se
              </button>
            </div>
          )}
        </section>

        {/* Local Database */}
        <section className="bg-zinc-900/50 rounded-3xl p-8 border border-white/5 space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center">
              <Database className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Lokální databáze</h2>
              <p className="text-sm text-zinc-500">Správa dat uložených přímo ve vašem prohlížeči.</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            <button className="bg-zinc-800 hover:bg-zinc-700 text-white px-6 py-3 rounded-xl font-medium transition-all">
              Exportovat data (JSON)
            </button>
            <button className="bg-zinc-800 hover:bg-zinc-700 text-white px-6 py-3 rounded-xl font-medium transition-all">
              Importovat data
            </button>
          </div>
        </section>
      </div>

      <div className="pt-12 border-t border-white/5 text-center">
        <p className="text-zinc-600 text-sm">StreamContinuum v1.0.0-alpha</p>
        <p className="text-zinc-700 text-xs mt-1">Vytvořeno pro Kodi & Google AI Studio</p>
      </div>
    </motion.div>
  );
}
