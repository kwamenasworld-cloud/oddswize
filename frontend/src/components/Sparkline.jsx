/**
 * Sparkline Component
 * Mini SVG chart showing odds movement over time
 */

const Sparkline = ({ data, width = 40, height = 16, color = '#666', highlightColor = null }) => {
  if (!data || data.length < 2) return null;

  // Calculate min/max for scaling
  const values = data.map(d => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  // Add padding to range
  const paddedMin = min - range * 0.1;
  const paddedMax = max + range * 0.1;
  const paddedRange = paddedMax - paddedMin;

  // Calculate points
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((d.value - paddedMin) / paddedRange) * height;
    return `${x},${y}`;
  }).join(' ');

  // Determine trend color
  const firstValue = values[0];
  const lastValue = values[values.length - 1];
  const trend = lastValue > firstValue ? 'up' : lastValue < firstValue ? 'down' : 'flat';
  const lineColor = highlightColor || (trend === 'up' ? '#4caf50' : trend === 'down' ? '#f44336' : color);

  // Calculate endpoint
  const endX = width;
  const endY = height - ((lastValue - paddedMin) / paddedRange) * height;

  return (
    <svg width={width} height={height} className="sparkline">
      {/* Line */}
      <polyline
        points={points}
        fill="none"
        stroke={lineColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* End dot */}
      <circle
        cx={endX}
        cy={endY}
        r="2"
        fill={lineColor}
      />
    </svg>
  );
};

/**
 * Generate mock odds history for demo
 * Creates realistic odds movement patterns
 */
export const generateOddsHistory = (currentOdds, hoursBack = 72, pattern = 'random') => {
  if (!currentOdds || currentOdds <= 1) return [];

  const points = [];
  const intervals = Math.floor(hoursBack / 4); // Data point every 4 hours

  // Determine movement pattern
  let drift = 0;
  if (pattern === 'drift') {
    drift = -0.02; // Odds lengthening (going up)
  } else if (pattern === 'steam') {
    drift = 0.02; // Odds shortening (going down)
  } else {
    drift = (Math.random() - 0.5) * 0.03; // Random slight drift
  }

  // Generate backwards from current
  let value = currentOdds;
  for (let i = intervals; i >= 0; i--) {
    const hoursAgo = i * 4;
    const timestamp = Date.now() - hoursAgo * 60 * 60 * 1000;

    // Add to beginning so oldest is first
    points.unshift({
      timestamp,
      value: Math.round(value * 100) / 100,
      hoursAgo
    });

    // Walk backwards with some randomness
    const change = drift + (Math.random() - 0.5) * 0.03;
    value = Math.max(1.01, value * (1 + change));
  }

  return points;
};

/**
 * Analyze odds movement to determine drift/steam
 */
export const analyzeOddsMovement = (history) => {
  if (!history || history.length < 2) {
    return { trend: 'stable', change: 0, percentChange: 0 };
  }

  const firstValue = history[0].value;
  const lastValue = history[history.length - 1].value;
  const change = lastValue - firstValue;
  const percentChange = ((lastValue - firstValue) / firstValue) * 100;

  // Recent movement (last 24 hours)
  const recentPoints = history.filter(p => p.hoursAgo <= 24);
  let recentChange = 0;
  if (recentPoints.length >= 2) {
    recentChange = ((recentPoints[recentPoints.length - 1].value - recentPoints[0].value) / recentPoints[0].value) * 100;
  }

  // Determine trend
  let trend = 'stable';
  if (percentChange > 3 || recentChange > 2) {
    trend = 'drift'; // Odds lengthening (less likely)
  } else if (percentChange < -3 || recentChange < -2) {
    trend = 'steam'; // Odds shortening (more likely, money coming in)
  }

  return {
    trend,
    change: Math.round(change * 100) / 100,
    percentChange: Math.round(percentChange * 10) / 10,
    recentChange: Math.round(recentChange * 10) / 10
  };
};

export default Sparkline;
