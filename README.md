# StreamContinuum Kodi Addon

Jednoduchý stream doplněk pro Kodi s integrací Trakt.tv a Webshare.cz.

## Instalace

### 1. Přidejte si zdroj repozitáře do Správce souborů
1. Otevřete Kodi a přejděte do **Nastavení** (ikona ozubeného kola).
2. Přejděte do **Správce souborů**.
3. Klikněte na **Přidat zdroj**.
4. Do pole "Cesta k médiu" zadejte: `https://lawkcornieur.github.io/StreamContinuum/`
5. Pojmenujte zdroj (např. `StreamContinuum Repo`) a potvrďte **OK**.

### 2. Nainstalujte repozitář
1. Vraťte se na hlavní obrazovku Kodi a přejděte do **Doplňky**.
2. Klikněte na ikonu **Instalátoru balíčků** (otevřená krabice vlevo nahoře).
3. Vyberte **Instalovat ze souboru zip**.
4. Pokud se zobrazí varování o neznámých zdrojích, povolte je v nastavení.
5. Najděte přidaný zdroj `StreamContinuum Repo`.
6. Vyberte soubor `repository.streamcontinuum-1.1.2.zip`.

### 3. Nainstalujte doplněk StreamContinuum
1. Vyberte **Instalovat z repozitáře**.
2. Vyberte **StreamContinuum Repository**.
3. Přejděte do **Doplňky videí**.
4. Vyberte **StreamContinuum** a klikněte na **Instalovat**.

## Konfigurace

### Webshare.cz
1. Po instalaci přejděte do nastavení doplňku.
2. V sekci **Webshare** zadejte své uživatelské jméno a heslo.

