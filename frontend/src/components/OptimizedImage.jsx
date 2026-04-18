import { memo } from 'react'

/**
 * OptimizedImage component with WebP support and PNG fallback
 * Automatically serves WebP to supported browsers for better performance
 *
 * @param {string} src - Image path (without extension)
 * @param {string} alt - Alternative text
 * @param {string} className - CSS classes
 * @param {object} ...props - Other img attributes
 */
const OptimizedImage = memo(({ src, alt, className, ...props }) => {
  // Extract filename without extension
  const srcWithoutExt = src.replace(/\.(png|jpg|jpeg)$/, '')

  return (
    <picture>
      <source srcSet={`${srcWithoutExt}.webp`} type="image/webp" />
      <img
        src={src}
        alt={alt}
        className={className}
        loading="lazy"
        {...props}
      />
    </picture>
  )
})

OptimizedImage.displayName = 'OptimizedImage'

export default OptimizedImage
