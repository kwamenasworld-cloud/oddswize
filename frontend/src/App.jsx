import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useState, useEffect, lazy, Suspense } from 'react';
import { AccountModal, LoginButton, UserMenu } from './components/AccountModal';
import SettingsPage from './pages/SettingsPage';
import { getUser, logOut } from './services/userPreferences';

const HomePage = lazy(() => import('./pages/HomePage'));
const OddsPage = lazy(() => import('./pages/OddsPage'));
const BookmakersPage = lazy(() => import('./pages/BookmakersPage'));
const NewsPage = lazy(() => import('./pages/NewsPage'));
const ArticlePage = lazy(() => import('./pages/ArticlePage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));

function App() {
  const [authOpen, setAuthOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [user, setUser] = useState(() => getUser());
  const [prefsVersion, setPrefsVersion] = useState(0);

  return (
    <BrowserRouter>
      <div className="app">
        <Header
          user={user}
          onLogin={() => setAuthOpen(true)}
          onOpenSettings={() => setSettingsOpen(true)}
          onLogout={() => setUser(null)}
        />
        <main>
          <Suspense fallback={<div className="page-loading">Loading...</div>}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/odds" element={<OddsPage prefsVersion={prefsVersion} />} />
              <Route path="/bookmakers" element={<BookmakersPage />} />
              <Route path="/news" element={<NewsPage />} />
              <Route path="/news/:slug" element={<ArticlePage />} />
              <Route path="/admin" element={<AdminPage />} />
            </Routes>
          </Suspense>
        </main>
        <Footer />
        <AccountModal
          isOpen={authOpen}
          onClose={() => setAuthOpen(false)}
          onAuthChange={(nextUser) => setUser(nextUser)}
        />
        {settingsOpen && (
          <SettingsPage
            onClose={() => setSettingsOpen(false)}
            onLogout={() => setUser(null)}
            onPreferencesSaved={() => setPrefsVersion((prev) => prev + 1)}
          />
        )}
      </div>
    </BrowserRouter>
  );
}

function Header({ user, onLogin, onOpenSettings, onLogout }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const displayName = user?.name || user?.email?.split('@')[0] || user?.phone || 'User';

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.classList.add('menu-open');
    } else {
      document.body.classList.remove('menu-open');
    }

    // Cleanup on unmount
    return () => {
      document.body.classList.remove('menu-open');
    };
  }, [menuOpen]);

  return (
    <header className="header">
      <div className="header-top">
        <NavLink to="/" className="logo" aria-label="OddsWize home">
          <img src="/logo.png" alt="" className="logo-icon" />
          <span className="logo-text">Odds<span>Wize</span></span>
        </NavLink>

        <button
          className="mobile-menu-btn"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <span className={`hamburger ${menuOpen ? 'open' : ''}`}></span>
        </button>

        <nav className={`nav ${menuOpen ? 'nav-open' : ''}`}>
          <NavLink
            to="/"
            className={({ isActive }) => isActive ? 'active' : ''}
            onClick={() => setMenuOpen(false)}
            end
          >
            Home
          </NavLink>
          <NavLink
            to="/odds"
            className={({ isActive }) => isActive ? 'active' : ''}
            onClick={() => setMenuOpen(false)}
          >
            Odds
          </NavLink>
          <NavLink
            to="/bookmakers"
            className={({ isActive }) => isActive ? 'active' : ''}
            onClick={() => setMenuOpen(false)}
          >
            Bookmakers
          </NavLink>
          <NavLink
            to="/news"
            className={({ isActive }) => isActive ? 'active' : ''}
            onClick={() => setMenuOpen(false)}
          >
            News
          </NavLink>
          <a
            href="/guides/odds-calculator/"
            onClick={() => setMenuOpen(false)}
          >
            Calculator
          </a>
          <div className="nav-account">
            {user ? (
              <>
                <span className="nav-account-name">Signed in as {displayName}</span>
                <button
                  type="button"
                  className="nav-account-btn"
                  onClick={() => {
                    onOpenSettings?.();
                    setMenuOpen(false);
                  }}
                >
                  Settings
                </button>
                <button
                  type="button"
                  className="nav-account-btn secondary"
                  onClick={() => {
                    logOut();
                    onLogout?.();
                    setMenuOpen(false);
                  }}
                >
                  Sign Out
                </button>
              </>
            ) : (
              <button
                type="button"
                className="nav-account-btn primary"
                onClick={() => {
                  onLogin?.();
                  setMenuOpen(false);
                }}
              >
                Sign In
              </button>
            )}
          </div>
        </nav>

        <div className="header-right">
          <div className="header-badge">
            <span className="age-badge">18+</span>
            <span className="responsible-text">Gamble Responsibly</span>
          </div>
          <div className="header-account">
            {user ? (
              <UserMenu user={user} onLogout={onLogout} onOpenSettings={onOpenSettings} />
            ) : (
              <LoginButton onClick={onLogin} />
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-links">
        <a href="/bookmakers">Bookmakers</a>
        <a href="/guides/odds-calculator/">Odds Calculator</a>
        <a href="#">About</a>
        <a href="#">Contact</a>
        <a href="#">Terms</a>
      </div>
      <p className="footer-disclaimer">
        18+ Gambling can be addictive. Please gamble responsibly. OddsWize compares odds from licensed
        bookmakers in Ghana. We may receive commission from bookmakers when you sign up through our links.
        This does not affect the odds displayed. Always check the bookmaker's website for the most up-to-date odds.
      </p>
      <p style={{ marginTop: '1rem', fontSize: '0.75rem' }}>
        © 2025 OddsWize. All rights reserved.
      </p>
    </footer>
  );
}

export default App;
