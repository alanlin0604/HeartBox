import { memo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default memo(function LazyLineChart({
  data,
  lines,
  xAxisKey = 'date',
  height = 300,
  gridStroke,
  axisStroke,
  tooltipStyle,
  showLegend = false,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis
          dataKey={xAxisKey}
          stroke={axisStroke}
          tick={{ fill: axisStroke, fontSize: 12 }}
        />
        <YAxis
          stroke={axisStroke}
          tick={{ fill: axisStroke, fontSize: 12 }}
        />
        <Tooltip contentStyle={tooltipStyle} />
        {showLegend && <Legend />}
        {lines.map((lineConfig) => (
          <Line
            key={lineConfig.dataKey}
            type="monotone"
            dataKey={lineConfig.dataKey}
            stroke={lineConfig.stroke}
            strokeWidth={lineConfig.strokeWidth || 2}
            dot={lineConfig.dot !== undefined ? lineConfig.dot : false}
            name={lineConfig.name}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
})
