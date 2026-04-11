import { memo } from 'react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip,
} from 'recharts'

export default memo(function LazyRadarChart({
  data,
  radars,
  angleKey = 'tag',
  height = 350,
  outerRadius = '65%',
  gridStroke,
  axisStroke,
  tooltipStyle,
  domain = [0, 10],
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} outerRadius={outerRadius} cx="50%" cy="50%">
        <PolarGrid stroke={gridStroke} />
        <PolarAngleAxis
          dataKey={angleKey}
          tick={{ fill: axisStroke, fontSize: 13 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={domain}
          tick={false}
        />
        <Tooltip contentStyle={tooltipStyle} />
        {radars.map((radarConfig) => (
          <Radar
            key={radarConfig.dataKey}
            name={radarConfig.name}
            dataKey={radarConfig.dataKey}
            stroke={radarConfig.stroke}
            fill={radarConfig.fill}
            fillOpacity={radarConfig.fillOpacity || 0.3}
          />
        ))}
      </RadarChart>
    </ResponsiveContainer>
  )
})
