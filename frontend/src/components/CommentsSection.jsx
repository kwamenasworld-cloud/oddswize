import { useState, useEffect } from 'react';

// Demo comments - In production, use a real backend or service like Firebase/Supabase
const DEMO_COMMENTS = {
  'real-madrid-vs-sevilla': [
    {
      id: 1,
      author: 'KwameB',
      avatar: 'KB',
      content: 'Real Madrid to win easily. Sevilla are in poor form. 1.28 odds are decent value.',
      likes: 12,
      time: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      prediction: 'Home Win',
    },
    {
      id: 2,
      author: 'AccraFan',
      avatar: 'AF',
      content: 'I\'m going for the draw. Real Madrid always struggle at home against Sevilla. Better value at 6.50.',
      likes: 5,
      time: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      prediction: 'Draw',
    },
  ],
  'arsenal-vs-chelsea': [
    {
      id: 3,
      author: 'GhanaGooner',
      avatar: 'GG',
      content: 'Arsenal at home are unbeatable! 1.85 is a steal. COYG!',
      likes: 18,
      time: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
      prediction: 'Home Win',
    },
    {
      id: 4,
      author: 'BlueFlag',
      avatar: 'BF',
      content: 'Chelsea have been playing well lately. Draw is my pick.',
      likes: 7,
      time: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      prediction: 'Draw',
    },
  ],
};

function CommentsSection({ matchId, matchName }) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [prediction, setPrediction] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    // Load comments from localStorage or use demo data
    const stored = localStorage.getItem(`comments_${matchId}`);
    if (stored) {
      setComments(JSON.parse(stored));
    } else {
      // Use demo comments if available, otherwise empty
      const demoKey = matchId?.toLowerCase().replace(/\s+/g, '-');
      setComments(DEMO_COMMENTS[demoKey] || []);
    }

    // Load saved author name
    const savedName = localStorage.getItem('oddswize_username');
    if (savedName) setAuthorName(savedName);
  }, [matchId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!newComment.trim() || !authorName.trim()) return;

    setIsSubmitting(true);

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));

    const comment = {
      id: Date.now(),
      author: authorName,
      avatar: authorName.substring(0, 2).toUpperCase(),
      content: newComment,
      likes: 0,
      time: new Date().toISOString(),
      prediction: prediction || null,
    };

    const updatedComments = [comment, ...comments];
    setComments(updatedComments);

    // Save to localStorage
    localStorage.setItem(`comments_${matchId}`, JSON.stringify(updatedComments));
    localStorage.setItem('oddswize_username', authorName);

    setNewComment('');
    setPrediction('');
    setIsSubmitting(false);
  };

  const handleLike = (commentId) => {
    const updatedComments = comments.map((c) =>
      c.id === commentId ? { ...c, likes: c.likes + 1 } : c
    );
    setComments(updatedComments);
    localStorage.setItem(`comments_${matchId}`, JSON.stringify(updatedComments));
  };

  const formatTimeAgo = (dateString) => {
    const date = new Date(dateString);
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
          <span className="comments-icon">💬</span>
          Match Discussion
          <span className="comments-count">{comments.length}</span>
        </h3>
        {matchName && <p className="comments-match">{matchName}</p>}
      </div>

      {/* Comment Form */}
      <form className="comment-form" onSubmit={handleSubmit}>
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
        <div className="form-footer">
          <span className="char-count">{newComment.length}/500</span>
          <button type="submit" className="submit-comment-btn" disabled={isSubmitting}>
            {isSubmitting ? 'Posting...' : 'Post Comment'}
          </button>
        </div>
      </form>

      {/* Comments List */}
      <div className="comments-list">
        {displayComments.length === 0 ? (
          <div className="no-comments">
            <span className="no-comments-icon">💭</span>
            <p>No comments yet. Be the first to share your prediction!</p>
          </div>
        ) : (
          displayComments.map((comment) => (
            <div key={comment.id} className="comment-card">
              <div className="comment-avatar" style={{ background: getAvatarColor(comment.author) }}>
                {comment.avatar}
              </div>
              <div className="comment-body">
                <div className="comment-meta">
                  <span className="comment-author">{comment.author}</span>
                  {comment.prediction && (
                    <span className={`comment-prediction ${comment.prediction.toLowerCase().replace(' ', '-')}`}>
                      {comment.prediction}
                    </span>
                  )}
                  <span className="comment-time">{formatTimeAgo(comment.time)}</span>
                </div>
                <p className="comment-content">{comment.content}</p>
                <div className="comment-actions">
                  <button className="like-btn" onClick={() => handleLike(comment.id)}>
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
                    </svg>
                    {comment.likes > 0 && <span>{comment.likes}</span>}
                  </button>
                  <button className="reply-btn">Reply</button>
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
    </div>
  );
}

// Generate consistent color for avatar based on name
function getAvatarColor(name) {
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
