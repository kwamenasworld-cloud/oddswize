import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import OddsPage from './pages/OddsPage';
import ArbitragePage from './pages/ArbitragePage';
import BookmakersPage from './pages/BookmakersPage';
import SettingsPage from './pages/SettingsPage';
import { AccountModal, UserMenu, LoginButton } from './components/AccountModal';
import { getUser } from './services/userPreferences';
import './index.css';

function App() {
  const [user, setUser] = useState(null);
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    // Check if user is logged in on mount
    const savedUser = getUser();
    if (savedUser) {
      setUser(savedUser);
    }
  }, []);

  const handleAuthChange = (newUser) => {
    setUser(newUser);
  };

  const handleLogout = () => {
    setUser(null);
  };

  return (
    <BrowserRouter>
      <div className="app">
        <Header
          user={user}
          onLoginClick={() => setShowAccountModal(true)}
          onLogout={handleLogout}
          onOpenSettings={() => setShowSettings(true)}
        />
        <main>
          <Routes>
            <Route path="/" element={<OddsPage />} />
            <Route path="/arbitrage" element={<ArbitragePage />} />
            <Route path="/bookmakers" element={<BookmakersPage />} />
          </Routes>
        </main>
        <Footer />

        <AccountModal
          isOpen={showAccountModal}
          onClose={() => setShowAccountModal(false)}
          onAuthChange={handleAuthChange}
        />

        {showSettings && (
          <SettingsPage
            onClose={() => setShowSettings(false)}
            onLogout={handleLogout}
          />
        )}
      </div>
    </BrowserRouter>
  );
}

function Header({ user, onLoginClick, onLogout, onOpenSettings }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="header">
      <div className="header-top">
        <NavLink to="/" className="logo">
          Odds<span>Wize</span>
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
          >
            Odds Comparison
          </NavLink>
          <NavLink
            to="/arbitrage"
            className={({ isActive }) => isActive ? 'active' : ''}
            onClick={() => setMenuOpen(false)}
          >
            Arbitrage
          </NavLink>
          <NavLink
            to="/bookmakers"
            className={({ isActive }) => isActive ? 'active' : ''}
            onClick={() => setMenuOpen(false)}
          >
            Bookmakers
          </NavLink>
        </nav>

        <div className="header-right">
          {user ? (
            <UserMenu
              user={user}
              onLogout={onLogout}
              onOpenSettings={onOpenSettings}
            />
          ) : (
            <LoginButton onClick={onLoginClick} />
          )}
          <div className="header-badge">
            <span className="age-badge">18+</span>
            <span className="responsible-text">Gamble Responsibly</span>
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
