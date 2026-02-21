import api from './axios';
import { getCached, setCache, invalidate } from './cache';

/** Invalidate all note-related caches (notes list, alerts, analytics). */
const invalidateNotesCaches = () => {
  invalidate('notes');
  invalidate('alerts');
  invalidate('analytics');
};

export const getNotes = (page = 1, filters = {}) => {
  const params = new URLSearchParams({ page });
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.append(key, value);
    }
  });
  const url = `/notes/?${params.toString()}`;
  const key = `notes:${url}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  const hasFilters = Object.keys(filters).some(
    k => filters[k] !== undefined && filters[k] !== null && filters[k] !== ''
  );
  return api.get(url).then(res => {
    setCache(key, res, hasFilters ? 30_000 : 60_000);
    return res;
  });
};

export const getNote = (id) => {
  const key = `note:${id}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/notes/${id}/`).then(res => {
    setCache(key, res, 30_000);
    return res;
  });
};

export const createNote = (content, metadata = {}) => {
  invalidateNotesCaches();
  return api.post('/notes/', { content, metadata });
};

export const updateNote = (id, content, metadata) => {
  invalidateNotesCaches();
  invalidate(`note:${id}`);
  return api.put(`/notes/${id}/`, { content, metadata });
};

export const deleteNote = (id) => {
  invalidateNotesCaches();
  invalidate(`note:${id}`);
  return api.delete(`/notes/${id}/`);
};

export const exportNotesPDF = (dateFrom, dateTo, lang) => {
  const params = new URLSearchParams();
  if (dateFrom) params.append('date_from', dateFrom);
  if (dateTo) params.append('date_to', dateTo);
  if (lang) params.append('lang', lang);
  return api.get(`/notes/export/?${params.toString()}`, { responseType: 'blob' });
};

export const togglePin = (noteId) => {
  invalidate('notes');
  invalidate(`note:${noteId}`);
  return api.post(`/notes/${noteId}/toggle_pin/`);
};

export const uploadAttachment = (noteId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/notes/${noteId}/attachments/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const reanalyzeNote = (id) => api.post(`/notes/${id}/reanalyze/`);

export const shareNote = (noteId, counselorId, isAnonymous) =>
  api.post(`/notes/${noteId}/share/`, {
    counselor_id: counselorId,
    is_anonymous: isAnonymous,
  });

export const getSharedNotes = () => {
  const cached = getCached('sharedNotes');
  if (cached) return Promise.resolve(cached);
  return api.get('/shared-notes/').then(res => {
    setCache('sharedNotes', res, 30_000);
    return res;
  });
};

export const batchDeleteNotes = (ids) => {
  invalidateNotesCaches();
  return api.post('/notes/batch_delete/', { ids });
};

export const exportNotesCSV = () =>
  api.get('/auth/export/csv/', { responseType: 'blob' });

// Trash (soft delete)
export const getTrashNotes = () => api.get('/notes/trash/');
export const restoreNote = (id) => {
  invalidate('notes');
  return api.post(`/notes/${id}/restore/`);
};
export const permanentDeleteNote = (id) =>
  api.delete(`/notes/${id}/permanent-delete/`);
