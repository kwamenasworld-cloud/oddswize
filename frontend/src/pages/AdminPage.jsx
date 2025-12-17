import { useEffect, useState } from 'react';
import { getCanonicalLeagues, getUnmapped, approveMapping, getUnmappedStats } from '../services/canonical';

function AdminPage() {
  const [adminKey, setAdminKey] = useState('');
  const [leagues, setLeagues] = useState([]);
  const [unmapped, setUnmapped] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadData();
  }, [adminKey]);

  const loadData = async () => {
    setLoading(true);
    setMessage('');
    try {
      const [lg, um, st] = await Promise.all([
        getCanonicalLeagues(),
        getUnmapped(adminKey),
        getUnmappedStats(adminKey),
      ]);
      setLeagues(lg || []);
      setUnmapped(um || []);
      setStats(st || null);
    } catch (e) {
      setMessage(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (item, leagueId) => {
    try {
      await approveMapping(item.provider, item.raw_league_id || 'unknown', leagueId, item.raw_league_name, adminKey);
      setMessage('Mapping approved. Reloading...');
      await loadData();
    } catch (e) {
      setMessage(`Approve failed: ${e.message}`);
    }
  };

  return (
    <div className="admin-page" style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Admin: League Mappings</h1>

      <div style={{ marginBottom: '12px' }}>
        <label>Admin Key: </label>
        <input
          type="password"
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
          placeholder="Enter ADMIN_API_KEY"
          style={{ padding: '6px 10px', width: '260px' }}
        />
        <button onClick={loadData} style={{ marginLeft: '8px', padding: '6px 12px' }}>Reload</button>
      </div>

      {stats && (
        <div style={{ marginBottom: '12px' }}>
          <strong>Unmapped:</strong> {stats.unmapped} / {stats.total_fixtures} (rate {(stats.unmapped_rate * 100).toFixed(2)}%)
        </div>
      )}

      {message && <div style={{ marginBottom: '12px', color: '#c00' }}>{message}</div>}

      {loading && <div>Loading...</div>}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>Provider</th>
            <th>Fixture</th>
            <th>Raw League</th>
            <th>Confidence</th>
            <th>Created</th>
            <th>Map To</th>
          </tr>
        </thead>
        <tbody>
          {unmapped.map((item, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
              <td>{item.provider}</td>
              <td>{item.home_team} vs {item.away_team}</td>
              <td>{item.raw_league_name}</td>
              <td>{item.confidence ? item.confidence.toFixed(2) : '-'}</td>
              <td>{item.created_at || ''}</td>
              <td>
                <select onChange={(e) => handleApprove(item, e.target.value)} defaultValue="">
                  <option value="">Select league...</option>
                  {leagues.map(l => (
                    <option key={l.league_id} value={l.league_id}>{l.display_name} ({l.country_code})</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default AdminPage;
