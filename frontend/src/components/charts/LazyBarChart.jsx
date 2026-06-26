import { memo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, LabelList } from 'recharts'

export default memo(function LazyBarChart({
  data,
  bars,
  xAxisKey = 'name',
  height = 300,
  gridStroke,
  axisStroke,
  tooltipStyle,
  showLegend = false,
  yDomain,
  showCountLabel = false,  // when true, render `count` field as a sub-label below each bar
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: showCountLabel ? 20 : 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis
          dataKey={xAxisKey}
          stroke={axisStroke}
          tick={{ fill: axisStroke, fontSize: 12 }}
        />
        <YAxis
          stroke={axisStroke}
          tick={{ fill: axisStroke, fontSize: 12 }}
          domain={yDomain || ['auto', 'auto']}
        />
        <Tooltip contentStyle={tooltipStyle} />
        {showLegend && <Legend />}
        {bars.map((barConfig) => (
          <Bar
            key={barConfig.dataKey}
            dataKey={barConfig.dataKey}
            fill={barConfig.fill}
            name={barConfig.name}
          >
            {showCountLabel && (
              <LabelList
                dataKey="count"
                position="top"
                formatter={(v) => v ? `n=${v}` : ''}
                fill={axisStroke}
                fontSize={11}
              />
            )}
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
})
