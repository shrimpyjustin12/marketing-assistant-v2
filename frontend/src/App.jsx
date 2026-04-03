import { useState, useEffect } from 'react' // 1. Added useEffect here
import CsvUpload from './components/CsvUpload'
import ContentDisplay from './components/ContentDisplay'
import Settings from './components/Settings'
import './App.css'
import React from 'react'

// Use /api for production (Vercel), localhost for development
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Format currency
const formatCurrency = (value) => {
  if (value === undefined || value === null) return null
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

const formatPct = (value) => {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
};

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
})
  const [selectedItem, setSelectedItem] = useState('');

  // 2. Load the key from the browser storage as soon as the app opens
  useEffect(() => {
    const savedKey = localStorage.getItem('marketing_api_key');
    if (savedKey) {
      setSettings(prev => ({ ...prev, apiKey: savedKey }));
    }
  }, []);

  // 3. Save the key whenever it changes
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
      console.log("Summary data from backend:", data)
      setSummary(data)
      setSelectedItem(data?.top_items?.[0]?.item_name || '')
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
          selected_item: selectedItem,
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

  const getStatusClass = (status) => {
  if (!status) return "status-neutral";

  const s = status.toLowerCase();

  if (s.includes("still")) return "status-good";
  if (s.includes("dropped")) return "status-bad";
  if (s.includes("entered") || s.includes("new")) return "status-info";

  return "status-neutral";
};

