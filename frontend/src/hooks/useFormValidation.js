import { useState, useCallback, useRef } from 'react'

/**
 * Form validation hook with inline error display
 * Follows Material Design and Apple HIG form validation patterns:
 * - Validate on blur (not on keystroke)
 * - Show errors only after user finishes input
 * - Clear errors on input change
 * - Preserve errors until field is valid
 *
 * @param {Object} initialValues - Initial form values
 * @param {Function} validateFn - Validation function: (values, fieldName?) => errors object
 * @param {Function} onSubmit - Submit handler: (values) => void | Promise<void>
 *
 * @example
 * const { values, errors, touched, handleChange, handleBlur, handleSubmit, isSubmitting } = useFormValidation(
 *   { email: '', password: '' },
 *   (values, field) => {
 *     const errors = {}
 *     if (field === 'email' || !field) {
 *       if (!values.email) errors.email = 'Email required'
 *       else if (!/\S+@\S+\.\S+/.test(values.email)) errors.email = 'Invalid email'
 *     }
 *     return errors
 *   },
 *   async (values) => { await login(values) }
 * )
 */
export function useFormValidation(initialValues, validateFn, onSubmit) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState({})
  const [touched, setTouched] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const firstErrorRef = useRef(null)

  /**
   * Handle input change - clears error for the field
   */
  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target
    const newValue = type === 'checkbox' ? checked : value

    setValues((prev) => ({ ...prev, [name]: newValue }))

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    }
  }, [errors])

  /**
   * Handle blur - validates the field and shows error if invalid
   */
  const handleBlur = useCallback((e) => {
    const { name } = e.target

    // Mark field as touched
    setTouched((prev) => ({ ...prev, [name]: true }))

    // Validate only this field
    const fieldErrors = validateFn(values, name)
    if (fieldErrors[name]) {
      setErrors((prev) => ({ ...prev, [name]: fieldErrors[name] }))
    }
  }, [values, validateFn])

  /**
   * Handle submit - validates all fields and calls onSubmit if valid
   */
  const handleSubmit = useCallback(async (e) => {
    e?.preventDefault?.()

    // Mark all fields as touched
    const allTouched = Object.keys(values).reduce((acc, key) => {
      acc[key] = true
      return acc
    }, {})
    setTouched(allTouched)

    // Validate all fields
    const allErrors = validateFn(values)

    if (Object.keys(allErrors).length > 0) {
      setErrors(allErrors)

      // Focus first error field after a short delay
      setTimeout(() => {
        const firstErrorField = Object.keys(allErrors)[0]
        const fieldElement = document.querySelector(`[name="${firstErrorField}"]`)
        if (fieldElement) {
          fieldElement.focus()
          firstErrorRef.current = fieldElement
        }
      }, 100)

      return
    }

    // Clear errors and submit
    setErrors({})
    setIsSubmitting(true)

    try {
      await onSubmit(values)
    } catch (error) {
      // Allow onSubmit to handle errors
      throw error
    } finally {
      setIsSubmitting(false)
    }
  }, [values, validateFn, onSubmit])

  /**
   * Reset form to initial values
   */
  const resetForm = useCallback(() => {
    setValues(initialValues)
    setErrors({})
    setTouched({})
    setIsSubmitting(false)
  }, [initialValues])

  /**
   * Set specific field value programmatically
   */
  const setFieldValue = useCallback((name, value) => {
    setValues((prev) => ({ ...prev, [name]: value }))
  }, [])

  /**
   * Set specific field error programmatically
   */
  const setFieldError = useCallback((name, error) => {
    setErrors((prev) => ({ ...prev, [name]: error }))
    setTouched((prev) => ({ ...prev, [name]: true }))
  }, [])

  /**
   * Check if field should show error (touched + has error)
   */
  const shouldShowError = useCallback((name) => {
    return touched[name] && errors[name]
  }, [touched, errors])

  return {
    values,
    errors,
    touched,
    isSubmitting,
    handleChange,
    handleBlur,
    handleSubmit,
    resetForm,
    setFieldValue,
    setFieldError,
    shouldShowError,
  }
}

export default useFormValidation
