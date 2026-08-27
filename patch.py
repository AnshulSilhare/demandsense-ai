import sys
with open('static/css/styles.css', 'r', encoding='utf-8') as f: css = f.read()
css = css.replace('grid-template-columns: repeat(4, 1fr);', 'grid-template-columns: repeat(5, 1fr);')
with open('static/css/styles.css', 'w', encoding='utf-8') as f: f.write(css)
with open('main.py', 'r', encoding='utf-8') as f: py = f.read()
py = py.replace('            {\n                \
label\: \Projected
Revenue
30
\,', '            {\n                \label\: \Days
of
Supply\,\n                \value\: dos,\n                \value_fmt\: f\
dos:.1f
\,\n                \unit\: \days\,\n                \delta_pct\: round(compliance_delta, 1),\n                \favorable\: bool(dos >= 30),\n                \chip\: \DoS\, \chip_color\: \teal\,\n                \sparkline\: spark_values\n            },\n            {\n                \label\: \Projected
Revenue
30
\,')
py = py.replace('    # KPI 3: Safety Stock Compliance %\\n    dos = float(impact_data.get(\
days_of_supply\, 0.0))\\n    compliance = float(min(1.0, dos / 30.0) * 100.0)\\n    stock = float(impact_data.get(\current_stock_units\, 0.0))\\n    avg_prev = float(filtered_df.tail(60).head(30)[\units_sold\].mean())\\n    prev_dos = float(stock / max(1.0, avg_prev))\\n    prev_compliance = float(min(1.0, prev_dos / 30.0) * 100.0)\\n    compliance_delta = float(compliance - prev_compliance)', '    # KPI 3: True Safety Stock Compliance %\\n    dos = float(impact_data.get(\days_of_supply\, 0.0))\\n    stock = float(impact_data.get(\current_stock_units\, 0.0))\\n    req_ss = float(impact_data.get(\safety_stock_units\, 1.0))\\n    compliance = float(min(100.0, max(0.0, (stock / req_ss) * 100))) if req_ss > 0 else 100.0\\n    avg_prev = float(filtered_df.tail(60).head(30)[\units_sold\].mean())\\n    prev_dos = float(stock / max(1.0, avg_prev))\\n    compliance_delta = 0.0')
with open('main.py', 'w', encoding='utf-8') as f: f.write(py)
