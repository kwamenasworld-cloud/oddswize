import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import OddsPage from './pages/OddsPage';
import ArbitragePage from './pages/ArbitragePage';
import BookmakersPage from './pages/BookmakersPage';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER } from './config/affiliates';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<OddsPage />} />
            <Route path="/arbitrage" element={<ArbitragePage />} />
            <Route path="/bookmakers" element={<BookmakersPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

function Header() {
  return (
    <header className="header">
      <div className="header-top">
        <NavLink to="/" className="logo">
          Odds<span>Wize</span>
        </NavLink>
        <nav className="nav">
          <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
            Odds Comparison
          </NavLink>
          <NavLink to="/arbitrage" className={({ isActive }) => isActive ? 'active' : ''}>
            Arbitrage
          </NavLink>
          <NavLink to="/bookmakers" className={({ isActive }) => isActive ? 'active' : ''}>
            Bookmakers
          </NavLink>
        </nav>
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
        © 2024 OddsWize. All rights reserved.
      </p>
    </footer>
  );
}

export default App;
