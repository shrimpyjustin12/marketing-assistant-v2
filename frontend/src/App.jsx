import { useState, useEffect } from 'react'
import CsvUpload from './components/CsvUpload'
import ContentDisplay from './components/ContentDisplay'
import Settings from './components/Settings'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const formatCurrency = (value) => {
  if (value === undefined || value === null) return null
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function App() {
  const [summary, setSummary] = useState(null)
  const [content, setContent] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingStatus, setLoadingStatus] = useState('')
  const [error, setError] = useState(null)
  const [settings, setSettings] = useState({ apiKey: '', model: 'gpt-5-mini-2025-08-07' })
  const [refreshing, setRefreshing] = useState({
    instagram: false,
    tiktok: false,
    actions: false,
  });

  useEffect(() => {
    const savedKey = localStorage.getItem('marketing_api_key');
    if (savedKey) {
      setSettings(prev => ({ ...prev, apiKey: savedKey }));
    }
  }, []);

  const handleSettingsChange = (newSettings) => {
    setSettings(newSettings);
    if (newSettings.apiKey) {
      localStorage.setItem('marketing_api_key', newSettings.apiKey);
    }
  }

  const handleUpload = async (file) => {
    setLoading(true)
    setLoadingStatus('Uploading CSV...')
    setError(null)
    setContent(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_BASE}/upload-csv`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Failed to upload CSV')
      }

      const data = await response.json()
      setSummary(data)
      setLoadingStatus('')
    } catch (err) {
      setError(err.message)
      setSummary(null)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    if (!summary) return

    if (!settings.apiKey) {
      setError('Please configure your OpenAI API key in settings first.')
      return
    }

    setLoading(true)
    setLoadingStatus('Generating marketing content...')
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/generate-content-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...summary,
          api_key: settings.apiKey,
          model: settings.model,
        }),
      })

      const data = await response.json()
      setContent(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      setLoadingStatus('')
    }
  }

  return (
    <div className="app">

      <header className="header">
        <div className="header-top">

          <div className="brand">
            <img className="brand-logo" src="/pho_banhmi_logo.png" alt="logo"/>
            <div className="brand-text">
              <h1 className="brand-title">Pho & Banh Mi Marketing Dashboard</h1>
              <p className="brand-subtitle">
                Transform sales data into ready-to-post marketing content
              </p>
            </div>
          </div>

          <Settings onSettingsChange={handleSettingsChange} />

        </div>
      </header>

      <main className="main">

        <section className="upload-section">
          <CsvUpload onUpload={handleUpload} loading={loading}/>
        </section>

        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
          </div>
        )}

        {summary && (
          <section className="summary-section">

            <h2>Sales Summary</h2>

            {summary.date_range && (
              <div className="date-range">
                Data Period: <strong>{summary.date_range.start} – {summary.date_range.end}</strong>
              </div>
            )}

            <div className="summary-grid">

              {/* TOP ITEMS */}

              <div className="summary-card">
                <h3>Top Items</h3>

                <ul>
                  {summary.top_items.map((item, idx) => (
                    <li key={idx} className="item-row">

                      <div className="item-info">
                        <span className="item-name">{item.item_name}</span>
                        {item.avg_price && (
                          <span className="item-price">{formatCurrency(item.avg_price)} avg</span>
                        )}
                      </div>

                      <div className="item-stats">
                        <span className="item-quantity">{item.quantity} units</span>
                        {item.net_sales && (
                          <span className="item-revenue">{formatCurrency(item.net_sales)}</span>
                        )}
                      </div>

                    </li>
                  ))}
                </ul>

              </div>

              {/* TOP CATEGORIES */}

              <div className="summary-card">
                <h3>Top Categories</h3>

                <ul>
                  {summary.top_categories.map((cat, idx) => (
                    <li key={idx} className="item-row">

                      <span className="item-name">{cat.category}</span>

                      <div className="item-stats">
                        <span className="item-quantity">{cat.quantity} units</span>
                        {cat.net_sales && (
                          <span className="item-revenue">{formatCurrency(cat.net_sales)}</span>
                        )}
                      </div>

                    </li>
                  ))}
                </ul>

              </div>

              {/* INSIGHTS */}

              <div className="summary-card insights-card">
                <h3>Key Insights</h3>

                <ul>
                  {summary.insights?.map((insight, idx) => (
                    <li key={idx} className="insight-item">
                      <span className="insight-text">{insight.text}</span>
                    </li>
                  ))}
                </ul>

              </div>

              {/* CSV COMPARISON */}

              <div className="summary-card comparison-card">

                <h3>Change vs Previous CSV</h3>

                {!summary?.top5_panels ? (
                  <p>Upload a second CSV to see comparison.</p>
                ) : (

                  <div className="comparison-modern">

                    {summary.top5_panels.old_top5_comparison.slice(0,5).map((row, idx) => (

                      <div key={idx} className="comparison-row">

                        <div className="comparison-item">
                          {row.item_name}
                        </div>

                        <div className="comparison-metrics">

                          <span className="metric-prev">
                            {row.prev_qty}
                          </span>

                          <span className="metric-arrow">
                            →
                          </span>

                          <span className="metric-current">
                            {row.curr_qty}
                          </span>

                          <span className={`metric-change ${row.pct_change >= 0 ? 'positive' : 'negative'}`}>
                            {row.pct_change >= 0 ? '▲' : '▼'} {Math.abs(row.pct_change).toFixed(1)}%
                          </span>

                        </div>

                        <div className={`status-pill ${row.status === 'Still Top 5' ? 'active' : 'dropped'}`}>
                          {row.status}
                        </div>

                      </div>

                    ))}

                  </div>

                )}

              </div>

            </div>

            <button
              className="generate-btn"
              onClick={handleGenerate}
              disabled={loading || !settings.apiKey}
            >
              {loading ? loadingStatus || 'Processing...' : 'Generate Marketing Content'}
            </button>

          </section>
        )}

        {content && (
          <section className="content-section">
            <h2>Generated Content</h2>
            <ContentDisplay content={content}/>
          </section>
        )}

      </main>

      <footer className="footer">
        Marketing Dashboard MVP
      </footer>

    </div>
  )
}

export default App