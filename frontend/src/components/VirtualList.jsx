import { memo, useRef, useState, useEffect, useCallback } from 'react'

/**
 * Virtualized list component for rendering large lists efficiently
 * Only renders visible items + buffer, significantly improves performance for 100+ items
 *
 * @param {Array} items - Array of items to render
 * @param {Function} renderItem - Render function: (item, index) => ReactNode
 * @param {number} itemHeight - Height of each item in pixels (must be fixed)
 * @param {number} overscan - Number of items to render outside viewport (default: 3)
 * @param {number} height - Container height (default: '100%')
 * @param {string} className - Additional CSS classes
 * @param {Function} onEndReached - Callback when scrolled near end (for infinite scroll)
 * @param {number} endReachedThreshold - Distance from end to trigger callback (default: 300px)
 *
 * @example
 * <VirtualList
 *   items={notes}
 *   itemHeight={120}
 *   renderItem={(note, index) => <NoteCard key={note.id} note={note} />}
 *   onEndReached={loadMore}
 * />
 */
export const VirtualList = memo(function VirtualList({
  items,
  renderItem,
  itemHeight,
  overscan = 3,
  height = '100%',
  className = '',
  onEndReached,
  endReachedThreshold = 300,
}) {
  const containerRef = useRef(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [containerHeight, setContainerHeight] = useState(0)

  // Update container height on mount and resize
  useEffect(() => {
    if (!containerRef.current) return

    const updateHeight = () => {
      setContainerHeight(containerRef.current.clientHeight)
    }

    updateHeight()
    window.addEventListener('resize', updateHeight)
    return () => window.removeEventListener('resize', updateHeight)
  }, [])

  // Handle scroll
  const handleScroll = useCallback((e) => {
    const newScrollTop = e.target.scrollTop
    setScrollTop(newScrollTop)

    // Infinite scroll support
    if (onEndReached) {
      const { scrollHeight, clientHeight } = e.target
      const distanceFromEnd = scrollHeight - clientHeight - newScrollTop

      if (distanceFromEnd < endReachedThreshold) {
        onEndReached()
      }
    }
  }, [onEndReached, endReachedThreshold])

  // Calculate visible range
  const totalHeight = items.length * itemHeight
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan)
  const endIndex = Math.min(
    items.length - 1,
    Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
  )

  // Get visible items
  const visibleItems = items.slice(startIndex, endIndex + 1)

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className={className}
      style={{
        height,
        overflow: 'auto',
        position: 'relative',
      }}
    >
      {/* Spacer for total height */}
      <div style={{ height: totalHeight, position: 'relative' }}>
        {/* Visible items */}
        <div
          style={{
            position: 'absolute',
            top: startIndex * itemHeight,
            left: 0,
            right: 0,
          }}
        >
          {visibleItems.map((item, index) =>
            renderItem(item, startIndex + index)
          )}
        </div>
      </div>
    </div>
  )
})

/**
 * Virtual grid component for 2D layouts
 * Useful for image galleries, card grids, etc.
 *
 * @example
 * <VirtualGrid
 *   items={photos}
 *   itemHeight={200}
 *   columns={3}
 *   gap={16}
 *   renderItem={(photo) => <PhotoCard photo={photo} />}
 * />
 */
export const VirtualGrid = memo(function VirtualGrid({
  items,
  itemHeight,
  columns = 2,
  gap = 16,
  overscan = 2,
  height = '100%',
  className = '',
  onEndReached,
  endReachedThreshold = 300,
}) {
  const containerRef = useRef(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [containerHeight, setContainerHeight] = useState(0)

  useEffect(() => {
    if (!containerRef.current) return

    const updateHeight = () => {
      setContainerHeight(containerRef.current.clientHeight)
    }

    updateHeight()
    window.addEventListener('resize', updateHeight)
    return () => window.removeEventListener('resize', updateHeight)
  }, [])

  const handleScroll = useCallback((e) => {
    const newScrollTop = e.target.scrollTop
    setScrollTop(newScrollTop)

    if (onEndReached) {
      const { scrollHeight, clientHeight } = e.target
      const distanceFromEnd = scrollHeight - clientHeight - newScrollTop

      if (distanceFromEnd < endReachedThreshold) {
        onEndReached()
      }
    }
  }, [onEndReached, endReachedThreshold])

  // Calculate grid dimensions
  const rowHeight = itemHeight + gap
  const totalRows = Math.ceil(items.length / columns)
  const totalHeight = totalRows * rowHeight

  // Calculate visible rows
  const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan)
  const endRow = Math.min(
    totalRows - 1,
    Math.ceil((scrollTop + containerHeight) / rowHeight) + overscan
  )

  // Get visible items
  const startIndex = startRow * columns
  const endIndex = Math.min(items.length - 1, (endRow + 1) * columns - 1)
  const visibleItems = items.slice(startIndex, endIndex + 1)

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className={className}
      style={{
        height,
        overflow: 'auto',
        position: 'relative',
      }}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div
          style={{
            position: 'absolute',
            top: startRow * rowHeight,
            left: 0,
            right: 0,
            display: 'grid',
            gridTemplateColumns: `repeat(${columns}, 1fr)`,
            gap: `${gap}px`,
          }}
        >
          {visibleItems.map((item, index) => (
            <div key={startIndex + index} style={{ height: itemHeight }}>
              {typeof item === 'function' ? item(startIndex + index) : item}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
})

/**
 * Auto-sizer wrapper that calculates item height dynamically
 * Use when you don't know the exact item height in advance
 *
 * Note: For best performance, prefer fixed heights when possible
 */
export const DynamicVirtualList = memo(function DynamicVirtualList({
  items,
  renderItem,
  estimatedItemHeight = 100,
  ...props
}) {
  const [measuredHeights, setMeasuredHeights] = useState({})
  const measureRef = useRef(null)

  // Measure first item to get approximate height
  useEffect(() => {
    if (!measureRef.current || items.length === 0) return

    const height = measureRef.current.getBoundingClientRect().height
    if (height > 0 && !measuredHeights[0]) {
      setMeasuredHeights({ 0: height })
    }
  }, [items, measuredHeights])

  const itemHeight = measuredHeights[0] || estimatedItemHeight

  return (
    <>
      {/* Hidden measurement element */}
      {items.length > 0 && !measuredHeights[0] && (
        <div
          ref={measureRef}
          style={{
            position: 'absolute',
            visibility: 'hidden',
            pointerEvents: 'none',
          }}
        >
          {renderItem(items[0], 0)}
        </div>
      )}

      <VirtualList
        items={items}
        renderItem={renderItem}
        itemHeight={itemHeight}
        {...props}
      />
    </>
  )
})

export default VirtualList
