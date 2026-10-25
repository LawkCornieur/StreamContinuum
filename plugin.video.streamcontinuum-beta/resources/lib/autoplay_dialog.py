# -*- coding: utf-8 -*-
"""
StreamContinuum - Autoplay Countdown Dialog
Poskytuje interaktivní odpočet pro automatické přehrávání další epizody
s možností okamžitého spuštění ("Přehrát nyní") nebo zrušení ("Zrušit").
"""

import time
import threading
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()

ACTION_PREVIOUS_MENU = 10
ACTION_STOP = 13
ACTION_NAV_BACK = 92


class AutoplayCountdownDialog(xbmcgui.WindowXMLDialog):
    """
    Vlastní dialogové okno s odpočtem automatického přehrávání,
    zobrazením názvu dílu, ubíhajícím progress barem a dvěma tlačítky.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.heading = kwargs.get('heading', '')
        self.line1 = kwargs.get('line1', '')
        self.line2 = kwargs.get('line2', '')
        self.btn_play_label = kwargs.get('btn_play', ADDON.getLocalizedString(30193) or 'Přehrát nyní')
        self.btn_cancel_label = kwargs.get('btn_cancel', ADDON.getLocalizedString(30194) or 'Zrušit')
        self.total_seconds = max(1, kwargs.get('seconds', 10))
        self.result = False
        self.running = False
        self.monitor = xbmc.Monitor()
        self.thread = None

    def onInit(self):
        self.setProperty('heading', str(self.heading))
        self.setProperty('line1', str(self.line1))
        self.setProperty('line2', str(self.line2))
        self.setProperty('btn_play_label', str(self.btn_play_label))
        self.setProperty('btn_cancel_label', str(self.btn_cancel_label))
        self.setProperty('percent', '100')
        self.setProperty('countdown_text', f"Spuštění za {self.total_seconds} s...")

        try:
            self.setFocusId(200)  # Výchozí fokus na tlačítko "Přehrát nyní"
        except Exception:
            pass

        self.running = True
        self.thread = threading.Thread(target=self._countdown_loop)
        self.thread.daemon = True
        self.thread.start()

    def _countdown_loop(self):
        start_time = time.time()
        while self.running and not self.monitor.abortRequested():
            elapsed = time.time() - start_time
            remaining = max(0, int(self.total_seconds - elapsed + 0.99))
            percent = int(max(0, min(100, (1.0 - (elapsed / self.total_seconds)) * 100)))

            self.setProperty('countdown_text', f"Spuštění za {remaining} s...")
            self.setProperty('percent', str(percent))
            try:
                prog = self.getControl(103)
                prog.setPercent(percent)
            except Exception:
                pass

            if elapsed >= self.total_seconds:
                self.result = True
                self.running = False
                self.close()
                break

            xbmc.sleep(100)

    def onClick(self, controlId):
        self.running = False
        if controlId == 200:
            # Uživatel zvolil okamžité pokračování
            self.result = True
        elif controlId == 201:
            # Uživatel zvolil zrušení
            self.result = False
        self.close()

    def onAction(self, action):
        action_id = action.getId()
        if action_id in (ACTION_NAV_BACK, ACTION_PREVIOUS_MENU, ACTION_STOP):
            self.running = False
            self.result = False
            self.close()


def run_autoplay_countdown(heading, line1, line2, seconds, show_continue_btn=True):
    """
    Spustí odpočet před přehráním dalšího dílu.
    
    Parametry:
        heading (str): Titulek dialogu (např. "Automaticky přehrát další")
        line1 (str): Hlavní popisek (např. "Další díl: Seriál S01E02")
        line2 (str): Doplňující popisek (např. název souboru na Webshare)
        seconds (int): Doba odpočtu ve vteřinách
        show_continue_btn (bool): Zda zobrazit dialog s tlačítkem pokračování
        
    Návratová hodnota:
        bool: True pokud má dojít ke spuštění (vypršel čas nebo kliknuto na Přehrát),
              False pokud uživatel odpočet zrušil.
    """
    if seconds <= 0:
        return True

    # 1. Pokud je povoleno tlačítko pokračování, pokusit se zobrazit WindowXMLDialog
    if show_continue_btn:
        try:
            addon_path = ADDON.getAddonInfo('path')
            btn_play = ADDON.getLocalizedString(30193) or "Přehrát nyní"
            btn_cancel = ADDON.getLocalizedString(30194) or "Zrušit"

            dialog = AutoplayCountdownDialog(
                'autoplay_dialog.xml', addon_path, 'Default', '720p',
                heading=heading, line1=line1, line2=line2,
                btn_play=btn_play, btn_cancel=btn_cancel,
                seconds=seconds
            )
            dialog.doModal()
            res = dialog.result
            del dialog
            return bool(res)
        except Exception as e:
            xbmc.log(f"StreamContinuum: WindowXMLDialog fallback due to: {e}", xbmc.LOGWARNING)

    # 2. Standardní DialogProgress (pokud je tlačítko vypnuté nebo došlo k chybě)
    dialog = xbmcgui.DialogProgress()
    dialog.create(heading, f"{line1}\n{line2}")
    monitor = xbmc.Monitor()
    try:
        total_ticks = max(1, seconds * 10)
        for i in range(total_ticks):
            if dialog.iscanceled() or monitor.abortRequested():
                return False
            percent = int(100 - (i / total_ticks * 100))
            remaining = max(0, seconds - (i // 10))
            dialog.update(percent, f"{line1}\n{line2}\nSpuštění za {remaining} s...")
            xbmc.sleep(100)

        if not dialog.iscanceled() and not monitor.abortRequested():
            return True
        return False
    finally:
        try:
            dialog.close()
        except Exception:
            pass