const getPercentClass = (percent) => {
  const num = Number(percent);

  if (num > 0) return "percent-good";
  if (num < 0) return "percent-bad";

  return "percent-neutral";
};

  const handleRefresh = async (platform) => {
  if (!summary) return;

  if (!settings.apiKey) {
    setError('Please configure your OpenAI API key in settings first.');
    return;
  }

  setError(null);
  setRefreshing((prev) => ({ ...prev, [platform]: true }));

  try {
    // Use previous text to force novelty
    let previousText = null;
    if (platform === "instagram") previousText = content?.instagram?.caption || null;
    if (platform === "tiktok") previousText = content?.tiktok?.caption || null;
    if (platform === "actions") {
      // promotion_ideas currently stores objects with {text, reason}
      previousText = content?.promotion_ideas?.map(i => i.text).join(" | ") || null;
    }

    const response = await fetch(`${API_BASE}/generate-platform`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...summary,
        api_key: settings.apiKey,
        model: settings.model,
        platform,                 // "instagram" | "tiktok" | "actions"
        previous_text: previousText,
        nonce: Date.now(),
        selected_item: selectedItem,
      }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || 'Failed to refresh content');
    }

    const data = await response.json();

    // data = { platform: "...", data: {...} }
    setContent((prev) => {
      if (!prev) return prev;

      if (platform === "instagram") {
        return { ...prev, instagram: data.data };
      }
      if (platform === "tiktok") {
        return { ...prev, tiktok: data.data };
      }
      if (platform === "actions") {
        // Convert actions list back into promotion_ideas objects so UI stays compatible
        const actions = data.data.actions || [];
        return {
          ...prev,
          promotion_ideas: actions.map((text) => ({ text, reason: "Refreshed suggestion" })),
        };
      }

      return prev;
    });

  } catch (err) {
    setError(err.message);
  } finally {
    setRefreshing((prev) => ({ ...prev, [platform]: false }));
  }
};

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">

          <div className="header-top">
            <div className="brand">
              <img className="brand-logo" src="/pho_banhmi_logo.png" alt="Pho & Banh Mi logo" />
              <div className="brand-text">
                <h1 className="brand-title">Pho & Banh Mi Marketing Dashboard</h1>
                <p className="brand-subtitle">Transform sales data into ready-to-post social content</p>
              </div>
            </div>

            <Settings onSettingsChange={handleSettingsChange} />
          </div>

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
                </ul>
              </div>
                                            <div className="summary-card comparison-card">
                                              <h3>Change vs Previous CSV</h3>

                                              {!summary?.top5_panels ? (
                                                <div className="comparison-empty-state">
                                                  Upload a second CSV to see comparison.
                                                </div>
                                              ) : (
                                                <div className="comparison-grid-3">
                                                  {/* Column 1 */}
                                                  <div>
                                                    <div className="comparison-col-title">PREVIOUS TOP 5</div>
                                                    <ul>
                                                      {summary.top5_panels.old_top5_comparison.map((row, idx) => (
                                                        <li key={idx} className="item-row comparison-panel-row">
                                                          <span className="item-name">{row.item_name}</span>
                                                          <div className="item-stats">
                                                            <span className="comparison-ranks">#{row.prev_rank}</span>
                                                            <span className="comparison-counts">{row.prev_qty} units</span>
                                                          </div>
                                                        </li>
                                                      ))}
                                                    </ul>
                                                  </div>

                                                  {/* Column 2 */}
                                                  <div>
                                                    <div className="comparison-col-title">OLD TOP 5 → CURRENT</div>
                                                    <ul>
                                                      {summary.top5_panels.old_top5_comparison.map((row, idx) => {
                                                        const statusText = row.status || "";
                                                        const lowerStatus = statusText.toLowerCase();

                                                        let statusClass = "status-neutral";
                                                        if (lowerStatus.includes("still")) statusClass = "status-good";
                                                        else if (lowerStatus.includes("dropped")) statusClass = "status-bad";
                                                        else if (lowerStatus.includes("entered") || lowerStatus.includes("new")) statusClass = "status-info";

                                                        let rowClass = "comparison-panel-row";
                                                        if (lowerStatus.includes("still")) rowClass += " row-still";
                                                        else if (lowerStatus.includes("dropped")) rowClass += " row-dropped";
                                                        else if (lowerStatus.includes("entered") || lowerStatus.includes("new")) rowClass += " row-entered";

                                                        return (
                                                          <li key={idx} className={`item-row ${rowClass}`}>
                                                            <span className="item-name">{row.item_name}</span>

                                                            <div className="item-stats comparison-middle-stats">
                                                              <span className="comparison-counts comparison-shift">
                                                                <span className="old-units">{row.prev_qty}</span>
                                                                <span className="comparison-arrow">→</span>
                                                                <span className="new-units">{row.curr_qty}</span>
                                                              </span>

                                                              <span className={`change comparison-percent ${
                                                                row.pct_change > 0 ? "pos" : row.pct_change < 0 ? "neg" : "neutral"
                                                              }`}>
                                                                {row.pct_change === null || row.pct_change === undefined
                                                                  ? "—"
                                                                  : `${row.pct_change > 0 ? "+" : ""}${row.pct_change.toFixed(1)}%`}
                                                              </span>

                                                              <span className={`comparison-status-badge ${statusClass}`}>
                                                                {row.status}
                                                              </span>
                                                            </div>
                                                          </li>
                                                        );
                                                      })}
                                                    </ul>
                                                  </div>

                                                  {/* Column 3 */}
                                                  <div>
                                                    <div className="comparison-col-title">CURRENT TOP 5</div>
                                                    <ul>
                                                      {summary.top5_panels.new_top5.map((row, idx) => (
                                                        <li key={idx} className="item-row comparison-panel-row">
                                                          <span className="item-name">{row.item_name}</span>
                                                          <div className="item-stats">
                                                            <span className="comparison-ranks">#{row.curr_rank}</span>
                                                            <span className="comparison-counts">{row.curr_qty} units</span>
                                                          </div>
                                                        </li>
                                                      ))}
                                                    </ul>
                                                  </div>
                                                </div>
                                              )}
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
          
          <div className="summary-card focus-card">
  <h3>Content Focus</h3>
  <label htmlFor="top-item-select" className="focus-label">
    Choose which top item the content should focus on:
  </label>

  <select
    id="top-item-select"
    className="focus-select"
    value={selectedItem}
    onChange={(e) => setSelectedItem(e.target.value)}
  >
    {summary.top_items?.map((item, idx) => (
      <option key={idx} value={item.item_name}>
        {item.item_name}
      </option>
    ))}
  </select>

  {selectedItem && (
    <p className="focus-hint">
      Generated content will focus on <strong>{selectedItem}</strong>.
    </p>
  )}
</div>
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
            <ContentDisplay
            content={content}
            onRefresh={handleRefresh}
            refreshing={refreshing}
            selectedItem={selectedItem}
            />
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

