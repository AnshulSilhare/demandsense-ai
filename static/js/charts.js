/**
 * DemandSense AI — Apache ECharts Chart Builders
 * ================================================
 * One builder function per chart. Each uses ChartTheme.init() to create
 * an ECharts instance and ChartTheme.setOption() to configure it.
 *
 * All charts use transparent backgrounds and adapt to the current theme.
 * Click handlers open the shared DetailDrawer for drill-down.
 */

const Charts = (() => {
  'use strict';

  /** Get current theme colors from ChartTheme */
  function _c() {
    return window.ChartTheme ? ChartTheme.getColors() : {
      text: '#0f172a', text2: '#475569', text3: '#94a3b8',
      border: 'rgba(15,23,42,.08)', border2: 'rgba(15,23,42,.15)',
      accent: '#1e3a5f', accentTitle: '#1d4ed8', accent2: '#0d9488',
      teal: '#0d9488', amber: '#d97706', green: '#16a34a', red: '#dc2626',
      surface: '#ffffff', bg: '#f8fafc', bg3: '#f1f5f9',
      glassBg: 'rgba(255,255,255,.08)', glassBorder: 'rgba(15,23,42,.08)',
      displayFont: "'Syne', sans-serif", bodyFont: "'DM Sans', sans-serif",
      monoFont: "'JetBrains Mono', monospace",
    };
  }

  function _isDark() { return document.body.classList.contains('dark'); }

  /** Format large numbers compactly */
  function _fmt(v) {
    if (v == null) return '—';
    if (Math.abs(v) >= 1e7) return '₹' + (v / 1e7).toFixed(2) + 'Cr';
    if (Math.abs(v) >= 1e5) return '₹' + (v / 1e5).toFixed(1) + 'L';
    if (Math.abs(v) >= 1000) return v.toLocaleString('en-IN');
    return v.toFixed?.(1) ?? String(v);
  }

  // ═══ 1. HERO CHART (Historical + Forecast with dataZoom) ═══
  function heroChart(containerId, history, forecast, impactData, festivals, festivalFilter) {
    const c = _c();
    const histDates = history.map(d => d.date);
    const histUnits = history.map(d => d.units_sold);
    const histRolling = history.map(d => d.rolling_7d);
    const fcDates = forecast.map(d => d.date);
    const fcUnits = forecast.map(d => d.predicted_units);
    const allDates = [...histDates, ...fcDates];

    const series = [
      // Historical raw demand (area)
      {
        name: 'Raw Daily Demand', type: 'line', symbol: 'none',
        data: histUnits, xAxisIndex: 0,
        areaStyle: { color: _isDark() ? 'rgba(255,255,255,.04)' : 'rgba(154,163,184,0.06)' },
        lineStyle: { color: c.text3, width: 1 },
        itemStyle: { color: c.text3 },
        opacity: festivalFilter ? 0.3 : 0.7,
        z: 1,
      },
      // 7d rolling average
      {
        name: '7-Day Rolling Avg', type: 'line', symbol: 'none', smooth: true,
        data: histRolling, xAxisIndex: 0,
        lineStyle: { color: c.text2, width: 1.5, type: 'dashed' },
        itemStyle: { color: c.text2 },
        z: 2,
      },
    ];

    // Confidence band
    if (forecast.length && forecast[0].upper_bound != null) {
      const upperData = new Array(histDates.length).fill(null).concat(forecast.map(d => d.upper_bound));
      const lowerData = new Array(histDates.length).fill(null).concat(forecast.map(d => d.lower_bound));
      series.push({
        name: '95% Confidence', type: 'line', symbol: 'none',
        data: upperData,
        lineStyle: { width: 0, opacity: 0 },
        areaStyle: { opacity: 0 },
        stack: 'ci', z: 3,
      });
      series.push({
        name: 'CI Lower', type: 'line', symbol: 'none',
        data: lowerData,
        lineStyle: { width: 0, opacity: 0 },
        areaStyle: { color: 'rgba(110,86,207,0.12)', opacity: 1 },
        stack: 'ci', z: 3, showInLegend: false,
      });
    }

    // Forecast line
    const forecastData = new Array(histDates.length).fill(null).concat(fcUnits);
    series.push({
      name: '30-Day Forecast', type: 'line', smooth: true,
      data: forecastData, symbolSize: 4,
      lineStyle: { color: c.accent, width: 2.5 },
      itemStyle: { color: c.accent },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: c.accent + '18' }, { offset: 1, color: c.accent + '02' }]
      }},
      z: 5,
    });

    // markLine for ROP & SS
    const markLines = [];
    if (impactData) {
      if (impactData.reorder_point_units) {
        markLines.push({
          yAxis: impactData.reorder_point_units, name: 'ROP',
          lineStyle: { color: c.red, type: 'dashed', width: 1.5 },
          label: { formatter: 'ROP: {c}', fontSize: 10, fontFamily: c.monoFont, color: c.red, position: 'insideEndTop' },
        });
      }
      if (impactData.safety_stock_units) {
        markLines.push({
          yAxis: impactData.safety_stock_units, name: 'Safety Stock',
          lineStyle: { color: c.amber, type: 'dotted', width: 1.5 },
          label: { formatter: 'SS: {c}', fontSize: 10, fontFamily: c.monoFont, color: c.amber, position: 'insideEndTop' },
        });
      }
    }

    // Forecast start markLine
    if (fcDates.length) {
      markLines.push({
        xAxis: fcDates[0], name: 'Forecast Start',
        lineStyle: { color: c.accent, type: 'dashed', width: 1.5 },
        label: { formatter: '◄ Forecast Start', fontSize: 10, fontFamily: c.monoFont, color: c.accent, position: 'insideEndTop' },
      });
    }

    if (markLines.length) {
      series[series.length - 1].markLine = {
        silent: true, symbol: 'none',
        data: markLines,
      };
    }

    // Festival markArea overlays
    if (festivals && festivals.length) {
      const markAreaData = [];
      festivals.forEach(f => {
        if (f.dates && f.dates.length >= 2) {
          markAreaData.push([
            { xAxis: f.dates[0], itemStyle: { color: f.change_pct > 0 ? 'rgba(217,119,6,0.06)' : 'rgba(220,38,38,0.06)' } },
            { xAxis: f.dates[1] }
          ]);
        }
      });
      if (markAreaData.length) {
        series[series.length - 1].markArea = { silent: true, data: markAreaData };
      }
    }

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', lineStyle: { color: c.border2 } },
      },
      legend: {
        data: ['Raw Daily Demand', '7-Day Rolling Avg', '30-Day Forecast', '95% Confidence'],
        bottom: 0,
      },
      toolbox: {
        feature: {
          brush: { type: ['lineX'], title: { lineX: 'Range Select' } },
          dataZoom: { title: { zoom: 'Zoom', back: 'Reset' } },
        },
        right: 16, top: 4,
      },
      brush: { toolbox: ['lineX'], xAxisIndex: 0 },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
        { type: 'slider', xAxisIndex: 0, height: 24, bottom: 32, borderColor: c.border,
          fillerColor: c.teal + '18', handleStyle: { color: c.teal },
          dataBackground: { lineStyle: { color: c.text3 }, areaStyle: { color: c.border } },
        },
      ],
      grid: { left: 56, right: 24, top: 24, bottom: 80, containLabel: false },
      xAxis: {
        type: 'category', data: allDates, boundaryGap: false,
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3,
          formatter: v => { const d = new Date(v); return d.toLocaleDateString('en-IN', {month:'short', day:'numeric'}); }
        },
        axisLine: { lineStyle: { color: c.border } },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3, formatter: v => v >= 1000 ? (v/1000).toFixed(0)+'K' : v },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      series,
      animationDuration: 800,
      animationEasing: 'cubicOut',
    };

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);

    // Brush selection → open detail drawer with date range stats
    const inst = ChartTheme.getInstance(containerId);
    if (inst) {
      inst.on('brushSelected', params => {
        const brushed = params.batch?.[0];
        if (!brushed || !brushed.selected?.[0]) return;
        const indices = brushed.selected[0].dataIndex;
        if (!indices.length) return;
        const selDates = indices.map(i => allDates[i]);
        const selValues = indices.map(i => histUnits[i]).filter(v => v != null);
        if (!selValues.length) return;
        const avg = (selValues.reduce((a,b) => a+b, 0) / selValues.length).toFixed(0);
        const peak = Math.max(...selValues);
        const min = Math.min(...selValues);
        DetailDrawer.open('Date Range Analysis', `
          <p style="color:var(--text3);font-family:var(--mono);font-size:.78rem;margin-bottom:.75rem">
            ${selDates[0]} → ${selDates[selDates.length-1]} (${selDates.length} days)
          </p>
          ${DetailDrawer.buildMetricTable([
            { label: 'Average Demand', value: Number(avg).toLocaleString(), unit: ' units' },
            { label: 'Peak Demand', value: peak.toLocaleString(), unit: ' units', highlight: true },
            { label: 'Minimum Demand', value: min.toLocaleString(), unit: ' units' },
            { label: 'Range', value: (peak - min).toLocaleString(), unit: ' units' },
            { label: 'Days Selected', value: selDates.length },
          ])}
        `);
      });
    }
  }

  // ═══ 2. DECOMPOSITION (3 linked charts) ═══
  function decompChart(trendId, seasonalId, residualId, dates, trend, seasonal, residual) {
    const c = _c();

    const baseOpts = (title, data, color, chartType, showSlider = false) => ({
      grid: { left: 48, right: 16, top: 22, bottom: showSlider ? 28 : 16, containLabel: false },
      title: { text: title, left: 4, top: 2, textStyle: { fontSize: 11, fontWeight: 600, color: c.text2, fontFamily: c.bodyFont } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'line' } },
      xAxis: {
        type: 'category', data: dates, boundaryGap: chartType === 'bar',
        axisLabel: {
          show: showSlider,
          fontSize: 9, fontFamily: c.monoFont, color: c.text3,
          formatter: v => { const d = new Date(v); return d.toLocaleDateString('en-IN', {month:'short', day:'numeric'}); }
        },
        axisLine: { lineStyle: { color: c.border } },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value', axisLabel: { fontSize: 9, fontFamily: c.monoFont, color: c.text3 },
        axisLine: { show: false }, splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
        ...(showSlider ? [{
          type: 'slider', xAxisIndex: 0, height: 14, bottom: 2, borderColor: c.border,
          fillerColor: c.teal + '18', handleStyle: { color: c.teal },
        }] : [])
      ],
      series: [{
        type: chartType || 'line', data, smooth: chartType !== 'bar', symbol: 'none',
        lineStyle: chartType !== 'bar' ? { color, width: 2 } : undefined,
        itemStyle: { color },
        areaStyle: chartType !== 'bar' ? { color: color + '12' } : undefined,
      }],
      animationDuration: 600,
    });

    const trendOpts = baseOpts('Trend', trend, c.accent, 'line', false);
    const seasonalOpts = baseOpts('Seasonality', seasonal, c.amber, 'line', false);
    seasonalOpts.series[0].markLine = {
      silent: true, symbol: 'none',
      data: [{ yAxis: 0, lineStyle: { color: c.amber, type: 'dotted', width: 1 } }],
    };

    const residualOpts = baseOpts('Residuals', residual, c.text3, 'bar', true);
    residualOpts.series[0].markLine = {
      silent: true, symbol: 'none',
      data: [{ yAxis: 0, lineStyle: { color: c.text3, type: 'dotted', width: 1 } }],
    };

    ChartTheme.init(trendId);
    ChartTheme.setOption(trendId, trendOpts);

    ChartTheme.init(seasonalId);
    ChartTheme.setOption(seasonalId, seasonalOpts);

    ChartTheme.init(residualId);
    ChartTheme.setOption(residualId, residualOpts);

    // Link all 3 charts for synchronized crosshair
    const t = ChartTheme.getInstance(trendId);
    const s = ChartTheme.getInstance(seasonalId);
    const r = ChartTheme.getInstance(residualId);
    if (t && s && r) {
      echarts.connect([t, s, r]);
    }
  }

  // ═══ 3. FESTIVAL IMPACT (Horizontal Bar / Lollipop) ═══
  function festivalChart(containerId, festivals, onFestivalClick) {
    const c = _c();
    if (!festivals || !festivals.length) {
      ChartTheme.init(containerId);
      ChartTheme.setOption(containerId, { title: { text: 'No festival data', left: 'center', top: 'center', textStyle: { color: c.text3, fontSize: 13 } } });
      return;
    }

    const names = festivals.map(f => f.festival_name || f.name || f.festival);
    const values = festivals.map(f => f.change_pct || f.impact_pct || 0);

    const option = {
      grid: { left: 140, right: 60, top: 12, bottom: 24, containLabel: false },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: params => {
          const p = params[0];
          return `<b>${p.name}</b><br/>Impact: ${p.value > 0 ? '+' : ''}${p.value.toFixed(1)}%`;
        },
      },
      xAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3, formatter: v => v + '%' },
        axisLine: { lineStyle: { color: c.border } },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      yAxis: {
        type: 'category', data: names, inverse: true,
        axisLabel: { fontSize: 11, fontFamily: c.bodyFont, color: c.text },
        axisLine: { show: false }, axisTick: { show: false },
      },
      series: [{
        type: 'bar', data: values.map((v, i) => ({
          value: v,
          itemStyle: {
            color: v > 0 ? c.amber : c.red,
            borderRadius: v > 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
          },
          label: {
            show: true, position: v > 0 ? 'right' : 'left',
            formatter: v > 0 ? `+${v.toFixed(0)}%` : `${v.toFixed(0)}%`,
            fontSize: 10, fontFamily: c.monoFont, color: c.text2,
          },
        })),
        barMaxWidth: 18,
        markLine: {
          silent: true, symbol: 'none',
          data: [{ xAxis: 0, lineStyle: { color: c.text3, width: 1 } }],
          label: { show: false },
        },
      }],
      animationDuration: 800,
    };

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);

    const inst = ChartTheme.getInstance(containerId);
    if (inst && onFestivalClick) {
      inst.on('click', params => {
        if (params.componentType === 'series') {
          onFestivalClick(names[params.dataIndex], params.dataIndex);
        }
      });
    }
  }

  // ═══ 4. RADAR CHART (Native ECharts Radar) ═══
  function radarChart(containerId, radarData, leaderboard, winnerName) {
    const c = _c();
    const metrics = ['MAPE', 'RMSE', 'MAE', 'WAPE'];

    // Fallback: if radarData is empty/missing, synthesize from leaderboard
    let rData = radarData;
    if (!rData || !rData.length) {
      if (leaderboard && leaderboard.length) {
        const mKeys = ['mape', 'rmse', 'mae', 'wape'];
        rData = [];
        mKeys.forEach(metric => {
          const validVals = leaderboard.map(m => m[metric] || 0).filter(v => v < 900);
          const maxVal = validVals.length ? Math.max(...validVals) : 100;
          const minVal = validVals.length ? Math.min(...validVals) : 0;
          leaderboard.forEach(row => {
            const mVal = row[metric] || 0;
            let score = 100;
            if (mVal >= 900) score = 0;
            else if (maxVal > minVal) score = 100 - 80 * ((mVal - minVal) / Math.max(1e-5, maxVal - minVal));
            rData.push({
              model_name: row.model_name,
              metric: metric.toUpperCase(),
              score: Math.round(score * 10) / 10,
              actual_value: mVal,
            });
          });
        });
      } else {
        rData = [];
      }
    }

    const modelNames = [...new Set(rData.map(r => r.model_name))];
    if (!modelNames.length) {
      ChartTheme.init(containerId);
      ChartTheme.setOption(containerId, { title: { text: 'No model data', left: 'center', top: 'center', textStyle: { color: c.text3 } } });
      return;
    }

    const indicator = metrics.map(m => ({ name: m + ' ↓', max: 100 }));

    const series = modelNames.map(name => {
      const isWinner = name === winnerName;
      const scores = metrics.map(m => {
        const row = rData.find(r => r.model_name === name && r.metric === m);
        return row ? row.score : 0;
      });

      return {
        name,
        type: 'radar',
        data: [{ value: scores, name }],
        symbol: isWinner ? 'circle' : 'emptyCircle',
        symbolSize: isWinner ? 6 : 3,
        lineStyle: { width: isWinner ? 2.5 : 1, color: isWinner ? c.accent : c.text3 },
        itemStyle: { color: isWinner ? c.accent : c.text3 },
        areaStyle: isWinner ? { color: c.accent + '1A' } : undefined,
        emphasis: { lineStyle: { width: 3 }, areaStyle: { color: c.accent + '30' } },
      };
    });

    const option = {
      tooltip: {
        trigger: 'item',
        formatter: params => {
          if (!params.value) return '';
          return `<b>${params.name}</b><br/>` + metrics.map((m, i) => `${m}: ${params.value[i].toFixed(1)}`).join('<br/>');
        },
      },
      legend: {
        data: modelNames, bottom: 0,
        textStyle: { fontSize: 10, fontFamily: c.bodyFont },
      },
      radar: {
        indicator,
        shape: 'polygon',
        splitArea: { areaStyle: { color: ['transparent'] } },
        splitLine: { lineStyle: { color: c.border } },
        axisLine: { lineStyle: { color: c.border } },
        axisName: { color: c.text2, fontSize: 11, fontFamily: c.monoFont },
        center: ['50%', '48%'], radius: '65%',
      },
      series,
      animationDuration: 1000,
    };

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);

    // Click on axis label → open drawer with ranked list for that metric
    const inst = ChartTheme.getInstance(containerId);
    if (inst) {
      inst.on('click', params => {
        if (params.targetType === 'axisName' || (params.componentType === 'radar' && params.name)) {
          const clickedMetric = (params.name || '').replace(' ↓', '');
          if (!metrics.includes(clickedMetric)) return;
          const metricKey = clickedMetric.toLowerCase();
          const ranked = [...(leaderboard || [])]
            .filter(m => m[metricKey] < 900)
            .sort((a, b) => a[metricKey] - b[metricKey]);
          const maxVal = ranked.length ? ranked[ranked.length - 1][metricKey] : 1;

          DetailDrawer.open(`${clickedMetric} — Model Ranking`, DetailDrawer.buildRankList(
            ranked.map((m, i) => ({
              rank: i + 1,
              name: m.model_name + (m.model_name === winnerName ? ' ★' : ''),
              value: m[metricKey].toFixed(4),
              bar: Math.max(5, (m[metricKey] / maxVal) * 100),
            }))
          ));
        }
      });
    }
  }

  // ═══ 5. FEATURE IMPORTANCE (Horizontal Bar) ═══
  function featureImportanceChart(containerId, features) {
    const c = _c();
    if (!features || !features.length) {
      ChartTheme.init(containerId);
      ChartTheme.setOption(containerId, { title: { text: 'No feature data', left: 'center', top: 'center', textStyle: { color: c.text3 } } });
      return;
    }

    const sorted = [...features].sort((a, b) => a.importance - b.importance);
    const topImportance = sorted[sorted.length - 1].importance;

    const option = {
      grid: { left: 140, right: 56, top: 8, bottom: 16, containLabel: false },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: params => `<b>${params[0].name}</b><br/>Importance: ${params[0].value.toFixed(4)} (${sorted.find(f => f.name.replace(/_/g, ' ') === params[0].name)?.pct || 0}%)`,
      },
      xAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3 },
        axisLine: { lineStyle: { color: c.border } },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      yAxis: {
        type: 'category', data: sorted.map(f => f.name.replace(/_/g, ' ')),
        axisLabel: { fontSize: 10, fontFamily: c.bodyFont, color: c.text },
        axisLine: { show: false }, axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: sorted.map(f => ({
          value: f.importance,
          itemStyle: {
            color: f.importance === topImportance ? c.accent : c.teal,
            borderRadius: [0, 4, 4, 0],
          },
          label: {
            show: true, position: 'right',
            formatter: `${f.pct}%`,
            fontSize: 10, fontFamily: c.monoFont, color: c.text2,
          },
        })),
        barMaxWidth: 22,
      }],
      animationDuration: 1000,
      animationEasing: 'cubicOut',
    };

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);

    // Click → open drawer with feature detail
    const inst = ChartTheme.getInstance(containerId);
    if (inst) {
      inst.on('click', params => {
        if (params.componentType !== 'series') return;
        const f = sorted[params.dataIndex];
        if (!f) return;
        const rank = sorted.length - params.dataIndex;
        const deltaFromTop = (topImportance - f.importance).toFixed(4);
        DetailDrawer.open(`Feature: ${f.name.replace(/_/g, ' ')}`, DetailDrawer.buildMetricTable([
          { label: 'Importance Score', value: f.importance.toFixed(4), highlight: true },
          { label: 'Contribution', value: f.pct + '%' },
          { label: 'Rank', value: '#' + rank + ' of ' + sorted.length },
          { label: 'Delta from #1', value: deltaFromTop },
        ]));
      });
    }
  }

  // ═══ 6. ACTUAL VS PREDICTED SCATTER ═══
  function scatterChart(containerId, leaderboard, history, forecast) {
    const c = _c();
    const n = Math.min(forecast.length, history.length, 30);
    const actuals = history.slice(-n).map(d => d.units_sold);
    const predicted = forecast.slice(0, n).map(d => d.predicted_units);
    const allVals = [...actuals, ...predicted];
    const minV = Math.min(...allVals) * 0.9;
    const maxV = Math.max(...allVals) * 1.1;

    const scatterData = actuals.map((a, i) => [a, predicted[i]]);
    const errors = actuals.map((a, i) => Math.abs(a - predicted[i]));
    const maxErr = Math.max(...errors) || 1;

    const option = {
      grid: { left: 56, right: 24, top: 16, bottom: 48, containLabel: false },
      tooltip: {
        trigger: 'item',
        formatter: p => `Actual: ${p.value[0]?.toLocaleString()}<br/>Predicted: ${p.value[1]?.toLocaleString()}<br/>Error: ${Math.abs(p.value[0] - p.value[1]).toLocaleString()}`,
      },
      xAxis: {
        type: 'value', name: 'Actual Units', nameLocation: 'center', nameGap: 32,
        nameTextStyle: { fontSize: 11, fontFamily: c.bodyFont, color: c.text2 },
        min: minV, max: maxV,
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3 },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      yAxis: {
        type: 'value', name: 'Predicted Units', nameLocation: 'center', nameGap: 40,
        nameTextStyle: { fontSize: 11, fontFamily: c.bodyFont, color: c.text2 },
        min: minV, max: maxV,
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3 },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      series: [
        // 45° perfect-fit diagonal
        {
          type: 'line', symbol: 'none', silent: true,
          data: [[minV, minV], [maxV, maxV]],
          lineStyle: { color: c.text3, width: 1.5, type: 'dashed' },
          z: 1,
        },
        // Scatter points
        {
          type: 'scatter',
          data: scatterData.map((d, i) => ({
            value: d,
            itemStyle: {
              color: errors[i] / maxErr < 0.33 ? c.green : errors[i] / maxErr < 0.66 ? c.amber : c.red,
            },
          })),
          symbolSize: 8,
          emphasis: { itemStyle: { borderColor: c.text, borderWidth: 2 } },
          z: 5,
        },
      ],
      visualMap: {
        show: true, type: 'continuous', min: 0, max: maxErr,
        dimension: 'none', inRange: { color: [c.green, c.amber, c.red] },
        text: ['High Error', 'Low'], textStyle: { fontSize: 9, color: c.text3 },
        right: 8, top: 'center', itemWidth: 10, itemHeight: 80,
        calculable: false,
      },
      animationDuration: 600,
    };

    // Remove visualMap (manual coloring above handles it)
    delete option.visualMap;

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);
  }

  // ═══ 7. INVENTORY TRAJECTORY ═══
  function inventoryChart(containerId, trajectory, safetyStock, rop) {
    const c = _c();
    const dates = trajectory.map(d => d.date);
    const stock = trajectory.map(d => d.projected_stock);
    const maxStock = Math.max(...stock) * 1.15;

    // Find stockout point
    const stockoutIdx = stock.findIndex(s => s <= 0);
    const markPoints = [];
    if (stockoutIdx >= 0) {
      markPoints.push({
        coord: [dates[stockoutIdx], 0],
        value: '⚠ STOCKOUT',
        symbolSize: 50,
        symbol: 'pin',
        itemStyle: { color: c.red },
        label: { color: '#fff', fontSize: 9, fontFamily: c.monoFont },
      });
    }

    const markLineData = [];
    if (rop > 0) {
      markLineData.push({
        yAxis: rop, name: 'Reorder Point',
        lineStyle: { color: c.red, type: 'dashed', width: 1.5 },
        label: { formatter: 'ROP: {c}', fontSize: 10, fontFamily: c.monoFont, color: c.red, position: 'insideEndTop' },
      });
    }
    if (safetyStock > 0) {
      markLineData.push({
        yAxis: safetyStock, name: 'Safety Stock',
        lineStyle: { color: c.amber, type: 'dotted', width: 1.5 },
        label: { formatter: 'SS: {c}', fontSize: 10, fontFamily: c.monoFont, color: c.amber, position: 'insideEndTop' },
      });
    }

    // markArea for risk zones
    const markAreaData = [];
    if (safetyStock > 0) {
      markAreaData.push([
        { yAxis: 0, itemStyle: { color: 'rgba(220,38,38,0.06)' } },
        { yAxis: safetyStock }
      ]);
    }
    if (safetyStock > 0 && rop > 0) {
      markAreaData.push([
        { yAxis: safetyStock, itemStyle: { color: 'rgba(217,119,6,0.06)' } },
        { yAxis: rop }
      ]);
    }
    if (rop > 0) {
      markAreaData.push([
        { yAxis: rop, itemStyle: { color: 'rgba(22,163,74,0.04)' } },
        { yAxis: maxStock }
      ]);
    }

    const option = {
      grid: { left: 56, right: 24, top: 16, bottom: 56, containLabel: false },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'cross' },
        formatter: params => {
          const p = params[0];
          return `<b>${p.name}</b><br/>Stock: ${p.value?.toLocaleString()} units`;
        },
      },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0 },
        { type: 'slider', xAxisIndex: 0, height: 20, bottom: 4, borderColor: c.border,
          fillerColor: c.teal + '18', handleStyle: { color: c.teal },
        },
      ],
      xAxis: {
        type: 'category', data: dates, boundaryGap: false,
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3,
          formatter: v => { const d = new Date(v); return d.toLocaleDateString('en-IN', {month:'short', day:'numeric'}); }
        },
        axisLine: { lineStyle: { color: c.border } },
      },
      yAxis: {
        type: 'value', max: maxStock,
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3, formatter: v => v >= 1000 ? (v/1000).toFixed(0)+'K' : v },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      series: [{
        type: 'line', data: stock, smooth: true, symbolSize: 4,
        lineStyle: { color: c.accent, width: 2.5 },
        itemStyle: { color: c.accent },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: c.accent + '18' }, { offset: 1, color: c.accent + '02' }]
        }},
        markLine: markLineData.length ? { silent: true, symbol: 'none', data: markLineData } : undefined,
        markPoint: markPoints.length ? { data: markPoints } : undefined,
        markArea: markAreaData.length ? { silent: true, data: markAreaData } : undefined,
      }],
      animationDuration: 800,
    };

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);
  }

  // ═══ 8. LEADERBOARD BAR ═══
  function leaderboardBar(containerId, leaderboard, winnerName) {
    const c = _c();
    const sorted = [...leaderboard].filter(m => m.mape < 900).sort((a, b) => b.mape - a.mape);
    const names = sorted.map(m => m.model_name);
    const scores = sorted.map(m => (100 - m.mape).toFixed(1));

    const option = {
      grid: { left: 120, right: 56, top: 8, bottom: 16, containLabel: false },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: p => `<b>${p[0].name}</b><br/>Score: ${p[0].value}`,
      },
      xAxis: {
        type: 'value', min: 0, max: 100,
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3 },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      yAxis: {
        type: 'category', data: names,
        axisLabel: { fontSize: 11, fontFamily: c.bodyFont, color: c.text },
        axisLine: { show: false }, axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: sorted.map(m => ({
          value: (100 - m.mape).toFixed(1),
          itemStyle: {
            color: m.model_name === winnerName ? c.accent : c.teal,
            borderRadius: [0, 4, 4, 0],
          },
          label: {
            show: true, position: 'right',
            formatter: m.model_name === winnerName ? `★ ${(100 - m.mape).toFixed(1)}` : (100 - m.mape).toFixed(1),
            fontSize: 10, fontFamily: c.monoFont,
            color: m.model_name === winnerName ? c.accent : c.text2,
            fontWeight: m.model_name === winnerName ? 700 : 400,
          },
        })),
        barMaxWidth: 24,
      }],
      animationDuration: 1200,
      animationEasing: 'cubicOut',
    };

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);

    // Click → open drawer with full model metrics
    const inst = ChartTheme.getInstance(containerId);
    if (inst) {
      inst.on('click', params => {
        if (params.componentType !== 'series') return;
        const m = sorted[params.dataIndex];
        if (!m) return;
        DetailDrawer.open(`Model: ${m.model_name}`, `
          <p style="color:var(--text3);font-size:.82rem;margin-bottom:.5rem">${m.model_name === winnerName ? '★ Tournament Winner' : 'Challenger Model'}</p>
          ${DetailDrawer.buildMetricTable([
            { label: 'MAPE', value: m.mape.toFixed(4), highlight: m.model_name === winnerName },
            { label: 'RMSE', value: m.rmse.toFixed(4) },
            { label: 'MAE', value: m.mae.toFixed(4) },
            { label: 'WAPE', value: m.wape.toFixed(4) },
            { label: 'Fit Time', value: (m.fit_time_sec || 0).toFixed(2), unit: 's' },
            { label: 'Status', value: m.status || 'OK' },
          ])}
        `);
      });
    }
  }

  // ═══ 9. ABC TREEMAP ═══
  function abcTreemap(containerId, abcData) {
    const c = _c();
    if (!abcData || !abcData.length) {
      ChartTheme.init(containerId);
      ChartTheme.setOption(containerId, { title: { text: 'No ABC data', left: 'center', top: 'center', textStyle: { color: c.text3 } } });
      return;
    }

    // Reshape flat table into hierarchical treemap data
    const classes = { A: [], B: [], C: [] };
    const classColors = { A: c.teal, B: c.amber, C: c.text3 };
    abcData.forEach(row => {
      const cls = row.abc_class || 'C';
      if (classes[cls]) {
        classes[cls].push({
          name: row.sku_name || row.sku_id,
          value: row.revenue_inr || 0,
          _raw: row,
        });
      }
    });

    const treeData = Object.entries(classes)
      .filter(([, items]) => items.length > 0)
      .map(([cls, items]) => ({
        name: `Class ${cls}`,
        itemStyle: { color: classColors[cls], borderColor: c.bg3, borderWidth: 2 },
        children: items.map(item => ({
          name: item.name,
          value: item.value,
          _raw: item._raw,
          itemStyle: { color: classColors[cls], borderColor: c.bg3, borderWidth: 1 },
        })),
      }));

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        formatter: params => {
          if (params.data?.children) {
            const total = params.data.children.reduce((s, c) => s + c.value, 0);
            return `<b>${params.data.name}</b><br/>${params.data.children.length} SKUs<br/>Revenue: ₹${(total/1e5).toFixed(1)}L`;
          }
          return `<b>${params.data.name}</b><br/>Revenue: ₹${(params.data.value/1e5).toFixed(1)}L<br/>Pareto Class: ${params.data._raw?.abc_class || '—'}`;
        },
      },
      series: [{
        type: 'treemap',
        data: treeData,
        roam: false,
        nodeClick: 'zoomToNode',
        breadcrumb: {
          show: true, left: 12, bottom: 8,
          itemStyle: { textStyle: { fontSize: 11, fontFamily: c.bodyFont, color: c.text } },
        },
        label: {
          show: true,
          formatter: '{b}',
          fontSize: 11,
          fontFamily: c.bodyFont,
          color: '#ffffff',
        },
        upperLabel: {
          show: true, height: 26,
          formatter: p => `${p.name} (${p.data?.children?.length || 0} SKUs)`,
          fontSize: 12, fontWeight: 700, fontFamily: c.displayFont,
          color: '#ffffff',
        },
        levels: [
          { itemStyle: { borderWidth: 2, borderColor: c.surface, gapWidth: 2 } },
          { itemStyle: { borderWidth: 1, borderColor: c.surface, gapWidth: 1 } },
        ],
      }],
      animationDuration: 800,
    };

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);

    // Click on leaf SKU → open drawer with detail
    const inst = ChartTheme.getInstance(containerId);
    if (inst) {
      inst.on('click', params => {
        const raw = params.data?._raw;
        if (!raw) return; // clicked a category node, not a leaf
        DetailDrawer.open(`SKU: ${raw.sku_name || raw.sku_id}`, DetailDrawer.buildMetricTable([
          { label: 'SKU ID', value: raw.sku_id },
          { label: 'Revenue', value: '₹' + (raw.revenue_inr / 1e5).toFixed(1) + 'L', highlight: true },
          { label: 'Cumulative Revenue', value: raw.cum_pct ? raw.cum_pct.toFixed(1) + '%' : '—' },
          { label: 'ABC Class', value: raw.abc_class },
        ]));
      });
    }
  }

  // ═══ 10. REGIONAL MAP (Scatter-based) ═══
  function mapChart(containerId, regions) {
    const c = _c();
    if (!regions || !regions.length) {
      ChartTheme.init(containerId);
      ChartTheme.setOption(containerId, { title: { text: 'No regional data', left: 'center', top: 'center', textStyle: { color: c.text3 } } });
      return;
    }

    const maxRev = Math.max(...regions.map(r => r.total_revenue));
    const maxUnits = Math.max(...regions.map(r => r.total_units));

    // Using scatter on a value-based coordinate (lat/lon mapped to x/y)
    // Since ECharts geo requires registered maps, use a clean scatter layout
    const option = {
      grid: { left: 48, right: 24, top: 24, bottom: 40, containLabel: false },
      tooltip: {
        trigger: 'item',
        formatter: p => `<b>${p.data._name}</b><br/>Revenue: ₹${(p.data._rev/1e5).toFixed(1)}L<br/>Units: ${p.data._units.toLocaleString()}`,
      },
      xAxis: {
        type: 'value', name: 'Longitude', min: 68, max: 98,
        axisLabel: { fontSize: 9, fontFamily: c.monoFont, color: c.text3 },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
        nameTextStyle: { fontSize: 10, color: c.text3 },
      },
      yAxis: {
        type: 'value', name: 'Latitude', min: 6, max: 38,
        axisLabel: { fontSize: 9, fontFamily: c.monoFont, color: c.text3 },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
        nameTextStyle: { fontSize: 10, color: c.text3 },
      },
      series: [{
        type: 'scatter',
        data: regions.map(r => ({
          value: [r.lon, r.lat],
          symbolSize: 12 + (r.total_revenue / maxRev) * 36,
          _name: r.region_name, _rev: r.total_revenue, _units: r.total_units,
          itemStyle: {
            color: c.accent,
            opacity: 0.7 + (r.total_revenue / maxRev) * 0.3,
          },
          label: {
            show: true, formatter: r.region_name,
            position: 'right', fontSize: 10, fontFamily: c.bodyFont, color: c.text2,
          },
        })),
        emphasis: {
          itemStyle: { borderColor: c.teal, borderWidth: 3, shadowBlur: 10, shadowColor: c.teal + '40' },
        },
      }],
      animationDuration: 800,
    };

    ChartTheme.init(containerId);
    ChartTheme.setOption(containerId, option);

    // Click → open drawer with region detail
    const inst = ChartTheme.getInstance(containerId);
    if (inst) {
      inst.on('click', params => {
        if (params.componentType !== 'series') return;
        const d = params.data;
        if (!d) return;
        DetailDrawer.open(`Region: ${d._name}`, DetailDrawer.buildMetricTable([
          { label: 'Total Revenue', value: '₹' + (d._rev / 1e5).toFixed(1) + 'L', highlight: true },
          { label: 'Total Units', value: d._units.toLocaleString() },
          { label: 'Revenue Share', value: ((d._rev / regions.reduce((s, r) => s + r.total_revenue, 0)) * 100).toFixed(1) + '%' },
          { label: 'Coordinates', value: `${d.value[1].toFixed(2)}°N, ${d.value[0].toFixed(2)}°E` },
        ]));
      });
    }
  }

  // ═══ 11. SCENARIO SIMULATOR (setOption merge for morphing) ═══
  function simChart(containerId, baseTraj, simTraj, baseSS, simSS, simRop, merge) {
    const c = _c();
    const baseDates = (baseTraj || []).map(d => d.date);
    const baseStock = (baseTraj || []).map(d => d.projected_stock);
    const simDates = (simTraj || []).map(d => d.date);
    const simStock = (simTraj || []).map(d => d.projected_stock);
    const allDates = baseDates.length >= simDates.length ? baseDates : simDates;

    const markLineData = [];
    if (baseSS > 0) {
      markLineData.push({
        yAxis: baseSS, name: 'Base SS',
        lineStyle: { color: c.amber, type: 'dotted', width: 1 },
        label: { formatter: 'Base SS', fontSize: 9, color: c.amber, position: 'insideEndTop' },
      });
    }
    if (simSS > 0 && simSS !== baseSS) {
      markLineData.push({
        yAxis: simSS, name: 'Sim SS',
        lineStyle: { color: c.red, type: 'dotted', width: 1 },
        label: { formatter: 'Sim SS', fontSize: 9, color: c.red, position: 'insideEndTop' },
      });
    }
    if (simRop > 0) {
      markLineData.push({
        yAxis: simRop, name: 'Sim ROP',
        lineStyle: { color: c.red, type: 'dashed', width: 1 },
        label: { formatter: 'Sim ROP', fontSize: 9, color: c.red, position: 'insideEndTop' },
      });
    }

    // Stockout markPoint + markArea
    const soIdx = simStock.findIndex(s => s <= 0);
    const markPoints = [];
    const markAreaData = [];
    if (soIdx >= 0 && simDates[soIdx]) {
      markPoints.push({
        coord: [simDates[soIdx], 0], value: '⚠ STOCKOUT', symbol: 'pin', symbolSize: 50,
        itemStyle: { color: c.red }, label: { color: '#fff', fontSize: 9, fontFamily: c.monoFont },
      });
      // Shade stockout zone
      markAreaData.push([
        { xAxis: simDates[soIdx], itemStyle: { color: 'rgba(220,38,38,0.08)' } },
        { xAxis: simDates[simDates.length - 1] || simDates[soIdx] }
      ]);
    }

    const option = {
      grid: { left: 56, right: 24, top: 16, bottom: 48, containLabel: false },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'cross' },
      },
      legend: { data: ['Baseline', 'Simulated'], bottom: 0 },
      xAxis: {
        type: 'category', data: allDates, boundaryGap: false,
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3,
          formatter: v => { const d = new Date(v); return d.toLocaleDateString('en-IN', {month:'short', day:'numeric'}); }
        },
        axisLine: { lineStyle: { color: c.border } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, fontFamily: c.monoFont, color: c.text3, formatter: v => v >= 1000 ? (v/1000).toFixed(0)+'K' : v },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      },
      series: [
        // Baseline (dashed)
        {
          name: 'Baseline', type: 'line', symbol: 'none', smooth: true,
          data: baseStock,
          lineStyle: { color: c.text3, width: 2, type: 'dashed' },
          itemStyle: { color: c.text3 },
          z: 2,
        },
        // Simulated (solid accent)
        {
          name: 'Simulated', type: 'line', smooth: true, symbolSize: 4,
          data: simStock,
          lineStyle: { color: c.accent, width: 3 },
          itemStyle: { color: c.accent },
          areaStyle: { color: c.accent + '0A' },
          markLine: markLineData.length ? { silent: true, symbol: 'none', data: markLineData } : undefined,
          markPoint: markPoints.length ? { data: markPoints } : undefined,
          markArea: markAreaData.length ? { silent: true, data: markAreaData } : undefined,
          z: 5,
        },
      ],
      animationDuration: merge ? 600 : 800,
      animationEasing: 'cubicInOut',
    };

    if (merge && ChartTheme.getInstance(containerId)) {
      // Merge mode: morphing animation via setOption
      ChartTheme.setOption(containerId, option, true);
    } else {
      ChartTheme.init(containerId);
      ChartTheme.setOption(containerId, option);
    }
  }

  // ── Public API ──
  return {
    heroChart,
    decompChart,
    festivalChart,
    radarChart,
    featureImportanceChart,
    scatterChart,
    inventoryChart,
    leaderboardBar,
    abcTreemap,
    mapChart,
    simChart,
  };
})();
