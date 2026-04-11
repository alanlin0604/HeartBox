import { memo, useState } from 'react'

/**
 * Optimized image component with lazy loading and proper attributes
 * @param {string} src - Image source URL
 * @param {string} alt - Alternative text (required for accessibility)
 * @param {string} className - Additional CSS classes
 * @param {boolean} eager - Load immediately (default: false for lazy loading)
 * @param {string} width - Image width (helps prevent layout shift)
 * @param {string} height - Image height (helps prevent layout shift)
 * @param {string} sizes - Responsive image sizes
 * @param {function} onLoad - Callback when image loads
 * @param {function} onError - Callback when image fails to load
 */
export default memo(function OptimizedImage({
  src,
  alt,
  className = '',
  eager = false,
  width,
  height,
  sizes,
  onLoad,
  onError,
  ...props
}) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [hasError, setHasError] = useState(false)

  const handleLoad = (e) => {
    setIsLoaded(true)
    onLoad?.(e)
  }

  const handleError = (e) => {
    setHasError(true)
    onError?.(e)
  }

  if (hasError) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        style={{
          width: width || '100%',
          height: height || 'auto',
          background: 'var(--surface-primary)',
          color: 'var(--text-secondary)',
        }}
        role="img"
        aria-label={alt}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
      </div>
    )
  }

  return (
    <>
      {!isLoaded && (
        <div
          className={`animate-pulse ${className}`}
          style={{
            width: width || '100%',
            height: height || 'auto',
            background: 'var(--surface-elevated)',
            aspectRatio: width && height ? `${width} / ${height}` : undefined,
          }}
          aria-hidden="true"
        />
      )}
      <img
        src={src}
        alt={alt}
        className={`${className} ${isLoaded ? 'block' : 'hidden'} transition-opacity duration-300`}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
        width={width}
        height={height}
        sizes={sizes}
        onLoad={handleLoad}
        onError={handleError}
        style={{
          opacity: isLoaded ? 1 : 0,
        }}
        {...props}
      />
    </>
  )
})
