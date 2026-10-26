import { LogoIcon, QueueIcon, StethoscopeIcon } from './Icons.jsx'

export default function Sidebar({ t, screen, onNavigate, kWaiting, hasOverloaded, capPct, capText }) {
  return (
    <nav className="sidebar" aria-label="Main">
      <div className="brand">
        <div className="brand-mark">
          <LogoIcon />
        </div>
        <div>
          <div className="brand-name">
            Dringlich<span>AI</span>
          </div>
          <div className="brand-sub">{t.dept}</div>
        </div>
      </div>

      <div className="nav-group">
        <div className="nav-heading">{t.navWork}</div>

        <button
          type="button"
          className={`nav-btn${screen === 'queue' ? ' is-active' : ''}`}
          onClick={() => onNavigate('queue')}
          aria-current={screen === 'queue' ? 'page' : undefined}
        >
          <QueueIcon />
          <span className="nav-label">{t.navQueue}</span>
          <span className={`nav-count${screen === 'queue' ? ' is-active' : ''}`}>{kWaiting}</span>
        </button>

        <button
          type="button"
          className={`nav-btn${screen === 'doctors' ? ' is-active' : ''}`}
          onClick={() => onNavigate('doctors')}
          aria-current={screen === 'doctors' ? 'page' : undefined}
        >
          <StethoscopeIcon />
          <span className="nav-label">{t.navDoctors}</span>
          {hasOverloaded && <span className="overload-dot" aria-label={t.overloadHint} />}
        </button>
      </div>

      <div className="sidebar-foot">
        <div className="cap-card">
          <div className="cap-title">{t.capTitle}</div>
          <div className="cap-track">
            <div className={`cap-fill${capPct > 80 ? ' is-hot' : ''}`} style={{ width: `${capPct}%` }} />
          </div>
          <div className="cap-text">{capText}</div>
        </div>

        <div className="user">
          <span className="avatar">AS</span>
          <div>
            <div className="user-name">Anna Schmitt</div>
            <div className="user-role">{t.role}</div>
          </div>
        </div>
      </div>
    </nav>
  )
}
