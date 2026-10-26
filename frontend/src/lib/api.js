// Thin wrapper around the DringlichAI FastAPI backend.
// All paths are relative so the same code works behind the Vite dev proxy and
// when FastAPI serves the production build from `frontend/dist`.

async function request(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body && body.detail) detail = body.detail
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

const json = (method, payload) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
})

export const api = {
  getPatients: () => request('/patients'),
  getDoctors: () => request('/doctors'),

  addDoctor: (doctor_name, specialty) =>
    request('/doctors', json('POST', { doctor_name, specialty })),

  setDoctorStatus: (doctor_name, status) =>
    request(`/doctors/${encodeURIComponent(doctor_name)}/status`, json('PATCH', { status })),

  treatPatient: (patient_name) =>
    request(`/patients/${encodeURIComponent(patient_name)}`, { method: 'DELETE' }),

  restorePatient: (patient) => request('/patients', json('POST', patient)),

  startTriage: (payload) => request('/triage', json('POST', payload)),

  decide: (payload) => request('/triage/decision', json('POST', payload))
}

// The backend broadcasts the literal string "update_queue" whenever the queue
// changes. Returns a small controller with a `close()` method.
export function openQueueSocket(onUpdate) {
  let socket = null
  let closed = false

  const connect = () => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    socket = new WebSocket(`${proto}://${window.location.host}/ws`)
    socket.onmessage = (event) => {
      if (event.data === 'update_queue') onUpdate()
    }
    socket.onclose = () => {
      if (!closed) setTimeout(connect, 2000)
    }
  }
  connect()

  return {
    close() {
      closed = true
      if (socket) socket.close()
    }
  }
}
