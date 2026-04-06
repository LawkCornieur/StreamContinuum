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
Grafická aktiva (ikony, fanarty) jsou spravována externě skrze Google Drive, který slouží jako "single source of truth". 

- **Zdroj**: [Google Drive Folder](https://drive.google.com/drive/folders/1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF)
- **Mechanismus**: Doplněk při spuštění kontroluje přítomnost souborů v `resources/` a `resources/media/`. Pokud chybí, automaticky je stáhne pomocí skriptu `build_assets.py`.
- **Struktura**:
  - `icon.png` -> `resources/icon.png`
  - `fanart.jpg` -> `resources/fanart.jpg`
  - `fanart_tra.jpg` -> `resources/media/fanart_tra.jpg`
  - `fanart_ws.jpg` -> `resources/media/fanart_ws.jpg`
  - `fanart_his.jpg` -> `resources/media/fanart_his.jpg`
