import { useState, useEffect } from 'react'
import './Settings.css'

function Settings({ onSettingsChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-5-mini-2025-08-07')
  const [saved, setSaved] = useState(false)
  const [balance, setBalance] = useState(null)
  const [checkingBalance, setCheckingBalance] = useState(false)

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedKey = localStorage.getItem('openai_api_key') || ''
    const savedModel = localStorage.getItem('openai_model') || 'gpt-5-mini-2025-08-07'
    setApiKey(savedKey)
    setModel(savedModel)
    onSettingsChange({ apiKey: savedKey, model: savedModel })
    if (savedKey) checkBalance(savedKey)
  }, [])

  // UPDATED: This now fetches actual usage ($ spent)
  const checkBalance = async (keyToCheck = apiKey) => {
    if (!keyToCheck || keyToCheck.length < 10) return
    
    setCheckingBalance(true)
    try {
      // Get dates for the current month
      const now = new Date();
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
      const today = now.toISOString().split('T')[0];

      // Fetch usage data (This is usually allowed by standard keys)
      const response = await fetch(`https://api.openai.com/v1/dashboard/billing/usage?start_date=${firstDay}&end_date=${today}`, {
        headers: {
          'Authorization': `Bearer ${keyToCheck}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        // OpenAI returns usage in cents (1/100th of a cent), so we divide by 100
        const totalSpent = data.total_usage ? (data.total_usage / 100).toFixed(2) : "0.00";
        
        setBalance({
          spent: `$${totalSpent}`,
          status: 'Active',
          info: 'Spent this month'
        })
      } else {
        // Fallback: If usage is blocked, just check if key is alive
        const ping = await fetch('https://api.openai.com/v1/models', {
          headers: { 'Authorization': `Bearer ${keyToCheck}` }
        })
        if (ping.ok) {
          setBalance({ status: 'Active', info: 'Balance hidden by OpenAI' })
        } else {
          const errorData = await response.json();
          if (errorData.error?.code === 'insufficient_quota') {
            setBalance({ error: 'Balance Empty (Top up required)' })
          } else {
            setBalance({ error: 'Invalid Key' })
          }
        }
      }
    } catch (err) {
      setBalance({ error: 'Connection Error' })
    } finally {
      setCheckingBalance(false)
    }
  }

  const handleSave = () => {
    localStorage.setItem('openai_api_key', apiKey)
    localStorage.setItem('openai_model', model)
    onSettingsChange({ apiKey, model })
    setSaved(true)
    checkBalance()
    setTimeout(() => setSaved(false), 2000)
  }

  const handleClear = () => {
    setApiKey('')
    setModel('gpt-5-mini-2025-08-07')
    setBalance(null)
    localStorage.removeItem('openai_api_key')
    localStorage.removeItem('openai_model')
    onSettingsChange({ apiKey: '', model: 'gpt-5-mini-2025-08-07' })
  }

  const isConfigured = apiKey.length > 0

  return (
    <div className="settings-container">
      <button 
        className={`settings-toggle ${isConfigured ? 'configured' : 'not-configured'}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path>
        </svg>
        <span>{isConfigured ? 'API Configured' : 'Configure API'}</span>
        {!isConfigured && <span className="pulse-dot"></span>}
      </button>

      {isOpen && (
        <div className="settings-panel">
          <div className="settings-header">
            <h3>API Settings</h3>
            <button className="close-btn" onClick={() => setIsOpen(false)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <div className="settings-body">
            <div className="form-group">
              <label htmlFor="api-key">OpenAI API Key</label>
              <input
                id="api-key"
                type="password"
                placeholder="sk-..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <p className="form-hint">Your API key is stored locally in your browser</p>
            </div>

            {/* UPDATED: Displays the Actual Dollars Spent */}
            {apiKey && (
              <div className="balance-section">
                {checkingBalance ? (
                  <p className="balance-loading">Checking balance...</p>
                ) : balance ? (
                  balance.error ? (
                    <p className="balance-error">⚠️ {balance.error}</p>
                  ) : (
                    <div className="balance-info">
                      <p className="balance-ok">✅ API Active</p>
                      {balance.spent && (
                        <p className="balance-spent">
                          Spent this month: <strong>{balance.spent}</strong>
                        </p>
                      )}
                      <p className="balance-detail">{balance.info}</p>
                      <a 
                        href="https://platform.openai.com/settings/organization/billing/overview" 
                        target="_blank" 
                        rel="noreferrer"
                        className="balance-link"
                      >
                        Check Full Balance ↗
                      </a>
                    </div>
                  )
                ) : null}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="model">Model</label>
              <input
                id="model"
                type="text"
                placeholder="gpt-5-mini-2025-08-07"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              />
            </div>

            <div className="settings-actions">
              <button className="clear-btn" onClick={handleClear}>Clear</button>
              <button className={`save-btn ${saved ? 'saved' : ''}`} onClick={handleSave}>
                {saved ? 'Saved!' : 'Save Settings'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Settings