### TMDb (API Nastavení)
Doplněk má v sobě integrovaný výchozí TMDb klíč pro načítání obrázků a metadat.
Pokud byste v budoucnu potřebovali použít vlastní klíč (např. kvůli omezením API):
1. Vytvořte si bezplatný účet na [themoviedb.org](https://www.themoviedb.org/).
2. Přejděte do nastavení účtu do sekce **API** a požádejte o klíč (typ Developer).
3. Vygenerovaný **API Key (v3 auth)** zkopírujte.
4. V nastavení doplňku StreamContinuum přejděte do sekce **TMDb** a vložte jej do pole **TMDb API klíč**.

### Trakt.tv (API Nastavení)
Pro fungování Trakt.tv integrace si musí každý uživatel vytvořit vlastní API aplikaci:
1. Přihlaste se na [trakt.tv](https://trakt.tv).
2. Přejděte do [Settings -> API Apps](https://trakt.tv/oauth/applications).
3. Klikněte na **New Application**.
4. Vyplňte libovolný název (např. `StreamContinuum`).
5. Do pole **Redirect URI** zadejte: `urn:ietf:wg:oauth:2.0:oob`
6. Uložte aplikaci a zkopírujte si **Client ID** a **Client Secret**.
7. V nastavení doplňku StreamContinuum v sekci **Trakt.tv** zadejte tyto údaje.
8. Poté klikněte na **Aktivovat zařízení** a zadejte kód na [trakt.tv/activate](https://trakt.tv/activate).

---
Vyvinuto pro Kodi 19+ (Matrix, Nexus, Omega).


## Seznam změn

**Verze 1.3.7**
- Přejmenování všech položek z ČSFD na TMDb.
- Přidáno vyhledávání přímo v kategorii TMDb stejně jako na Trakt.tv.
- Oprava navigace po zavření nastavení (již se nevrací do prázdné složky).
- Přidána samostatná záložka pro TMDb nastavení.

**Verze 1.3.6**
- Oprava synchronizace historie na Webshare (soubory se nahrávají a přesouvají korektně jako privátní).
- Přidáno uživatelské nastavení a dialogové potvrzení pro vypnutí ověřování SSL certifikátů při chybě připojení k ČSFD.

**Verze 1.3.5**
- Oprava parsování a načítání sekce ČSFD (odolnější regulární výrazy a ignorování SSL chyb).

**Verze 1.3.4**
- Oprava navigace ČSFD a Trakt.tv katalogů (oprava chybějícího směrování v run()).
- Odstranění TMDB klíče z nastavení a oprava načítání obrázků (plakáty a pozadí se načítají automaticky z TMDB na pozadí podle ID z Trakt.tv).

**Verze 1.3.3**
- Přidána sekce ČSFD.cz: TV tipy dne, Premiéry VOD, Premiéry DVD a Blu-ray.
- U seriálů v ČSFD i Trakt.tv navigace přes Série -> Epizody -> hledaní na Webshare.
- Přidány katalogy Trakt.tv: Trendy, Popularní, Doporučené filmy i seriály.
- Bohatší zobrazeni metadat (plakát, fanart, žánry, hodnocení, délka, popis).
- Doplnění překladů pro Angličtinu a Němčinu.
- Integrace obrazků přes Trakt.tv (vyžaduje nastavené Trakt API).

**Verze 1.3.2**
- Přidána ochrana proti přetížení API (pauza 0.5s mezi mazáním jednotlivých souborů v cyklu).
- Robustnější nahrávání souborů na Webshare (zvýšen timeout na 60s, implementováno 3x opakování při chybě s 2s prodlevou).

**Verze 1.3.1**
- Odstraněna varování (deprecated warnings) v Kodi logu pomocí přechodu na nové InfoTagVideo API.
- Oprava mazání souborů na Webshare (změna API endpointu na správný remove_file).

**Verze 1.3.0**
- Stabilizace otevírání oken a přidání spolehlivých časových limitů pro zavření přehrávače.
- Oprava a stabilizace mazání souborů na Webshare (přidána 2s pauza a validace XML odpovědí).

**Verze 1.2.9**
- Dynamická aktualizace zobrazení verze v nastavení doplňku.
- Oprava pádu doplňku při synchronizaci historie (KeyError: 'title').
- Opraveny chybové hlášky ohledně zastaralých metod při spouštění přehrávání.

**Verze 1.2.8**
- Oprava filtrování epizod stejného seriálu v historii vyhledávání.
- Úprava Trakt.tv menu a oprava řazení seriálů (nově se zobrazují skutečně nejnovější sledované jako první).

**Verze 1.2.7**
- Oprava exportu nastavení a záloha Trakt.tv credentials (upload_url) na Webshare 
- Oprava pádu kvůli zamknutému souboru při aktualizaci doplňku pod Windows.

**Verze 1.2.6**
- Přepracování historie vyhledávání, možnost úpravy položky.
- Úprava přesměrování po přehrání položky do historie ihned.

**Verze 1.2.5**
- Oprava a doplnění anglického překladu
- Přidán něměcký překlad

**Verze 1.2.4**
- Oprava exportu nastavení na Webshare (přidáno logování a stabilizace)
- Přidána možnost automatického spuštění doplňku po startu Kodi
- Oprava poškození binárních souborů na GitHubu (úprava .gitattributes)

**Verze 1.2.3**
- Aktualizace grafických aktiv a audio souborů z media-src
- Stabilizace procesu synchronizace s GitHubem
- Pročištění starých verzí archivů

**Verze 1.2.2**
- Oprava automatického sestavení na GitHub Actions (vyřešen konflikt s 'unstaged changes')
- Sjednocení procesu nahrávání vygenerovaných souborů do repozitáře

**Verze 1.2.1**
- Oprava poškození grafických souborů při nahrávání z AI Studia (vypnuto LFS)
- Oprava konfliktů při automatickém sestavení repozitáře na GitHubu

**Verze 1.2.0**
- Oprava exportu nastavení (kompatibilita s novějšími verzemi šifrovací knihovny)
- Zvýšení spolehlivosti předvyplněného hledání po přehrání
- Oprava synchronizace verze a seznamu změn v repozitáři

**Verze 1.1.9**
- Oprava cesty ke grafickým souborům
- Odstraněna nefunkční volba maximálního rozlišení
- Oprava a rozšíření voleb po skončení přehrávání
- Přidána volba předvyplněného hledání po přehrání
- Přidána uvítací melodie při startu Kodi (lze vypnout v nastavení)

**Verze 1.1.8**
- Oprava automatického návratu po přehrání
- Oprava poškození obrázků při nahrávání na GitHub
- Výchozí akce po přehrání nastavena na původní hledání

**Verze 1.1.7**
- Přidána možnost volby akce po skončení přehrávání
- Přidána funkce zálohování a obnovy nastavení na Webshare
- Odstraněno nefunkční tlačítko návodu na webu
- Přechod na jednotný zdroj obrázků z media-src
- Odstraněny staré skripty pro stahování z Google Drive

**Verze 1.1.6**
- Vylepšení zobrazení výsledků hledání z Webshare
- Přidána možnost optimalizace názvů souborů
- Přepočet velikosti nad 1000 MB na GB
- Oprava zobrazení obrázků v doplňku i na webu

**Verze 1.1.5**
- Kompletní lokalizace do angličtiny a češtiny
- Přidána podpora pro tmavý režim na webu repozitáře
- Oprava aktualizačního mechanismu doplňku

**Verze 1.1.4**
- Oprava vyhledávání z historie (automatické spuštění)
- Synchronizace verze s repozitářem

**Verze 1.1.3**
- Oprava hlavního menu (odstranění nefunkční hlavičky)
- Přidány navigační drobky (nadpisy sekcí)
- Vylepšení ikon v menu
- Oprava zobrazení historie změn

**Verze 1.1.2**
- Modernizované hlavní menu
- Rozšířené možnosti v historii (E+1, S+1, Trakt search)
- Možnost označit/odznačit zhlédnuté na Trakt.tv
- Optimalizace historie

**Verze 1.1.1**
- Oprava vyhledávání na Webshare
- Podpora pro Trakt.tv watchlist
- Základní historie hledání
