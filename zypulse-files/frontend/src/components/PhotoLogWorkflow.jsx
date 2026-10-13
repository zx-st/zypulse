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

function factorOf(key, customFactor) {
  if (key === 'custom') return Number(customFactor) || 1
  const p = PORTIONS.find((x) => x.key === key)
  return p ? p.factor : 1
}

const SIM_TAG = 'Simulated AI recognition — demo mode'

// Technical validation only - the content of an upload is never analysed.
const ALLOWED_UPLOAD_TYPES = ['image/png', 'image/jpeg', 'image/webp']
const MAX_UPLOAD_BYTES = 8 * 1024 * 1024

export default function PhotoLogWorkflow({ logType, userId, language, today, onConfirm, onCancel, onSaveFavourite }) {
  const t = (text) => translateText(language, text)
  const [samples, setSamples] = useState([])
  const [screen, setScreen] = useState('picker') // picker | review
  const [selected, setSelected] = useState(null) // recognized analysis result
  const [uploadMsg, setUploadMsg] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  // Uploaded original: held in the browser until the user confirms the log.
  const [pendingFile, setPendingFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)

  // editable state for the review screen
  const [gValue, setGValue] = useState('')
  const [gUnit, setGUnit] = useState('mmol/L')
  const [gDate, setGDate] = useState(today)
  const [gNotes, setGNotes] = useState('')

  const [mName, setMName] = useState('')
  const [mStrength, setMStrength] = useState('')
  const [mForm, setMForm] = useState('')
  const [mQty, setMQty] = useState('')
  const [mStatus, setMStatus] = useState('taken')
  const [mConfirmed, setMConfirmed] = useState(false)
  const [mNotes, setMNotes] = useState('')

  const [mealItems, setMealItems] = useState([])
  const [mealCustom, setMealCustom] = useState({})
  const [mealMod, setMealMod] = useState('')
  const [mealNotes, setMealNotes] = useState('')
  const [favSaved, setFavSaved] = useState(false)

  useEffect(() => {
    let active = true
    if (screen === 'picker') {
      api.getPhotoSamples(logType)
        .then((data) => { if (active) setSamples(data) })
        .catch(() => { /* ignore */ })
    }
    return () => { active = false }
  }, [logType, screen])

  const openSample = async (sampleId) => {
    setError(null)
    setUploadMsg(null)
    try {
      const res = await api.analyzePhoto({ user_id: userId, category: logType, sample_id: sampleId })
      if (!res.recognized) {
        setUploadMsg(res.reason || 'Not recognised.')
        return
      }
      loadIntoReview(res)
    } catch (e) {
      setError(e.message || 'Analysis failed')
    }
  }

  const releasePreview = () => {
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return null
    })
  }

  const onUpload = async (e) => {
    const file = e.target.files && e.target.files[0]
    if (!file) return
    e.target.value = '' // allow re-selecting the same file
    setError(null)

    // Type + size validation happens before anything is stored or previewed.
    if (!ALLOWED_UPLOAD_TYPES.includes(file.type)) {
      setPendingFile(null)
      setUploadMsg(t('Unsupported file type. Upload a PNG, JPEG or WebP image.'))
      return
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setPendingFile(null)
      setUploadMsg(t('Image is too large (max 8 MB).'))
      return
    }
    if (file.size === 0) {
      setPendingFile(null)
      setUploadMsg(t('The selected file is empty.'))
      return
    }

    try {
      // No vision capability: the server reports the upload as unrecognised.
      const res = await api.analyzePhoto({ user_id: userId, category: logType, filename: file.name })
      if (res.recognized) {
        releasePreview()
        setPendingFile(null)
        loadIntoReview(res)
        return
      }
      // Keep the original visible and let the user type everything in.
      releasePreview()
      const url = URL.createObjectURL(file)
      setPendingFile(file)
      setPreviewUrl(url)
      setUploadMsg(res.reason || t('Not a recognised demo photo. Please enter details manually below.'))
      setSelected({
        recognized: false,
        simulated: true,
        category: logType,
        image: url,
        isUpload: true,
        extraction: logType === 'meal' ? { visible_in_photo: [], items: [emptyMealItem(0)] } : {},
      })
      loadIntoReviewFromUpload(logType)
      setScreen('review')
    } catch (err) {
      setUploadMsg(t('Could not read this photo. Please use manual entry.'))
    }
  }

  const emptyMealItem = (idx) => ({
    _idx: idx,
    food_id: null,
    food_name: '',
    editable_name: true,
    portion_key: '1',
    custom_factor: 1,
    base_carbs: null,
    base_sugar: null,
    base_calories: null,
    base_protein: null,
    is_sugary_drink: false,
    source: t('Entered by you - photo was not analysed'),
  })

  // Uploads start from an empty, fully editable review form.
  const loadIntoReviewFromUpload = (type) => {
    if (type === 'glucose') {
      setGValue('')
      setGUnit('mmol/L')
      setGDate(today)
      setGNotes('')
    } else if (type === 'medication') {
      setMName('')
      setMStrength('')
      setMForm('')
      setMQty('')
      setMStatus('taken')
      setMConfirmed(false)
      setMNotes('')
    } else {
      setMealItems([emptyMealItem(0)])
      setMealCustom({})
      setMealMod('')
      setMealNotes('')
      setFavSaved(false)
    }
  }

  const loadIntoReview = (res) => {
    setSelected(res)
    const ext = res.extraction || {}
    if (logType === 'glucose') {
      setGValue(ext.reading != null ? String(ext.reading) : '')
      setGUnit(ext.unit || 'mmol/L')
      setGDate(today)
      setGNotes('')
    } else if (logType === 'medication') {
      setMName(ext.name || '')
      setMStrength(ext.strength || '')
      setMForm(ext.form || '')
      setMQty(ext.visible_qty != null ? String(ext.visible_qty) : '')
      setMStatus('taken')
      setMConfirmed(false)
      setMNotes('')
    } else if (logType === 'meal') {
      const items = (ext.items || []).map((it, i) => ({
        ...it,
        _idx: i,
        portion_key: it.portion_key || '1',
        custom_factor: 1,
      }))
      setMealItems(items)
      setMealCustom({})
      setMealMod('')
      setMealNotes('')
      setFavSaved(false)
    }
    setScreen('review')
  }

  const reset = () => {
    setSelected(null)
    setScreen('picker')
    setUploadMsg(null)
    setError(null)
    // Nothing was stored yet, so dropping the local preview leaves no file behind.
    releasePreview()
    setPendingFile(null)
  }

  // Portion-adjusted values are computed deterministically from the BASE value
  // supplied by the photo service / nutrition catalogue (never invented here).
  const mealScaled = (it) => {
    const f = factorOf(it.portion_key, mealCustom[it._idx] ?? it.custom_factor)
    const r1 = (v) => Math.round((Number(v) || 0) * f * 10) / 10
    const carbBase = it.base_carbs != null ? it.base_carbs : it.carbs
    const calBase = it.base_calories != null ? it.base_calories : it.calories
    const protBase = it.base_protein != null ? it.base_protein : it.protein
    return {
      carbs: carbBase != null ? r1(carbBase) : null,
      sugar: it.base_sugar != null ? r1(it.base_sugar) : null,
      calories: calBase != null ? r1(calBase) : null,
      protein: protBase != null ? r1(protBase) : null,
    }
  }

  const addOpt = (a, b) => (a == null || b == null ? null : Math.round((a + b) * 10) / 10)
  const mealTotals = mealItems.reduce(
    (acc, it) => {
      const s = mealScaled(it)
      return { carbs: addOpt(acc.carbs, s.carbs), sugar: addOpt(acc.sugar, s.sugar), calories: addOpt(acc.calories, s.calories) }
    },
    { carbs: 0, sugar: 0, calories: 0 },
  )
  const fmt = (v, unit) => (v == null ? t('Estimate unavailable') : `~${v}${unit}`)

  const handleConfirm = async () => {
    if (busy) return // one save per confirm
    setBusy(true)
    setError(null)
    let uploadedRef = null
    try {
      let payload
      if (logType === 'glucose') {
        const raw = parseFloat(gValue)
        if (isNaN(raw) || raw <= 0) { setError(t('Please enter the glucose reading.')); setBusy(false); return }
        // store in mmol/L (backend expects mmol/L 1-35)
        let mmol = gUnit === 'mg/dL' ? raw / 18 : raw
        mmol = Math.round(mmol * 10) / 10
        if (mmol < 1 || mmol > 35) { setError(t('Reading out of range (1-35 mmol/L).')); setBusy(false); return }
        payload = {
          value: mmol,
          unit: gUnit,
          period: 'fasting',
          recorded_date: gDate,
          notes: gNotes || null,
          photo_ref: selected.image,
        }
      } else if (logType === 'medication') {
        if (!mConfirmed) { setError(t('Please confirm this is the medication and quantity you actually took.')); setBusy(false); return }
        const qtyNote = mQty ? ` Quantity taken: ${mQty}.` : ''
        payload = {
          period: 'morning',
          status: mStatus,
          medication_name: mName,
          dose: mStrength,
          notes: `${mForm ? mForm + '. ' : ''}${qtyNote}${mNotes ? ' ' + mNotes : ''}`.trim() || null,
          photo_ref: selected.image,
          confirmed: true,
        }
      } else {
        const items = mealItems.map((it) => {
          const s = mealScaled(it)
          return {
            food_name: it.food_name,
            food_id: it.food_id,
            portion_key: it.portion_key,
            portion_label: PORTIONS.find((p) => p.key === it.portion_key)?.label || it.portion_key,
            carbs: s.carbs ?? 0,
            sugar: s.sugar ?? 0,
            is_sugary_drink: !!it.is_sugary_drink,
            calories: s.calories,
            protein: s.protein,
            source: it.source,
          }
        })
        if (items.length === 0) { setError(t('No items to save.')); setBusy(false); return }
        const missingName = items.some((it) => !it.food_name || !it.food_name.trim())
        if (missingName) { setError(t('Please name every food or drink you entered.')); setBusy(false); return }
        const notes = [mealMod ? `Modification: ${mealMod}` : '', mealNotes].filter(Boolean).join('. ')
        payload = { items, notes: notes || null, photo_ref: selected.image, modification: mealMod || null }
      }

      // The original is stored only now that the user has confirmed the entry.
      if (pendingFile) {
        const up = await api.uploadPhoto(pendingFile, userId)
        uploadedRef = up.photo_ref
        payload.photo_ref = up.photo_ref
      }

      const saved = await onConfirm(payload)

      // Link the stored file to the new record so it is never an orphan.
      if (uploadedRef && saved && saved.record_id) {
        try {
          await api.attachPhoto(uploadedRef.replace('photo:', ''), userId, saved.record_id)
        } catch { /* the nightly/startup purge handles an unlinked upload */ }
      }

      reset()
    } catch (e) {
      // Roll the stored file back so a failed save leaves nothing behind.
      if (uploadedRef) {
        try { await api.discardPhoto(uploadedRef.replace('photo:', ''), userId) } catch { /* ignore */ }
      }
      setError(e.message || 'Failed to save.')
    } finally {
      setBusy(false)
    }
  }

  const saveFavourites = () => {
    if (!onSaveFavourite) return
    // Save the confirmed item (name + base nutrition + portion) so it can be
    // reused later from the meal page WITHOUT uploading a new photo.
    mealItems.forEach((it) => onSaveFavourite({
      food_id: it.food_id || null,
      food_name: it.food_name,
      base_carbs: it.base_carbs,
      base_sugar: it.base_sugar,
      is_sugary_drink: !!it.is_sugary_drink,
      source: it.source,
    }))
    setFavSaved(true)
  }

  // ----------------------------- RENDER -----------------------------
  return (
    <div className="photo-workflow">
      <div className="sim-banner">⚠ {t(SIM_TAG)} — {t('no real vision model is connected. Review and confirm before saving.')}</div>

      {uploadMsg && (
        <div className="manual-fallback">
          📎 {uploadMsg}
          <div className="manual-fallback-hint">{t('Use the manual entry form on this page.')}</div>
        </div>
      )}

      {screen === 'picker' && (
        <div>
          <div className="photo-entry">
            <label className="btn btn-secondary btn-sm" style={{ display: 'inline-block', width: 'auto', marginRight: 8 }}>
              📤 {t('Upload / Take Photo')}
              <input type="file" accept="image/*" capture="environment" onChange={onUpload} style={{ display: 'none' }} />
            </label>
            <span className="photo-filename">{t('unrecognised uploads fall back to manual entry')}</span>
          </div>

          <div className="sample-heading">{t('Try a sample photo (reliable demo):')}</div>

          <div className="sample-grid">
            {samples.map((s) => (
              <button key={s.sample_id} className="sample-card" onClick={() => openSample(s.sample_id)}>
                <img className="sample-thumb" src={s.image} alt={s.label} />
                <div className="sample-label">{s.label}</div>
                <div className="sample-tags">
                  <span className="simulated-tag">{t('demo')}</span>
                  {s.needs_review && <span className="badge badge-warn">{t('needs review')}</span>}
                  {s.from_saved_list && <span className="badge badge-info">{t('saved list')}</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {screen === 'review' && selected && (
        <div className="review-panel">
          <div className="photo-preview">
            <img src={selected.image} alt="original" />
            <div className="photo-preview-cap">
              {selected.isUpload ? t('Your uploaded photo (original)') : t('Original photo (demo)')}
            </div>
          </div>

          {selected.isUpload && (
            <div className="manual-fallback">
              🔎 {t('This photo was not analysed. Demo mode has no real vision AI, so nothing was read from your image.')}
              <div className="manual-fallback-hint">
                {t('Fill in the details below yourself. Your photo is saved with the entry only after you confirm.')}
              </div>
            </div>
          )}

          {logType === 'glucose' && (() => {
            const ext = selected.extraction
            return (
              <div>
                <div className="review-badges">
                  <span className="badge">{t('Visible in photo')}: {ext.visible_in_photo?.join(', ') || '—'}</span>
                  {ext.needs_review && <span className="badge badge-warn">{t('Needs your review')}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">{t('Glucose reading')}</label>
                  <input className="form-input" type="number" step="0.1" min="0" value={gValue}
                    onChange={(e) => setGValue(e.target.value)} placeholder={ext.needs_review ? t('enter reading') : ''} />
                  {ext.needs_review && <div className="hint-warn">{t('Reading not legible — please enter it yourself.')}</div>}
                </div>
                <div className="form-group">
                  <label className="form-label">{t('Unit')}</label>
                  <select className="form-select" value={gUnit} onChange={(e) => setGUnit(e.target.value)}>
                    <option value="mmol/L">mmol/L</option>
                    <option value="mg/dL">mg/dL</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">{t('Date')}</label>
                  <input className="form-input" type="date" value={gDate} onChange={(e) => setGDate(e.target.value)} />
                </div>
                {ext.datetime && (
                  <div className="hint-muted">{t('Time shown on device')}: {ext.datetime} ({t('simulated extraction')})</div>
                )}
                <div className="form-group">
                  <label className="form-label">{t('Notes (optional)')}</label>
                  <textarea className="form-textarea" value={gNotes} onChange={(e) => setGNotes(e.target.value)} />
                </div>
              </div>
            )
          })()}

          {logType === 'medication' && (() => {
            const ext = selected.extraction
            return (
              <div>
                <div className="review-badges">
                  <span className="badge">{t('Visible in photo')}: {ext.visible_in_photo?.join(', ') || '—'}</span>
                </div>
                <div className="form-group">
                  <label className="form-label">{t('Medication')}</label>
                  <input className="form-input" value={mName} onChange={(e) => setMName(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">{t('Strength')}</label>
                  <input className="form-input" value={mStrength} onChange={(e) => setMStrength(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">{t('Form')}</label>
                  <input className="form-input" value={mForm} onChange={(e) => setMForm(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">{ext.unclear_qty ? t('Quantity you took') : t('Visible quantity')}</label>
                  <input className="form-input" type="number" min="0" value={mQty}
                    onChange={(e) => setMQty(e.target.value)} placeholder={ext.unclear_qty ? t('not visible — enter yours') : ''} />
                  {ext.unclear_qty && <div className="hint-warn">{t('Quantity not clearly visible in photo.')}</div>}
                </div>
                <div className="form-group">
                  <label className="form-label">{t('Status')}</label>
                  <select className="form-select" value={mStatus} onChange={(e) => setMStatus(e.target.value)}>
                    <option value="taken">{t('Taken')}</option>
                    <option value="missed">{t('Missed')}</option>
                    <option value="skipped">{t('Skipped')}</option>
                  </select>
                </div>
                <label className="confirm-check">
                  <input type="checkbox" checked={mConfirmed} onChange={(e) => setMConfirmed(e.target.checked)} />
                  {t('Is this the medication and quantity you actually took?')}
                </label>
                <div className="hint-muted">{t('A photo does not prove medication was taken. Confirm only if you took it.')}</div>
                <div className="form-group">
                  <label className="form-label">{t('Notes (optional)')}</label>
                  <textarea className="form-textarea" value={mNotes} onChange={(e) => setMNotes(e.target.value)} />
                </div>
              </div>
            )
          })()}

          {logType === 'meal' && (
            <div>
              <div className="review-badges">
                <span className="badge">{t('Visible in photo')}: {selected.extraction.visible_in_photo?.join(', ') || '—'}</span>
              </div>
              {mealItems.map((it) => {
                const s = mealScaled(it)
                return (
                  <div key={it._idx} className="food-row">
                    <div className="food-row-head">
                      {it.editable_name ? (
                        <input className="form-input" value={it.food_name} placeholder={t('Food or drink name')}
                          onChange={(e) => setMealItems((items) => items.map((x) => x._idx === it._idx ? { ...x, food_name: e.target.value } : x))} />
                      ) : (
                        <strong>{it.food_name}</strong>
                      )}
                      {mealItems.length > 1 && (
                        <button type="button" className="btn-link danger"
                          onClick={() => setMealItems((items) => items.filter((x) => x._idx !== it._idx))}>
                          {t('Remove')}
                        </button>
                      )}
                    </div>
                    <div className="food-row-controls">
                      <select className="form-select" style={{ maxWidth: 110 }} value={it.portion_key}
                        onChange={(e) => setMealItems((items) => items.map((x) => x._idx === it._idx ? { ...x, portion_key: e.target.value } : x))}>
                        {PORTIONS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
                      </select>
                      {it.portion_key === 'custom' && (
                        <input className="form-input" style={{ maxWidth: 70 }} type="number" step="0.25" min="0"
                          value={mealCustom[it._idx] ?? it.custom_factor}
                          onChange={(e) => setMealCustom((c) => ({ ...c, [it._idx]: e.target.value }))} />
                      )}
                      <label className="food-num">{t('carbs')} (g)
                        <input className="form-input" type="number" step="0.1" min="0" value={s.carbs ?? ''}
                          placeholder={s.carbs == null ? t('Estimate unavailable') : ''}
                          onChange={(e) => setMealItems((items) => items.map((x) => x._idx === it._idx
                            ? { ...x, base_carbs: e.target.value === '' ? null : Number(e.target.value) } : x))} />
                      </label>
                      <label className="food-num">{t('kcal')}
                        <input className="form-input" type="number" step="1" min="0" value={s.calories ?? ''}
                          placeholder={s.calories == null ? t('Estimate unavailable') : ''}
                          onChange={(e) => setMealItems((items) => items.map((x) => x._idx === it._idx
                            ? { ...x, base_calories: e.target.value === '' ? null : Number(e.target.value) } : x))} />
                      </label>
                      <span className="nutri-src">{it.source}</span>
                    </div>
                    <div className="food-row-sub">
                      {t('protein')}: {s.protein != null ? `${s.protein}g` : t('Estimate unavailable')} · {t('sugar')}: {s.sugar != null ? `${s.sugar}g` : t('Estimate unavailable')}
                    </div>
                  </div>
                )
              })}
              {selected.isUpload && (
                <button type="button" className="btn btn-secondary btn-sm"
                  onClick={() => setMealItems((items) => [...items, emptyMealItem((items[items.length - 1]?._idx ?? 0) + 1)])}>
                  + {t('Add another item')}
                </button>
              )}
              <div className="meal-totals">
                <span>{t('Meal total')}:</span>
                <span>{fmt(mealTotals.carbs, `g ${t('carbs')}`)}</span>
                <span>{fmt(mealTotals.sugar, `g ${t('sugar')}`)}</span>
                <span>{fmt(mealTotals.calories, ' kcal')}</span>
              </div>
              <div className="form-group">
                <label className="form-label">{t('Preparation / modification (your note, not from photo)')}</label>
                <input className="form-input" value={mealMod} placeholder={t('e.g. less sweet')}
                  onChange={(e) => setMealMod(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('Notes (optional)')}</label>
                <textarea className="form-textarea" value={mealNotes} onChange={(e) => setMealNotes(e.target.value)} />
              </div>
              {onSaveFavourite && (
                <button className="btn btn-secondary btn-sm" onClick={saveFavourites} disabled={favSaved}>
                  {favSaved ? t('Saved to favourites') : t('Save foods to favourites')}
                </button>
              )}
            </div>
          )}

          {error && <div className="error-msg">{error}</div>}

          <div className="photo-actions">
            <button className="btn btn-primary btn-sm" onClick={handleConfirm} disabled={busy}>
              {busy ? t('Saving...') : t('Confirm & Save')}
            </button>
            <button className="btn btn-secondary btn-sm" onClick={reset} disabled={busy}>{t('Retake / Replace')}</button>
            <button className="btn btn-secondary btn-sm" onClick={() => { reset(); onCancel && onCancel() }} disabled={busy}>{t('Cancel')}</button>
          </div>
        </div>
      )}
    </div>
  )
}
