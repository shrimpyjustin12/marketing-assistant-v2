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
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to upload CSV')
      }

      const data = await response.json()
      setSummary(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      setLoadingStatus('')
    }
  }

  const generateMarketingContent = async () => {
    if (!summary || !settings.apiKey) return

    setLoading(true)
    setLoadingStatus('Generating marketing content...')
    setContent('')

    try {
      const response = await fetch(`${API_BASE}/generate-content-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...summary,
          api_key: settings.apiKey,
          model: settings.model
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to generate content')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const contentChunk = line.replace('data: ', '')
            fullContent += contentChunk
            setContent(fullContent)
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
        <div className="header-top">
          <div className="header-content">
            <h1>Marketing Dashboard</h1>
            <p>Transform your Toast sales data into marketing gold</p>
          </div>
          <Settings onSettingsChange={handleSettingsChange} />
        </div>
      </header>

      <main className="main">
        {!summary && (
          <div className="upload-container">
            <CsvUpload onUpload={handleUpload} loading={loading} />
          </div>
        )}

        {error && <div className="error-message">{error}</div>}

        {summary && (
          <div className="dashboard-grid">
            <section className="summary-section card">
              <div className="card-header">
                <h2>Sales Summary</h2>
              </div>
              
              <div className="summary-grid">
                <div className="top-items">
                  <h3>Top 5 Items</h3>
                  <div className="items-list">
                    {summary.top_items.map((item, index) => (
                      <div key={index} className="item-row">
                        <span className="item-rank">{index + 1}</span>
                        <div className="item-info">
                          <span className="item-name">{item.item_name}</span>
                          <span className="item-stats">
                            {item.quantity} units · {formatCurrency(item.net_sales)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="top-categories">
                  <h3>Revenue by Category</h3>
                  <div className="categories-list">
                    {summary.top_categories.map((cat, index) => (
                      <div key={index} className="category-row">
                        <span className="category-name">{cat.category}</span>
                        <div className="category-bar-container">
                          <div 
                            className="category-bar" 
                            style={{ 
                              width: `${(cat.net_sales / summary.top_categories[0].net_sales) * 100}%` 
                            }}
                          ></div>
                        </div>
                        <span className="category-value">{formatCurrency(cat.net_sales)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="insights-section">
                <h3>Quick Insights</h3>
                <div className="insights-grid">
                  {summary.insights.map((insight, index) => (
                    <div key={index} className={`insight-card ${insight.type}`}>
                      <p>{insight.text}</p>
                    </div>
                  ))}
                </div>
              </div>

              <button 
                onClick={generateMarketingContent} 
                disabled={loading || !settings.apiKey}
                className="generate-button"
              >
                {loading ? 'Generating...' : !settings.apiKey ? 'Configure API Key First' : 'Generate Marketing Content'}
              </button>
            </section>

            {content !== null && (
              <ContentDisplay content={content} loading={loading && content === ''} />
            )}
          </div>
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
      </main>

      <footer className="footer">
        <p>© 2026 Marketing Dashboard for Toast POS</p>
      </footer>
    </div>
  )
}

export default App