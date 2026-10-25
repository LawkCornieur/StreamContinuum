import os
import json
import xbmcaddon
import xbmcvfs
import re
import time
import xbmc
import datetime
import unicodedata
import threading

try:
    import tmdb
except ImportError:
    try:
        import resources.lib.tmdb as tmdb
    except Exception:
        tmdb = None

ADDON = xbmcaddon.Addon()
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
HISTORY_FILE = os.path.join(PROFILE_DIR, 'history.json')
TOMBSTONES_FILE = os.path.join(PROFILE_DIR, 'history_tombstones.json')
TOMBSTONE_EXPIRATION_DAYS = 30
_history_file_lock = threading.Lock()

_EPISODE_PATTERN = re.compile(
    r'^(.*?)(?:[\s._\-]+|(?<=[^\W\d_]))(?:S(\d+)\s*E(\d+)\b|\b(\d+)x(\d+)\b|\b(?:série|serie|season)\s*(\d+)\s*(?:epizoda|díl|dil|ep|e)\s*(\d+)\b)',
    re.IGNORECASE
)

_SERIES_DETECT_PATTERN = re.compile(
    r'(?:^|[\s._\-]|(?<=[^\W\d_]))(?:s\d+\s*e\d+\b|\bseason\s*\d+\b|\bsérie\s*\d+\b|\bserie\s*\d+\b|\bs\d+\b|\be\d+\b|\b\d+x\d+\b)',
    re.IGNORECASE
)

_VIDEO_EXT_PATTERN = re.compile(r'\.(mkv|avi|mp4|m4v|mov|wmv|ts|flv)$', re.IGNORECASE)


def _safe_timestamp(val):
    if not val:
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        pass
    try:
        val_str = str(val).replace('T', ' ').strip()
        if len(val_str) >= 10:
            dt = datetime.datetime.fromisoformat(val_str[:19])
            return int(dt.timestamp())
    except Exception:
        pass
    return 0


def has_non_latin(s):
    if not s:
        return False
    for ch in str(s):
        o = ord(ch)
        if o > 0x024F and not (0x1E00 <= o <= 0x1EFF or 0x2000 <= o <= 0x206F):
            return True
    return False


def sanitize_title(s):
    if not s:
        return ""
    cleaned = []
    for ch in str(s):
        o = ord(ch)
        if o < 32 or (0x007F <= o <= 0x009F) or (0xD800 <= o <= 0xDFFF) or (0xFFF0 <= o <= 0xFFFF) or o >= 0x10000:
            continue
        cleaned.append(ch)
    return "".join(cleaned).strip()


def strip_diacritics(s):
    if not s:
        return ""
    norm = unicodedata.normalize('NFKD', str(s))
    return "".join(c for c in norm if not unicodedata.combining(c))


def is_series(query):
    if not query:
        return False
    return bool(_SERIES_DETECT_PATTERN.search(str(query)))


def parse_episode_info(query):
    """
    Vrátí n-tici (ws_base, season, episode, episode_code) z vyhledávacího dotazu.
    Pokud dotaz neobsahuje označení epizody, vrací (get_base_name(query), None, None, None).
    """
    if not query:
        return "", None, None, None
    q_str = str(query).strip()
    m = _EPISODE_PATTERN.search(q_str)
    if m:
        raw_base = (m.group(1) or "").strip()
        cleaned_base = re.sub(r'[\s._\-]+$', '', raw_base).strip()
        ws_base = get_base_name(cleaned_base) if cleaned_base else get_base_name(q_str)
        season = int(m.group(2) or m.group(4) or m.group(6))
        episode = int(m.group(3) or m.group(5) or m.group(7))
        ep_code = f"S{season:02d}E{episode:02d}"
        return ws_base, season, episode, ep_code
    return get_base_name(q_str), None, None, None


