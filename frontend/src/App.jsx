import { useState } from 'react'
import CsvUpload from './components/CsvUpload'
import ContentDisplay from './components/ContentDisplay'
import Settings from './components/Settings'
import './App.css'

// Use /api for production (Vercel), localhost for development
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Format currency
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

  const handleSettingsChange = (newSettings) => {
    setSettings(newSettings)
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
        let errorMsg = 'Failed to upload CSV'
        try {
          const data = await response.json()
          errorMsg = data.detail || errorMsg
        } catch {
          errorMsg = `Server error: ${response.status}`
        }
        throw new Error(errorMsg)
      }

      const text = await response.text()
      if (!text) {
        throw new Error('Empty response from server')
      }
      
      const data = JSON.parse(text)
      setSummary(data)
      setLoadingStatus('')
    } catch (err) {
      setError(err.message || 'An error occurred while uploading')
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
    setLoadingStatus('Connecting to AI...')
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/generate-content-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...summary,
          api_key: settings.apiKey,
          model: settings.model,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to generate content')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(line => line.startsWith('data: '))

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.error) {
              throw new Error(data.error)
            }
            
            if (data.status === 'connecting') {
              setLoadingStatus('Connecting to AI...')
            } else if (data.status === 'generating') {
              setLoadingStatus('Generating marketing content...')
            } else if (data.status === 'streaming') {
              setLoadingStatus(`Generating content... (${data.partial} chars)`)
            } else if (data.status === 'processing') {
              setLoadingStatus('Processing response...')
            } else if (data.status === 'complete') {
              setContent(data.data)
              setLoadingStatus('')
            }
          } catch (parseErr) {
            if (parseErr.message !== "Unexpected end of JSON input") {
              throw parseErr
            }
          }
        }
      }
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
        <div className="header-content">
          <div className="header-top">
            <h1>Marketing Dashboard</h1>
            <Settings onSettingsChange={handleSettingsChange} />
          </div>
          <p>Transform your sales data into engaging social media content</p>
        </div>
      </header>

      <main className="main">
        <section className="upload-section">
          <CsvUpload onUpload={handleUpload} loading={loading} />
        </section>

        {error && (
          <div className="error-message">
            <span className="error-icon">!</span>
            <div className="error-content">
              <strong>Error</strong>
              <p>{error}</p>
            </div>
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
              <div className="summary-card">
                <h3>Top Items</h3>
                <ul>
                  {summary.top_items.map((item, idx) => (
                    <li key={idx} className="item-row">
                      <div className="item-info">

                        <span className="item-name">
  {item.item_name}
  {item.performance_tag && (
    <span className={`tag ${item.performance_tag.type}`}>
      {item.performance_tag.label}
    </span>
  )}
</span>


                        
                        {item.avg_price && (
                          <span className="item-price">{formatCurrency(item.avg_price)} avg</span>
                        )}
                      </div>
                      <div className="item-stats">
                        <span className="item-quantity">{item.quantity || item.total_sold} units</span>
                        {item.net_sales && (
                          <span className="item-revenue">{formatCurrency(item.net_sales)}</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="summary-card">
                <h3>Top Categories</h3>
                <ul>
                  {summary.top_categories.map((cat, idx) => (
                    <li key={idx} className="item-row">
                      <span className="item-name">{cat.category}</span>
                      <div className="item-stats">
                        <span className="item-quantity">{cat.quantity || cat.total_sold} units</span>
                        {cat.net_sales && (
                          <span className="item-revenue">{formatCurrency(cat.net_sales)}</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="summary-card insights-card">
                <h3>Key Insights</h3>
                <ul>
                  {/* New insights format */}
                  {summary.insights && summary.insights.map((insight, idx) => (
                    <li key={idx} className="insight-item">
                      <span className={`insight-badge ${insight.type}`}>
                        {insight.type === 'bestseller' && '🏆'}
                        {insight.type === 'revenue' && '💰'}
                        {insight.type === 'top_revenue' && '📈'}
                        {insight.type === 'discount' && '🏷️'}
                        {insight.type === 'premium' && '⭐'}
                        {insight.type === 'trend' && '📊'}
                      </span>
                      <span className="insight-text">{insight.text}</span>
                    </li>
                  ))}
                  {/* Legacy monthly trends support */}
                  {summary.monthly_trends && !summary.insights && summary.monthly_trends.map((trend, idx) => (
                    <li key={idx} className="insight-item">
                      <span className="insight-badge trend">📊</span>
                      <span className="insight-text">
                        <strong>{trend.month}:</strong> {trend.trend}
                      </span>
                    </li>
                  ))}
                  {/* Show message if no insights */}
                  {!summary.insights && !summary.monthly_trends && (
                    <li className="insight-item">
                      <span className="insight-text">Upload data to see insights</span>
                    </li>
                  )}
                </ul>
              </div>
            </div>

            <button
              className="generate-btn"
              onClick={handleGenerate}
              disabled={loading || !settings.apiKey}
            >
              {loading ? (
                <div className="btn-loading">
                  <div className="btn-spinner"></div>
                  <span>{loadingStatus || 'Processing...'}</span>
                </div>
              ) : !settings.apiKey ? (
                'Configure API Key First'
              ) : (
                'Generate Marketing Content'
              )}
            </button>
          </section>
        )}

        {loading && loadingStatus && !content && summary && (
          <div className="loading-card">
            <div className="loading-animation">
              <div className="pulse-ring"></div>
              <div className="pulse-ring delay-1"></div>
              <div className="pulse-ring delay-2"></div>
              <div className="loading-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>
              </div>
            </div>
            <p className="loading-status">{loadingStatus}</p>
            <p className="loading-hint">This may take a few seconds...</p>
          </div>
        )}

        {content && (
          <section className="content-section">
            <h2>Generated Content</h2>
            <ContentDisplay content={content} />
          </section>
        )}
      </main>

      <footer className="footer">
        <p>Marketing Dashboard MVP • Using {settings.model || 'gpt-5-mini-2025-08-07'}</p>
      </footer>
    </div>
  )
}

export default App
