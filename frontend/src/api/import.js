import api from './axios'

export const importAPI = {
  /**
   * Preview an import file without writing.
   * @param {File} file - .csv or .json
   * @returns {Promise<{format, total_rows, preview_rows, columns, suggested_mapping, sync_limit}>}
   */
  async previewFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await api.post('/notes/import/preview/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  /**
   * Run an import. Small files come back synchronously with `{mode:'sync',
   * imported, errors}`; larger files return `{mode:'async', job_id, status}`
   * and the caller should poll `getJobStatus`.
   *
   * @param {File} file
   * @param {Object|null} mapping - {<source column>: <target field>}
   */
  async importFile(file, mapping = null) {
    const formData = new FormData()
    formData.append('file', file)
    if (mapping) formData.append('mapping', JSON.stringify(mapping))
    const res = await api.post('/notes/import/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  /** Poll a single import job's progress. */
  async getJobStatus(jobId) {
    const res = await api.get(`/notes/import/jobs/${jobId}/`)
    return res.data
  },

  // --- Backwards-compatible aliases (older callers used CSV-specific names) ---
  previewCSV(file) { return this.previewFile(file) },
  importCSV(file, mapping) { return this.importFile(file, mapping) },
}
