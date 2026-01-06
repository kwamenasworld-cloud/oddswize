import { useEffect, useRef, useState } from 'react';
import { AccountModal, LoginButton, UserMenu } from './AccountModal';
import { getUser } from '../services/userPreferences';
import {
  fetchComments,
  getTurnstileSiteKey,
  likeComment,
  loadTurnstileScript,
  postComment,
} from '../services/comments';

function CommentsSection({ matchId, matchName, league }) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [prediction, setPrediction] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [user, setUser] = useState(() => getUser());
  const [authOpen, setAuthOpen] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState('');
  const turnstileRef = useRef(null);
  const turnstileWidgetId = useRef(null);
  const turnstileKey = getTurnstileSiteKey();

  useEffect(() => {
    if (!matchId) return;
    setLoading(true);
    setError('');
    fetchComments({ matchId })
      .then((data) => {
        setComments(data?.data || []);
      })
      .catch((err) => {
        setError(err.message || 'Unable to load comments.');
      })
      .finally(() => setLoading(false));
  }, [matchId]);

  useEffect(() => {
    if (!user) return;
    const displayName = user.name || user.email?.split('@')[0] || user.phone || '';
    if (displayName && !authorName) {
      setAuthorName(displayName);
    }
  }, [user, authorName]);

  useEffect(() => {
    if (!turnstileKey || !turnstileRef.current) return;
    let cancelled = false;
    loadTurnstileScript()
      .then(() => {
        if (cancelled || !turnstileRef.current || !window.turnstile) return;
        if (turnstileWidgetId.current === null) {
          turnstileWidgetId.current = window.turnstile.render(turnstileRef.current, {
            sitekey: turnstileKey,
            callback: (token) => setTurnstileToken(token),
            'expired-callback': () => setTurnstileToken(''),
            'error-callback': () => setTurnstileToken(''),
          });
        } else {
          window.turnstile.reset(turnstileWidgetId.current);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Verification failed to load. Please try again later.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [turnstileKey, matchId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!newComment.trim() || !authorName.trim()) return;
    if (!user) {
      setError('Please sign in to comment.');
      return;
    }
    if (turnstileKey && !turnstileToken) {
      setError('Please complete the verification.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const response = await postComment({
        match_id: matchId,
        match_name: matchName,
        league,
        author_name: authorName,
        author_id: user?.id,
        content: newComment,
        prediction: prediction || null,
        turnstile_token: turnstileToken || null,
      });

      if (response?.data) {
        setComments((prev) => [response.data, ...prev]);
      }

      setNewComment('');
      setPrediction('');
      setTurnstileToken('');
      if (window.turnstile && turnstileWidgetId.current !== null) {
        window.turnstile.reset(turnstileWidgetId.current);
      }
    } catch (err) {
      setError(err.message || 'Unable to post comment.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLike = async (commentId) => {
    try {
      const response = await likeComment(commentId);
      if (response?.data?.liked) {
        setComments((prev) => prev.map((comment) => (
          comment.id === commentId
            ? { ...comment, likes: (comment.likes || 0) + 1 }
            : comment
        )));
      }
    } catch (err) {
      // Ignore like errors
    }
  };

  const formatTimeAgo = (dateString) => {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return 'Just now';
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  const displayComments = showAll ? comments : comments.slice(0, 3);

  return (
    <div className="comments-section">
      <div className="comments-header">
        <h3>
          <span className="comments-icon">dY'ª</span>
          Match Discussion
          <span className="comments-count">{comments.length}</span>
        </h3>
        <div className="comments-auth">
          {user ? (
            <UserMenu user={user} onLogout={() => setUser(null)} />
          ) : (
            <LoginButton onClick={() => setAuthOpen(true)} />
          )}
        </div>
        {matchName && <p className="comments-match">{matchName}</p>}
      </div>

      <form className="comment-form" onSubmit={handleSubmit}>
        {!user && (
          <div className="comments-locked">
            <p>Sign in to join the discussion and keep spam out.</p>
            <button type="button" className="submit-comment-btn" onClick={() => setAuthOpen(true)}>
              Sign In to Comment
            </button>
          </div>
        )}

        {user && (
          <>
            <div className="form-row">
              <input
                type="text"
                placeholder="Your nickname"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                className="comment-input name-input"
                maxLength={20}
                required
              />
              <select
                value={prediction}
                onChange={(e) => setPrediction(e.target.value)}
                className="comment-select"
              >
                <option value="">Your prediction (optional)</option>
                <option value="Home Win">Home Win</option>
                <option value="Draw">Draw</option>
                <option value="Away Win">Away Win</option>
              </select>
            </div>
            <textarea
              placeholder="Share your thoughts, predictions, or betting tips..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              className="comment-textarea"
              rows={3}
              maxLength={500}
              required
            />
            {turnstileKey && (
              <div className="comment-turnstile" ref={turnstileRef} />
            )}
            {error && <p className="comment-error">{error}</p>}
            <div className="form-footer">
              <span className="char-count">{newComment.length}/500</span>
              <button type="submit" className="submit-comment-btn" disabled={isSubmitting}>
                {isSubmitting ? 'Posting...' : 'Post Comment'}
              </button>
            </div>
          </>
        )}
      </form>

      <div className="comments-list">
        {loading ? (
          <div className="no-comments">
            <span className="no-comments-icon">dY"-</span>
            <p>Loading comments...</p>
          </div>
        ) : displayComments.length === 0 ? (
          <div className="no-comments">
            <span className="no-comments-icon">dY'-</span>
            <p>No comments yet. Be the first to share your prediction!</p>
          </div>
        ) : (
          displayComments.map((comment) => (
            <div key={comment.id} className="comment-card">
              <div className="comment-avatar" style={{ background: getAvatarColor(comment.author_name || comment.author) }}>
                {(comment.author_name || comment.author || 'U').substring(0, 2).toUpperCase()}
              </div>
              <div className="comment-body">
                <div className="comment-meta">
                  <span className="comment-author">{comment.author_name || comment.author}</span>
                  {(comment.prediction || comment.prediction === '') && (
                    <span className={`comment-prediction ${(comment.prediction || '').toLowerCase().replace(' ', '-')}`}>
                      {comment.prediction}
                    </span>
                  )}
                  <span className="comment-time">{formatTimeAgo(comment.created_at || comment.time)}</span>
                </div>
                <p className="comment-content">{comment.content}</p>
                <div className="comment-actions">
                  <button className="like-btn" onClick={() => handleLike(comment.id)}>
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
                    </svg>
                    {comment.likes > 0 && <span>{comment.likes}</span>}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {comments.length > 3 && (
        <button className="show-more-comments" onClick={() => setShowAll(!showAll)}>
          {showAll ? 'Show Less' : `Show All ${comments.length} Comments`}
        </button>
      )}

      <AccountModal
        isOpen={authOpen}
        onClose={() => setAuthOpen(false)}
        onAuthChange={(nextUser) => setUser(nextUser)}
      />
    </div>
  );
}

function getAvatarColor(name = '') {
  const colors = [
    '#1a73e8', '#00c853', '#ff5722', '#9c27b0',
    '#00bcd4', '#ff9800', '#e91e63', '#3f51b5',
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

export default CommentsSection;