def get_base_name(query):
    if not query:
        return ""
    q = str(query)
    q = _VIDEO_EXT_PATTERN.sub('', q)
    q = re.sub(r'[._]', ' ', q)
    q = re.sub(r'(?:[\s._\-]+|(?<=[^\W\d_]))(?:s\d+\s*e\d+|\bseason\s*\d+|\bsérie\s*\d+|\bserie\s*\d+|\bs\d+\b|\be\d+\b|\b\d+x\d+\b).*$', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\b(2160p|1080p|720p|480p|4k|uhd|hd|hdtv|web-?dl|bluray|blu-?ray|bdrip|brrip|dvdrip|dvd|laserdisk|laserdisc|cd|vhs|remux|x264|x265|h264|hevc|aac|ac3|dts)\b.*$', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\b(cz|sk|en|de|czech|czdab|skdab|dabing|dab|czsub|sksub|sub|titulky|tit|cztit|sktit|repack|proper|extended|unrated)\b.*$', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\s*\(?\d{4}\)?$', '', q).strip()
    q = re.sub(r'[\-\–\—\s]+$', '', q).strip()
    q = re.sub(r'\s+', ' ', q).strip()
    return sanitize_title(q) if q else sanitize_title(str(query))


def normalize_match_key(s):
    if not s:
        return ""
    base = get_base_name(s)
    ascii_s = strip_diacritics(base).lower()
    ascii_s = re.sub(r'[:\-\–\—/\\|(),.!?\'\"]+', ' ', ascii_s)
    ascii_s = re.sub(r'\s+', ' ', ascii_s).strip()
    return ascii_s


_ABBREVIATIONS = [
    (re.compile(r'\b(st)\b', re.IGNORECASE), 'Star Trek'),
    (re.compile(r'\b(sw)\b', re.IGNORECASE), 'Star Wars'),
    (re.compile(r'\b(got)\b', re.IGNORECASE), 'Game of Thrones'),
    (re.compile(r'\b(lotr)\b', re.IGNORECASE), 'Lord of the Rings'),
]


def expand_abbreviations(text):
    if not text:
        return []
    variants = []
    t = str(text).strip()
    for pattern, replacement in _ABBREVIATIONS:
        if pattern.search(t):
            expanded = pattern.sub(replacement, t).strip()
            if expanded and expanded != t:
                variants.append(expanded)
                if re.search(r'\b(ds9)\b', expanded, re.IGNORECASE):
                    variants.append(re.sub(r'\b(ds9)\b', 'Deep Space Nine', expanded, flags=re.IGNORECASE).strip())
                elif re.search(r'\b(tng)\b', expanded, re.IGNORECASE):
                    variants.append(re.sub(r'\b(tng)\b', 'The Next Generation', expanded, flags=re.IGNORECASE).strip())
                elif re.search(r'\b(snw)\b', expanded, re.IGNORECASE):
                    variants.append(re.sub(r'\b(snw)\b', 'Strange New Worlds', expanded, flags=re.IGNORECASE).strip())
    return variants


def _clean_item_title(raw_title, query, tmdb_id):
    if not raw_title:
        return None
    t = sanitize_title(raw_title)
    if not t or has_non_latin(t):
        return None
    if not tmdb_id:
        if _VIDEO_EXT_PATTERN.search(t) or is_series(t):
            return None
        if query and t.strip().lower() == str(query).strip().lower():
            return None
    return t


def normalize_history_item(item, default_ts=None):
    if not isinstance(item, dict):
        return None
    if item.get('is_deleted'):
        return None
    raw_query = item.get('query')
    if not raw_query or not str(raw_query).strip():
        return None

    clean_query = str(raw_query).strip()
    now = default_ts or int(time.time())

    tmdb_id = item.get('tmdb_id')
    try:
        tmdb_id = int(tmdb_id) if (tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0')) else None
    except (ValueError, TypeError):
        tmdb_id = None

    s_info = item.get('series_info') if isinstance(item.get('series_info'), dict) else {}
    ws_base, season, episode, ep_code = parse_episode_info(clean_query)
    if season is None and item.get('season') is not None:
        try:
            season = int(item.get('season'))
        except (ValueError, TypeError):
            season = None
    if episode is None and item.get('episode') is not None:
        try:
            episode = int(item.get('episode'))
        except (ValueError, TypeError):
            episode = None
    if season is None and s_info.get('season') is not None:
        try:
            season = int(s_info.get('season'))
        except (ValueError, TypeError):
            season = None
    if episode is None and s_info.get('episode') is not None:
        try:
            episode = int(s_info.get('episode'))
        except (ValueError, TypeError):
            episode = None

    if season is not None and episode is not None:
        ep_code = f"S{season:02d}E{episode:02d}"
    else:
        ep_code = None

    is_tv = (
        item.get('media_type') in ('tvshow', 'tv', 'show')
        or is_series(clean_query)
        or (season is not None and episode is not None)
    )
    media_type = 'tvshow' if is_tv else 'movie'

    if is_tv:
        saved_ws_base = item.get('ws_base') or s_info.get('ws_base')
        if saved_ws_base and str(saved_ws_base).strip():
            ws_base = get_base_name(saved_ws_base) or ws_base
        if season is not None and episode is not None and ws_base:
            clean_query = f"{ws_base} S{season:02d}E{episode:02d}"
    else:
        ws_base = get_base_name(clean_query)

    title = _clean_item_title(item.get('title'), raw_query, tmdb_id)

    year = item.get('year')
    try:
        year = int(str(year)[:4]) if year else None
    except (ValueError, TypeError):
        year = None

    rating = item.get('rating')
    try:
        rating = float(rating) if rating is not None else None
    except (ValueError, TypeError):
        rating = None

    runtime = item.get('runtime')
    try:
        runtime = int(runtime) if runtime is not None else None
        if runtime == 0:
            runtime = None
    except (ValueError, TypeError):
        runtime = None

    genres = item.get('genres', [])
    if isinstance(genres, str):
        genres = [g.strip() for g in genres.split(',') if g.strip()]
    elif not isinstance(genres, list):
        genres = []

    added_at = _safe_timestamp(item.get('added_at')) or now
    last_played_at = _safe_timestamp(item.get('last_played_at')) or added_at
    updated_at = _safe_timestamp(item.get('updated_at')) or last_played_at
    identified_at = _safe_timestamp(item.get('identified_at')) or (now if tmdb_id else None)
    is_watched = bool(item.get('is_watched', True))

    watched_eps = []
    if is_tv:
        raw_we = s_info.get('watched_episodes') or item.get('watched_episodes') or []
        if isinstance(raw_we, list):
            for code in raw_we:
                if isinstance(code, str) and re.match(r'^S\d+E\d+$', code.strip(), re.IGNORECASE):
                    norm_c = code.strip().upper()
                    if norm_c not in watched_eps:
                        watched_eps.append(norm_c)
        if is_watched and ep_code and ep_code not in watched_eps:
            watched_eps.append(ep_code)

        last_w_s = s_info.get('last_watched_season')
        last_w_e = s_info.get('last_watched_episode')
        if is_watched and season is not None and episode is not None:
            last_w_s = season
            last_w_e = episode

        series_info_obj = {
            'ws_base': ws_base,
            'season': season,
            'episode': episode,
            'episode_code': ep_code,
            'last_watched_season': last_w_s,
            'last_watched_episode': last_w_e,
            'watched_episodes': sorted(watched_eps)
        }
    else:
        series_info_obj = None

    return {
        'query': clean_query,
        'title': title,
        'year': year,
        'plot': str(item.get('plot') or '') if item.get('plot') else '',
        'genres': genres,
        'rating': rating,
        'runtime': runtime,
        'poster': item.get('poster') or None,
        'still': item.get('still') or None,
        'fanart': item.get('fanart') or None,
        'tmdb_id': tmdb_id,
        'media_type': media_type,
        'ws_base': ws_base,
        'season': season if is_tv else None,
        'episode': episode if is_tv else None,
        'episode_code': ep_code if is_tv else None,
        'series_info': series_info_obj,
        'identified_at': identified_at,
        'is_watched': is_watched,
        'last_played_at': last_played_at,
        'updated_at': updated_at,
        'added_at': added_at,
        'is_series_completed': bool(item.get('is_series_completed', False)),
        '_raw_title_hint': str(item.get('title') or '')
    }


def _extract_candidate_names(norm_item):
    names = set()
    for src in (norm_item.get('title'), norm_item.get('ws_base'), norm_item.get('query'), norm_item.get('_raw_title_hint')):
        if not src:
            continue
        k = normalize_match_key(src)
        if k and len(k) >= 2:
            names.add(k)
        raw_base = get_base_name(src)
        # Rozdělení složených názvů typu "Zakon gangu / Sons of Anarchy" nebo "Zákon gangu | Sons of Anarchy"
        # Dvojtečka (:) a pomlčky (-/–/—) se nesmí dělit, protože jsou legitimní součástí názvu a podtitulu!
        parts = re.split(r'\s*[/\\|]+\s*', raw_base)
        if len(parts) > 1:
            for part in parts:
                pk = normalize_match_key(part)
                if pk and len(pk) >= 2 and not pk.isdigit():
                    names.add(pk)

        # Alternativní názvy v závorkách typu "Zákon gangu (Sons of Anarchy)" nebo doplňky "(st ds9)"
        m = re.match(r'^(.*?)\s*[\(\[](.*?)[\)\]]\s*$', raw_base)
        if m:
            main_p = m.group(1).strip()
            paren_p = m.group(2).strip()
            k_main = normalize_match_key(main_p)
            if k_main and len(k_main) >= 2 and not k_main.isdigit():
                names.add(k_main)
            k_paren = normalize_match_key(paren_p)
            ignored_tags = {
                'cz', 'sk', 'en', 'de', 'fr', 'ru', 'pl', 'hu', 'it', 'es',
                'dab', 'dabing', 'tit', 'titulky', 'sub', 'subs', 'czdab', 'skdab', 'cztit', 'sktit'
            }
            if k_paren and len(k_paren) >= 2 and not k_paren.isdigit() and k_paren not in ignored_tags:
                names.add(k_paren)

    expanded_names = set()
    for n in names:
        for exp in expand_abbreviations(n):
            k_exp = normalize_match_key(exp)
            if k_exp and len(k_exp) >= 2:
                expanded_names.add(k_exp)
    names.update(expanded_names)

    return names


def _merge_metadata(target, source):
    """Doplní chybějící TMDb metadata ze source do target."""
    if not source:
        return target
    for k in ['tmdb_id', 'title', 'year', 'plot', 'genres', 'rating', 'runtime', 'poster', 'still', 'fanart', 'identified_at', 'is_series_completed']:
        t_val = target.get(k)
        s_val = source.get(k)
        if s_val is not None and s_val != '' and s_val != [] and s_val != 0:
            if t_val is None or t_val == '' or t_val == [] or t_val == 0 or (k == 'is_series_completed' and s_val is True):
                target[k] = s_val
    return target


def consolidate_history_items(raw_items):
    """
    Sjednotí, deduplikuje a strukturovaně seskupí položky historie a watchlistu.
    - Filmy: 1 záznam na film (nejnovější stav podle updated_at/last_played_at, zachování TMDb metadat).
    - Seriály: seskupení všech epizod téhož seriálu (podle tmdb_id i normalizovaných názvů/dotazů),
      sloučení stavu totožných epizod (SxxExx), zachování nejvyšší/nejnovější zhlédnuté epizody v historii
      a nejvýše jedné nezhlédnuté následující epizody (pokud je > poslední zhlédnutá epizoda a již byla vysílána).
    """
    if not raw_items or not isinstance(raw_items, list):
        return []

    now = int(time.time())
    current_year = datetime.date.today().year
    normalized = []
    for idx, it in enumerate(raw_items):
        n = normalize_history_item(it, default_ts=now - idx)
        if n:
            normalized.append(n)

    if not normalized:
        return []

    # Union-Find seskupení zvlášť pro seriály a pro filmy
    def _group_items(sub_list):
        n_len = len(sub_list)
        parent = list(range(n_len))
        root_tmdb = {}
        for i, it in enumerate(sub_list):
            tid = it.get('tmdb_id')
            try:
                tid = int(tid) if (tid and str(tid).strip().lower() not in ('none', '', '0')) else None
            except (ValueError, TypeError):
                tid = None
            root_tmdb[i] = tid

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                t_a = root_tmdb.get(ra)
                t_b = root_tmdb.get(rb)
                if t_a is not None and t_b is not None and t_a != t_b:
                    # Striktní ochrana: Různá autoritativní TMDb ID představují odlišná díla a nesmí být sloučena!
                    return False
                parent[rb] = ra
                root_tmdb[ra] = t_a if t_a is not None else t_b
                return True
            return False

        # 1. Spojení podle shodného TMDb ID
        tmdb_owner = {}
        for i, it in enumerate(sub_list):
            tid = root_tmdb.get(i)
            if tid:
                if tid in tmdb_owner:
                    union(tmdb_owner[tid], i)
                else:
                    tmdb_owner[tid] = i

        # 2. Spojení podle shody kandidátních názvů (např. varianty dotazů nebo dual-titles)
        name_owner = {}
        for i, it in enumerate(sub_list):
            c_names = _extract_candidate_names(it)
            for cn in c_names:
                if cn in name_owner:
                    union(name_owner[cn], i)
                else:
                    name_owner[cn] = i

        groups = {}
        for i, it in enumerate(sub_list):
            r = find(i)
            groups.setdefault(r, []).append(it)
        return list(groups.values())

    tv_items = [it for it in normalized if it.get('media_type') == 'tvshow']
    movie_items = [it for it in normalized if it.get('media_type') != 'tvshow']

    result_items = []

    # 1. Konsolidace filmů
    for m_group in _group_items(movie_items):
        # Seřadit podle (updated_at, last_played_at, is_watched) sestupně
        m_group.sort(
            key=lambda x: (
                _safe_timestamp(x.get('updated_at')),
                _safe_timestamp(x.get('last_played_at')),
                1 if x.get('is_watched', True) else 0,
                1 if x.get('tmdb_id') else 0
            ),
            reverse=True
        )
        winner = dict(m_group[0])
        for other in m_group[1:]:
            _merge_metadata(winner, other)
        winner.pop('_raw_title_hint', None)
        winner['series_info'] = None
        result_items.append(winner)

    # 2. Konsolidace seriálů
    for s_group in _group_items(tv_items):
        # Nejlepší metadata ze skupiny
        meta_template = {}
        identified_candidates = sorted(
            [x for x in s_group if x.get('tmdb_id')],
            key=lambda x: (
                1 if x.get('plot') else 0,
                1 if x.get('poster') else 0,
                1 if (x.get('runtime') or 0) > 0 else 0,
                _safe_timestamp(x.get('identified_at')),
                _safe_timestamp(x.get('updated_at'))
            ),
            reverse=True
        )
        for cand in identified_candidates + s_group:
            _merge_metadata(meta_template, cand)

        # Preferovaný čistý ws_base (z nejnovější ztotožněné nebo nejnovější položky)
        preferred_ws_base = None
        for cand in sorted(s_group, key=lambda x: (1 if x.get('tmdb_id') else 0, _safe_timestamp(x.get('updated_at'))), reverse=True):
            wb = cand.get('ws_base')
            if wb and not _VIDEO_EXT_PATTERN.search(wb):
                preferred_ws_base = wb
                break
        if not preferred_ws_base:
            preferred_ws_base = meta_template.get('title') or s_group[0].get('ws_base') or get_base_name(s_group[0].get('query', ''))

        # Seskupit podle epizody (season, episode)
        ep_map = {}
        all_watched_codes = set()
        for it in s_group:
            s_info = it.get('series_info') or {}
            for wc in s_info.get('watched_episodes', []):
                all_watched_codes.add(wc)
            s_num = it.get('season')
            e_num = it.get('episode')
            ep_key = (s_num if s_num is not None else 0, e_num if e_num is not None else 0)
            ep_map.setdefault(ep_key, []).append(it)

        consolidated_eps = {}
        for ep_key, ep_list in ep_map.items():
            # Pro stejnou epizodu vyhrává nejnovější updated_at; při shodě vyhrává is_watched=True
            ep_list.sort(
                key=lambda x: (
                    _safe_timestamp(x.get('updated_at')),
                    _safe_timestamp(x.get('last_played_at')),
                    1 if x.get('is_watched', True) else 0,
                    1 if x.get('tmdb_id') else 0
                ),
                reverse=True
            )
            ep_winner = dict(ep_list[0])
            for other_ep in ep_list[1:]:
                _merge_metadata(ep_winner, other_ep)
            _merge_metadata(ep_winner, meta_template)
            if ep_winner.get('is_watched', True) and ep_winner.get('episode_code'):
                all_watched_codes.add(ep_winner['episode_code'])
            consolidated_eps[ep_key] = ep_winner

        watched_eps = [ep for ep in consolidated_eps.values() if ep.get('is_watched', True)]
        unwatched_eps = [ep for ep in consolidated_eps.values() if not ep.get('is_watched', True)]

        best_watched = None
        max_w_tuple = (-1, -1)
        max_w_updated = 0
        if watched_eps:
            watched_eps.sort(
                key=lambda x: (
                    x.get('season') or 0,
                    x.get('episode') or 0,
                    _safe_timestamp(x.get('updated_at')),
                    _safe_timestamp(x.get('last_played_at'))
                ),
                reverse=True
            )
            best_watched = dict(watched_eps[0])
            for w_ep in watched_eps[1:]:
                _merge_metadata(best_watched, w_ep)
            max_w_tuple = (best_watched.get('season') or 0, best_watched.get('episode') or 0)
            max_w_updated = max(_safe_timestamp(x.get('updated_at')) for x in watched_eps)
            max_w_played = max(_safe_timestamp(x.get('last_played_at')) for x in watched_eps)
            best_watched['last_played_at'] = max_w_played
            best_watched['updated_at'] = max(max_w_updated, max_w_played)
            ws_b = best_watched.get('ws_base') or preferred_ws_base
            best_watched['ws_base'] = ws_b
            if best_watched.get('season') is not None and best_watched.get('episode') is not None and ws_b:
                best_watched['query'] = f"{ws_b} S{best_watched['season']:02d}E{best_watched['episode']:02d}"
            best_watched['series_info'] = {
                'ws_base': ws_b,
                'season': best_watched.get('season'),
                'episode': best_watched.get('episode'),
                'episode_code': best_watched.get('episode_code'),
                'last_watched_season': best_watched.get('season'),
                'last_watched_episode': best_watched.get('episode'),
                'watched_episodes': sorted(all_watched_codes)
            }
            best_watched.pop('_raw_title_hint', None)
            if any(it.get('is_series_completed') for it in s_group):
                best_watched['is_series_completed'] = True
            result_items.append(best_watched)

        # Nezhlédnutá epizoda (Watchlist): pouze pokud je > max_w_tuple a nemá budoucí rok vydání
        valid_unwatched = []
        for u_ep in unwatched_eps:
            u_tuple = (u_ep.get('season') or 0, u_ep.get('episode') or 0)
            u_year = u_ep.get('year')
            if u_year and isinstance(u_year, int) and u_year > current_year:
                continue
            if u_ep.get('episode_code') and u_ep.get('episode_code') in all_watched_codes:
                continue
            if best_watched is None or u_tuple > max_w_tuple:
                valid_unwatched.append(u_ep)

        if valid_unwatched:
            valid_unwatched.sort(
                key=lambda x: (
                    _safe_timestamp(x.get('updated_at')),
                    _safe_timestamp(x.get('last_played_at')),
                    x.get('season') or 0,
                    x.get('episode') or 0
                ),
                reverse=True
            )
            best_unwatched = dict(valid_unwatched[0])
            _merge_metadata(best_unwatched, meta_template)
            ws_b = best_unwatched.get('ws_base') or preferred_ws_base
            best_unwatched['ws_base'] = ws_b
            if best_unwatched.get('season') is not None and best_unwatched.get('episode') is not None and ws_b:
                best_unwatched['query'] = f"{ws_b} S{best_unwatched['season']:02d}E{best_unwatched['episode']:02d}"
            best_unwatched['series_info'] = {
                'ws_base': ws_b,
                'season': best_unwatched.get('season'),
                'episode': best_unwatched.get('episode'),
                'episode_code': best_unwatched.get('episode_code'),
                'last_watched_season': best_watched.get('season') if best_watched else None,
                'last_watched_episode': best_watched.get('episode') if best_watched else None,
                'watched_episodes': sorted(all_watched_codes)
            }
            best_unwatched.pop('_raw_title_hint', None)
            result_items.append(best_unwatched)

    # Watchlist položky (nezhlédnuté) zachovat všechny, nesmí být ořezány historií
    watchlist_result = [it for it in result_items if not it.get('is_watched', True)]
    watched_result = [it for it in result_items if it.get('is_watched', True)]

    # Historii zhlédnutých děl seřadit striktně podle data shlédnutí (last_played_at s fallbackem na added_at)
    watched_result.sort(
        key=lambda x: (
            _safe_timestamp(x.get('last_played_at')) or _safe_timestamp(x.get('added_at'))
        ),
        reverse=True
    )
    # Ponechat štědře až do 100 nejnověji zhlédnutých děl
    watched_result = watched_result[:100]

    # Watchlist položky seřadit podle data přidání / aktualizace sestupně
    watchlist_result.sort(
        key=lambda x: max(
            _safe_timestamp(x.get('updated_at')),
            _safe_timestamp(x.get('added_at'))
        ),
        reverse=True
    )

    final_combined = watchlist_result + watched_result
    return final_combined


def load_tombstones():
    """Načte lokálně uložené náhrobky ze souboru history_tombstones.json."""
    if not os.path.exists(TOMBSTONES_FILE):
        return []
    try:
        with open(TOMBSTONES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                now = int(time.time())
                cutoff = now - (TOMBSTONE_EXPIRATION_DAYS * 86400)
                valid = []
                for t in data:
                    if isinstance(t, dict) and t.get('is_deleted') and _safe_timestamp(t.get('deleted_at')) > cutoff:
                        valid.append(t)
                return valid
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error loading tombstones: {e}", xbmc.LOGWARNING)
    return []


def save_tombstones(tombstones):
    """Uloží náhrobky do history_tombstones.json."""
    if not os.path.exists(PROFILE_DIR):
        try:
            os.makedirs(PROFILE_DIR)
        except Exception:
            pass
    try:
        temp_file = f"{TOMBSTONES_FILE}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(tombstones, f, ensure_ascii=False, indent=4)
        os.replace(temp_file, TOMBSTONES_FILE)
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error saving tombstones: {e}", xbmc.LOGWARNING)


def item_matches_tombstone(item, tombstone):
    """
    Ověří, zda daná položka historie odpovídá náhrobku smazání.
    Vrací True, pokud položka odpovídá náhrobku a její čas změny/přehrání <= tombstone.deleted_at.
    """
    if not isinstance(item, dict) or not isinstance(tombstone, dict):
        return False
    if not tombstone.get('is_deleted'):
        return False

    del_time = _safe_timestamp(tombstone.get('deleted_at'))
    if del_time <= 0:
        return False

    # Pokud byla položka přehrána nebo upravena PO čase smazání, náhrobek ji nesmí smazat (uživatel ji znovu vyhledal/přidal)
    item_time = max(
        _safe_timestamp(item.get('updated_at')),
        _safe_timestamp(item.get('last_played_at')),
        _safe_timestamp(item.get('added_at'))
    )
    if item_time > del_time:
        return False

    t_tmdb = tombstone.get('tmdb_id')
    try:
        t_tmdb = int(t_tmdb) if t_tmdb and str(t_tmdb).strip().lower() not in ('none', '', '0') else None
    except (ValueError, TypeError):
        t_tmdb = None

    i_tmdb = item.get('tmdb_id')
    try:
        i_tmdb = int(i_tmdb) if i_tmdb and str(i_tmdb).strip().lower() not in ('none', '', '0') else None
    except (ValueError, TypeError):
        i_tmdb = None

    if t_tmdb and i_tmdb:
        if t_tmdb == i_tmdb:
            return True
        return False

    # Klíče a normalizované názvy náhrobku
    t_keys = set(tombstone.get('match_keys') or [])
    t_del_q = tombstone.get('deleted_query') or tombstone.get('query') or ''
    if t_del_q:
        k = normalize_match_key(t_del_q)
        if k:
            t_keys.add(k)
    t_ws = tombstone.get('ws_base')
    if t_ws:
        k = normalize_match_key(t_ws)
        if k:
            t_keys.add(k)

    # Klíče položky
    i_keys = set(_extract_candidate_names(item))
    i_q = item.get('query') or ''
    if i_q:
        k = normalize_match_key(i_q)
        if k:
            i_keys.add(k)
    i_ws = item.get('ws_base')
    if i_ws:
        k = normalize_match_key(i_ws)
        if k:
            i_keys.add(k)

    # Přímá textová shoda původního query
    if t_del_q and i_q and str(t_del_q).strip().lower() == str(i_q).strip().lower():
        return True

    # Shoda v klíčích
    if t_keys and i_keys and bool(t_keys & i_keys):
        t_type = tombstone.get('media_type')
        i_type = item.get('media_type')
        if not t_type or not i_type or t_type == i_type:
            return True

    return False


def remove_matching_tombstones(item_or_query):
    """Odstraní náhrobek, pokud uživatel položku znovu přidal/přehrál."""
    tombstones = load_tombstones()
    if not tombstones:
        return
    norm_item = None
    if isinstance(item_or_query, dict):
        norm_item = item_or_query
    else:
        q_str = str(item_or_query).strip()
        ws_base, season, episode, _ = parse_episode_info(q_str)
        norm_item = {
            'query': q_str,
            'ws_base': ws_base,
            'media_type': 'tvshow' if is_series(q_str) or season is not None else 'movie'
        }

    item_keys = set(_extract_candidate_names(norm_item))
    if norm_item.get('query'):
        k = normalize_match_key(norm_item['query'])
        if k:
            item_keys.add(k)
    if norm_item.get('ws_base'):
        k = normalize_match_key(norm_item['ws_base'])
        if k:
            item_keys.add(k)

    item_tmdb = norm_item.get('tmdb_id')
    try:
        item_tmdb = int(item_tmdb) if item_tmdb and str(item_tmdb).strip().lower() not in ('none', '', '0') else None
    except (ValueError, TypeError):
        item_tmdb = None

    kept_tombstones = []
    changed = False
    for t in tombstones:
        t_tmdb = t.get('tmdb_id')
        try:
            t_tmdb = int(t_tmdb) if t_tmdb and str(t_tmdb).strip().lower() not in ('none', '', '0') else None
        except (ValueError, TypeError):
            t_tmdb = None

        matched = False
        if item_tmdb and t_tmdb and item_tmdb == t_tmdb:
            matched = True
        else:
            t_keys = set(t.get('match_keys') or [])
            if t.get('deleted_query'):
                k = normalize_match_key(t['deleted_query'])
                if k:
                    t_keys.add(k)
            if t.get('ws_base'):
                k = normalize_match_key(t['ws_base'])
                if k:
                    t_keys.add(k)
            if item_keys and t_keys and bool(item_keys & t_keys):
                t_type = t.get('media_type')
                i_type = norm_item.get('media_type')
                if not t_type or not i_type or t_type == i_type:
                    matched = True

        if matched:
            changed = True
        else:
            kept_tombstones.append(t)

    if changed:
        save_tombstones(kept_tombstones)


def merge_tombstones(list_a, list_b):
    """
    Sloučí dva seznamy náhrobků (např. lokální a vzdálený z Webshare),
    odstraní duplicity (ponechá nejnovější deleted_at) a vyfiltruje expirované.
    """
    now = int(time.time())
    cutoff = now - (TOMBSTONE_EXPIRATION_DAYS * 86400)
    all_raw = (list_a or []) + (list_b or [])
    merged_map = {}

    for t in all_raw:
        if not isinstance(t, dict) or not t.get('is_deleted'):
            continue
        del_at = _safe_timestamp(t.get('deleted_at'))
        if del_at <= cutoff:
            continue

        tmdb_id = t.get('tmdb_id')
        try:
            tmdb_id = int(tmdb_id) if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0') else None
        except (ValueError, TypeError):
            tmdb_id = None

        ws_base = normalize_match_key(t.get('ws_base') or '')
        del_q = normalize_match_key(t.get('deleted_query') or t.get('query') or '')
        m_type = t.get('media_type') or ''

        if tmdb_id:
            key = f"tmdb:{tmdb_id}"
        elif ws_base:
            key = f"ws:{m_type}:{ws_base}"
        elif del_q:
            key = f"q:{del_q}"
        else:
            continue

        if key in merged_map:
            existing = merged_map[key]
            if del_at > _safe_timestamp(existing.get('deleted_at')):
                all_keys = sorted(list(set((existing.get('match_keys') or []) + (t.get('match_keys') or []))))
                t_copy = dict(t)
                t_copy['match_keys'] = all_keys
                merged_map[key] = t_copy
            else:
                existing['match_keys'] = sorted(list(set((existing.get('match_keys') or []) + (t.get('match_keys') or []))))
        else:
            t_copy = dict(t)
            t_copy['match_keys'] = sorted(list(set(t_copy.get('match_keys') or [])))
            merged_map[key] = t_copy

    return list(merged_map.values())


def filter_items_by_tombstones(items, tombstones):
    """Vyfiltruje ze seznamu položek ty, které odpovídají platným náhrobkům."""
    if not items:
        return []
    if not tombstones:
        return [it for it in items if isinstance(it, dict) and not it.get('is_deleted')]
    alive = []
    for item in items:
        if not isinstance(item, dict) or item.get('is_deleted'):
            continue
        deleted = False
        for t in tombstones:
            if item_matches_tombstone(item, t):
                deleted = True
                break
        if not deleted:
            alive.append(item)
    return alive


def get_history(deduplicate=True):
    if not os.path.exists(PROFILE_DIR):
        try:
            os.makedirs(PROFILE_DIR)
        except Exception:
            pass
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            items = json.load(f)
            if not isinstance(items, list):
                return []
            raw_active = [it for it in items if isinstance(it, dict) and not it.get('is_deleted') and str(it.get('query', '')).strip()]
            if not deduplicate:
                now = int(time.time())
                norm_list = []
                for idx, it in enumerate(raw_active):
                    n = normalize_history_item(it, default_ts=now - idx)
                    if n:
                        n.pop('_raw_title_hint', None)
                        norm_list.append(n)
                norm_list.sort(
                    key=lambda x: (
                        (_safe_timestamp(x.get('last_played_at')) or _safe_timestamp(x.get('added_at')))
                        if x.get('is_watched', True) else
                        max(_safe_timestamp(x.get('updated_at')), _safe_timestamp(x.get('added_at')))
                    ),
                    reverse=True
                )
                return norm_list
            return consolidate_history_items(raw_active)
    except json.JSONDecodeError as jde:
        xbmc.log(f"StreamContinuum History: Corrupted history.json detected: {jde}", xbmc.LOGERROR)
        try:
            bak_file = HISTORY_FILE + '.corrupted'
            if os.path.exists(HISTORY_FILE):
                os.replace(HISTORY_FILE, bak_file)
        except Exception:
            pass
        return []
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error loading history.json: {e}", xbmc.LOGERROR)
        return []


def get_history_item(query):
    if not query:
        return None
    items = get_history(deduplicate=True)
    norm_q = str(query).strip().lower()
    for item in items:
        if item.get('query') == query or str(item.get('query', '')).strip().lower() == norm_q:
            return item
    q_match = normalize_match_key(query)
    if q_match:
        for item in items:
            item_q = item.get('query', '')
            if normalize_match_key(item_q) == q_match or q_match in _extract_candidate_names(item):
                return item
    return None


def get_watched_episodes_set(tmdb_id=None, ws_base=None):
    """
    Vrátí množinu kódů zhlédnutých epizod (např. {'S01E01', 'S01E02'}) pro daný seriál.
    """
    watched_set = set()
    try:
        clean_tid = None
        if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0'):
            try:
                clean_tid = int(tmdb_id)
            except (ValueError, TypeError):
                clean_tid = None

        norm_wb = normalize_match_key(ws_base) if ws_base else None
        all_items = get_history(deduplicate=False)
        for it in all_items:
            it_tid = it.get('tmdb_id')
            try:
                it_tid = int(it_tid) if it_tid and str(it_tid).strip().lower() not in ('none', '', '0') else None
            except (ValueError, TypeError):
                it_tid = None

            matched = False
            if clean_tid and it_tid:
                matched = (clean_tid == it_tid)
            elif norm_wb:
                it_wb = normalize_match_key(it.get('ws_base') or it.get('query'))
                if it_wb and it_wb == norm_wb:
                    matched = True
                else:
                    cands = _extract_candidate_names(it)
                    if norm_wb in cands:
                        matched = True

            if matched:
                s_info = it.get('series_info') or {}
                for code in s_info.get('watched_episodes', []):
                    watched_set.add(code)
                if it.get('is_watched', True):
                    code = it.get('episode_code')
                    if code:
                        watched_set.add(code)
                    s = it.get('season')
                    e = it.get('episode')
                    if s is not None and e is not None:
                        watched_set.add(f"S{int(s):02d}E{int(e):02d}")
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error in get_watched_episodes_set: {e}", xbmc.LOGWARNING)
    return watched_set


def _save_history(history_list, tombstones=None):
    with _history_file_lock:
        try:
            if not os.path.exists(PROFILE_DIR):
                try:
                    os.makedirs(PROFILE_DIR)
                except Exception:
                    pass
            current_tombstones = load_tombstones()
            if tombstones:
                current_tombstones = merge_tombstones(current_tombstones, tombstones)
                save_tombstones(current_tombstones)

            raw_active = [it for it in (history_list or []) if isinstance(it, dict) and not it.get('is_deleted') and str(it.get('query', '')).strip()]
            filtered = filter_items_by_tombstones(raw_active, current_tombstones)
            consolidated = consolidate_history_items(filtered)

            full_output = consolidated + current_tombstones
            temp_file = f"{HISTORY_FILE}.{os.getpid()}.{threading.get_ident()}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(full_output, f, ensure_ascii=False, indent=4)
            os.replace(temp_file, HISTORY_FILE)
        except Exception as e:
            xbmc.log(f"StreamContinuum History: Error saving history.json: {e}", xbmc.LOGERROR)


def add_to_history(query):
    if not query:
        return
    query_str = str(query).strip()
    remove_matching_tombstones(query_str)
    history_items = get_history(deduplicate=True)
    now = int(time.time())
    ws_base, season, episode, ep_code = parse_episode_info(query_str)
    query_is_series = is_series(query_str) or (season is not None and episode is not None)

    new_item = {
        'query': query_str,
        'title': None,
        'year': None,
        'plot': '',
        'genres': [],
        'rating': None,
        'runtime': None,
        'poster': None,
        'fanart': None,
        'tmdb_id': None,
        'media_type': 'tvshow' if query_is_series else 'movie',
        'ws_base': ws_base,
        'season': season if query_is_series else None,
        'episode': episode if query_is_series else None,
        'episode_code': ep_code if query_is_series else None,
        'identified_at': None,
        'is_watched': True,
        'last_played_at': now,
        'updated_at': now,
        'added_at': now
    }

    history_items.insert(0, new_item)
    _save_history(history_items)


def add_to_watchlist_local(query, tmdb_data=None):
    if not query:
        return
    query_str = str(query).strip()
    history_items = get_history(deduplicate=True)
    now = int(time.time())
    ws_base, season, episode, ep_code = parse_episode_info(query_str)
    
    if tmdb_data and (season is None or episode is None):
        if tmdb_data.get('season') is not None and tmdb_data.get('episode') is not None:
            try:
                season = int(tmdb_data['season'])
                episode = int(tmdb_data['episode'])
                ep_code = f"S{season:02d}E{episode:02d}"
            except (ValueError, TypeError):
                pass
        elif tmdb_data.get('season') is not None:
            try:
                season = int(tmdb_data['season'])
            except (ValueError, TypeError):
                pass

    query_is_series = is_series(query_str) or (tmdb_data and tmdb_data.get('media_type') in ('tvshow', 'tv', 'show')) or (season is not None and episode is not None)

    target_tmdb_id = tmdb_data.get('tmdb_id') if tmdb_data else None
    try:
        target_tmdb_id = int(target_tmdb_id) if target_tmdb_id and str(target_tmdb_id).strip().lower() not in ('none', '', '0') else None
    except (ValueError, TypeError):
        target_tmdb_id = None

    max_watched_s = -1
    max_watched_e = -1
    all_watched_codes = set()

    if query_is_series:
        match_base_key = normalize_match_key(ws_base or (tmdb_data.get('title') if tmdb_data else None) or query_str)
        existing_ws_base = None

        for it in history_items:
            it_is_tv = (
                it.get('media_type') in ('tvshow', 'tv', 'show')
                or is_series(it.get('query'))
                or (it.get('season') is not None and it.get('episode') is not None)
            )
            if not it_is_tv:
                continue

            it_tmdb = it.get('tmdb_id')
            try:
                it_tmdb = int(it_tmdb) if it_tmdb and str(it_tmdb).strip().lower() not in ('none', '', '0') else None
            except (ValueError, TypeError):
                it_tmdb = None

            is_match = False
            if target_tmdb_id and it_tmdb and target_tmdb_id == it_tmdb:
                is_match = True
            else:
                it_key = normalize_match_key(it.get('ws_base') or it.get('query'))
                if match_base_key and it_key and match_base_key == it_key:
                    is_match = True
                else:
                    cand_names = set(_extract_candidate_names(it))
                    if match_base_key and match_base_key in cand_names:
                        is_match = True

            if is_match:
                if not existing_ws_base and it.get('ws_base'):
                    existing_ws_base = it.get('ws_base')
                if not target_tmdb_id and it_tmdb:
                    target_tmdb_id = it_tmdb
                if it.get('is_series_completed'):
                    it['is_series_completed'] = False

                s_info = it.get('series_info') or {}
                for wc in s_info.get('watched_episodes', []):
                    all_watched_codes.add(wc)

                if it.get('is_watched', True):
                    s_num = it.get('season')
                    e_num = it.get('episode')
                    if s_num is None and s_info.get('last_watched_season') is not None:
                        s_num = s_info.get('last_watched_season')
                    if e_num is None and s_info.get('last_watched_episode') is not None:
                        e_num = s_info.get('last_watched_episode')
                    if s_num is not None and e_num is not None:
                        all_watched_codes.add(f"S{int(s_num):02d}E{int(e_num):02d}")
                        if (s_num, e_num) > (max_watched_s, max_watched_e):
                            max_watched_s = s_num
                            max_watched_e = e_num

        ep_meta_obj = None

        if season is not None and episode is not None:
            target_s = season
            target_e = episode
        elif season is not None and episode is None:
            target_s = season
            target_e = 1
            if target_tmdb_id and tmdb:
                try:
                    s_eps = tmdb.get_season_episodes(target_tmdb_id, target_s) or []
                    unwatched_eps = [e for e in s_eps if f"S{target_s:02d}E{int(e.get('episode_number', 0)):02d}" not in all_watched_codes]
                    if unwatched_eps:
                        target_e = unwatched_eps[0].get('episode_number', 1)
                except Exception:
                    pass
        elif max_watched_s > 0 and max_watched_e > 0:
            target_s = max_watched_s
            target_e = max_watched_e + 1
            if target_tmdb_id and tmdb:
                try:
                    show_details = tmdb.get_show_seasons(target_tmdb_id)
                    if show_details and 'seasons' in show_details:
                        seasons = show_details.get('seasons', [])
                        curr_s_obj = next((s for s in seasons if s.get('season_number') == target_s), None)
                        if curr_s_obj:
                            max_eps = curr_s_obj.get('episode_count', 0)
                            if max_eps > 0 and target_e > max_eps:
                                higher_seasons = [s for s in seasons if (s.get('season_number') or 0) > target_s and (s.get('season_number') or 0) > 0]
                                higher_seasons.sort(key=lambda x: x.get('season_number') or 0)
                                if higher_seasons:
                                    target_s = higher_seasons[0].get('season_number')
                                    target_e = 1
                except Exception as e:
                    xbmc.log(f"StreamContinuum History: TMDb season calculation error in add_to_watchlist_local: {e}", xbmc.LOGWARNING)
        else:
            target_s = 1
            target_e = 1

        clean_base = sanitize_title(tmdb_data.get('title')) if (tmdb_data and tmdb_data.get('title')) else (existing_ws_base or ws_base or query_str)
        ws_base = clean_base
        season = target_s
        episode = target_e
        ep_code = f"S{target_s:02d}E{target_e:02d}"
        query_str = f"{clean_base} {ep_code}"

        if target_tmdb_id and tmdb:
            try:
                cached_eps = tmdb.get_season_episodes(target_tmdb_id, target_s) or []
                ep_meta_obj = next((e for e in cached_eps if e.get('episode_number') == target_e), None)
            except Exception:
                ep_meta_obj = None

        if ep_meta_obj:
            if not tmdb_data:
                tmdb_data = {}
            if ep_meta_obj.get('overview'):
                tmdb_data['plot'] = ep_meta_obj.get('overview')
            if ep_meta_obj.get('rating'):
                tmdb_data['rating'] = ep_meta_obj.get('rating')
            if ep_meta_obj.get('runtime'):
                tmdb_data['runtime'] = ep_meta_obj.get('runtime')
            if ep_meta_obj.get('still'):
                tmdb_data['still'] = ep_meta_obj.get('still')
            if ep_meta_obj.get('air_date'):
                try:
                    tmdb_data['year'] = int(str(ep_meta_obj.get('air_date'))[:4])
                except (ValueError, TypeError):
                    pass

    remove_matching_tombstones(query_str)
    if ws_base:
        remove_matching_tombstones(ws_base)
    if tmdb_data and tmdb_data.get('title'):
        remove_matching_tombstones(tmdb_data['title'])

    item_to_add = {
        'query': query_str,
        'title': sanitize_title(tmdb_data.get('title')) if (tmdb_data and tmdb_data.get('title')) else None,
        'year': tmdb_data.get('year') if tmdb_data else None,
        'plot': tmdb_data.get('plot', '') if tmdb_data else '',
        'genres': tmdb_data.get('genres', []) if tmdb_data else [],
        'rating': tmdb_data.get('rating') if tmdb_data else None,
        'runtime': tmdb_data.get('runtime') if tmdb_data else None,
        'poster': tmdb_data.get('poster') if tmdb_data else None,
        'still': tmdb_data.get('still') if tmdb_data else None,
        'fanart': tmdb_data.get('fanart') if tmdb_data else None,
        'tmdb_id': target_tmdb_id if target_tmdb_id else (tmdb_data.get('tmdb_id') if tmdb_data else None),
        'media_type': tmdb_data.get('media_type') if (tmdb_data and tmdb_data.get('media_type')) else ('tvshow' if query_is_series else 'movie'),
        'ws_base': ws_base,
        'season': season if query_is_series else None,
        'episode': episode if query_is_series else None,
        'episode_code': ep_code if query_is_series else None,
        'identified_at': now if (target_tmdb_id or (tmdb_data and tmdb_data.get('tmdb_id'))) else None,
        'is_watched': False,
        'last_played_at': 0,
        'updated_at': now,
        'added_at': now
    }
    if query_is_series:
        item_to_add['series_info'] = {
            'ws_base': ws_base,
            'season': season,
            'episode': episode,
            'episode_code': ep_code,
            'last_watched_season': max_watched_s if max_watched_s > 0 else None,
            'last_watched_episode': max_watched_e if max_watched_e > 0 else None,
            'watched_episodes': sorted(all_watched_codes) if all_watched_codes else []
        }
    remove_matching_tombstones(item_to_add)

    replaced = False
    for idx, cand in enumerate(history_items):
        if cand.get('is_watched', True):
            continue
        c_is_tv = (
            cand.get('media_type') in ('tvshow', 'tv', 'show')
            or is_series(cand.get('query'))
            or (cand.get('season') is not None and cand.get('episode') is not None)
        )
        if c_is_tv == query_is_series:
            c_tmdb = cand.get('tmdb_id')
            try:
                c_tmdb = int(c_tmdb) if c_tmdb and str(c_tmdb).strip().lower() not in ('none', '', '0') else None
            except (ValueError, TypeError):
                c_tmdb = None
            is_same = False
            if target_tmdb_id and c_tmdb and target_tmdb_id == c_tmdb:
                is_same = True
            else:
                c_key = normalize_match_key(cand.get('ws_base') or cand.get('query'))
                q_key = normalize_match_key(ws_base or query_str)
                if c_key and q_key and c_key == q_key:
                    is_same = True
            if is_same:
                history_items[idx] = item_to_add
                replaced = True
                break

    if not replaced:
        history_items.insert(0, item_to_add)

    _save_history(history_items)


def set_watched_status(query, is_watched):
    if not query:
        return False
    history_items = get_history(deduplicate=True)
    now = int(time.time())
    norm_q = str(query).strip().lower()
    q_match = normalize_match_key(query)
    q_ws_base, q_season, q_episode, q_ep_code = parse_episode_info(query)
    q_is_tv = is_series(query) or (q_season is not None and q_episode is not None)

    target_tmdb_id = None
    exact_matched = False
    for it in history_items:
        it_q = str(it.get('query', '')).strip().lower()
        if it_q == norm_q or (q_ep_code and it.get('episode_code') == q_ep_code and normalize_match_key(it_q) == q_match):
            target_tmdb_id = it.get('tmdb_id')
            it['is_watched'] = bool(is_watched)
            it['updated_at'] = now
            s_info = it.get('series_info')
            if is_watched:
                it['last_played_at'] = now
                if isinstance(s_info, dict):
                    if q_ep_code:
                        w_eps = set(s_info.get('watched_episodes', []))
                        w_eps.add(q_ep_code)
                        s_info['watched_episodes'] = sorted(w_eps)
                    if q_season is not None:
                        s_info['last_watched_season'] = q_season
                    if q_episode is not None:
                        s_info['last_watched_episode'] = q_episode
            else:
                # Pokud uživatel ručně odznačil epizodu jako nezhlédnutou, odebrat ji ze seznamu watched_episodes
                if isinstance(s_info, dict) and q_ep_code and q_ep_code in s_info.get('watched_episodes', []):
                    s_info['watched_episodes'] = [c for c in s_info['watched_episodes'] if c != q_ep_code]
            exact_matched = True

    updated = exact_matched
    if not exact_matched:
        for item in history_items:
            item_query = str(item.get('query', '')).strip().lower()
            item_match = normalize_match_key(item_query)
            item_is_tv = item.get('media_type') in ('tvshow', 'tv', 'show') or is_series(item_query)
            item_tmdb_id = item.get('tmdb_id')

            matches = (item_query == norm_q)
            if not matches and q_is_tv and item_is_tv:
                if target_tmdb_id and item_tmdb_id and target_tmdb_id == item_tmdb_id:
                    if q_ep_code and item.get('episode_code') == q_ep_code:
                        matches = True
                elif q_match and item_match and q_match == item_match:
                    if q_ep_code and item.get('episode_code') == q_ep_code:
                        matches = True

            if matches:
                item['is_watched'] = bool(is_watched)
                item['updated_at'] = now
                s_info = item.get('series_info')
                if is_watched:
                    item['last_played_at'] = now
                    if isinstance(s_info, dict):
                        if q_ep_code:
                            w_eps = set(s_info.get('watched_episodes', []))
                            w_eps.add(q_ep_code)
                            s_info['watched_episodes'] = sorted(w_eps)
                        if q_season is not None:
                            s_info['last_watched_season'] = q_season
                        if q_episode is not None:
                            s_info['last_watched_episode'] = q_episode
                else:
                    if isinstance(s_info, dict) and q_ep_code and q_ep_code in s_info.get('watched_episodes', []):
                        s_info['watched_episodes'] = [c for c in s_info['watched_episodes'] if c != q_ep_code]
                updated = True

    if not updated and is_watched:
        new_item = {
            'query': str(query).strip(),
            'title': None,
            'year': None,
            'plot': '',
            'genres': [],
            'rating': None,
            'runtime': None,
            'poster': None,
            'fanart': None,
            'tmdb_id': target_tmdb_id,
            'media_type': 'tvshow' if q_is_tv else 'movie',
            'ws_base': q_ws_base,
            'season': q_season if q_is_tv else None,
            'episode': q_episode if q_is_tv else None,
            'episode_code': q_ep_code if q_is_tv else None,
            'identified_at': None,
            'is_watched': True,
            'last_played_at': now,
            'updated_at': now,
            'added_at': now
        }
        if q_is_tv:
            new_item['series_info'] = {
                'ws_base': q_ws_base,
                'season': q_season,
                'episode': q_episode,
                'episode_code': q_ep_code,
                'last_watched_season': q_season,
                'last_watched_episode': q_episode,
                'watched_episodes': [q_ep_code] if q_ep_code else []
            }
        history_items.insert(0, new_item)
        updated = True

    if updated:
        _save_history(history_items)
    return updated


def delete_from_history(query):
    if not query:
        return
    query_str = str(query).strip()
    norm_q = query_str.lower()

    # 1. Zjistit cíl a metadata
    target_item = get_history_item(query_str)
    q_ws_base, q_season, q_episode, _ = parse_episode_info(query_str)

    target_tmdb_id = target_item.get('tmdb_id') if target_item else None
    try:
        target_tmdb_id = int(target_tmdb_id) if target_tmdb_id and str(target_tmdb_id).strip().lower() not in ('none', '', '0') else None
    except (ValueError, TypeError):
        target_tmdb_id = None

    target_media_type = (target_item.get('media_type') if target_item else None) or ('tvshow' if is_series(query_str) or q_season is not None else 'movie')
    target_ws_base = (target_item.get('ws_base') if target_item else None) or q_ws_base or get_base_name(query_str)

    target_keys = set()
    if target_item:
        target_keys.update(_extract_candidate_names(target_item))
    if query_str:
        k = normalize_match_key(query_str)
        if k:
            target_keys.add(k)
    if target_ws_base:
        k = normalize_match_key(target_ws_base)
        if k:
            target_keys.add(k)

    # 2. Načíst všechny surové položky z HISTORY_FILE
    raw_items = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    raw_items = loaded
        except Exception as e:
            xbmc.log(f"StreamContinuum History: Error reading history file in delete_from_history: {e}", xbmc.LOGWARNING)
            raw_items = []

    remaining_items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        if item.get('is_deleted'):
            continue

        it_q = str(item.get('query', '')).strip()
        norm_it_q = it_q.lower()
        it_tmdb = item.get('tmdb_id')
        try:
            it_tmdb = int(it_tmdb) if it_tmdb and str(it_tmdb).strip().lower() not in ('none', '', '0') else None
        except (ValueError, TypeError):
            it_tmdb = None

        it_type = item.get('media_type')
        it_ws = item.get('ws_base') or get_base_name(it_q)

        matches = False
        if norm_it_q == norm_q:
            matches = True
        elif target_tmdb_id and it_tmdb:
            matches = (target_tmdb_id == it_tmdb)
        elif (target_media_type == 'tvshow' or it_type == 'tvshow' or is_series(it_q) or is_series(query_str)):
            if target_ws_base and it_ws and normalize_match_key(target_ws_base) == normalize_match_key(it_ws):
                matches = True
            elif target_keys and bool(target_keys & set(_extract_candidate_names(item))):
                matches = True
            elif normalize_match_key(it_q) and normalize_match_key(query_str) and normalize_match_key(it_q) == normalize_match_key(query_str):
                matches = True
        else:
            if target_keys and bool(target_keys & set(_extract_candidate_names(item))):
                matches = True
            elif normalize_match_key(it_q) and normalize_match_key(query_str) and normalize_match_key(it_q) == normalize_match_key(query_str):
                matches = True

        if not matches:
            remaining_items.append(item)

    # 3. Zaznamenat náhrobek
    now = int(time.time())
    new_tombstone = {
        'is_deleted': True,
        'deleted_at': now,
        'query': '',
        'deleted_query': query_str,
        'ws_base': target_ws_base or get_base_name(query_str),
        'tmdb_id': target_tmdb_id,
        'media_type': target_media_type,
        'match_keys': sorted(list(target_keys))
    }

    current_tombstones = load_tombstones()
    updated_tombstones = merge_tombstones(current_tombstones, [new_tombstone])
    save_tombstones(updated_tombstones)

    # 4. Uložit pročištěnou historii včetně náhrobků
    _save_history(remaining_items, tombstones=updated_tombstones)
    xbmc.log(f"StreamContinuum History: Deleted '{query_str}' from history (recorded tombstone at {now})", xbmc.LOGINFO)


def update_history_item(old_query, new_query):
    if not old_query or not new_query:
        return
    remove_matching_tombstones(new_query)
    history_items = get_history(deduplicate=True)
    now = int(time.time())
    norm_old = str(old_query).strip().lower()
    old_match = normalize_match_key(old_query)
    ws_base, season, episode, ep_code = parse_episode_info(new_query)

    updated = False
    for item in history_items:
        item_q = str(item.get('query', '')).strip()
        if item_q == str(old_query).strip() or item_q.lower() == norm_old or (old_match and normalize_match_key(item_q) == old_match):
            item['query'] = new_query
            item['ws_base'] = ws_base
            item['season'] = season
            item['episode'] = episode
            item['episode_code'] = ep_code
            item['last_played_at'] = now
            item['updated_at'] = now
            updated = True
            break
    if updated:
        _save_history(history_items)


def update_history_with_tmdb_data(original_query, tmdb_data):
    if not original_query:
        return False
    history_items = get_history(deduplicate=True)
    updated = False
    now = int(time.time())
    norm_orig = str(original_query).strip().lower()
    orig_match = normalize_match_key(original_query)
    orig_base = get_base_name(original_query).strip()

    clean_title = sanitize_title(tmdb_data.get('title'))
    if has_non_latin(clean_title) or not clean_title:
        clean_title = orig_base or original_query

    for item in history_items:
        item_query = str(item.get('query', '')).strip().lower()
        item_match = normalize_match_key(item.get('query', ''))
        if item_query == norm_orig or str(item.get('query', '')).strip() == str(original_query).strip() or (orig_match and item_match == orig_match):
            item['title'] = clean_title
            item['year'] = tmdb_data.get('year')
            item['plot'] = tmdb_data.get('plot')
            item['genres'] = tmdb_data.get('genres', [])
            item['rating'] = tmdb_data.get('rating')
            item['runtime'] = tmdb_data.get('runtime')
            item['poster'] = tmdb_data.get('poster')
            item['fanart'] = tmdb_data.get('fanart')
            item['tmdb_id'] = tmdb_data.get('tmdb_id')
            item['media_type'] = tmdb_data.get('media_type')
            item['identified_at'] = now
            item['updated_at'] = now
            updated = True

    if not updated and original_query:
        ws_base, season, episode, ep_code = parse_episode_info(original_query)
        new_item = {
            'query': original_query,
            'title': clean_title,
            'year': tmdb_data.get('year'),
            'plot': tmdb_data.get('plot'),
            'genres': tmdb_data.get('genres', []),
            'rating': tmdb_data.get('rating'),
            'runtime': tmdb_data.get('runtime'),
            'poster': tmdb_data.get('poster'),
            'fanart': tmdb_data.get('fanart'),
            'tmdb_id': tmdb_data.get('tmdb_id'),
            'media_type': tmdb_data.get('media_type'),
            'ws_base': ws_base,
            'season': season,
            'episode': episode,
            'episode_code': ep_code,
            'identified_at': now,
            'is_watched': True,
            'last_played_at': now,
            'updated_at': now,
            'added_at': now
        }
        history_items.insert(0, new_item)
        updated = True
    if updated:
        _save_history(history_items)
    return updated


_last_check_next_episodes_time = 0


def _get_watchlist_check_interval():
    try:
        val = ADDON.getSetting('watchlist_check_interval')
        idx = int(val) if str(val).isdigit() else 3
        if idx == 0:
            return 60
        elif idx == 1:
            return 6 * 3600
        elif idx == 2:
            return 12 * 3600
        elif idx == 3:
            return 24 * 3600
        elif idx == 4:
            return 1000000000
    except Exception:
        pass
    return 24 * 3600


def _get_last_watchlist_check_ts():
    try:
        ts_str = ADDON.getSetting('watchlist_last_check_ts')
        if ts_str and str(ts_str).isdigit():
            return int(ts_str)
    except Exception:
        pass
    try:
        state_file = os.path.join(PROFILE_DIR, 'history_state.json')
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                st = json.load(f)
                return int(st.get('watchlist_last_check_ts', 0))
    except Exception:
        pass
    return 0


def _set_last_watchlist_check_ts(ts):
    global _last_check_next_episodes_time
    _last_check_next_episodes_time = int(ts)
    try:
        ADDON.setSetting('watchlist_last_check_ts', str(int(ts)))
    except Exception:
        pass
    try:
        state_file = os.path.join(PROFILE_DIR, 'history_state.json')
        st = {}
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    st = json.load(f)
            except Exception:
                st = {}
        st['watchlist_last_check_ts'] = int(ts)
        temp_file = f"{state_file}.{os.getpid()}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(st, f)
        os.replace(temp_file, state_file)
    except Exception:
        pass


def check_and_update_next_episodes(force=False, target_tmdb_id=None):
    global _last_check_next_episodes_time
    if tmdb is None:
        return False

    now_ts = int(time.time())
    # Throttling / mezipaměť: pokud nejde o vynucenou kontrolu ani o konkrétní ID, nespouštět častěji než zvolený interval.
    # Pokud však v historii existuje aktivní zhlédnutý seriál, který dosud nemá žádný navazující díl ve watchlistu,
    # throttling se vynechá a kontrola se provede okamžitě.
    if not force and target_tmdb_id is None:
        has_missing_next = False
        try:
            cached_history = get_history(deduplicate=True)
            watched_series = [
                it for it in cached_history
                if (it.get('media_type') in ('tvshow', 'tv', 'show') or is_series(it.get('query')) or (it.get('season') is not None and it.get('episode') is not None))
                and it.get('is_watched', True)
                and not it.get('is_series_completed')
            ]
            unwatched_series = [
                it for it in cached_history
                if (it.get('media_type') in ('tvshow', 'tv', 'show') or is_series(it.get('query')))
                and not it.get('is_watched', True)
            ]
            unwatched_ids = {it.get('tmdb_id') for it in unwatched_series if it.get('tmdb_id')}
            unwatched_names = {normalize_match_key(it.get('ws_base') or it.get('query')) for it in unwatched_series if (it.get('ws_base') or it.get('query'))}

            for ws in watched_series:
                w_tid = ws.get('tmdb_id')
                w_name = normalize_match_key(ws.get('ws_base') or ws.get('query'))
                if (w_tid and w_tid in unwatched_ids) or (w_name and w_name in unwatched_names):
                    continue
                has_missing_next = True
                break
        except Exception:
            has_missing_next = False

        if not has_missing_next:
            last_check_ts = _get_last_watchlist_check_ts()
            if last_check_ts <= 0:
                last_check_ts = _last_check_next_episodes_time
            interval = _get_watchlist_check_interval()
            if (now_ts - last_check_ts) < interval:
                xbmc.log(f"StreamContinuum History: Watchlist check throttled by cache (last check: {now_ts - last_check_ts}s ago, interval: {interval}s)", xbmc.LOGDEBUG)
                return False

    try:
        all_items = get_history(deduplicate=True)
        if not all_items:
            return False

        today = datetime.date.today()
        new_watchlist_entries = []
        generated_tmdb_ids = set()
        generated_names = set()
        items_modified_meta = False

        for item in all_items:
            is_tv = (
                item.get('media_type') in ('tvshow', 'tv', 'show')
                or is_series(item.get('query'))
                or (item.get('season') is not None and item.get('episode') is not None)
            )
            if not is_tv or not item.get('is_watched', True):
                continue

            # Přeskočit již kompletně ukončené a dokoukané seriály
            if item.get('is_series_completed'):
                continue

            last_s = item.get('season')
            last_e = item.get('episode')
            s_info = item.get('series_info') or {}
            if last_s is None and s_info.get('last_watched_season') is not None:
                last_s = s_info.get('last_watched_season')
            if last_e is None and s_info.get('last_watched_episode') is not None:
                last_e = s_info.get('last_watched_episode')

            if last_s is None or last_e is None:
                continue

            ws_base = item.get('ws_base') or get_base_name(item.get('query', ''))
            tmdb_id = item.get('tmdb_id')
            try:
                tmdb_id = int(tmdb_id) if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0') else None
            except (ValueError, TypeError):
                tmdb_id = None

            # Pokud byl specifikován konkrétní target_tmdb_id, zpracovat prioritně pouze jej
            if target_tmdb_id is not None:
                try:
                    if int(target_tmdb_id) != tmdb_id:
                        continue
                except (ValueError, TypeError):
                    continue

            # Kontrola, zda již seriál má nezhlédnutou navazující epizodu ve watchlistu
            already_in_watchlist = False
            watched_codes_check = set(s_info.get('watched_episodes', []))
            for u_cand in all_items:
                if u_cand.get('is_watched', True):
                    continue
                u_is_tv = u_cand.get('media_type') in ('tvshow', 'tv', 'show') or is_series(u_cand.get('query'))
                if not u_is_tv:
                    continue

                u_tid = u_cand.get('tmdb_id')
                try:
                    u_tid = int(u_tid) if u_tid and str(u_tid).strip().lower() not in ('none', '', '0') else None
                except (ValueError, TypeError):
                    u_tid = None

                is_same_series = False
                if tmdb_id and u_tid:
                    is_same_series = (tmdb_id == u_tid)
                else:
                    u_wb = normalize_match_key(u_cand.get('ws_base') or u_cand.get('query'))
                    s_wb = normalize_match_key(ws_base) if ws_base else None
                    if u_wb and s_wb and u_wb == s_wb:
                        is_same_series = True
                    else:
                        u_cands = set(_extract_candidate_names(u_cand))
                        s_cands = set(_extract_candidate_names(item))
                        if u_cands.intersection(s_cands):
                            is_same_series = True

                if is_same_series:
                    u_s = u_cand.get('season')
                    u_e = u_cand.get('episode')
                    u_code = u_cand.get('episode_code')
                    if u_s is not None and u_e is not None:
                        # Nezhlédnutá epizoda je skutečně navazující pouze pokud je > (last_s, last_e) a dosud nebyla zhlédnuta
                        if (u_s, u_e) > (last_s, last_e) and (not u_code or u_code not in watched_codes_check):
                            already_in_watchlist = True
                            break
                    elif not u_code or u_code not in watched_codes_check:
                        already_in_watchlist = True
                        break

            if (tmdb_id and tmdb_id in generated_tmdb_ids) or (ws_base and normalize_match_key(ws_base) in generated_names):
                already_in_watchlist = True

            if already_in_watchlist:
                continue

            # Pokud chybí tmdb_id, pokusit se o dohledání ze všech možných kandidátních názvů i jejich expanzí
            if not tmdb_id:
                search_candidates = []
                if item.get('title'):
                    search_candidates.append(item.get('title'))
                if ws_base:
                    search_candidates.append(ws_base)
                for part in re.split(r'\s*[/\\|]+\s*', ws_base or ''):
                    p_clean = get_base_name(part)
                    if p_clean and p_clean not in search_candidates:
                        search_candidates.append(p_clean)
                for cn in _extract_candidate_names(item):
                    if cn and cn not in search_candidates:
                        search_candidates.append(cn)

                expanded_cands = []
                for sc in search_candidates:
                    for exp in expand_abbreviations(sc):
                        if exp not in search_candidates and exp not in expanded_cands:
                            expanded_cands.append(exp)
                search_candidates.extend(expanded_cands)

                for sc in search_candidates:
                    sc_clean = re.sub(r'\s*\(?\d{4}\)?$', '', str(sc)).strip()
                    if not sc_clean:
                        continue
                    try:
                        res = tmdb.search_tmdb(sc_clean)
                        for r in res:
                            if r.get('type') == 'show' and r.get('id'):
                                tmdb_id = int(r.get('id'))
                                item['tmdb_id'] = tmdb_id
                                item['identified_at'] = int(time.time())
                                if r.get('clean_title') or r.get('title'):
                                    ct = sanitize_title(r.get('clean_title') or r.get('title'))
                                    if ct and not has_non_latin(ct):
                                        item['title'] = ct
                                items_modified_meta = True
                                break
                    except Exception:
                        pass
                    if tmdb_id:
                        break

            if not tmdb_id:
                continue

            try:
                show_details = tmdb.get_show_seasons(tmdb_id)
                if not show_details or 'seasons' not in show_details:
                    continue

                curr_season_eps = tmdb.get_season_episodes(tmdb_id, last_s) or []
                watched_codes = set((item.get('series_info') or {}).get('watched_episodes', []))

                # Hledání nejbližší následující epizody v aktuální sérii, která dosud nebyla zhlédnuta
                higher_eps_curr = [
                    e for e in curr_season_eps
                    if (e.get('episode_number') or 0) > last_e
                    and f"S{last_s:02d}E{int(e.get('episode_number', 0)):02d}" not in watched_codes
                ]
                higher_eps_curr.sort(key=lambda x: x.get('episode_number') or 0)
                next_ep_obj = higher_eps_curr[0] if higher_eps_curr else None
                target_season = last_s
                target_episode = (next_ep_obj.get('episode_number') or (last_e + 1)) if next_ep_obj else (last_e + 1)

                next_season_eps = []
                if not next_ep_obj:
                    # Hledání následující série (season_number > last_s a season_number > 0)
                    all_seasons = show_details.get('seasons', [])
                    higher_seasons = [s for s in all_seasons if (s.get('season_number') or 0) > last_s and (s.get('season_number') or 0) > 0]
                    higher_seasons.sort(key=lambda x: x.get('season_number') or 0)
                    for next_season_obj in higher_seasons:
                        target_season = next_season_obj.get('season_number')
                        all_ns_eps = tmdb.get_season_episodes(tmdb_id, target_season) or []
                        unwatched_ns_eps = [
                            e for e in all_ns_eps
                            if f"S{target_season:02d}E{int(e.get('episode_number', 0)):02d}" not in watched_codes
                        ]
                        unwatched_ns_eps.sort(key=lambda x: x.get('episode_number') or 0)
                        if unwatched_ns_eps:
                            next_season_eps = unwatched_ns_eps
                            next_ep_obj = unwatched_ns_eps[0]
                            target_episode = next_ep_obj.get('episode_number') or 1
                            break

                if not next_ep_obj:
                    show_status = str(show_details.get('status') or '').strip().lower()
                    if show_status in ('ended', 'canceled', 'ukončeno'):
                        item['is_series_completed'] = True
                        items_modified_meta = True

                if next_ep_obj:
                    air_date_str = next_ep_obj.get('air_date')
                    is_aired = False
                    if air_date_str and len(str(air_date_str).strip()) >= 10:
                        try:
                            air_dt = datetime.datetime.strptime(str(air_date_str).strip()[:10], '%Y-%m-%d').date()
                            if air_dt <= today:
                                is_aired = True
                        except Exception:
                            is_aired = False

                    # Robustní fallback, pokud TMDb u dané epizody nemá vyplněný air_date:
                    if not is_aired and (not air_date_str or not str(air_date_str).strip()):
                        # 1. Zkontrolovat datum premiéry celé řady
                        season_meta = next((s for s in show_details.get('seasons', []) if s.get('season_number') == target_season), None)
                        s_air_date = season_meta.get('air_date') if season_meta else None
                        if s_air_date and len(str(s_air_date).strip()) >= 10:
                            try:
                                s_dt = datetime.datetime.strptime(str(s_air_date).strip()[:10], '%Y-%m-%d').date()
                                if s_dt <= today:
                                    is_aired = True
                            except Exception:
                                pass

                        # 2. Zkontrolovat, zda jiná epizoda v téže řadě (od daného čísla výše) již byla odvysílána
                        if not is_aired:
                            eps_in_season = curr_season_eps if target_season == last_s else next_season_eps
                            for other_ep in eps_in_season:
                                if (other_ep.get('episode_number') or 0) >= target_episode:
                                    o_air = other_ep.get('air_date')
                                    if o_air and len(str(o_air).strip()) >= 10:
                                        try:
                                            o_dt = datetime.datetime.strptime(str(o_air).strip()[:10], '%Y-%m-%d').date()
                                            if o_dt <= today:
                                                is_aired = True
                                                break
                                        except Exception:
                                            pass

                        # 3. Zkontrolovat status seriálu a rok vydání
                        if not is_aired:
                            show_year = show_details.get('year')
                            show_status = str(show_details.get('status') or '').strip().lower()
                            if show_status in ('ended', 'canceled', 'ukončeno'):
                                is_aired = True
                            elif show_year and isinstance(show_year, int) and show_year < today.year:
                                is_aired = True

                    target_code = f"S{target_season:02d}E{target_episode:02d}"
                    if is_aired and target_code not in watched_codes:
                        next_query = f"{ws_base} {target_code}"
                        full_show_title = show_details.get('title') or item.get('title') or ws_base
                        plot_text = next_ep_obj.get('overview') or show_details.get('overview') or ''

                        # Výpočet spolehlivé délky epizody: z epizody, ze seriálu, z ostatních epizod řady, nebo z historie
                        ep_runtime = next_ep_obj.get('runtime') or 0
                        if not ep_runtime:
                            ep_runtime = show_details.get('runtime') or 0
                        if not ep_runtime:
                            eps_for_rt = curr_season_eps if target_season == last_s else next_season_eps
                            for e_it in eps_for_rt:
                                r_val = e_it.get('runtime') or 0
                                if r_val > 0:
                                    ep_runtime = r_val
                                    break
                        if not ep_runtime:
                            ep_runtime = item.get('runtime') or 0

                        tmdb_data = {
                            'tmdb_id': tmdb_id,
                            'media_type': 'tvshow',
                            'title': full_show_title,
                            'year': int(str(air_date_str)[:4]) if (air_date_str and len(str(air_date_str)) >= 4) else show_details.get('year'),
                            'plot': plot_text,
                            'poster': show_details.get('poster') or item.get('poster'),
                            'still': next_ep_obj.get('still') if next_ep_obj else None,
                            'fanart': show_details.get('fanart') or item.get('fanart'),
                            'rating': next_ep_obj.get('rating') or show_details.get('rating'),
                            'runtime': ep_runtime,
                            'genres': show_details.get('genres', [])
                        }
                        new_watchlist_entries.append((next_query, tmdb_data))
                        if tmdb_id:
                            generated_tmdb_ids.add(tmdb_id)
                        if ws_base:
                            wb = normalize_match_key(ws_base)
                            if wb:
                                generated_names.add(wb)
            except Exception as check_e:
                xbmc.log(f"StreamContinuum History: Error checking next episode for {ws_base}: {check_e}", xbmc.LOGWARNING)

        # Uložit všechny nově vygenerované díly najednou
        if new_watchlist_entries:
            current_history = get_history(deduplicate=True)
            now_ts = int(time.time())
            for n_q, t_data in new_watchlist_entries:
                remove_matching_tombstones(n_q)
                w_base, s_num, e_num, e_code = parse_episode_info(n_q)
                item_obj = {
                    'query': n_q,
                    'title': sanitize_title(t_data.get('title')) if (t_data and t_data.get('title')) else None,
                    'year': t_data.get('year') if t_data else None,
                    'plot': t_data.get('plot', '') if t_data else '',
                    'genres': t_data.get('genres', []) if t_data else [],
                    'rating': t_data.get('rating') if t_data else None,
                    'runtime': t_data.get('runtime') if t_data else None,
                    'poster': t_data.get('poster') if t_data else None,
                    'still': t_data.get('still') if t_data else None,
                    'fanart': t_data.get('fanart') if t_data else None,
                    'tmdb_id': t_data.get('tmdb_id') if t_data else None,
                    'media_type': 'tvshow',
                    'ws_base': w_base,
                    'season': s_num,
                    'episode': e_num,
                    'episode_code': e_code,
                    'identified_at': now_ts,
                    'is_watched': False,
                    'last_played_at': 0,
                    'updated_at': now_ts,
                    'added_at': now_ts
                }
                current_history.insert(0, item_obj)
            if items_modified_meta:
                for c_it in current_history:
                    for a_it in all_items:
                        if c_it.get('query') == a_it.get('query'):
                            if a_it.get('tmdb_id') and not c_it.get('tmdb_id'):
                                c_it['tmdb_id'] = a_it.get('tmdb_id')
                                c_it['identified_at'] = a_it.get('identified_at')
                            if a_it.get('title') and not c_it.get('title'):
                                c_it['title'] = a_it.get('title')
                            if a_it.get('is_series_completed'):
                                c_it['is_series_completed'] = True
            _save_history(current_history)
            if target_tmdb_id is None:
                _set_last_watchlist_check_ts(now_ts)
            else:
                _last_check_next_episodes_time = now_ts
            return True
        elif items_modified_meta:
            try:
                current_saved = get_history(deduplicate=False)
                for c_it in current_saved:
                    for a_it in all_items:
                        if c_it.get('query') == a_it.get('query'):
                            if a_it.get('tmdb_id') and not c_it.get('tmdb_id'):
                                c_it['tmdb_id'] = a_it.get('tmdb_id')
                                c_it['identified_at'] = a_it.get('identified_at')
                            if a_it.get('title') and not c_it.get('title'):
                                c_it['title'] = a_it.get('title')
                            if a_it.get('is_series_completed'):
                                c_it['is_series_completed'] = True
                _save_history(current_saved)
            except Exception:
                pass

        if target_tmdb_id is None:
            _set_last_watchlist_check_ts(now_ts)
        else:
            _last_check_next_episodes_time = now_ts
        return False
    except Exception as e:
        xbmc.log(f"StreamContinuum History: check_and_update_next_episodes failed: {e}", xbmc.LOGERROR)
        return False


def clear_history():
    if os.path.exists(HISTORY_FILE):
        try:
            os.remove(HISTORY_FILE)
            xbmc.log(f"StreamContinuum History: Cleared history file: {HISTORY_FILE}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"StreamContinuum History: Error clearing history file: {e}", xbmc.LOGERROR)
    if os.path.exists(TOMBSTONES_FILE):
        try:
            os.remove(TOMBSTONES_FILE)
            xbmc.log(f"StreamContinuum History: Cleared tombstones file: {TOMBSTONES_FILE}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"StreamContinuum History: Error clearing tombstones file: {e}", xbmc.LOGERROR)

