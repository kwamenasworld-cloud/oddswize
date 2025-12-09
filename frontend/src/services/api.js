import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STATIC_DATA_URL = '/data/odds_data.json';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

// Try to fetch from static JSON file (updated by auto_scanner.py)
const fetchStaticData = async () => {
  try {
    const response = await axios.get(STATIC_DATA_URL, { timeout: 5000 });
    return response.data;
  } catch (error) {
    console.log('Static data not available');
    return null;
  }
};

// Get all matches with odds comparison
export const getMatches = async (limit = 100, offset = 0, minBookmakers = 2) => {
  try {
    // Try API first
    const response = await api.get('/api/matches', {
      params: { limit, offset, min_bookmakers: minBookmakers },
    });
    return response.data;
  } catch (error) {
    // Fallback to static data
    console.log('API unavailable, trying static data...');
    const staticData = await fetchStaticData();
    if (staticData && staticData.matches) {
      return staticData.matches.slice(offset, offset + limit);
    }
    throw error;
  }
};

// Get arbitrage opportunities
export const getArbitrage = async (bankroll = 100) => {
  try {
    const response = await api.get('/api/arbitrage', {
      params: { bankroll },
    });
    return response.data;
  } catch (error) {
    // Fallback to static data
    const staticData = await fetchStaticData();
    if (staticData && staticData.arbitrage) {
      return staticData.arbitrage;
    }
    throw error;
  }
};

// Get scanner status
export const getStatus = async () => {
  try {
    const response = await api.get('/api/status');
    return response.data;
  } catch (error) {
    // Fallback to static data
    const staticData = await fetchStaticData();
    if (staticData && staticData.stats) {
      return {
        last_scan: staticData.last_updated,
        ...staticData.stats
      };
    }
    throw error;
  }
};

// Trigger a new scan
export const triggerScan = async () => {
  const response = await api.post('/api/scan');
  return response.data;
};

// Get bookmaker list
export const getBookmakers = async () => {
  const response = await api.get('/api/bookmakers');
  return response.data;
};

// Get last update time from static data
export const getLastUpdate = async () => {
  const staticData = await fetchStaticData();
  if (staticData) {
    return {
      lastUpdated: staticData.last_updated,
      nextUpdate: staticData.next_update
    };
  }
  return null;
};

export default api;
