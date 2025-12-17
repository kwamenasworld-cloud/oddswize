const API_BASE = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000';

const fetchJson = async (path) => {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
};

export const getCanonicalLeagues = async () => {
  return fetchJson('/api/leagues');
};

export const getCanonicalFixtures = async (limit = 500, offset = 0) => {
  // limit/offset via query; backend supports offset/limit
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return fetchJson(`/api/fixtures?${params.toString()}`);
};

export const getUnmapped = async (adminKey) => {
  const params = adminKey ? `?admin_key=${encodeURIComponent(adminKey)}` : '';
  return fetchJson(`/api/unmapped${params}`);
};

export const approveMapping = async (provider, providerLeagueId, leagueId, providerName, adminKey) => {
  const params = new URLSearchParams({ provider, provider_league_id: providerLeagueId, league_id: leagueId });
  if (providerName) params.set('provider_name', providerName);
  if (adminKey) params.set('admin_key', adminKey);
  const res = await fetch(`${API_BASE}/api/approve_mapping?${params.toString()}`, { method: 'POST' });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
};

export const getUnmappedStats = async (adminKey) => {
  const params = adminKey ? `?admin_key=${encodeURIComponent(adminKey)}` : '';
  return fetchJson(`/api/unmapped_stats${params}`);
};

export default {
  getCanonicalLeagues,
  getCanonicalFixtures,
  getUnmapped,
  approveMapping,
  getUnmappedStats,
};
