import { useEffect } from 'react'
import CopyButton from './CopyButton'
import './ContentDisplay.css'

function ContentDisplay({ content }) {

  if (!content) return null

  // Add useEffect for tooltips
  useEffect(() => {
    const positionTooltips = () => {
      const tooltipParents = document.querySelectorAll('.tooltip-parent');
      
      tooltipParents.forEach(parent => {
        parent.removeEventListener('mouseenter', handleMouseEnter);
        parent.removeEventListener('mouseleave', handleMouseLeave);
        
        parent.addEventListener('mouseenter', handleMouseEnter);
        parent.addEventListener('mouseleave', handleMouseLeave);
      });
    };
    
    const handleMouseEnter = (e) => {
      const parent = e.currentTarget;
      const tooltip = parent.querySelector('.idea-tooltip');
      if (!tooltip) return;
      
      const rect = parent.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const tooltipWidth = 340;
      const offset = 20;
      
      let left = rect.right + offset;
      let top = rect.top + (rect.height / 2) - 60;
      
      if (left + tooltipWidth > viewportWidth - 20) {
        left = rect.left - tooltipWidth - offset;
        tooltip.classList.add('left-side');
      } else {
        tooltip.classList.remove('left-side');
      }
      
      if (top < 20) top = 20;
      
      const tooltipHeight = tooltip.offsetHeight || 150;
      
      if (top + tooltipHeight > viewportHeight - 20) {
        top = viewportHeight - tooltipHeight - 20;
      }
      
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
    };
    
    const handleMouseLeave = (e) => {
      const tooltip = e.currentTarget.querySelector('.idea-tooltip');
      if (tooltip) {
        tooltip.style.left = '';
        tooltip.style.top = '';
        tooltip.classList.remove('left-side');
      }
    };
    
    positionTooltips();
    
    window.addEventListener('scroll', positionTooltips, true);
    window.addEventListener('resize', positionTooltips);
    
    return () => {
      window.removeEventListener('scroll', positionTooltips, true);
      window.removeEventListener('resize', positionTooltips);
      
      const tooltipParents = document.querySelectorAll('.tooltip-parent');
      tooltipParents.forEach(parent => {
        parent.removeEventListener('mouseenter', handleMouseEnter);
        parent.removeEventListener('mouseleave', handleMouseLeave);
      });
    };
  }, [content]);

  return (
    <div className="content-grid">

      {/* Instagram Section */}
      <div className="content-card instagram-card">
        <div className="card-header">
          <h3>📸 Instagram</h3>
          <CopyButton text={content.instagram?.caption + '\n\n' + content.instagram?.hashtags?.join(' ') || ''} />
        </div>

        <div className="card-content">
          <div className="caption-item">
            <p className="caption-text" style={{ whiteSpace: 'pre-line' }}>{content.instagram?.caption}</p>
            <CopyButton text={content.instagram?.caption || ''} />
          </div>

          <div className="hashtags-container">
            {content.instagram?.hashtags?.map((tag, idx) => (
              <span key={idx} className="hashtag instagram-hashtag" onClick={() => navigator.clipboard.writeText(tag)}>
                {tag}
              </span>
            ))}
          </div>
          <p className="hashtag-hint">Click any hashtag to copy it individually</p>
        </div>
      </div>

      {/* TikTok Section */}
      <div className="content-card tiktok-card">
        <div className="card-header">
          <h3>🎵 TikTok</h3>
          <CopyButton text={content.tiktok?.caption + '\n\n' + content.tiktok?.hashtags?.join(' ') || ''} />
        </div>

        <div className="card-content">
          <div className="caption-item">
            <p className="caption-text">{content.tiktok?.caption}</p>
            <CopyButton text={content.tiktok?.caption || ''} />
          </div>

          <div className="hashtags-container">
            {content.tiktok?.hashtags?.map((tag, idx) => (
              <span key={idx} className="hashtag tiktok-hashtag" onClick={() => navigator.clipboard.writeText(tag)}>
                {tag}
              </span>
            ))}
          </div>
          <p className="hashtag-hint">Click any hashtag to copy it individually</p>
        </div>
      </div>

      {/* Promotion Ideas */}
      <div className="content-card ideas-card">
        <div className="card-header">
          <h3>💡 Promotion Ideas</h3>
          <CopyButton text={content.promotion_ideas?.map(i => i.text).join('\n\n') || ''} />
        </div>

        <div className="card-content">
          {content.promotion_ideas?.map((idea, idx) => (
            <div key={idx} className="idea-item tooltip-parent">
              <div className="idea-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 16v-4" />
                  <path d="M12 8h.01" />
                </svg>
              </div>

              <div className="idea-content">
                <p className="idea-text">{idea.text}</p>
                <CopyButton text={idea.text} />

                <div className="idea-tooltip">
                  <strong>Why this recommendation:</strong>
                  <p>{idea.reason}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

export default ContentDisplay