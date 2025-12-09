/**
 * User Preferences Service
 * Simple local storage-based user preferences (no financial features)
 */

const PREFS_KEY = 'oddswize_user_prefs';
const USER_KEY = 'oddswize_user';

// Default preferences
const DEFAULT_PREFS = {
  favoriteLeagues: [],
  favoriteTeams: [],
  defaultBookmakers: ['Betway Ghana', 'SportyBet Ghana', '1xBet Ghana', '22Bet Ghana', 'SoccaBet Ghana'],
  notifications: {
    bestOdds: true,
    bigEdges: true,
    favoriteTeams: true,
    dailyDigest: false,
  },
  display: {
    defaultView: 'all', // 'all', 'favorites', 'edges'
    oddsFormat: 'decimal', // 'decimal', 'fractional', 'american'
    showProbability: false,
  },
  createdAt: null,
  updatedAt: null,
};

/**
 * Load user from localStorage
 */
export const getUser = () => {
  try {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  } catch (e) {
    console.log('[UserPrefs] Error loading user:', e);
    return null;
  }
};

/**
 * Save user to localStorage
 */
export const saveUser = (user) => {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return true;
  } catch (e) {
    console.log('[UserPrefs] Error saving user:', e);
    return false;
  }
};

/**
 * Sign up with email or phone
 */
export const signUp = (identifier, name = '') => {
  const isEmail = identifier.includes('@');
  const user = {
    id: `user_${Date.now()}`,
    email: isEmail ? identifier : null,
    phone: !isEmail ? identifier : null,
    name: name || (isEmail ? identifier.split('@')[0] : 'User'),
    createdAt: new Date().toISOString(),
    lastLogin: new Date().toISOString(),
  };

  saveUser(user);

  // Initialize preferences
  const prefs = {
    ...DEFAULT_PREFS,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  savePreferences(prefs);

  console.log('[UserPrefs] User signed up:', user.id);
  return user;
};

/**
 * Log in (simple identifier-based)
 */
export const logIn = (identifier) => {
  const existingUser = getUser();

  if (existingUser && (existingUser.email === identifier || existingUser.phone === identifier)) {
    existingUser.lastLogin = new Date().toISOString();
    saveUser(existingUser);
    console.log('[UserPrefs] User logged in:', existingUser.id);
    return existingUser;
  }

  // If no existing user, create one
  return signUp(identifier);
};

/**
 * Log out
 */
export const logOut = () => {
  localStorage.removeItem(USER_KEY);
  // Keep preferences for when they log back in
  console.log('[UserPrefs] User logged out');
};

/**
 * Check if user is logged in
 */
export const isLoggedIn = () => {
  return getUser() !== null;
};

/**
 * Load preferences from localStorage
 */
export const getPreferences = () => {
  try {
    const prefs = localStorage.getItem(PREFS_KEY);
    if (prefs) {
      return { ...DEFAULT_PREFS, ...JSON.parse(prefs) };
    }
    return DEFAULT_PREFS;
  } catch (e) {
    console.log('[UserPrefs] Error loading preferences:', e);
    return DEFAULT_PREFS;
  }
};

/**
 * Save preferences to localStorage
 */
export const savePreferences = (prefs) => {
  try {
    const updated = {
      ...prefs,
      updatedAt: new Date().toISOString(),
    };
    localStorage.setItem(PREFS_KEY, JSON.stringify(updated));
    console.log('[UserPrefs] Preferences saved');
    return true;
  } catch (e) {
    console.log('[UserPrefs] Error saving preferences:', e);
    return false;
  }
};

/**
 * Update specific preference
 */
export const updatePreference = (key, value) => {
  const prefs = getPreferences();
  prefs[key] = value;
  return savePreferences(prefs);
};

/**
 * Toggle favorite league
 */
export const toggleFavoriteLeague = (league) => {
  const prefs = getPreferences();
  const index = prefs.favoriteLeagues.indexOf(league);

  if (index === -1) {
    prefs.favoriteLeagues.push(league);
  } else {
    prefs.favoriteLeagues.splice(index, 1);
  }

  return savePreferences(prefs);
};

/**
 * Toggle favorite team
 */
export const toggleFavoriteTeam = (team) => {
  const prefs = getPreferences();
  const index = prefs.favoriteTeams.indexOf(team);

  if (index === -1) {
    prefs.favoriteTeams.push(team);
  } else {
    prefs.favoriteTeams.splice(index, 1);
  }

  return savePreferences(prefs);
};

/**
 * Check if league is favorite
 */
export const isFavoriteLeague = (league) => {
  const prefs = getPreferences();
  return prefs.favoriteLeagues.includes(league);
};

/**
 * Check if team is favorite
 */
export const isFavoriteTeam = (team) => {
  const prefs = getPreferences();
  return prefs.favoriteTeams.includes(team);
};

/**
 * Update notification setting
 */
export const updateNotificationSetting = (key, value) => {
  const prefs = getPreferences();
  prefs.notifications[key] = value;
  return savePreferences(prefs);
};

/**
 * Update display setting
 */
export const updateDisplaySetting = (key, value) => {
  const prefs = getPreferences();
  prefs.display[key] = value;
  return savePreferences(prefs);
};

/**
 * Reset preferences to defaults
 */
export const resetPreferences = () => {
  return savePreferences({
    ...DEFAULT_PREFS,
    createdAt: new Date().toISOString(),
  });
};

/**
 * Export user data (GDPR compliance)
 */
export const exportUserData = () => {
  return {
    user: getUser(),
    preferences: getPreferences(),
    exportedAt: new Date().toISOString(),
  };
};

/**
 * Delete all user data
 */
export const deleteUserData = () => {
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(PREFS_KEY);
  console.log('[UserPrefs] All user data deleted');
};

export default {
  getUser,
  saveUser,
  signUp,
  logIn,
  logOut,
  isLoggedIn,
  getPreferences,
  savePreferences,
  updatePreference,
  toggleFavoriteLeague,
  toggleFavoriteTeam,
  isFavoriteLeague,
  isFavoriteTeam,
  updateNotificationSetting,
  updateDisplaySetting,
  resetPreferences,
  exportUserData,
  deleteUserData,
};
