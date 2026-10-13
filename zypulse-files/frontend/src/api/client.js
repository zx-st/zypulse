// In development, Vite proxies /api to FastAPI. In production, set
// VITE_API_BASE_URL to the deployed backend URL, including its /api prefix.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };
  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }
  const response = await fetch(url, config);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export const api = {
  // Health logging
  logGlucose: (data) => request('/logs/glucose', { method: 'POST', body: data }),
  logMedication: (data) => request('/logs/medication', { method: 'POST', body: data }),
  logActivity: (data) => request('/logs/activity', { method: 'POST', body: data }),

  // Chat
  chat: (data) => request('/chat', { method: 'POST', body: data }),
  getDailyBriefing: (data) => request('/daily-briefing', { method: 'POST', body: data }),
  getAiUsage: (userId) => request(`/ai-usage?user_id=${encodeURIComponent(userId)}`),

  // Trends
  getTrends: (params) => {
    const query = new URLSearchParams(params).toString();
    return request(`/trends?${query}`);
  },

  // Preferences
  getPreferences: (userId) => request(`/preferences?user_id=${userId}`),
  updatePreferences: (userId, data) => request(`/preferences?user_id=${userId}`, { method: 'PUT', body: data }),
  getNotifications: (userId) => request(`/notifications?user_id=${userId}`),
  markNotificationRead: (notificationId, userId) => request(`/notifications/${notificationId}/read?user_id=${userId}`, { method: 'PUT' }),

  // History (unified chronological view)
  getHistory: (params) => {
    const query = new URLSearchParams(params).toString();
    return request(`/history?${query}`);
  },

  // Notes for doctor visit
  createNote: (data) => request('/notes', { method: 'POST', body: data }),
  getVisitNotes: (userId) => request(`/notes/visit?user_id=${userId}`),
  updateNote: (recordId, data) => request(`/notes/${recordId}`, { method: 'PUT', body: data }),

  // Meal log
  searchFoods: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/foods?${query}`);
  },
  getRecentFoods: (userId) => request(`/foods/recent?user_id=${userId}`),
  createMeal: (data) => request('/meals', { method: 'POST', body: data }),
  getMeals: (userId) => request(`/meals?user_id=${userId}`),
  updateMeal: (recordId, data) => request(`/meals/${recordId}`, { method: 'PUT', body: data }),
  deleteMeal: (recordId) => request(`/meals/${recordId}`, { method: 'DELETE' }),
  getPhotoSamples: (category) => request(`/photo-samples?category=${category}`),
  analyzePhoto: (data) => request('/photo-analyze', { method: 'POST', body: data }),

  // Uploaded originals (private storage, ownership-checked reads)
  uploadPhoto: async (file, userId) => {
    const form = new FormData();
    form.append('file', file);
    form.append('user_id', userId);
    const response = await fetch(`${API_BASE}/photos/upload`, { method: 'POST', body: form });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return response.json();
  },
  attachPhoto: (photoKey, userId, recordId) =>
    request(`/photos/${photoKey}/attach?user_id=${encodeURIComponent(userId)}&record_id=${recordId}`, { method: 'POST' }),
  discardPhoto: (photoKey, userId) =>
    request(`/photos/${photoKey}?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' }),
  // Uploaded photos are not public files: they are read through an endpoint
  // that checks the owner, so the URL always carries the user id.
  photoUrl: (photoKey, userId) =>
    `${API_BASE}/photos/${photoKey}?user_id=${encodeURIComponent(userId)}`,

  // Activities
  searchActivities: (params) => {
    const query = new URLSearchParams(params).toString();
    return request(`/activities?${query}`);
  },
};
