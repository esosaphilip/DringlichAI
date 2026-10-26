import { useState } from 'react'
import { PlusIcon } from './Icons.jsx'
import KpiCard from './KpiCard.jsx'
import { palette, waitMinutes } from '../lib/priority.js'

const LOAD_CAP = 4

const STATUS_META = (t) => ({
  available: { text: t.stAvailable, bg: '#f0fdf4', fg: '#166534', dot: '#16a34a' },
  break: { text: t.stBreak, bg: '#fef9c3', fg: '#854d0e', dot: '#ca8a04' },
  off: { text: t.stOff, bg: '#f1f5f9', fg: '#475569', dot: '#94a3b8' }
})

const ORDER = { available: 0, break: 1, off: 2 }

function initialsOf(name) {
  const parts = String(name || '').replace(/^Dr\.\s*/i, '').split(' ').filter(Boolean)
  return ((parts[0] || '')[0] || '') + ((parts[parts.length - 1] || '')[0] || '')
}

export default function DoctorsScreen({ t, lang, doctors, patients, nowMinutes, onToggleStatus, onAddDoctor }) {
  const [name, setName] = useState('')
  const [spec, setSpec] = useState('')

  const meta = STATUS_META(t)
  const sorted = doctors
    .slice()
    .sort((a, b) => (ORDER[a.status] ?? 3) - (ORDER[b.status] ?? 3))

  const onDuty = doctors.filter((d) => d.status !== 'off').length
  const avgLoad = onDuty ? (patients.length / onDuty).toFixed(1) : '0'
  const avgLoadText = lang === 'de' ? avgLoad.replace('.', ',') : avgLoad

  const submit = (event) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    onAddDoctor(trimmed, spec.trim())
    setName('')
    setSpec('')
  }

  return (
    <div className="stack">
      <section className="kpi-row" aria-label="Staff overview">
        <KpiCard
          label={t.sAvailable}
          value={doctors.filter((d) => d.status === 'available').length}
          color="#166534"
        />
        <KpiCard
          label={t.sBreak}
          value={doctors.filter((d) => d.status === 'break').length}
          color="#854d0e"
        />
        <KpiCard label={t.kLoad} value={avgLoadText} />
        <KpiCard
          label={t.sOff}
          value={doctors.filter((d) => d.status === 'off').length}
          color="#475569"
        />
      </section>

      <section className="doctor-grid" aria-label={t.navDoctors}>
        {sorted.map((d) => {
          const load = d.active_load || 0
          const full = load >= LOAD_CAP
          const sm = meta[d.status] || meta.available
          const mine = patients
            .filter((p) => p.doctor_name === d.doctor_name)
            .sort((a, b) => a.priority - b.priority)

          return (
            <article
              key={d.doctor_name}
              className={`doctor-card${full ? ' is-full' : ''}${d.status === 'off' ? ' is-off' : ''}`}
            >
              <div className="doctor-top">
                <span className="doctor-avatar">{initialsOf(d.doctor_name)}</span>
                <div className="doctor-ident">
                  <h3 className="doctor-name">{d.doctor_name}</h3>
                  <div className="doctor-spec">{d.specialty}</div>
                </div>
                <span className="status-pill" style={{ background: sm.bg, color: sm.fg }}>
                  <span className="status-dot" style={{ background: sm.dot }} />
                  {sm.text}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div className="load-row">
                  <span className="load-label">{t.thLoad}</span>
                  <span className={`load-value${full ? ' is-full' : ''}`}>
                    {load} / {LOAD_CAP} {t.patients}
                  </span>
                </div>
                <div className="slots">
                  {[0, 1, 2, 3].map((i) => (
                    <span
                      key={i}
                      className={`slot${i < load ? (full ? ' is-full' : ' is-used') : ''}`}
                    />
                  ))}
                </div>
              </div>

              <div className="doctor-patients">
                {mine.map((p) => {
                  const level = p.priority >= 1 && p.priority <= 5 ? p.priority : 5
                  return (
                    <div key={p.patient_name} className="mini-patient">
                      <span className="dot" style={{ background: palette(level).dot }} />
                      <span className="mini-code">{`P${level}`}</span>
                      <span className="mini-name">{p.patient_name}</span>
                      <span className="mini-wait">
                        {waitMinutes(p.appointment_time, nowMinutes)} {t.min}
                      </span>
                    </div>
                  )
                })}
                {mine.length === 0 && <div className="no-patients">{t.noPatients}</div>}
              </div>

              <div className="doctor-actions">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() =>
                    onToggleStatus(d.doctor_name, d.status === 'break' ? 'available' : 'break')
                  }
                >
                  {d.status === 'break' ? t.endBreak : t.setBreak}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() =>
                    onToggleStatus(d.doctor_name, d.status === 'off' ? 'available' : 'off')
                  }
                >
                  {d.status === 'off' ? t.setOn : t.setOff}
                </button>
              </div>
            </article>
          )
        })}

        <form className="add-card" onSubmit={submit}>
          <div className="add-card-head">
            <span className="add-avatar">
              <PlusIcon size={20} strokeWidth={2.2} />
            </span>
            <h3>{t.addTitle}</h3>
          </div>

          <div className="field">
            <label htmlFor="dz-dname">{t.lDocName}</label>
            <input
              id="dz-dname"
              className="input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Dr. …"
            />
          </div>

          <div className="field">
            <label htmlFor="dz-dspec">{t.lSpec}</label>
            <input
              id="dz-dspec"
              className="input"
              type="text"
              value={spec}
              onChange={(e) => setSpec(e.target.value)}
              placeholder={t.phSpec}
            />
          </div>

          <button type="submit" className="btn btn-primary">
            {t.addCta}
          </button>
        </form>
      </section>
    </div>
  )
}
