import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import HomePage from './pages/HomePage';
import OddsPage from './pages/OddsPage';
import BookmakersPage from './pages/BookmakersPage';
import NewsPage from './pages/NewsPage';
import ArticlePage from './pages/ArticlePage';
import AdminPage from './pages/AdminPage';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/odds" element={<OddsPage />} />
            <Route path="/bookmakers" element={<BookmakersPage />} />
            <Route path="/news" element={<NewsPage />} />
            <Route path="/news/:slug" element={<ArticlePage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);

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
        </nav>

        <div className="header-right">
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
