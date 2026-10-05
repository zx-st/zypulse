import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'

const PORTIONS = [
  { key: '0.25', label: '1/4', factor: 0.25 },
  { key: '0.5', label: '1/2', factor: 0.5 },
  { key: '0.75', label: '3/4', factor: 0.75 },
  { key: '1', label: '1', factor: 1 },
  { key: '1.5', label: '1.5', factor: 1.5 },
  { key: '2', label: '2', factor: 2 },
  { key: 'custom', label: 'Custom', factor: null },
]

const MEAL_TYPES = ['breakfast', 'lunch', 'dinner', 'snack']

function factorOf(key) {
  const p = PORTIONS.find((x) => x.key === key)
  return p ? p.factor : 1
}

function recompute(item) {
  const f = item.portion_key === 'custom' ? (Number(item.custom_factor) || 1) : factorOf(item.portion_key)
  return {
    ...item,
    carbs: Math.round((item.base_carbs || 0) * f * 10) / 10,
    sugar: Math.round((item.base_sugar || 0) * f * 10) / 10,
  }
}

function emptyDraft() {
  return {
    meal_type: 'breakfast',
    items: [],
    notes: '',
    include_in_visit: false,
    editingId: null,
  }
}

export default function MealLogPage({ userId, language }) {
  const t = (text) => translateText(language, text)
  const [draft, setDraft] = useState(emptyDraft())
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [recent, setRecent] = useState([])
  const [meals, setMeals] = useState([])
  const [photo, setPhoto] = useState(null) // simulated review payload
  const [photoFile, setPhotoFile] = useState(null)
  const [msg, setMsg] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const today = new Date().toISOString().split('T')[0]

  useEffect(() => { loadRecent(); loadMeals() }, [userId])

  const loadRecent = async () => {
    try { setRecent(await api.getRecentFoods(userId)) } catch { /* ignore */ }
  }
  const loadMeals = async () => {
    try { setMeals(await api.getMeals(userId)) } catch { /* ignore */ }
  }

  const search = async (q) => {
    setQuery(q)
    try {
      const data = await api.searchFoods(q ? { q } : {})
      setResults(data)
    } catch (e) { setError(e.message) }
  }

  const addFood = (food) => {
    const base = {
      food_id: food.food_id,
      food_name: food.name,
      base_carbs: food.base_carbs,
      base_sugar: food.base_sugar,
      is_sugary_drink: food.is_sugary_drink,
      portion_key: '1',
      custom_factor: 1,
    }
    setDraft((d) => ({ ...d, items: [...d.items, recompute(base)] }))
    setResults([])
    setQuery('')
  }

  const addRecent = async (name) => {
    try {
      const data = await api.searchFoods({ q: name })
      if (data && data.length > 0) addFood(data[0])
    } catch { /* ignore */ }
  }

  const updateItem = (idx, patch) => {
    setDraft((d) => {
      const items = d.items.slice()
      items[idx] = recompute({ ...items[idx], ...patch })
      return { ...d, items }
    })
  }

  const removeItem = (idx) => {
    setDraft((d) => ({ ...d, items: d.items.filter((_, i) => i !== idx) }))
  }

  const totals = draft.items.reduce(
    (acc, it) => ({ carbs: acc.carbs + (it.carbs || 0), sugar: acc.sugar + (it.sugar || 0) }),
    { carbs: 0, sugar: 0 }
  )

  const handlePhoto = (e) => {
    const file = e.target.files && e.target.files[0]
    if (!file) return
    setPhotoFile(file.name)
    setError(null)
    api.analyzePhoto({ user_id: userId, filename: file.name })
      .then((res) => {
        const items = res.foods.map((f) => recompute({
          food_id: f.food_id, food_name: f.food_name,
          base_carbs: f.carbs, base_sugar: f.sugar,
          is_sugary_drink: f.is_sugary_drink,
          portion_key: f.portion_key || '1', custom_factor: 1,
        }))
        setPhoto({
          simulated: res.simulated,
          items,
          estimated_carbs: res.estimated_carbs,
          estimated_sugar: res.estimated_sugar,
          sugary_drink_detected: res.sugary_drink_detected,
          balance: res.balance,
          disclaimer: res.disclaimer,
        })
      })
      .catch((e) => setError(t('Photo analysis failed: ') + e.message))
  }

  const applyPhotoToDraft = () => {
    setDraft((d) => ({ ...d, items: [...d.items, ...photo.items] }))
    setPhoto(null)
    setPhotoFile(null)
    setMsg(t('Simulated photo result added - review portions/values, then save.'))
  }

  const saveMeal = async () => {
    setError(null); setMsg(null)
    if (draft.items.length === 0) { setError(t('Add at least one food or drink.')); return }
    setSaving(true)
    try {
      const payload = {
        user_id: userId,
        meal_type: draft.meal_type,
        items: draft.items.map((it) => ({
          food_id: it.food_id || null,
          food_name: it.food_name,
          portion_key: it.portion_key,
          portion_label: PORTIONS.find((p) => p.key === it.portion_key)?.label || it.portion_key,
          carbs: it.carbs,
          sugar: it.sugar,
          is_sugary_drink: it.is_sugary_drink,
        })),
        notes: draft.notes || null,
        include_in_visit: draft.include_in_visit,
        recorded_date: today,
      }
      if (draft.editingId) {
        await api.updateMeal(draft.editingId, payload)
        setMsg(t('Meal updated.'))
      } else {
        await api.createMeal(payload)
        setMsg(t('Meal saved.'))
      }
      setDraft(emptyDraft())
      await Promise.all([loadMeals(), loadRecent()])
    } catch (e) { setError(e.message) }
    finally { setSaving(false) }
  }

  const startEdit = (m) => {
    let parsed = {}
    try { parsed = JSON.parse(m.value_text || '{}') } catch { /* ignore */ }
    setDraft({
      meal_type: parsed.meal_type || 'breakfast',
      items: (parsed.items || []).map((it) => recompute({
        food_id: it.food_id, food_name: it.food_name,
        base_carbs: it.carbs, base_sugar: it.sugar,
        is_sugary_drink: it.is_sugary_drink,
        portion_key: it.portion_key || '1', custom_factor: 1,
      })),
      notes: m.notes || '',
      include_in_visit: !!m.include_in_visit_summary,
      editingId: m.record_id,
    })
    setMsg(null); setError(null)
  }

  const handleDelete = async (id) => {
    if (!confirm(t('Delete this meal entry?'))) return
    try {
      await api.deleteMeal(id)
      setMsg(t('Meal deleted.'))
      await loadMeals()
    } catch (e) { setError(e.message) }
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">🍽️ {t('Quick Meal Log')}</div>
        <div className="simulated-tag" style={{ marginBottom: 10 }}>
          {t('Estimates are illustrative - not clinically precise')}
        </div>

        <div className="form-group">
          <label className="form-label">{t('Meal')}</label>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {MEAL_TYPES.map((t) => (
              <button
                key={t}
                className={`btn btn-sm ${draft.meal_type === t ? 'btn-primary' : 'btn-secondary'}`}
                style={{ flex: 1, textTransform: 'capitalize' }}
                onClick={() => setDraft((d) => ({ ...d, meal_type: t }))}
              >
                {translateText(language, t)}
              </button>
            ))}
          </div>
        </div>

        {draft.editingId && (
          <div className="success-msg">{t('Editing meal')} #{draft.editingId}。{t('Save to update.')}</div>
        )}

        {/* Recent / favourite tags */}
        {recent.length > 0 && (
          <div className="form-group">
            <label className="form-label">{t('Recent / favourites')}</label>
            <div className="filter-chips">
              {recent.map((r) => (
                <button key={r.food_name} className="chip" onClick={() => addRecent(r.food_name)}>
                  ↺ {r.food_name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Search food */}
        <div className="form-group">
          <label className="form-label">{t('Search food / drink')}</label>
          <input
            className="form-input"
            type="text"
            placeholder={t('e.g. chicken rice, teh tarik, water')}
            value={query}
            onChange={(e) => search(e.target.value)}
          />
          {results.length > 0 && (
            <div className="food-results">
              {results.map((f) => (
                <button key={f.food_id} className="food-result" onClick={() => addFood(f)}>
                  <span>{f.name}</span>
                  <span className="food-meta">
                    ~{f.base_carbs}g {t('carbs')}{f.is_sugary_drink ? ` · ${t('sugary drink')}` : ''}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Current meal items */}
        {draft.items.length > 0 && (
          <div className="meal-items">
            {draft.items.map((it, i) => (
              <div key={i} className="food-row">
                <div className="food-row-head">
                  <strong>{it.food_name}</strong>
                  {it.is_sugary_drink && <span className="simulated-tag">{t('sugary drink')}</span>}<button className="link-danger" onClick={() => removeItem(i)}>{t('remove')}</button>
                </div>
                <div className="food-row-controls">
                  <select
                    className="form-select"
                    style={{ maxWidth: 110 }}
                    value={it.portion_key}
                    onChange={(e) => updateItem(i, { portion_key: e.target.value })}
                  >
                    {PORTIONS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
                  </select>
                  {it.portion_key === 'custom' && (
                    <input
                      className="form-input"
                      style={{ maxWidth: 70 }}
                      type="number" step="0.25" min="0"
                      value={it.custom_factor}
                      onChange={(e) => updateItem(i, { custom_factor: e.target.value })}
                    />
                  )}
                  <label className="food-num">
                    {t('carbs')}
                    <input
                      className="form-input" type="number" step="0.1" min="0"
                      value={it.carbs}
                      onChange={(e) => updateItem(i, { carbs: Number(e.target.value) || 0, base_carbs: it.base_carbs })}
                    />
                  </label>
                  <label className="food-num">
                    {t('sugar')}
                    <input
                      className="form-input" type="number" step="0.1" min="0"
                      value={it.sugar}
                      onChange={(e) => updateItem(i, { sugar: Number(e.target.value) || 0, base_sugar: it.base_sugar })}
                    />
                  </label>
                </div>
              </div>
            ))}
            <div className="meal-totals">
              <span>{t('Meal total:')}</span><span>~{Math.round(totals.carbs * 10) / 10}g {t('carbs')}</span><span>~{Math.round(totals.sugar * 10) / 10}g {t('sugar')}</span>
            </div>
          </div>
        )}

        {/* Photo / scan entry point */}
        <div className="photo-entry">
          <label className="btn btn-secondary btn-sm" style={{ display: 'inline-block', width: 'auto' }}>
            📷 {t('Scan photo (simulated AI)')}
            <input type="file" accept="image/*" capture="environment" onChange={handlePhoto} style={{ display: 'none' }} />
          </label>
          {photoFile && <span className="photo-filename">📎 {photoFile}</span>}
        </div>

        {/* Simulated photo review */}
        {photo && (
          <div className="review-panel">
            <div className="sim-banner">
              ⚠ {t('SIMULATED recognition - no real vision model is connected. Review and confirm before saving.')}
            </div>
            {photo.items.map((it, i) => (
              <div key={i} className="food-row">
                <div className="food-row-head">
                  <strong>{it.food_name}</strong>
                  {it.is_sugary_drink && <span className="simulated-tag">{t('sugary drink')}</span>}
                </div>
                <div className="food-row-controls">
                  <label className="food-num">{t('carbs')}
                    <input className="form-input" type="number" step="0.1" min="0" value={it.carbs}
                      onChange={(e) => {
                        const v = [...photo.items]; v[i] = { ...v[i], carbs: Number(e.target.value) || 0 };
                        setPhoto((p) => ({ ...p, items: v }))
                      }} />
                  </label>
                  <label className="food-num">{t('sugar')}
                    <input className="form-input" type="number" step="0.1" min="0" value={it.sugar}
                      onChange={(e) => {
                        const v = [...photo.items]; v[i] = { ...v[i], sugar: Number(e.target.value) || 0 };
                        setPhoto((p) => ({ ...p, items: v }))
                      }} />
                  </label>
                </div>
              </div>
            ))}
            <div className="meal-totals">
              <span>{t('Estimated')}</span><span>~{photo.estimated_carbs}g {t('carbs')}</span><span>~{photo.estimated_sugar}g {t('sugar')}</span>{photo.sugary_drink_detected && <span className="simulated-tag">{t('sugary drink detected')}</span>}
            </div>
            <div className="balance-note">{photo.balance}</div>
            <button className="btn btn-primary btn-sm" onClick={applyPhotoToDraft}>{t('Add to meal & review')}</button><button className="btn btn-secondary btn-sm" onClick={() => { setPhoto(null); setPhotoFile(null) }}>{t('Discard')}</button>
          </div>
        )}

        <div className="form-group" style={{ marginTop: 12 }}>
          <label className="form-label">{t('Note (optional)')}</label>
          <textarea className="form-textarea" value={draft.notes} maxLength={1000}
            onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
            placeholder="e.g. Felt full after this meal" />
        </div>
        <label className="checkbox-row">
          <input type="checkbox" checked={draft.include_in_visit}
            onChange={(e) => setDraft((d) => ({ ...d, include_in_visit: e.target.checked }))} />
          {t('Include this note in visit summary for my doctor')}
        </label>

        {msg && <div className="success-msg">{msg}</div>}
        {error && <div className="error-msg">{error}</div>}

        <button className="btn btn-primary" onClick={saveMeal} disabled={saving}>
          {saving ? t('Saving...') : draft.editingId ? t('Update Meal') : t('Save Meal')}
        </button>
        {draft.editingId && (
          <button className="btn btn-secondary" onClick={() => { setDraft(emptyDraft()); setMsg(null) }}>{t('Cancel edit')}</button>
        )}
      </div>

      {/* Logged meals */}
      <div className="card">
        <div className="card-title">📋 {t('Logged Meals')}</div>
        {meals.length === 0 ? (
          <div className="empty-state">{t('No meals logged yet.')}</div>
        ) : (
          meals.map((m) => {
            let parsed = {}
            try { parsed = JSON.parse(m.value_text || '{}') } catch { /* ignore */ }
            return (
              <div key={m.record_id} className="history-item">
                <div className="history-icon">🍽️</div>
                <div className="history-body">
                  <div className="history-title" style={{ textTransform: 'capitalize' }}>
                    {translateText(language, parsed.meal_type || 'meal')}{m.include_in_visit_summary && ` · ${t('in visit summary')}`}
                  </div>
                  <div className="history-detail">
                    {(parsed.items || []).map((it) => it.food_name).join(', ')}
                  </div>
                  {parsed.totals && (
                    <div className="history-sub">
                      ~{parsed.totals.carbs}g carbs · ~{parsed.totals.sugar}g sugar
                    </div>
                  )}
                  {m.notes && <div className="history-sub">“{m.notes}”</div>}
                </div>
                <div className="history-actions">
                  <button className="link-btn" onClick={() => startEdit(m)}>{t('edit')}</button><button className="link-danger" onClick={() => handleDelete(m.record_id)}>{t('delete')}</button>
                </div>
                <div className="history-date">{m.recorded_date}</div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
