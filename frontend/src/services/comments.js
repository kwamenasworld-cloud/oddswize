const API_URL = import.meta.env.VITE_CLOUDFLARE_API_URL || 'https://oddswize-api.kwamenahb.workers.dev';
const TURNSTILE_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
const TURNSTILE_SCRIPT_ID = 'turnstile-script';
let turnstileScriptPromise;

const request = async (path, options = {}) => {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data?.success === false) {
    const message = data?.error || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
};

export const fetchComments = async ({ matchId, limit = 20, offset = 0 }) => {
  const query = new URLSearchParams({
    match_id: matchId,
    limit: String(limit),
    offset: String(offset),
  });
  return request(`/api/comments?${query.toString()}`);
};

export const postComment = async (payload) => {
  return request('/api/comments', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
};

export const likeComment = async (commentId) => {
  return request(`/api/comments/${commentId}/like`, {
    method: 'POST',
  });
};

export const getTurnstileSiteKey = () => {
  return import.meta.env.VITE_TURNSTILE_SITE_KEY || '';
};

export const loadTurnstileScript = () => {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('Turnstile unavailable'));
  }
  if (window.turnstile) {
    return Promise.resolve(window.turnstile);
  }
  if (turnstileScriptPromise) {
    return turnstileScriptPromise;
  }
  turnstileScriptPromise = new Promise((resolve, reject) => {
    const handleError = () => {
      turnstileScriptPromise = null;
      reject(new Error('Turnstile failed to load'));
    };
    const existing = document.getElementById(TURNSTILE_SCRIPT_ID);
    if (existing) {
      existing.addEventListener('load', () => resolve(window.turnstile), { once: true });
      existing.addEventListener('error', handleError, { once: true });
      return;
    }
    const script = document.createElement('script');
    script.id = TURNSTILE_SCRIPT_ID;
    script.src = TURNSTILE_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve(window.turnstile);
    script.onerror = handleError;
    document.head.appendChild(script);
  });
  return turnstileScriptPromise;
};
