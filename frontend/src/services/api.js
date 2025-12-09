import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

// Get all matches with odds comparison
export const getMatches = async (limit = 100, offset = 0, minBookmakers = 2) => {
  const response = await api.get('/api/matches', {
    params: { limit, offset, min_bookmakers: minBookmakers },
  });
  return response.data;
};

// Get arbitrage opportunities
export const getArbitrage = async (bankroll = 100) => {
  const response = await api.get('/api/arbitrage', {
    params: { bankroll },
  });
  return response.data;
};

// Get scanner status
export const getStatus = async () => {
  const response = await api.get('/api/status');
  return response.data;
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

export default api;
