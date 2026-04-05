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
6. Vyberte soubor `repository.streamcontinuum-1.0.0.zip`.

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
