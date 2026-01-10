import { useState } from 'react';
import { trackEvent } from '../services/analytics';

function ShareButton({ home_team, away_team, league, time, bestHome, bestDraw, bestAway, shareLink }) {
  const [showShareMenu, setShowShareMenu] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!home_team || !away_team) return null;

  // Format match details for sharing
  const formatOddValue = (value) => {
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? numberValue.toFixed(2) : '-';
  };

  const formatShareText = () => {
    // Extract values and bookmakers (handle both old and new format)
    const homeValue = bestHome?.value || bestHome || null;
    const homeBookie = bestHome?.bookmaker || '';
    const drawValue = bestDraw?.value || bestDraw || null;
    const drawBookie = bestDraw?.bookmaker || '';
    const awayValue = bestAway?.value || bestAway || null;
    const awayBookie = bestAway?.bookmaker || '';

    return `Match: ${home_team} vs ${away_team}

Time: ${time}
League: ${league}

Best Odds:
${home_team}: ${formatOddValue(homeValue)}${homeBookie ? ` (${homeBookie})` : ''}
Draw: ${formatOddValue(drawValue)}${drawBookie ? ` (${drawBookie})` : ''}
${away_team}: ${formatOddValue(awayValue)}${awayBookie ? ` (${awayBookie})` : ''}

Compare all odds on OddsWize:
${shareLink}

Find the best betting odds in Ghana.`;
  };

  const handleWhatsAppShare = () => {
    const text = formatShareText();
    const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(text)}`;
    window.open(whatsappUrl, '_blank');
    trackEvent('share', {
      method: 'whatsapp',
      placement: 'odds_match_share',
      match: `${home_team} vs ${away_team}`,
      league,
      link_url: shareLink,
    });
    setShowShareMenu(false);
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareLink);
      trackEvent('share', {
        method: 'copy_link',
        placement: 'odds_match_share',
        match: `${home_team} vs ${away_team}`,
        league,
        link_url: shareLink,
      });
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
        setShowShareMenu(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleCopyText = async () => {
    try {
      const text = formatShareText();
      await navigator.clipboard.writeText(text);
      trackEvent('share', {
        method: 'copy_text',
        placement: 'odds_match_share',
        match: `${home_team} vs ${away_team}`,
        league,
        link_url: shareLink,
      });
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
        setShowShareMenu(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="share-button-container">
      <button
        className="share-btn"
        onClick={() => setShowShareMenu(!showShareMenu)}
        title="Share match"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="18" cy="5" r="3" />
          <circle cx="6" cy="12" r="3" />
          <circle cx="18" cy="19" r="3" />
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
      </button>

      {showShareMenu && (
        <>
          <div className="share-menu-backdrop" onClick={() => setShowShareMenu(false)} />
          <div className="share-menu">
            <div className="share-menu-header">
              <h3>Share Match</h3>
              <button className="share-menu-close" onClick={() => setShowShareMenu(false)} aria-label="Close">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="share-menu-content">
              <div className="share-match-preview">
                <div className="share-match-teams">
                  {home_team} vs {away_team}
                </div>
                <div className="share-match-league">{league}</div>
              </div>

              <div className="share-options">
                <button className="share-option whatsapp" onClick={handleWhatsAppShare}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.304-1.654a11.882 11.882 0 005.713 1.457h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                  </svg>
                  <span>Share to WhatsApp</span>
                </button>

                <button className="share-option" onClick={handleCopyLink}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                  </svg>
                  <span>{copied ? 'Copied!' : 'Copy Link'}</span>
                </button>

                <button className="share-option" onClick={handleCopyText}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                  <span>{copied ? 'Copied!' : 'Copy Message'}</span>
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default ShareButton;
