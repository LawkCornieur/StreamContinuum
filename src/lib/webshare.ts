import axios from 'axios';

/**
 * Webshare.cz API Service
 * Documentation: https://webshare.cz/api/
 */

const WEBSHARE_API_URL = 'https://webshare.cz/api';

const webshareClient = axios.create({
  baseURL: WEBSHARE_API_URL,
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
});

export const webshareService = {
  /**
   * Login to Webshare and get a token
   */
  login: async (username: string, password_or_hash: string) => {
    try {
      // Webshare API expects data in a specific format
      // Usually it's a POST with username and password_or_hash (SHA1 of password)
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password_or_hash);
      params.append('digest', ''); // Optional digest for better security if needed

      const response = await webshareClient.post('/login/', params);
      
      // Webshare returns XML by default or JSON if requested/configured
      // For simplicity in this prototype, we assume JSON or handle the response
      if (response.data && response.data.status === 'OK') {
        return {
          token: response.data.token,
          username: response.data.username,
          vip: response.data.vip === '1',
        };
      }
      return null;
    } catch (error) {
      console.error('Webshare login error:', error);
      return null;
    }
  },

  /**
   * Check if the token is still valid
   */
  checkToken: async (token: string) => {
    try {
      const params = new URLSearchParams();
      params.append('wst', token);
      const response = await webshareClient.post('/user_data/', params);
      return response.data && response.data.status === 'OK';
    } catch (error) {
      return false;
    }
  },

  /**
   * Search for files on Webshare
   */
  search: async (query: string, token?: string) => {
    try {
      const params = new URLSearchParams();
      params.append('search', query);
      if (token) params.append('wst', token);
      
      const response = await webshareClient.post('/search/', params);
      return response.data;
    } catch (error) {
      console.error('Webshare search error:', error);
      return null;
    }
  }
};
