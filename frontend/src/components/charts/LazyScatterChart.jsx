import { memo } from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default memo(function LazyScatterChart({
  data,
  scatters,
  xAxisKey,
  yAxisKey,
  height = 300,
  gridStroke,
  axisStroke,
  tooltipStyle,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis
          dataKey={xAxisKey}
          stroke={axisStroke}
          tick={{ fill: axisStroke, fontSize: 12 }}
        />
        <YAxis
          dataKey={yAxisKey}
          stroke={axisStroke}
          tick={{ fill: axisStroke, fontSize: 12 }}
        />
        <Tooltip contentStyle={tooltipStyle} cursor={{ strokeDasharray: '3 3' }} />
        {scatters.map((scatterConfig) => (
          <Scatter
            key={scatterConfig.name}
            name={scatterConfig.name}
            data={scatterConfig.data || data}
            fill={scatterConfig.fill}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  )
})
