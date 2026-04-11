import { memo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default memo(function LazyBarChart({
  data,
  bars,
  xAxisKey = 'name',
  height = 300,
  gridStroke,
  axisStroke,
  tooltipStyle,
  showLegend = false,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
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
        {bars.map((barConfig) => (
          <Bar
            key={barConfig.dataKey}
            dataKey={barConfig.dataKey}
            fill={barConfig.fill}
            name={barConfig.name}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
})
