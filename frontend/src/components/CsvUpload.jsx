import { useRef, useState } from 'react'
import './CsvUpload.css'

function CsvUpload({ onUpload, loading }) {
  const fileInputRef = useRef(null)
  const [fileName, setFileName] = useState(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFileSelect = (file) => {
    if (file && file.name.endsWith('.csv')) {
      setFileName(file.name)
      onUpload(file)
    } else {
      alert('Please select a CSV file')
    }
  }

  const handleChange = (e) => {
    const file = e.target.files[0]
    handleFileSelect(file)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    handleFileSelect(file)
  }

  return (
    <div
      className={`upload-zone ${isDragging ? 'dragging' : ''} ${loading ? 'loading' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !loading && fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={handleChange}
        disabled={loading}
      />

      <div className="upload-content">
        {loading ? (
          <>
            <div className="spinner"></div>
            <p className="upload-text">Processing...</p>
          </>
        ) : (
          <>
            <div className="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="upload-text">
              {fileName ? (
                <>
                  <span className="file-name">{fileName}</span>
                  <span className="file-hint">Click to upload a different file</span>
                </>
              ) : (
                <>
                  <span className="main-text">Drop your CSV file here</span>
                  <span className="sub-text">or click to browse</span>
                </>
              )}
            </p>
            <p className="format-hint">
              Expected format: date, item_name, quantity_sold, category
            </p>
          </>
        )}
      </div>
    </div>
  )
}

export default CsvUpload

