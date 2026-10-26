import { PlusIcon } from './Icons.jsx'

export default function Topbar({ t, lang, onLang, title, subtitle, clock, onNewPatient }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="topbar-title">
          <h1>{title}</h1>
          <div className="topbar-sub">{subtitle}</div>
        </div>

        <div className="live-pill">
          <span className="live-dot" />
          {t.live}
        </div>

        <div className="clock" aria-label="Current time">
          {clock}
        </div>

        <div className="seg" role="group" aria-label="Language">
          <button
            type="button"
            className={`seg-btn${lang === 'de' ? ' is-on' : ''}`}
            onClick={() => onLang('de')}
            aria-pressed={lang === 'de'}
          >
            DE
          </button>
          <button
            type="button"
            className={`seg-btn${lang === 'en' ? ' is-on' : ''}`}
            onClick={() => onLang('en')}
            aria-pressed={lang === 'en'}
          >
            EN
          </button>
        </div>

        <button type="button" className="btn btn-primary" onClick={onNewPatient}>
          <PlusIcon />
          {t.newPatient}
        </button>
      </div>
    </header>
  )
}
