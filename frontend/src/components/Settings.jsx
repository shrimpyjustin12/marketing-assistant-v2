import { useState, useEffect } from 'react'
import './Settings.css'

function Settings({ onSettingsChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-5-mini-2025-08-07')
  const [saved, setSaved] = useState(false)
  const [balance, setBalance] = useState(null) // 1. Add balance state
  const [checkingBalance, setCheckingBalance] = useState(false) // 2. Loading state for balance check

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedKey = localStorage.getItem('openai_api_key') || ''
    const savedModel = localStorage.getItem('openai_model') || 'gpt-5-mini-2025-08-07'
    setApiKey(savedKey)
    setModel(savedModel)
    onSettingsChange({ apiKey: savedKey, model: savedModel })
    if (savedKey) checkBalance(savedKey) // 3. Check balance if key exists
  }, [])

  // 4. Balance checker function
  const checkBalance = async (keyToCheck = apiKey) => {
    if (!keyToCheck || keyToCheck.length < 10) return
    
    setCheckingBalance(true)
    try {
      const response = await fetch('https://api.openai.com/v1/dashboard/billing/subscription', {
        headers: {
          'Authorization': `Bearer ${keyToCheck}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        // You can also fetch usage data
        const usageResponse = await fetch('https://api.openai.com/v1/dashboard/billing/usage', {
          headers: {
            'Authorization': `Bearer ${keyToCheck}`
          }
        })
        
        if (usageResponse.ok) {
          const usageData = await usageResponse.json()
          setBalance({
            plan: data.plan?.title || 'Pay-as-you-go',
            expires: data.access_until ? new Date(data.access_until * 1000).toLocaleDateString() : 'N/A',
            // You can add more fields if needed
          })
        } else {
          setBalance({ plan: 'Valid key', expires: 'Unknown' })
        }
      } else {
        setBalance({ error: 'Invalid key or no access' })
      }
    } catch (err) {
      console.log('Could not fetch balance')
      setBalance({ error: 'Could not verify' })
    } finally {
      setCheckingBalance(false)
    }
  }

  const handleSave = () => {
    localStorage.setItem('openai_api_key', apiKey)
    localStorage.setItem('openai_model', model)
    onSettingsChange({ apiKey, model })
    setSaved(true)
    checkBalance() // 5. Check balance when saving new key
    setTimeout(() => setSaved(false), 2000)
  }

  const handleClear = () => {
    setApiKey('')
    setModel('gpt-5-mini-2025-08-07')
    setBalance(null) // 6. Clear balance when clearing key
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

            {/* 7. Balance display section */}
            {apiKey && (
              <div className="balance-section">
                {checkingBalance ? (
                  <p className="balance-loading">Checking balance...</p>
                ) : balance ? (
                  balance.error ? (
                    <p className="balance-error">⚠️ {balance.error}</p>
                  ) : (
                    <div className="balance-info">
                      <p className="balance-ok">✅ API Key Active</p>
                      {balance.plan && <p className="balance-plan">Plan: {balance.plan}</p>}
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
              <p className="form-hint">e.g., gpt-4o-mini, gpt-4o, gpt-3.5-turbo</p>
            </div>

            <div className="settings-actions">
              <button className="clear-btn" onClick={handleClear}>
                Clear
              </button>
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