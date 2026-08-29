/**
 * DemandSense AI — Interactive Tab Walkthrough Guide
 * Provides step-by-step interactive popups and guided walkthroughs for every tab.
 */
(function() {
  'use strict';

  const GUIDE_DATA = {
    tab1: {
      id: 'tab1',
      badge: 'Tab 1 of 5',
      title: '📈 Demand Intelligence & Decomposition',
      subtitle: 'Analyze high-precision 30-day forecast curves, seasonal cycles, and Indian festival uplift multipliers.',
      heroIcon: '📈',
      overview: 'This tab provides your core demand forecasting intelligence. It combines historical sales with machine learning forecasts, confidence intervals, and time-series decomposition.',
      steps: [
        {
          num: '1',
          title: 'Top Parameter Control Suite',
          icon: '🎛️',
          text: 'Use the top bar to select any of the <strong>20 FMCG SKUs</strong> (Staples, Beverages, Personal Care), filter by <strong>5 Indian Regions</strong>, set your supplier <strong>Lead Time</strong> (1–30 days), and adjust <strong>Current Warehouse Stock</strong>.',
          badge: 'Filter Controls'
        },
        {
          num: '2',
          title: 'Interactive 30-Day Demand Hero Chart',
          icon: '📊',
          text: 'The main chart plots 3 years of actuals alongside the <strong>30-day forward forecast</strong>. Use the <strong>dataZoom slider</strong> at the bottom to zoom into specific date ranges, and toggle <strong>80% and 95% Confidence Intervals</strong> in the legend to view uncertainty envelopes.',
          badge: 'Interactive Chart'
        },
        {
          num: '3',
          title: 'Tri-Plot Time-Series Decomposition',
          icon: '🔗',
          text: 'Three synchronized sub-charts decompose sales into <strong>Underlying Trend</strong>, <strong>Weekly Seasonality</strong> (e.g. weekend vs weekday purchasing), and <strong>Residual Noise</strong>. Hover over any point to scrub across all three charts simultaneously.',
          badge: 'Synced Crosshair'
        },
        {
          num: '4',
          title: 'Festival Uplift Multipliers',
          icon: '🪔',
          text: 'The engine models major Indian festivals (<strong>Diwali +45%</strong>, <strong>Holi +25%</strong>, <strong>Navratri +10%</strong>). Click any festival card to highlight that event period on the hero chart and inspect its ramp-up window.',
          badge: 'Market Multipliers'
        }
      ],
      proTip: '💡 <strong>Pro Tip:</strong> Watch for sudden spikes in the <em>Residual Noise</em> plot — they often indicate unmodeled local promotional bursts or regional competitor outages.'
    },

    tab2: {
      id: 'tab2',
      badge: 'Tab 2 of 5',
      title: '🏆 Auto-ML Model Selection & Model Comparison',
      subtitle: 'Evaluate 5 competing statistical and ML algorithms to understand why the winning model was selected.',
      heroIcon: '🏆',
      overview: 'DemandSense automatically runs a continuous model tournament across 5 distinct architectures to select the model with the lowest prediction error on your specific SKU.',
      steps: [
        {
          num: '1',
          title: 'The 5 Competing Models',
          icon: '🤖',
          text: 'The tournament trains <strong>Exponential Smoothing (Holt-Winters)</strong>, <strong>Facebook Prophet</strong>, <strong>SARIMAX</strong>, <strong>XGBoost Regressor</strong>, and a <strong>14-Day Moving Average</strong> baseline comparator.',
          badge: 'Algorithm Suite'
        },
        {
          num: '2',
          title: '5-Axis Radar Arena Comparison',
          icon: '🎯',
          text: 'The interactive radar chart normalizes models across 5 operational dimensions: <strong>Accuracy (1 - MAPE)</strong>, <strong>Precision (1 - RMSE)</strong>, <strong>Stability</strong>, <strong>Fitting Speed</strong>, and <strong>Variance Control</strong>.',
          badge: 'Radar Visualization'
        },
        {
          num: '3',
          title: 'Tournament Leaderboard Table',
          icon: '📋',
          text: 'Compare statistical metrics side-by-side: <strong>MAPE</strong> (Mean Absolute % Error — lower is better), <strong>RMSE</strong>, <strong>MAE</strong>, and <strong>WAPE</strong>. The gold badge marks the reigning tournament champion.',
          badge: 'Metric Ranking'
        },
        {
          num: '4',
          title: 'XGBoost Feature Importance',
          icon: '🧬',
          text: 'Discover what external factors drive demand. Top drivers include <strong>lag_1 (yesterday sales)</strong>, <strong>is_monsoon (rainfall seasonality)</strong>, <strong>rolling_mean_7 (7-day velocity)</strong>, and <strong>is_salary_window</strong> (1st–5th of month shopping surge).',
          badge: 'Model Explainability'
        }
      ],
      proTip: '💡 <strong>Pro Tip:</strong> A MAPE under 10% indicates excellent industrial forecasting accuracy. If MAPE exceeds 15%, consider increasing historical training data or accounting for stockout days.'
    },

    tab3: {
      id: 'tab3',
      badge: 'Tab 3 of 5',
      title: '📦 Inventory Control & Pareto ABC',
      subtitle: 'Calculate analytical Safety Stock, Reorder Points (ROP), and classify your entire portfolio by revenue.',
      heroIcon: '📦',
      overview: 'Transform forecast predictions into concrete warehouse decisions. Prevent costly stockouts while minimizing working capital tied up in excess buffer stock.',
      steps: [
        {
          num: '1',
          title: 'Analytical Safety Stock Formula',
          icon: '🛡️',
          text: 'Calculates dynamic buffer stock using standard statistical formula: <code>SS = Z × σ_D × √L</code> where <strong>Z</strong> is derived from your target service level (90% → 1.28, 95% → 1.65, 98% → 2.05).',
          badge: 'Formula Driven'
        },
        {
          num: '2',
          title: 'Reorder Point (ROP) Trigger',
          icon: '⚡',
          text: 'Calculated as <code>ROP = (Average Daily Demand × Lead Time) + Safety Stock</code>. Whenever warehouse stock drops below this exact threshold, issue a replenishment purchase order.',
          badge: 'Order Trigger'
        },
        {
          num: '3',
          title: 'Interactive ABC Pareto Treemap',
          icon: '🗺️',
          text: 'Hierarchical 2-level treemap partitioning your catalog into <strong>Class A</strong> (Top 80% revenue — 98% SLA), <strong>Class B</strong> (Next 15% revenue — 95% SLA), and <strong>Class C</strong> (Remaining 5% revenue — 90% SLA). Click any branch to drill down.',
          badge: 'Drill-Down Treemap'
        },
        {
          num: '4',
          title: 'Regional Demand Distribution',
          icon: '📍',
          text: 'Geographic breakdown of units sold and revenue across <strong>North, South, East, West, and Central</strong> zones to balance regional fulfillment hubs.',
          badge: 'Geo Analytics'
        }
      ],
      proTip: '💡 <strong>Pro Tip:</strong> Never allow Class A SKUs to drop below ROP — because Class A accounts for 80% of revenue, a single Class A stockout causes major revenue loss.'
    },

    tab4: {
      id: 'tab4',
      badge: 'Tab 4 of 5',
      title: '🧪 What-If Scenario Simulator',
      subtitle: 'Stress-test supply chain resilience against price changes, marketing spikes, competitor shocks, and supplier delays.',
      heroIcon: '🧪',
      overview: 'The What-If Simulator lets you run real-time stress testing on demand and warehouse stock without altering production data.',
      steps: [
        {
          num: '1',
          title: 'One-Click Scenario Presets',
          icon: '⚡',
          text: 'Quickly trigger realistic market events: <strong>Diwali Mega Surge</strong>, <strong>Monsoon Supply Disruption</strong> (+7 days lead time), <strong>Price Hike & Inflation</strong> (+15% price), or <strong>Aggressive Promo Weekend</strong>.',
          badge: 'Quick Scenarios'
        },
        {
          num: '2',
          title: 'Interactive Multi-Shock Sliders',
          icon: '🎚️',
          text: 'Fine-tune 5 independent levers: <strong>Price Change (-30% to +30%)</strong>, <strong>Marketing Boost</strong>, <strong>Promo Discount</strong>, <strong>Competitor Shocks</strong>, and <strong>Lead Time Overrides</strong>.',
          badge: 'Real-Time Elasticity'
        },
        {
          num: '3',
          title: 'Live Depletion Trajectory Morph',
          icon: '📉',
          text: 'The trajectory chart compares baseline stock depletion (blue line) against the simulated shock scenario (orange line) with live morphing animations.',
          badge: 'Trajectory Chart'
        },
        {
          num: '4',
          title: 'Simulated Risk & Reorder Delta',
          icon: '⚠️',
          text: 'Review updated Safety Stock, Reorder Point, and Revenue at Risk under the simulated conditions to decide if temporary buffer expansion is needed.',
          badge: 'Financial Impact'
        }
      ],
      proTip: '💡 <strong>Pro Tip:</strong> If the simulated trajectory line dips below the Safety Stock dashed line before Day 30, your current stock is insufficient to survive the shock scenario.'
    },

    tab5: {
      id: 'tab5',
      badge: 'Tab 5 of 5',
      title: '🚨 AI Prescriptive Insights & Executive Briefing',
      subtitle: 'Automated purchase orders, diagnostic alert banners, and 1-click executive decision downloads.',
      heroIcon: '🚨',
      overview: 'The executive command center synthesizes all forecasting, inventory, and simulation data into clear action items and ready-to-execute purchase orders.',
      steps: [
        {
          num: '1',
          title: 'System Health Diagnostic Banner',
          icon: '🔔',
          text: 'Displays real-time status: <strong>Critical Alert (🔴 Stockout Risk Detected)</strong>, <strong>Warning (🟡 Reorder Approaching)</strong>, or <strong>Healthy (🟢 Buffer Stock Compliant)</strong>.',
          badge: 'Diagnostic Alert'
        },
        {
          num: '2',
          title: '4 AI Recommendation Cards',
          icon: '🤖',
          text: 'Structured AI advice across four operational domains: <strong>Procurement Action</strong>, <strong>Warehouse Logistics</strong>, <strong>Risk Mitigation</strong>, and <strong>Sales Opportunities</strong>.',
          badge: 'Executive Directives'
        },
        {
          num: '3',
          title: 'Automated Purchase Order (PO) Draft',
          icon: '📋',
          text: 'Auto-generates a ready-to-send purchase order with calculated PO Trigger Date, Recommended Units, Total Value in ₹ INR, and Target Supplier Delivery Date.',
          badge: 'Ready to Execute'
        },
        {
          num: '4',
          title: 'Executive PDF & CSV Downloads',
          icon: '📥',
          text: 'Export a single-page <strong>Executive PDF Brief</strong> for management meetings, or download the <strong>PO CSV Spreadsheet</strong> to import directly into your ERP/SAP system.',
          badge: '1-Click Export'
        }
      ],
      proTip: '💡 <strong>Pro Tip:</strong> Review the AI Prescriptive Insights first thing every morning to identify any SKU crossing the reorder threshold before morning supplier dispatch windows close.'
    }
  };

  let activeGuideTab = 'tab1';

  function el(id) { return document.getElementById(id); }
  function $$(sel) { return document.querySelectorAll(sel); }

  const WalkthroughGuide = {
    /**
     * Open the walkthrough guide popup.
     * @param {string} [tabId] - Optional specific tab ID (defaults to active dashboard tab)
     */
    open: function(tabId) {
      if (!tabId) {
        // Look up active tab from DOM or fallback
        const activeNavTab = document.querySelector('.nav-tab.active');
        tabId = activeNavTab ? activeNavTab.getAttribute('data-tab') : 'tab1';
      }
      activeGuideTab = tabId;

      this.render();

      const overlay = el('guideModalOverlay');
      if (overlay) {
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
      }
    },

    /**
     * Close the walkthrough guide popup.
     */
    close: function() {
      const overlay = el('guideModalOverlay');
      if (overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = '';
      }
    },

    /**
     * Switch to a specific tab guide.
     * @param {string} tabId
     */
    switchTab: function(tabId) {
      if (GUIDE_DATA[tabId]) {
        activeGuideTab = tabId;
        this.render();
      }
    },

    /**
     * Navigate to the next tab guide.
     */
    next: function() {
      const tabKeys = Object.keys(GUIDE_DATA);
      const currIdx = tabKeys.indexOf(activeGuideTab);
      const nextIdx = (currIdx + 1) % tabKeys.length;
      this.switchTab(tabKeys[nextIdx]);
    },

    /**
     * Navigate to the previous tab guide.
     */
    prev: function() {
      const tabKeys = Object.keys(GUIDE_DATA);
      const currIdx = tabKeys.indexOf(activeGuideTab);
      const prevIdx = (currIdx - 1 + tabKeys.length) % tabKeys.length;
      this.switchTab(tabKeys[prevIdx]);
    },

    /**
     * Render the guide modal contents.
     */
    render: function() {
      const data = GUIDE_DATA[activeGuideTab];
      if (!data) return;

      // Update header
      const badgeEl = el('guideTabBadge');
      if (badgeEl) badgeEl.textContent = data.badge;

      const titleEl = el('guideTitle');
      if (titleEl) titleEl.textContent = data.title;

      const subEl = el('guideSub');
      if (subEl) subEl.textContent = data.subtitle;

      // Update tab switcher buttons
      $$('.guide-tab-btn').forEach(btn => {
        const t = btn.getAttribute('data-tab');
        btn.classList.toggle('active', t === activeGuideTab);
      });

      // Build body HTML
      const bodyEl = el('guideBody');
      if (bodyEl) {
        let html = `
          <div class="guide-overview-box">
            <div class="guide-overview-icon">${data.heroIcon}</div>
            <div class="guide-overview-text">${data.overview}</div>
          </div>

          <div class="guide-steps-grid">
        `;

        data.steps.forEach(step => {
          html += `
            <div class="guide-step-card">
              <div class="guide-step-header">
                <div class="guide-step-num">${step.num}</div>
                <div class="guide-step-icon">${step.icon}</div>
                <div class="guide-step-title">${step.title}</div>
                <span class="guide-step-badge">${step.badge}</span>
              </div>
              <div class="guide-step-text">${step.text}</div>
            </div>
          `;
        });

        html += `
          </div>

          <div class="guide-protip-box">
            ${data.proTip}
          </div>
        `;

        bodyEl.innerHTML = html;
      }

      // Update dots
      const dotsEl = el('guideDots');
      if (dotsEl) {
        const tabKeys = Object.keys(GUIDE_DATA);
        dotsEl.innerHTML = tabKeys.map(k => `
          <span class="guide-dot ${k === activeGuideTab ? 'active' : ''}" data-tab="${k}" title="${GUIDE_DATA[k].title}"></span>
        `).join('');

        dotsEl.querySelectorAll('.guide-dot').forEach(dot => {
          dot.addEventListener('click', (e) => {
            const t = e.target.getAttribute('data-tab');
            if (t) WalkthroughGuide.switchTab(t);
          });
        });
      }
    },

    /**
     * Initialize event listeners on DOM ready.
     */
    init: function() {
      // Toggle button in navbar
      const guideNavBtn = el('tabGuideBtn');
      if (guideNavBtn) {
        guideNavBtn.addEventListener('click', () => {
          WalkthroughGuide.open();
        });
      }

      // Close button
      const closeBtn = el('guideClose');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => {
          WalkthroughGuide.close();
        });
      }

      // Got it button
      const gotItBtn = el('guideGotItBtn');
      if (gotItBtn) {
        gotItBtn.addEventListener('click', () => {
          // If the guide tab is different from active tab, switch dashboard to it
          const navTabBtn = document.querySelector(`.nav-tab[data-tab="${activeGuideTab}"]`);
          if (navTabBtn && !navTabBtn.classList.contains('active')) {
            navTabBtn.click();
          }
          WalkthroughGuide.close();
        });
      }

      // Next / Prev buttons
      const nextBtn = el('guideNextBtn');
      if (nextBtn) nextBtn.addEventListener('click', () => WalkthroughGuide.next());

      const prevBtn = el('guidePrevBtn');
      if (prevBtn) prevBtn.addEventListener('click', () => WalkthroughGuide.prev());

      // Tab switcher clicks
      const tabSwitcher = el('guideTabSwitcher');
      if (tabSwitcher) {
        tabSwitcher.addEventListener('click', (e) => {
          const btn = e.target.closest('.guide-tab-btn');
          if (btn) {
            const tabId = btn.getAttribute('data-tab');
            WalkthroughGuide.switchTab(tabId);
          }
        });
      }

      // Backdrop overlay click to close
      const overlay = el('guideModalOverlay');
      if (overlay) {
        overlay.addEventListener('click', (e) => {
          if (e.target === overlay) {
            WalkthroughGuide.close();
          }
        });
      }

      // In-tab guide buttons
      document.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-walkthrough-btn');
        if (btn) {
          const t = btn.getAttribute('data-guide');
          WalkthroughGuide.open(t);
        }
      });

      // Escape key to close
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && overlay && overlay.classList.contains('active')) {
          WalkthroughGuide.close();
        }
      });
    }
  };

  window.WalkthroughGuide = WalkthroughGuide;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => WalkthroughGuide.init());
  } else {
    WalkthroughGuide.init();
  }
})();
