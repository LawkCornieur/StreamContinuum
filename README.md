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
6. Vyberte soubor `repository.streamcontinuum-1.1.0.zip`.

### 3. Nainstalujte doplněk StreamContinuum
1. Vyberte **Instalovat z repozitáře**.
2. Vyberte **StreamContinuum Repository**.
3. Přejděte do **Doplňky videí**.
4. Vyberte **StreamContinuum** a klikněte na **Instalovat**.

## Konfigurace

### Webshare.cz
1. Po instalaci přejděte do nastavení doplňku.
2. V sekci **Webshare** zadejte své uživatelské jméno a heslo.

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
