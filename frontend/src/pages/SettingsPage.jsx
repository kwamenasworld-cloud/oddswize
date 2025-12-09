import { useState, useEffect } from 'react';
import {
  getPreferences,
  savePreferences,
  updateNotificationSetting,
  updateDisplaySetting,
  exportUserData,
  deleteUserData,
  getUser,
} from '../services/userPreferences';
import { BOOKMAKER_AFFILIATES } from '../config/affiliates';
import { BookmakerLogo } from '../components/BookmakerLogo';

// Available leagues for Ghana market
const AVAILABLE_LEAGUES = [
  'English Premier League',
  'La Liga',
  'Serie A',
  'Bundesliga',
  'Ligue 1',
  'UEFA Champions League',
  'UEFA Europa League',
  'Ghana Premier League',
  'Africa Cup of Nations',
];

// Available bookmakers
const AVAILABLE_BOOKMAKERS = Object.keys(BOOKMAKER_AFFILIATES);

export default function SettingsPage({ onClose, onLogout }) {
  const [prefs, setPrefs] = useState(getPreferences());
  const [user, setUser] = useState(getUser());
  const [activeTab, setActiveTab] = useState('favorites');
  const [saved, setSaved] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSave = () => {
    savePreferences(prefs);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const toggleLeague = (league) => {
    const newFavorites = prefs.favoriteLeagues.includes(league)
      ? prefs.favoriteLeagues.filter((l) => l !== league)
      : [...prefs.favoriteLeagues, league];
    setPrefs({ ...prefs, favoriteLeagues: newFavorites });
  };

  const toggleBookmaker = (bookmaker) => {
    const newBookmakers = prefs.defaultBookmakers.includes(bookmaker)
      ? prefs.defaultBookmakers.filter((b) => b !== bookmaker)
      : [...prefs.defaultBookmakers, bookmaker];
    setPrefs({ ...prefs, defaultBookmakers: newBookmakers });
  };

  const updateNotification = (key, value) => {
    setPrefs({
      ...prefs,
      notifications: { ...prefs.notifications, [key]: value },
    });
  };

  const updateDisplay = (key, value) => {
    setPrefs({
      ...prefs,
      display: { ...prefs.display, [key]: value },
    });
  };

  const handleExportData = () => {
    const data = exportUserData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `oddswize-data-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDeleteAccount = () => {
    if (confirmDelete) {
      deleteUserData();
      onLogout?.();
      onClose?.();
    } else {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content settings-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        <div className="settings-header">
          <h2>Settings</h2>
          {user && (
            <p className="settings-user">
              Signed in as <strong>{user.name || user.email || user.phone}</strong>
            </p>
          )}
        </div>

        <div className="settings-tabs">
          <button
            className={activeTab === 'favorites' ? 'active' : ''}
            onClick={() => setActiveTab('favorites')}
          >
            Favorites
          </button>
          <button
            className={activeTab === 'bookmakers' ? 'active' : ''}
            onClick={() => setActiveTab('bookmakers')}
          >
            Bookmakers
          </button>
          <button
            className={activeTab === 'notifications' ? 'active' : ''}
            onClick={() => setActiveTab('notifications')}
          >
            Notifications
          </button>
          <button
            className={activeTab === 'display' ? 'active' : ''}
            onClick={() => setActiveTab('display')}
          >
            Display
          </button>
          <button
            className={activeTab === 'account' ? 'active' : ''}
            onClick={() => setActiveTab('account')}
          >
            Account
          </button>
        </div>

        <div className="settings-content">
          {activeTab === 'favorites' && (
            <div className="settings-section">
              <h3>Favorite Leagues</h3>
              <p className="settings-hint">Select leagues to highlight and filter</p>
              <div className="settings-grid">
                {AVAILABLE_LEAGUES.map((league) => (
                  <label key={league} className="settings-checkbox">
                    <input
                      type="checkbox"
                      checked={prefs.favoriteLeagues.includes(league)}
                      onChange={() => toggleLeague(league)}
                    />
                    <span className="checkmark"></span>
                    {league}
                  </label>
                ))}
              </div>

              <h3 style={{ marginTop: '1.5rem' }}>Favorite Teams</h3>
              <p className="settings-hint">
                Add teams by clicking the star icon next to team names on the odds page
              </p>
              {prefs.favoriteTeams.length > 0 ? (
                <div className="favorite-teams-list">
                  {prefs.favoriteTeams.map((team) => (
                    <span key={team} className="favorite-team-tag">
                      {team}
                      <button
                        onClick={() =>
                          setPrefs({
                            ...prefs,
                            favoriteTeams: prefs.favoriteTeams.filter((t) => t !== team),
                          })
                        }
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="no-favorites">No favorite teams yet</p>
              )}
            </div>
          )}

          {activeTab === 'bookmakers' && (
            <div className="settings-section">
              <h3>Default Bookmakers</h3>
              <p className="settings-hint">Choose which bookmakers to show by default</p>
              <div className="bookmaker-grid">
                {AVAILABLE_BOOKMAKERS.map((bookmaker) => (
                  <label key={bookmaker} className="bookmaker-checkbox">
                    <input
                      type="checkbox"
                      checked={prefs.defaultBookmakers.includes(bookmaker)}
                      onChange={() => toggleBookmaker(bookmaker)}
                    />
                    <div className="bookmaker-option">
                      <BookmakerLogo bookmaker={bookmaker} size={32} />
                      <span>{BOOKMAKER_AFFILIATES[bookmaker]?.name || bookmaker}</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="settings-section">
              <h3>Notification Preferences</h3>
              <p className="settings-hint">Choose what alerts you want to receive</p>
              <div className="notification-options">
                <label className="settings-toggle">
                  <span>
                    <strong>Best Odds Alerts</strong>
                    <small>Get notified when odds significantly improve</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={prefs.notifications.bestOdds}
                    onChange={(e) => updateNotification('bestOdds', e.target.checked)}
                  />
                  <span className="toggle-slider"></span>
                </label>

                <label className="settings-toggle">
                  <span>
                    <strong>Big Edge Opportunities</strong>
                    <small>Alert when odds are 10%+ above market average</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={prefs.notifications.bigEdges}
                    onChange={(e) => updateNotification('bigEdges', e.target.checked)}
                  />
                  <span className="toggle-slider"></span>
                </label>

                <label className="settings-toggle">
                  <span>
                    <strong>Favorite Teams</strong>
                    <small>Notify when your favorite teams are playing</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={prefs.notifications.favoriteTeams}
                    onChange={(e) => updateNotification('favoriteTeams', e.target.checked)}
                  />
                  <span className="toggle-slider"></span>
                </label>

                <label className="settings-toggle">
                  <span>
                    <strong>Daily Digest</strong>
                    <small>Receive a daily summary of best opportunities</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={prefs.notifications.dailyDigest}
                    onChange={(e) => updateNotification('dailyDigest', e.target.checked)}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
            </div>
          )}

          {activeTab === 'display' && (
            <div className="settings-section">
              <h3>Display Settings</h3>

              <div className="settings-option">
                <label>Default View</label>
                <select
                  value={prefs.display.defaultView}
                  onChange={(e) => updateDisplay('defaultView', e.target.value)}
                >
                  <option value="all">All Matches</option>
                  <option value="favorites">Favorites Only</option>
                  <option value="edges">Best Edges</option>
                </select>
              </div>

              <div className="settings-option">
                <label>Odds Format</label>
                <select
                  value={prefs.display.oddsFormat}
                  onChange={(e) => updateDisplay('oddsFormat', e.target.value)}
                >
                  <option value="decimal">Decimal (1.50)</option>
                  <option value="fractional">Fractional (1/2)</option>
                  <option value="american">American (+150)</option>
                </select>
              </div>

              <label className="settings-toggle" style={{ marginTop: '1rem' }}>
                <span>
                  <strong>Show Probability</strong>
                  <small>Display implied probability alongside odds</small>
                </span>
                <input
                  type="checkbox"
                  checked={prefs.display.showProbability}
                  onChange={(e) => updateDisplay('showProbability', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          )}

          {activeTab === 'account' && (
            <div className="settings-section">
              <h3>Account</h3>

              <div className="account-actions">
                <button className="btn-secondary" onClick={handleExportData}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="7,10 12,15 17,10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Export My Data
                </button>

                <button
                  className={`btn-danger ${confirmDelete ? 'confirm' : ''}`}
                  onClick={handleDeleteAccount}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3,6 5,6 21,6" />
                    <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                  </svg>
                  {confirmDelete ? 'Click again to confirm' : 'Delete Account'}
                </button>
              </div>

              <p className="account-info">
                Member since: {user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : 'N/A'}
              </p>
            </div>
          )}
        </div>

        <div className="settings-footer">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave}>
            {saved ? 'Saved!' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
