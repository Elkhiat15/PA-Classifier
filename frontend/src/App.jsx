import { useMemo, useState } from 'react'
import './App.css'

const API_BASE = '/api'

// The LLM providers the backend supports (see policy_classifier/models.py).
const PROVIDERS = [
  { id: 'gemini', label: 'Gemini' },
  { id: 'mistral', label: 'Mistral' },
  { id: 'groq', label: 'Groq' },
]

const EVENT_TYPES = {
  user_input: { label: 'User Input', accent: '#3b82f6' },
  tool_call: { label: 'Tool Call', accent: '#a855f7' },
  tool_response: { label: 'Tool Response', accent: '#14b8a6' },
  model_output: { label: 'Model Output', accent: '#f97316' },
}

function typeMeta(type) {
  return EVENT_TYPES[type] || { label: type || 'Unknown', accent: '#64748b' }
}

function payloadText(event) {
  const payload = event?.payload
  if (typeof payload === 'string') return payload
  if (payload === undefined || payload === null) return ''
  return JSON.stringify(payload, null, 2)
}

async function classifyEvent(trace, eventId, provider) {
  const res = await fetch(`${API_BASE}/classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trace, event_id: eventId, provider }),
  })
  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status})`
    try {
      const body = await res.json()
      if (body && body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      /* keep the default message */
    }
    throw new Error(detail)
  }
  return res.json()
}

function App() {
  const [jsonText, setJsonText] = useState('')
  const [trace, setTrace] = useState(null)
  const [events, setEvents] = useState([])
  const [parseError, setParseError] = useState(null)
  const [results, setResults] = useState({})
  const [reasonOpen, setReasonOpen] = useState({})
  const [classifying, setClassifying] = useState(false)
  const [provider, setProvider] = useState('gemini')
  const [theme, setTheme] = useState(
    () => document.documentElement.dataset.theme || 'light',
  )

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem('pa-theme', next)
    } catch {
      /* storage unavailable — theme still applies for this session */
    }
  }

  const parsedCount = events.length

  const doneCount = useMemo(
    () =>
      Object.values(results).filter(
        (r) => r.status === 'done' || r.status === 'error',
      ).length,
    [results],
  )

  const pendingCount = parsedCount - doneCount

  const handleEventChange = (key, value) => {
    setEvents((prev) =>
      prev.map((e) => (e.key === key ? { ...e, content: value, payload: value } : e)),
    )
    // Editing invalidates previous result for this event
    setResults((prev) => {
      if (!prev[key]) return prev
      const next = { ...prev }
      delete next[key]
      return next
    })
    setReasonOpen((prev) => {
      if (!prev[key]) return prev
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  // Parse the whole trace, then classify each event one-by-one, showing
  // each result as soon as it arrives (no waiting for the full batch).
  const handleClassify = async () => {
    if (classifying) return

    let parsed
    try {
      parsed = JSON.parse(jsonText)
      if (!Array.isArray(parsed)) {
        throw new Error('Top-level JSON value must be a list (array).')
      }
    } catch (err) {
      setParseError(err.message || 'Invalid JSON')
      setTrace(null)
      setEvents([])
      setResults({})
      setReasonOpen({})
      return
    }

    const header = parsed.find(
      (item) => item && typeof item === 'object' && !('event_id' in item),
    )
    const evts = parsed.filter(
      (item) => item && typeof item === 'object' && 'event_id' in item,
    )

    if (!header || !('role' in header)) {
      setParseError('Missing trace metadata object with a "role" field.')
      setTrace(null)
      setEvents([])
      setResults({})
      setReasonOpen({})
      return
    }
    if (evts.length === 0) {
      setParseError('No events found — each event object needs an "event_id" field.')
      setTrace(null)
      setEvents([])
      setResults({})
      setReasonOpen({})
      return
    }

    setParseError(null)
    setTrace(header)

    const mapped = evts.map((e, i) => ({
      ...e,
      key: `${e.event_id ?? 'event'}-${i}`,
      content: payloadText(e),
    }))
    setEvents(mapped)
    setReasonOpen({})
    setResults(
      Object.fromEntries(mapped.map((e) => [e.key, { status: 'pending' }])),
    )
    setClassifying(true)

    // Reconstruct the trace the backend expects: metadata first, then events.
    const bodyTrace = [
      header,
      ...mapped.map((e) => ({
        event_id: e.event_id,
        event_type: e.event_type,
        payload: e.payload ?? e.content,
      })),
    ]

    for (const event of mapped) {
      try {
        const decision = await classifyEvent(bodyTrace, event.event_id, provider)
        setResults((prev) => ({
          ...prev,
          [event.key]: { status: 'done', ...decision },
        }))
      } catch (err) {
        setResults((prev) => ({
          ...prev,
          [event.key]: {
            status: 'error',
            error: err.message || 'Classification failed',
          },
        }))
      }
    }

    setClassifying(false)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Policy Alignment Classifier</h1>
          <p className="subtitle">
            Paste a trace as JSON, then classify each event against the policy.
          </p>
        </div>
        <div className="header-right">
          {trace && (
            <div className="trace-chip" title="Trace metadata">
              <span className="trace-id">{trace.trace_id || 'trace'}</span>
              <span className="trace-role">{trace.role || 'unknown role'}</span>
            </div>
          )}
          <label className="provider-picker" title="LLM provider">
            <span className="provider-label">Model</span>
            <select
              className="provider-select"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              disabled={classifying}
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            title={
              theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'
            }
            aria-label={
              theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'
            }
          >
            {theme === 'dark' ? (
              <svg
                viewBox="0 0 24 24"
                width="17"
                height="17"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
              </svg>
            ) : (
              <svg
                viewBox="0 0 24 24"
                width="17"
                height="17"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
            <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </header>

      <section className="input-panel">
        <div className="input-panel-head">
          <label htmlFor="trace-json">Trace JSON (list of events)</label>
          <div className="input-actions">
            <span className="event-count">
              {parsedCount} event{parsedCount === 1 ? '' : 's'} mapped
            </span>
          </div>
        </div>
        <textarea
          id="trace-json"
          className="json-input"
          value={jsonText}
          spellCheck={false}
          onChange={(e) => setJsonText(e.target.value)}
          placeholder='Paste a JSON list, e.g. [ { "trace_id": "...", "role": "employee" }, { "event_id": "...", ... } ]'
        />
        {parseError && <div className="parse-error">JSON error: {parseError}</div>}
        {parsedCount > 0 && !parseError && (
          <div className="parse-status">
            {pendingCount > 0
              ? `${pendingCount} event${pendingCount === 1 ? '' : 's'} awaiting classification`
              : 'All events classified'}
            {doneCount > 0 && ` · ${doneCount}/${parsedCount} done`}
          </div>
        )}
        <div className="classify-bar">
          <span className="classify-hint">
            {parsedCount > 0
              ? `Classify all ${parsedCount} parsed event${parsedCount === 1 ? '' : 's'}`
              : 'Paste a trace, then classify its events'}
          </span>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleClassify}
            disabled={classifying || !jsonText.trim()}
          >
            {classifying ? 'Classifying…' : 'Classify'}
          </button>
        </div>
      </section>

      <section className="events">
        {events.map((event, idx) => {
          const meta = typeMeta(event.event_type)
          const result = results[event.key]
          const isOpen = !!reasonOpen[event.key]
          const rules = result?.policy_rule_ids || []
          return (
            <article
              className="event-card"
              key={event.key}
              style={{ '--accent': meta.accent }}
            >
              <div className="event-side">
                <div className="event-head">
                  <span className="type-badge">{meta.label}</span>
                  <span className="event-id">{event.event_id || `event ${idx + 1}`}</span>
                </div>
                <div className="payload-caption">Payload</div>
                <textarea
                  className="event-payload"
                  value={event.content}
                  spellCheck={false}
                  onChange={(e) => handleEventChange(event.key, e.target.value)}
                  aria-label={`${meta.label} payload ${event.event_id || idx + 1}`}
                />
              </div>

              <div className="result-side">
                <div className="result-title">Classification</div>

                {!result && (
                  <div className="result-empty">Not classified yet.</div>
                )}

                {result && result.status === 'pending' && (
                  <div className="result-pending">
                    <span className="spinner" aria-hidden="true" />
                    Classifying…
                  </div>
                )}

                {result && result.status === 'error' && (
                  <div className="result-error">{result.error}</div>
                )}

                {result && result.status === 'done' && (
                  <div className="result-body">
                    <div className="result-row">
                      <span className="result-label">Model prediction</span>
                      <span
                        className={`verdict verdict-${String(result.decision).toLowerCase()}`}
                      >
                        {result.decision}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-label">Confidence</span>
                      <span className="confidence">
                        <span className="conf-bar">
                          <span
                            className="conf-fill"
                            style={{ width: `${result.confidence * 100}%` }}
                          />
                        </span>
                        <span className="conf-num">
                          {(result.confidence * 100).toFixed(1)}%
                        </span>
                      </span>
                    </div>

                    <div className="result-row rules-row">
                      <span className="result-label">Policy rules</span>
                      <span className="rule-chips">
                        {rules.length > 0 ? (
                          rules.map((id) => (
                            <span className="rule-chip" key={id}>
                              {id}
                            </span>
                          ))
                        ) : (
                          <span className="rule-empty">—</span>
                        )}
                      </span>
                    </div>

                    <div className="result-row reason-row">
                      <span className="result-label">Reason</span>
                      <button
                        type="button"
                        className={`reason-toggle${isOpen ? ' open' : ''}`}
                        title={isOpen ? 'Hide reason' : 'Show reason'}
                        aria-expanded={isOpen}
                        onClick={() =>
                          setReasonOpen((prev) => ({ ...prev, [event.key]: !isOpen }))
                        }
                      >
                        <svg
                          viewBox="0 0 24 24"
                          width="16"
                          height="16"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                        <span>{isOpen ? 'Hide' : 'Show'}</span>
                      </button>
                    </div>

                    {isOpen && (
                      <div className="reason-text">{result.reasoning}</div>
                    )}
                  </div>
                )}
              </div>
            </article>
          )
        })}

        {events.length === 0 && !parseError && (
          <div className="empty-state">
            Paste a JSON list above and press <strong>Classify</strong> to run the
            policy alignment classifier.
          </div>
        )}
      </section>
    </div>
  )
}

export default App