import { useState } from 'react';
import { signUp, logIn, getUser, logOut, isLoggedIn } from '../services/userPreferences';

/**
 * Account Modal Component
 * Simple signup/login with email or phone
 */
export function AccountModal({ isOpen, onClose, onAuthChange }) {
  const [mode, setMode] = useState('login'); // 'login' or 'signup'
  const [identifier, setIdentifier] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const validateIdentifier = (value) => {
    const isEmail = value.includes('@');
    const isPhone = /^\+?[\d\s-]{10,}$/.test(value.replace(/\s/g, ''));
    return isEmail || isPhone;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!identifier.trim()) {
      setError('Please enter your email or phone number');
      return;
    }

    if (!validateIdentifier(identifier)) {
      setError('Please enter a valid email or phone number');
      return;
    }

    setLoading(true);

    try {
      let user;
      if (mode === 'signup') {
        user = signUp(identifier, name);
      } else {
        user = logIn(identifier);
      }

      if (user) {
        onAuthChange?.(user);
        onClose();
        setIdentifier('');
        setName('');
      }
    } catch (err) {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content account-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        <div className="account-modal-header">
          <h2>{mode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
          <p>{mode === 'login' ? 'Sign in to access your preferences' : 'Save your favorites and settings'}</p>
        </div>

        <form onSubmit={handleSubmit} className="account-form">
          {mode === 'signup' && (
            <div className="form-group">
              <label htmlFor="name">Name (optional)</label>
              <input
                type="text"
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="form-input"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="identifier">Email or Phone</label>
            <input
              type="text"
              id="identifier"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="email@example.com or +233..."
              className="form-input"
              required
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="account-modal-footer">
          {mode === 'login' ? (
            <p>
              Don't have an account?{' '}
              <button className="link-btn" onClick={() => setMode('signup')}>
                Sign up
              </button>
            </p>
          ) : (
            <p>
              Already have an account?{' '}
              <button className="link-btn" onClick={() => setMode('login')}>
                Sign in
              </button>
            </p>
          )}
        </div>

        <p className="account-privacy-note">
          We only store your preferences locally on this device. No passwords required.
        </p>
      </div>
    </div>
  );
}

/**
 * User Menu Component
 * Shows user info and options when logged in
 */
export function UserMenu({ user, onLogout, onOpenSettings }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!user) return null;

  const displayName = user.name || user.email?.split('@')[0] || 'User';
  const initials = displayName.slice(0, 2).toUpperCase();

  const handleLogout = () => {
    logOut();
    onLogout?.();
    setIsOpen(false);
  };

  return (
    <div className="user-menu">
      <button
        className="user-menu-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="User menu"
      >
        <div className="user-avatar">{initials}</div>
      </button>

      {isOpen && (
        <>
          <div className="user-menu-backdrop" onClick={() => setIsOpen(false)} />
          <div className="user-menu-dropdown">
            <div className="user-menu-header">
              <div className="user-avatar-large">{initials}</div>
              <div className="user-info">
                <span className="user-name">{displayName}</span>
                <span className="user-email">{user.email || user.phone}</span>
              </div>
            </div>
            <div className="user-menu-items">
              <button onClick={() => { onOpenSettings?.(); setIsOpen(false); }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
                </svg>
                Settings
              </button>
              <button onClick={handleLogout}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                  <polyline points="16,17 21,12 16,7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                Sign Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/**
 * Login Button Component
 * Shows when user is not logged in
 */
export function LoginButton({ onClick }) {
  return (
    <button className="login-btn" onClick={onClick}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
      <span>Sign In</span>
    </button>
  );
}

export default AccountModal;
