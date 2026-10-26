import { useMemo, useState } from 'react'
import { CheckIcon, SearchIcon } from './Icons.jsx'
import KpiCard from './KpiCard.jsx'
import { palette, TARGET, waitMinutes } from '../lib/priority.js'

export default function QueueScreen({ t, patients, doctors, nowMinutes, newName, onTreated }) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState(0)

  const docByName = useMemo(() => {
    const map = {}
    doctors.forEach((d) => {
      map[d.doctor_name] = d
    })
    return map
  }, [doctors])

  const rows = useMemo(() => {
    return patients
      .map((p) => {
        const level = p.priority >= 1 && p.priority <= 5 ? p.priority : 5
        const wait = waitMinutes(p.appointment_time, nowMinutes)
        const target = TARGET[level - 1]
        return { ...p, level, wait, target, overdue: wait > target }
      })
      .sort((a, b) => a.level - b.level || String(a.appointment_time).localeCompare(String(b.appointment_time)))
  }, [patients, nowMinutes])

  const counts = useMemo(() => {
    const byLevel = { 0: rows.length, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }
    rows.forEach((r) => {
      byLevel[r.level] += 1
    })
    return byLevel
  }, [rows])

  const q = query.trim().toLowerCase()
  const visible = rows
    .filter((r) => !filter || r.level === filter)
    .filter(
      (r) =>
        !q ||
        r.patient_name.toLowerCase().includes(q) ||
        String(r.ticket || '').toLowerCase().includes(q)
    )

  const waiting = rows.length
  const critical = rows.filter((r) => r.level <= 2).length
  const overdueCount = rows.filter((r) => r.overdue).length

  return (
    <div className="stack">
      <section className="kpi-row" aria-label="Overview">
        <KpiCard label={t.kWaiting} value={waiting} />
        <KpiCard label={t.kCritical} value={critical} color="#991b1b" />
        <KpiCard label={t.kOverdue} value={overdueCount} color="#9a3412" hot={overdueCount > 0} />
        <KpiCard label={t.kDoctors} value={doctors.filter((d) => d.status === 'available').length} />
      </section>

      <section className="panel">
        <div className="panel-head">
          <div className="search">
            <label className="visually-hidden" htmlFor="dz-search">
              {t.search}
            </label>
            <SearchIcon />
            <input
              id="dz-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.search}
            />
          </div>

          <div className="chips" role="group" aria-label={t.filter}>
            {[0, 1, 2, 3, 4, 5].map((level) => {
              const on = filter === level
              const color = level ? palette(level) : null
              return (
                <button
                  key={level}
                  type="button"
                  className={`chip${on ? ' is-on' : ''}`}
                  onClick={() => setFilter(level)}
                  aria-pressed={on}
                >
                  {level > 0 && <span className="dot" style={{ background: color.dot }} />}
                  {level ? `P${level}` : t.all}
                  <span className="chip-count">{counts[level]}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="table">
          <div className="table-inner">
            <div className="table-head">
              <span>{t.thP}</span>
              <span>{t.thPatient}</span>
              <span>{t.thSym}</span>
              <span>{t.thDoc}</span>
              <span>{t.thWait}</span>
              <span className="right">{t.thAct}</span>
            </div>

            {visible.map((r) => {
              const c = palette(r.level)
              const doc = docByName[r.doctor_name]
              const ratio = Math.min(100, Math.round((r.wait / r.target) * 100))
              const barColor = r.overdue ? '#ea580c' : ratio > 70 ? '#ca8a04' : '#0284c7'
              const aiText = r.confidence
                ? `${t.aiConf} ${r.confidence} % · ${t.nurseOk}`
                : t.nurseOk
              const initials =
                String(r.doctor_name || '—')
                  .replace(/^Dr\.\s*/i, '')
                  .split(' ')
                  .filter(Boolean)
                  .map((w) => w[0])
                  .slice(0, 2)
                  .join('') || '—'

              return (
                <div key={r.patient_name} className={`row${r.level === 1 ? ' is-critical' : ''}`}>
                  <div>
                    <span
                      className="badge"
                      style={{ background: c.bg, color: c.fg, border: `1px solid ${c.bd}` }}
                    >
                      <span className="dot" style={{ background: c.dot }} />
                      {`P${r.level} · ${t.labels[r.level - 1]}`}
                    </span>
                  </div>

                  <div style={{ minWidth: 0 }}>
                    <div className="cell-name">
                      {r.patient_name}
                      {r.patient_name === newName && <span className="tag-new">{t.newTag}</span>}
                    </div>
                    <div className="cell-sub">
                      <span className="mono">{r.ticket || '—'}</span> · {aiText}
                    </div>
                  </div>

                  <div className="cell-sym">{r.sickness}</div>

                  <div className="doc-cell">
                    <span className="doc-avatar">{doc ? initials : '—'}</span>
                    <div style={{ minWidth: 0 }}>
                      <div className="doc-name">{r.doctor_name || '—'}</div>
                      <div className="doc-spec">{doc ? doc.specialty : ''}</div>
                    </div>
                  </div>

                  <div className="wait">
                    <div className="wait-line">
                      <span className={`wait-value${r.overdue ? ' is-overdue' : ''}`}>
                        {r.wait} {t.min}
                      </span>
                      <span className="wait-target">
                        / {r.target} {t.min}
                      </span>
                    </div>
                    <span className="wait-track">
                      <span className="wait-bar" style={{ width: `${ratio}%`, background: barColor }} />
                    </span>
                    {r.overdue && <span className="overdue-flag">{t.overTarget}</span>}
                  </div>

                  <div className="cell-action">
                    <button type="button" className="btn btn-danger" onClick={() => onTreated(r)}>
                      <CheckIcon />
                      {t.treated}
                    </button>
                  </div>
                </div>
              )
            })}

            {visible.length === 0 && <div className="empty">{t.empty}</div>}
          </div>
        </div>
      </section>
    </div>
  )
}
