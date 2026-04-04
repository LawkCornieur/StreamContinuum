import axios from 'axios';

/**
 * Trakt.tv API Service
 * Handles communication with Trakt.tv
 * Note: Client ID and Secret should be in .env
 */

const TRAKT_API_URL = 'https://api.trakt.tv';

const traktClient = axios.create({
  baseURL: TRAKT_API_URL,
  headers: {
    'Content-Type': 'application/json',
    'trakt-api-version': '2',
  },
});

export const setTraktAuth = (clientId: string, accessToken?: string) => {
  traktClient.defaults.headers['trakt-api-key'] = clientId;
  if (accessToken) {
    traktClient.defaults.headers['Authorization'] = `Bearer ${accessToken}`;
  }
};

export const traktService = {
  search: async (query: string, type: 'movie' | 'show' = 'movie') => {
    try {
      const response = await traktClient.get(`/search/${type}`, {
        params: { query, extended: 'full' },
      });
      return response.data;
    } catch (error) {
      console.error('Trakt search error:', error);
      return [];
    }
  },

  getTrending: async (type: 'movies' | 'shows' = 'movies') => {
    try {
      const response = await traktClient.get(`/${type}/trending`, {
        params: { extended: 'full', limit: 20 },
      });
      return response.data;
    } catch (error) {
      console.error('Trakt trending error:', error);
      return [];
    }
  },

  getShowSeasons: async (id: string | number) => {
    try {
      const response = await traktClient.get(`/shows/${id}/seasons`, {
        params: { extended: 'full' },
      });
      return response.data;
    } catch (error) {
      console.error('Trakt seasons error:', error);
      return [];
    }
  },

  getSeasonEpisodes: async (id: string | number, season: number) => {
    try {
      const response = await traktClient.get(`/shows/${id}/seasons/${season}`, {
        params: { extended: 'full' },
      });
      return response.data;
    } catch (error) {
      console.error('Trakt episodes error:', error);
      return [];
    }
  },

  generateDeviceCode: async (clientId: string) => {
    try {
      const response = await axios.post(`${TRAKT_API_URL}/oauth/device/code`, {
        client_id: clientId,
      });
      return response.data; // { device_code, user_code, verification_url, expires_in, interval }
    } catch (error) {
      console.error('Trakt device code error:', error);
      return null;
    }
  },

  pollForDeviceToken: async (clientId: string, clientSecret: string, deviceCode: string) => {
    try {
      const response = await axios.post(`${TRAKT_API_URL}/oauth/device/token`, {
        code: deviceCode,
        client_id: clientId,
        client_secret: clientSecret,
      });
      return response.data; // { access_token, token_type, expires_in, refresh_token, scope, created_at }
    } catch (error) {
      // 400: Pending, 404: Not Found, 409: Already Used, 410: Expired, 418: Denied
      if (axios.isAxiosError(error) && error.response?.status === 400) {
        return { status: 'pending' };
      }
      console.error('Trakt device token error:', error);
      return { status: 'error', message: error instanceof Error ? error.message : 'Unknown error' };
    }
  },

  getNextEpisode: async (id: string | number, season: number, episode: number) => {
    // Logic to find the next episode
    // In a real Kodi addon, this would check the manifest or Trakt's progress API
    try {
      const episodes = await traktService.getSeasonEpisodes(id, season);
      const nextInSeason = episodes.find((e: any) => e.number === episode + 1);
      
      if (nextInSeason) return nextInSeason;

      // Check next season
      const nextSeasonEpisodes = await traktService.getSeasonEpisodes(id, season + 1);
      if (nextSeasonEpisodes && nextSeasonEpisodes.length > 0) {
        return nextSeasonEpisodes[0];
      }

      return null;
    } catch (error) {
      return null;
    }
  }
};
