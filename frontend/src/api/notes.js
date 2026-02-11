import api from './axios';
import { getCached, setCache, invalidate } from './cache';

export const getNotes = (page = 1, filters = {}) => {
  const params = new URLSearchParams({ page });
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.append(key, value);
    }
  });
  const url = `/notes/?${params.toString()}`;
  const hasFilters = Object.keys(filters).some(
    k => filters[k] !== undefined && filters[k] !== null && filters[k] !== ''
  );
  if (hasFilters) return api.get(url);
  const key = `notes:${url}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(url).then(res => {
    setCache(key, res, 60_000);
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
  invalidate('notes');
  invalidate('alerts');
  invalidate('analytics');
  return api.post('/notes/', { content, metadata });
};

export const updateNote = (id, content, metadata) => {
  invalidate('notes');
  invalidate(`note:${id}`);
  invalidate('analytics');
  return api.put(`/notes/${id}/`, { content, metadata });
};

export const deleteNote = (id) => {
  invalidate('notes');
  invalidate(`note:${id}`);
  invalidate('analytics');
  invalidate('alerts');
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
  invalidate('notes');
  invalidate('analytics');
  invalidate('alerts');
  return api.post('/notes/batch_delete/', { ids });
};

export const exportNotesCSV = () =>
  api.get('/auth/export/csv/', { responseType: 'blob' });
