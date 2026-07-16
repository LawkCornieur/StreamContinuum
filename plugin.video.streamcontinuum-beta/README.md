# StreamContinuum - Kodi Addon

StreamContinuum je moderní Kodi doplněk pro Webshare.cz s integrací Trakt.tv.

## Vlastnosti
- **Trakt.tv Sync**: Automatické ukládání shlédnutých dílů a filmů.
- **Webshare.cz**: Přístup k tisícům souborů ve vysoké kvalitě.
- **Remote Friendly**: Rozhraní optimalizované pro dálkové ovladače.
- **Smart History**: Navrhování dalších epizod na základě historie.

## Instalace
1. Stáhněte si tento repozitář jako ZIP.
2. V Kodi zvolte `Doplňky` -> `Instalovat ze souboru ZIP`.
3. Po instalaci přejděte do nastavení doplňku a aktivujte Trakt.tv.

## Vývoj
Tento projekt je vyvíjen s pomocí Google AI Studio.

## Správa obrázků (Asset Management)
Grafická aktiva (ikony, fanarty) jsou spravována ze složky media-src, který slouží jako "single source of truth". 

- **Mechanismus**: Doplněk při spuštění kontroluje přítomnost souborů v `resources/` a `resources/media/`. Pokud chybí, automaticky je stáhne pomocí skriptu `build_assets.py`.
- **Struktura**:
  - `icon.png` -> `resources/icon.png`
  - `fanart.png` -> `resources/fanart.png`
  - `fanart_tra.png` -> `resources/media/fanart_tra.png`
  - `fanart_ws.png` -> `resources/media/fanart_ws.png`
  - `fanart_his.png` -> `resources/media/fanart_his.png`
