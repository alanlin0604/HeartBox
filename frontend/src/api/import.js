import api from './axios'

export const importAPI = {
  /**
   * 預覽 CSV 文件（不實際匯入）
   * @param {File} file - CSV 文件
   * @returns {Promise<{total_rows, preview_rows, columns, suggested_mapping}>}
   */
  async previewCSV(file) {
    const formData = new FormData()
    formData.append('file', file)

    const res = await api.post('/notes/import/preview/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return res.data
  },

  /**
   * 匯入 CSV 文件
   * @param {File} file - CSV 文件
   * @param {Object} mapping - 欄位映射（可選）
   * @returns {Promise<{imported, errors}>}
   */
  async importCSV(file, mapping = null) {
    const formData = new FormData()
    formData.append('file', file)

    if (mapping) {
      formData.append('mapping', JSON.stringify(mapping))
    }

    const res = await api.post('/notes/import/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return res.data
  },
}
