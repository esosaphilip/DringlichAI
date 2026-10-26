import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Topbar from './components/Topbar.jsx'
import QueueScreen from './components/QueueScreen.jsx'
import DoctorsScreen from './components/DoctorsScreen.jsx'
import IntakeDrawer from './components/IntakeDrawer.jsx'
import Toast from './components/Toast.jsx'
import { PlusIcon } from './components/Icons.jsx'
import { api, openQueueSocket } from './lib/api.js'
import { dict } from './lib/i18n.js'
import { clockString } from './lib/priority.js'

const LOAD_CAP = 4
const TOAST_MS = 5000

export default function App() {
  const [lang, setLang] = useState('en')
  const [screen, setScreen] = useState('queue')

  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])
  const [loadError, setLoadError] = useState(false)

  const [now, setNow] = useState(() => new Date())

  const [stage, setStage] = useState(null)
  const [form, setForm] = useState({ name: '', sym: '', time: '' })
  const [formError, setFormError] = useState(false)
  const [pending, setPending] = useState(null)
  const [override, setOverride] = useState(null)

  const [toast, setToast] = useState(null)
  const [newName, setNewName] = useState(null)

  const toastTimer = useRef(null)
  const t = useMemo(() => dict(lang), [lang])

  const nowMinutes = now.getHours() * 60 + now.getMinutes()

  const showToast = useCallback((message, undoPayload = null) => {
    clearTimeout(toastTimer.current)
    setToast({ message, undo: undoPayload })
    toastTimer.current = setTimeout(() => setToast(null), TOAST_MS)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [patientsRes, doctorsRes] = await Promise.all([api.getPatients(), api.getDoctors()])
      setPatients(patientsRes.queue || [])
      setDoctors(doctorsRes.doctors || [])
      setLoadError(false)
    } catch {
      setLoadError(true)
    }
  }, [])

  useEffect(() => {
    refresh()
    const socket = openQueueSocket(refresh)
    const ticker = setInterval(() => setNow(new Date()), 20000)
    return () => {
      socket.close()
      clearInterval(ticker)
    }
  }, [refresh])

  useEffect(() => () => clearTimeout(toastTimer.current), [])

  /* ------------------------------------------------------------- queue --- */

  const handleTreated = async (patient) => {
    try {
      await api.treatPatient(patient.patient_name)
      setPatients((prev) => prev.filter((p) => p.patient_name !== patient.patient_name))
      showToast(`${patient.patient_name} ${t.treatedMsg}`, patient)
    } catch (err) {
      showToast(err.message)
    }
  }

  const handleUndo = async () => {
    const item = toast?.undo
    if (!item) return
    clearTimeout(toastTimer.current)
    setToast(null)
    try {
      await api.restorePatient({
        patient_name: item.patient_name,
        sickness: item.sickness,
        priority: item.priority,
        doctor_name: item.doctor_name,
        status: item.status,
        appointment_time: item.appointment_time,
        ticket: item.ticket ?? null,
        confidence: item.confidence ?? null
      })
      await refresh()
    } catch (err) {
      showToast(err.message)
    }
  }

  /* ----------------------------------------------------------- doctors --- */

  const handleToggleStatus = async (doctorName, status) => {
    try {
      const res = await api.setDoctorStatus(doctorName, status)
      await refresh()
      if (res && res.reassigned) showToast(`${res.reassigned} ${t.reassigned}`)
    } catch (err) {
      showToast(err.message)
    }
  }

  const handleAddDoctor = async (name, specialty) => {
    const full = name.startsWith('Dr.') ? name : `Dr. ${name}`
    try {
      await api.addDoctor(full, specialty || '—')
      await refresh()
    } catch (err) {
      showToast(err.message)
    }
  }

  /* ------------------------------------------------------------ intake --- */

  const openIntake = () => {
    setForm({ name: '', sym: '', time: clockString(new Date()) })
    setFormError(false)
    setOverride(null)
    setStage('form')
  }

  const closeDrawer = () => {
    setStage(null)
    setPending(null)
    setOverride(null)
  }

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    if (field === 'name' || field === 'sym') setFormError(false)
  }

  const handleAddChip = (chip) => {
    setForm((prev) => {
      const current = prev.sym.trim().replace(/[\s,]+$/, '')
      return { ...prev, sym: current ? `${current}, ${chip.toLowerCase()}` : chip }
    })
    setFormError(false)
  }

  const handleSubmitIntake = async () => {
    if (!form.name.trim() || !form.sym.trim()) {
      setFormError(true)
      return
    }
    setStage('loading')
    const threadId = `thread-${Date.now()}`
    try {
      const res = await api.startTriage({
        patient_name: form.name.trim(),
        sickness: form.sym.trim(),
        appointment_time: form.time,
        thread_id: threadId
      })
      const assigned = doctors.find((d) => d.doctor_name === res.assigned_doctor)
      setPending({
        threadId,
        name: res.patient_name,
        time: form.time,
        level: res.ai_suggested_priority,
        conf: res.ai_confidence ?? 0,
        why: res.ai_reasoning || '',
        chart: res.ai_guideline || '',
        docName: res.assigned_doctor,
        docSpec: assigned ? assigned.specialty : ''
      })
      setOverride(null)
      setStage('review')
    } catch (err) {
      setStage('form')
      showToast(err.message)
    }
  }

  const handleApprove = async () => {
    if (!pending) return
    const level = override || pending.level
    try {
      await api.decide({
        thread_id: pending.threadId,
        approved: true,
        priority_override: override
      })
      setNewName(pending.name)
      closeDrawer()
      setScreen('queue')
      await refresh()
      showToast(`${pending.name} ${t.queuedAs} P${level} ${t.with} ${pending.docName}`)
    } catch (err) {
      showToast(err.message)
    }
  }

  const handleReject = async () => {
    if (pending) {
      try {
        await api.decide({ thread_id: pending.threadId, approved: false })
      } catch {
        /* rejection needs no feedback beyond the toast */
      }
    }
    closeDrawer()
    showToast(t.rejected)
  }

  /* -------------------------------------------------------------- shell --- */

  const onDuty = doctors.filter((d) => d.status !== 'off').length
  const capacity = onDuty * LOAD_CAP
  const capPct = capacity ? Math.min(100, Math.round((patients.length / capacity) * 100)) : 100
  const hasOverloaded = doctors.some((d) => d.status !== 'off' && (d.active_load || 0) >= LOAD_CAP)

  return (
    <div className="app">
      <Sidebar
        t={t}
        screen={screen}
        onNavigate={setScreen}
        kWaiting={patients.length}
        hasOverloaded={hasOverloaded}
        capPct={capPct}
        capText={`${capPct} %${t.capText}`}
      />

      <div className="main">
        <Topbar
          t={t}
          lang={lang}
          onLang={setLang}
          title={screen === 'queue' ? t.qTitle : t.dTitle}
          subtitle={screen === 'queue' ? t.qSub : t.dSub}
          clock={clockString(now)}
          onNewPatient={openIntake}
        />

        <main className="content">
          {loadError && (
            <div
              className="note"
              role="alert"
              style={{ background: '#fef2f2', borderColor: '#fecaca', color: '#991b1b' }}
            >
              {t.backendError}
            </div>
          )}

          {screen === 'queue' ? (
            <QueueScreen
              t={t}
              patients={patients}
              doctors={doctors}
              nowMinutes={nowMinutes}
              newName={newName}
              onTreated={handleTreated}
            />
          ) : (
            <DoctorsScreen
              t={t}
              lang={lang}
              doctors={doctors}
              patients={patients}
              nowMinutes={nowMinutes}
              onToggleStatus={handleToggleStatus}
              onAddDoctor={handleAddDoctor}
            />
          )}
        </main>
      </div>

      <button type="button" className="fab" onClick={openIntake} aria-label={t.newPatient}>
        <PlusIcon size={28} />
      </button>

      {stage && (
        <IntakeDrawer
          t={t}
          stage={stage}
          values={form}
          onChange={handleChange}
          onNow={() => handleChange('time', clockString(new Date()))}
          onAddChip={handleAddChip}
          onSubmit={handleSubmitIntake}
          formError={formError}
          onClose={closeDrawer}
          pending={pending}
          override={override}
          onOverride={setOverride}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}

      {toast && (
        <Toast
          message={toast.message}
          canUndo={!!toast.undo}
          undoLabel={t.undo}
          onUndo={handleUndo}
        />
      )}
    </div>
  )
}
