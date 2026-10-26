import { CheckIcon, CloseIcon, ShieldIcon, SparkleIcon } from './Icons.jsx'
import { palette } from '../lib/priority.js'

const STAGE_INDEX = { form: 0, loading: 1, review: 2 }

function FormStage({ t, values, onChange, onNow, onAddChip, onSubmit, formError }) {
  return (
    <>
      <div className="drawer-body">
        <div className="field field-lg">
          <label htmlFor="dz-name">{t.lName}</label>
          <input
            id="dz-name"
            className="input"
            type="text"
            value={values.name}
            onChange={(e) => onChange('name', e.target.value)}
            placeholder={t.phName}
          />
        </div>

        <div className="field field-lg">
          <label htmlFor="dz-sym">{t.lSym}</label>
          <div className="chips" aria-label={t.quick}>
            {t.chips.map((chip) => (
              <button
                key={chip}
                type="button"
                className="chip"
                onClick={() => onAddChip(chip)}
              >
                {`+ ${chip}`}
              </button>
            ))}
          </div>
          <textarea
            id="dz-sym"
            className="input"
            rows={5}
            value={values.sym}
            onChange={(e) => onChange('sym', e.target.value)}
            placeholder={t.phSym}
          />
        </div>

        <div className="field field-lg">
          <label htmlFor="dz-time">{t.lTime}</label>
          <div className="time-row">
            <input
              id="dz-time"
              className="input"
              type="time"
              value={values.time}
              onChange={(e) => onChange('time', e.target.value)}
            />
            <button type="button" className="btn btn-ghost" onClick={onNow}>
              {t.now}
            </button>
          </div>
        </div>

        <div className="note">
          <ShieldIcon />
          {t.hitlNote}
        </div>
      </div>

      <div className="drawer-foot">
        <button type="button" className="btn btn-primary btn-block" onClick={onSubmit}>
          <SparkleIcon />
          {t.submit}
        </button>
        {formError && (
          <p className="form-error" role="alert">
            {t.formError}
          </p>
        )}
      </div>
    </>
  )
}

function LoadingStage({ t }) {
  return (
    <div className="loading">
      <div className="spinner" />
      <div>
        <div className="loading-title">{t.mLoadingTitle}</div>
        <p className="loading-sub">{t.mLoadingSub}</p>
      </div>
      <div className="loading-steps">
        <div className="loading-step">
          <span className="loading-step-dot" />
          {t.step1}
        </div>
        <div className="loading-step">
          <span className="loading-step-dot is-active" />
          {t.step2}
        </div>
        <div className="loading-step is-idle">
          <span className="loading-step-dot is-idle" />
          {t.step3}
        </div>
      </div>
    </div>
  )
}

function ReviewStage({ t, pending, override, onOverride, onApprove, onReject }) {
  const level = override || pending.level
  const c = palette(level)
  const doc = pending.doc

  return (
    <>
      <div className="drawer-body">
        <div className="review-top">
          <div>
            <div className="review-name">{pending.name}</div>
            <div className="review-meta">
              {t.lTime} · <span className="mono">{pending.time || '—'}</span>
            </div>
          </div>
          <div className="review-suggest">
            <div className="review-suggest-label">{t.mSuggested}</div>
            <span
              className="badge badge-lg"
              style={{ background: c.bg, color: c.fg, border: `1px solid ${c.bd}` }}
            >
              <span className="dot" style={{ background: c.dot }} />
              {`P${level} · ${t.labels[level - 1]}`}
            </span>
          </div>
        </div>

        <div className="why-card">
          <div className="why-head">
            <span className="why-title">{t.mWhy}</span>
            <span className="why-conf">{`${pending.conf} % ${t.mConf}`}</span>
          </div>
          <div className="why-track">
            <div className="why-fill" style={{ width: `${Math.min(100, pending.conf)}%` }} />
          </div>
          <p className="why-text">{pending.why || '—'}</p>
          <div className="why-source">
            {t.mSource}: {pending.chart || '—'}
          </div>
        </div>

        <div className="doc-assign">
          <span className="doc-assign-avatar">
            {String(pending.docName || '—')
              .replace(/^Dr\.\s*/i, '')
              .split(' ')
              .filter(Boolean)
              .map((w) => w[0])
              .slice(0, 2)
              .join('') || '—'}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="doc-assign-label">{t.mDoc}</div>
            <div className="doc-assign-name">{pending.docName || '—'}</div>
            <div className="doc-assign-spec">{pending.docSpec || ''}</div>
          </div>
          <span className="doc-assign-note">{t.mDocNote}</span>
        </div>

        <div>
          <div className="override-label">{t.mOverride}</div>
          <div className="pills" role="group" aria-label={t.mOverride}>
            {[1, 2, 3, 4, 5].map((p) => {
              const on = p === level
              const pc = palette(p)
              const style = on
                ? { background: pc.bg, color: pc.fg, border: `2px solid ${pc.dot}` }
                : undefined
              return (
                <button
                  key={p}
                  type="button"
                  className="pill"
                  onClick={() => onOverride(p === pending.level ? null : p)}
                  aria-pressed={on}
                  style={style}
                >
                  {`P${p}`}
                </button>
              )
            })}
          </div>
          {override && <p className="override-note">{t.overrideNote}</p>}
        </div>
      </div>

      <div className="drawer-foot">
        <div className="drawer-foot-row">
          <button type="button" className="btn-reject" onClick={onReject}>
            {t.reject}
          </button>
          <button type="button" className="btn-approve" onClick={() => onApprove(doc)}>
            <CheckIcon size={16} />
            {t.approve}
          </button>
        </div>
      </div>
    </>
  )
}

export default function IntakeDrawer({
  t,
  stage,
  values,
  onChange,
  onNow,
  onAddChip,
  onSubmit,
  formError,
  onClose,
  pending,
  override,
  onOverride,
  onApprove,
  onReject
}) {
  const stepIndex = STAGE_INDEX[stage]
  const titles = { form: t.intakeTitle, loading: t.loadingTitle, review: t.reviewTitle }
  const stepLabels = [t.stepForm, t.stepAi, t.stepApprove]

  return (
    <div className="drawer-root">
      <button
        type="button"
        className="drawer-scrim"
        onClick={onClose}
        aria-label={t.close}
        tabIndex={-1}
      />
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="dz-dtitle">
        <div className="drawer-head">
          <div className="drawer-head-main">
            <h2 id="dz-dtitle" className="drawer-title">
              {titles[stage]}
            </h2>
            <div className="steps" aria-label="Progress">
              {stepLabels.map((label, i) => (
                <div key={label} className="step">
                  <span className={`step-bar${i <= stepIndex ? ' is-done' : ''}`} />
                  <span className={`step-label${i === stepIndex ? ' is-current' : ''}`}>{label}</span>
                </div>
              ))}
            </div>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t.close}>
            <CloseIcon />
          </button>
        </div>

        {stage === 'form' && (
          <FormStage
            t={t}
            values={values}
            onChange={onChange}
            onNow={onNow}
            onAddChip={onAddChip}
            onSubmit={onSubmit}
            formError={formError}
          />
        )}

        {stage === 'loading' && <LoadingStage t={t} />}

        {stage === 'review' && pending && (
          <ReviewStage
            t={t}
            pending={pending}
            override={override}
            onOverride={onOverride}
            onApprove={onApprove}
            onReject={onReject}
          />
        )}
      </aside>
    </div>
  )
}
