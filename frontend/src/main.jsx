import { StrictMode, Component } from 'react'
import { createRoot } from 'react-dom/client'
import './critical.css'
import './mobile-performance.css'
import App from './App.jsx'

let fullStylesLoaded = false;
const loadFullStyles = () => {
  if (fullStylesLoaded) return;
  fullStylesLoaded = true;
  import('./index.css');
};

if (typeof window !== 'undefined') {
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(() => loadFullStyles(), { timeout: 2000 });
  } else {
    setTimeout(loadFullStyles, 0);
  }
} else {
  loadFullStyles();
}

// Error boundary to catch and display runtime errors
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('React Error Boundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px', fontFamily: 'system-ui, sans-serif', maxWidth: '800px', margin: '0 auto' }}>
          <h1 style={{ color: '#e53935' }}>Something went wrong</h1>
          <details style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: '16px', borderRadius: '8px', marginTop: '16px' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>Error Details</summary>
            <p style={{ color: '#d32f2f', marginTop: '12px' }}>{this.state.error && this.state.error.toString()}</p>
            <p style={{ fontSize: '12px', color: '#666', marginTop: '8px' }}>
              {this.state.errorInfo && this.state.errorInfo.componentStack}
            </p>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: '20px', padding: '10px 20px', background: '#1a73e8', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
