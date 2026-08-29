/**
 * DemandSense AI — App Controller
 * =================================
 * State management, API fetch layer, DOM rendering, debouncing.
 * Re-fetches from relevant endpoints on filter change, re-renders only affected DOM sections.
 */

(() => {
  'use strict';

  // ═══ STATE ═══
  const state = {
    sku: 'SKU001',
    region: 'ALL',
    leadTime: 7,
    serviceLevel: 'A',
    stock: 25000,
    activeTab: 'tab1',
    festivalFilter: null,
    // Cached API responses
    config: null,
    forecastData: null,
    decompData: null,
    festivalData: null,
    abcData: null,
    regionalData: null,
    fiData: null,
    simData: null,
    historyRange: 0, // 0 = all
  };

  // ═══ DEBOUNCE UTILITY ═══
  function debounce(fn, ms = 400) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  // ═══ API LAYER WITH AUTOMATIC COLD-START & DEPLOYMENT RETRY ═══
  const API = {
    async get(path, retries = 4, initialDelay = 1200, signal = null) {
      let delay = initialDelay;
      for (let attempt = 0; attempt <= retries; attempt++) {
        try {
          const res = await fetch(path, { signal });
          if (res.ok) return await res.json();
          // If server is 500, 502, 503, 504 (cold start, deployment reload, or worker restart), auto-retry
          if ([500, 502, 503, 504].includes(res.status) && attempt < retries) {
            await new Promise(r => setTimeout(r, delay));
            delay *= 1.5;
            continue;
          }
          throw new Error(`API ${path}: ${res.status}`);
        } catch (err) {
          if (err.name === 'AbortError') throw err;
          if (attempt < retries) {
            await new Promise(r => setTimeout(r, delay));
            delay *= 1.5;
            continue;
          }
          throw err;
        }
      }
    },
    async post(path, body, retries = 3, initialDelay = 1500) {
      let delay = initialDelay;
      for (let attempt = 0; attempt <= retries; attempt++) {
        try {
          const res = await fetch(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
          if (res.ok) return await res.json();
          if ([500, 502, 503, 504].includes(res.status) && attempt < retries) {
            await new Promise(r => setTimeout(r, delay));
            delay *= 1.5;
            continue;
          }
          throw new Error(`API ${path}: ${res.status}`);
        } catch (err) {
          if (err.name === 'AbortError') throw err;
          if (attempt < retries) {
            await new Promise(r => setTimeout(r, delay));
            delay *= 1.5;
            continue;
          }
          throw err;
        }
      }
    },
  };

  function _qs() {
    const incLlm = state.activeTab === 'tab5' ? 'true' : 'false';
    return `sku=${state.sku}&region=${state.region}&lead_time=${state.leadTime}&service_level=${state.serviceLevel}&stock=${state.stock}&include_llm=${incLlm}&_t=${Date.now()}`;
  }

  // ═══ INIT ═══
  async function init() {
    setupTheme();
    setupNav();
    setupFilters();
    setupModal();
    setupScrollEffects();

    try {
      state.config = await API.get('/api/config');
      populateFilters(state.config);
      el('appVersion').textContent = `v${state.config.version}`;
    } catch (e) {
      toast('Failed to load config: ' + e.message, true);
    }

    loadForecast();
  }

  // ═══ DOM HELPERS ═══
  function el(id) { return document.getElementById(id); }
  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }

  function toast(msg, isError = false) {
    const t = el('toastMsg');
    t.textContent = msg;
    t.style.display = 'block';
    t.style.borderColor = isError ? 'var(--red)' : 'var(--green)';
    t.style.color = isError ? 'var(--red)' : 'var(--text)';
    setTimeout(() => { t.style.display = 'none'; }, 4000);
  }

  // ═══ THEME (Light Mode Default) ═══
  function setupTheme() {
    const saved = localStorage.getItem('ds-theme');
    if (saved === 'dark') {
      document.body.classList.add('dark');
    } else {
      document.body.classList.remove('dark');
    }
    updateThemeIcon();

    el('themeToggle')?.addEventListener('click', () => {
      document.body.classList.toggle('dark');
      const isDark = document.body.classList.contains('dark');
      localStorage.setItem('ds-theme', isDark ? 'dark' : 'light');
      updateThemeIcon();
      reRenderAllCharts();
      if (typeof window !== 'undefined') window.dispatchEvent(new Event('scroll'));
    });
  }

  function updateThemeIcon() {
    const btn = el('themeToggle');
    if (btn) btn.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
  }

  // ═══ NAV TABS & MOBILE/TABLET BOTTOM TAB BAR ═══
  let _lastTabIndex = 0;
  const _tabSequence = ['tab1', 'tab2', 'tab3', 'tab4', 'tab5'];

  function updateTopTabIndicator(target) {
    const indicator = el('navTabIndicator');
    const navTabs = el('navTabs');
    if (!indicator || !navTabs) return;
    const activeTab = navTabs.querySelector(`.nav-tab[data-tab="${target || state.activeTab}"]`);
    if (!activeTab) return;

    const navRect = navTabs.getBoundingClientRect();
    const tabRect = activeTab.getBoundingClientRect();
    if (tabRect.width === 0) return;

    const left = tabRect.left - navRect.left;
    const width = tabRect.width;

    indicator.style.transform = `translateX(${left}px)`;
    indicator.style.width = `${width}px`;
  }

  function updateBottomTabIndicator(target) {
    const indicator = el('btabIndicator');
    const tabBar = el('bottomTabBar');
    if (!indicator || !tabBar) return;
    const activeBtab = tabBar.querySelector(`.btab[data-tab="${target || state.activeTab}"]`);
    if (!activeBtab) return;

    const barRect = tabBar.getBoundingClientRect();
    const tabRect = activeBtab.getBoundingClientRect();
    if (tabRect.width === 0) return;

    const left = tabRect.left - barRect.left;
    const width = tabRect.width;

    indicator.style.transform = `translateX(${left}px)`;
    indicator.style.width = `${width}px`;
  }

  // ═══ CUSTOM CINEMATIC EASED SMOOTH SCROLL CONTROLLER (Graceful & Frictionless) ═══
  let activeScrollAnim = null;

  function gracefulScrollTo(targetY, duration = 380, onComplete = null) {
    if (activeScrollAnim) {
      cancelAnimationFrame(activeScrollAnim);
      activeScrollAnim = null;
    }

    const startY = window.scrollY;
    const diff = targetY - startY;
    if (Math.abs(diff) < 4) {
      window.scrollTo({ left: 0, top: targetY, behavior: 'instant' });
      if (window.renderKpiConveyorGlobal) window.renderKpiConveyorGlobal(targetY);
      if (window.updateStickyPillGlobal) window.updateStickyPillGlobal(targetY);
      if (onComplete) onComplete();
      return;
    }
    const startTime = performance.now();

    function step(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(1, elapsed / duration);
      // Luxurious C2 Quintic Smootherstep for liquid smooth acceleration & deceleration
      const ease = progress * progress * progress * (progress * (progress * 6 - 15) + 10);

      const currentPos = startY + diff * ease;
      window.scrollTo({ left: 0, top: currentPos, behavior: 'instant' });
      if (window.renderKpiConveyorGlobal) window.renderKpiConveyorGlobal(currentPos);
      if (window.updateStickyPillGlobal) window.updateStickyPillGlobal(currentPos);

      if (progress < 1) {
        activeScrollAnim = requestAnimationFrame(step);
      } else {
        activeScrollAnim = null;
        if (onComplete) onComplete();
      }
    }
    activeScrollAnim = requestAnimationFrame(step);
  }

  let activeForecastPromise = null;
let _forecastRetryCount = 0;

  function switchTab(target) {
    if (!target || target === state.activeTab) return;

    // Sync top nav tabs & slide indicator chip
    $$('.nav-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === target);
    });
    updateTopTabIndicator(target);

    // Sync mobile bottom tab bar & slide indicator chip
    $$('.bottom-tab-bar .btab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === target);
    });
    updateBottomTabIndicator(target);

    // Switch tab contents immediately
    $$('.tab-content').forEach(tc => tc.classList.remove('active'));
    const activePanel = el(target);
    activePanel?.classList.add('active');
    state.activeTab = target;

    function refreshTabCharts() {
      if (activeForecastPromise && !state.forecastData) {
        activeForecastPromise.then(() => {
          if (state.activeTab === target) refreshTabCharts();
        });
      }

      if (target === 'tab1') {
        if (state.forecastData) renderHeroChart();
        if (!state.decompData) loadDecomp(); else {
          const { dates, trend, seasonal, residual } = state.decompData;
          Charts.decompChart('decompTrend', 'decompSeasonal', 'decompResidual', dates, trend, seasonal, residual);
        }
        if (!state.festivalData) loadFestival(); else {
          Charts.festivalChart('festivalChart', state.festivalData.festivals, (festName) => {
            state.festivalFilter = state.festivalFilter === festName ? null : festName;
            renderHeroChart();
          });
        }
      }
      if (target === 'tab2') {
        if (state.forecastData) renderTab2();
        if (!state.fiData) loadFeatureImportance(); else {
          Charts.featureImportanceChart('fiChart', state.fiData.features);
        }
      }
      if (target === 'tab3') {
        renderInventory();
        if (!state.abcData) loadAbc(); else {
          Charts.abcTreemap('abcTreemap', state.abcData.table);
        }
        if (!state.regionalData) loadRegional(); else {
          Charts.mapChart('mapChart', state.regionalData.regions);
        }
      }
      if (target === 'tab4') {
        renderSimSliders();
        if (!state.simData && state.forecastData?.impact_data) {
          state.simData = {
            base_trajectory: state.forecastData.impact_data.inventory_trajectory,
            sim_impact: state.forecastData.impact_data,
            eff_lt: state.leadTime,
            eff_dem_scale: 1.0,
          };
          renderSimMetrics();
        }
        renderSimChart(false);
      }
      if (target === 'tab5') {
        renderTab5();
      }

      // Trigger resize on all active chart instances
      if (window.ChartTheme?._instances) {
        for (const inst of ChartTheme._instances.values()) {
          if (inst && !inst.isDisposed()) inst.resize();
        }
      }
    }

    // Render charts IMMEDIATELY upon tab click with zero perceptual delay
    refreshTabCharts();

    // Smoothly glide viewport to tab heading
    if (activePanel) {
      const headerOffset = window.innerWidth < 768 ? 64 : 80;
      const elementPosition = activePanel.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

      gracefulScrollTo(Math.max(0, offsetPosition), 380, () => {
        if (window.ChartTheme?._instances) {
          for (const inst of ChartTheme._instances.values()) {
            if (inst && !inst.isDisposed()) inst.resize();
          }
        }
      });
    }
  }

  function setupNav() {
    $$('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    $$('.bottom-tab-bar .btab').forEach(btab => {
      btab.addEventListener('click', () => switchTab(btab.dataset.tab));
    });

    // Initial positioning & resize sync for sliding indicators
    setTimeout(() => {
      updateTopTabIndicator(state.activeTab);
      updateBottomTabIndicator(state.activeTab);
    }, 150);
    window.addEventListener('resize', debounce(() => {
      updateTopTabIndicator(state.activeTab);
      updateBottomTabIndicator(state.activeTab);
    }, 150), { passive: true });
  }

  // ═══ PURE CONTINUOUS SCROLL CONVEYOR & QUANTUM SNAKE ENGINE ═══
  function setupScrollEffects() {
    const nav = el('topNav');
    const kpiBar = el('kpiBar');
    const kpiWrapper = el('kpiBarWrapper');
    let cachedMetrics = null;

    function measureMetrics() {
      if (!kpiWrapper || window.innerWidth < 1360) return;
      const cards = [el('kpi0'), el('kpi1'), el('kpi2'), el('kpi3')].filter(Boolean);
      if (cards.length < 4) return;

      const wrapperRect = kpiWrapper.getBoundingClientRect();
      const colWidth = (wrapperRect.width - 3 * 19.2) / 4;

      cachedMetrics = {
        wrapperLeft: wrapperRect.left,
        wrapperTop: wrapperRect.top + window.scrollY, // document-relative top
        colWidth: colWidth,
        scrollStart: 10,
        scrollEnd: 460 // Generous 450px travel range gives each phase full visibility and silky flow
      };
    }

    // C2 Quintic Smootherstep (Ken Perlin curve: zero velocity & zero acceleration at endpoints)
    function smootherstep(x) {
      const c = Math.max(0, Math.min(1, x));
      return c * c * c * (c * (c * 6 - 15) + 10);
    }

    // ═══ DOCK SIDE TOGGLE (Left vs Right) ═══
    let dockSide = localStorage.getItem('ds-kpi-dock-side') || 'left';

    function updateDockSideUI() {
      const sideIcon = el('railSideIcon');
      const sideText = el('railSideText');

      if (dockSide === 'right') {
        document.body.classList.add('kpi-dock-right');
        document.body.classList.remove('kpi-dock-left');
        if (sideIcon) sideIcon.textContent = '◨';
        if (sideText) sideText.textContent = 'Right';
      } else {
        document.body.classList.add('kpi-dock-left');
        document.body.classList.remove('kpi-dock-right');
        if (sideIcon) sideIcon.textContent = '◧';
        if (sideText) sideText.textContent = 'Left';
      }
    }

    el('railSideToggle')?.addEventListener('click', () => {
      dockSide = dockSide === 'left' ? 'right' : 'left';
      localStorage.setItem('ds-kpi-dock-side', dockSide);
      updateDockSideUI();
      cachedMetrics = null;
      handleScroll();
    });

    updateDockSideUI();

    const canvas = el('kpiSnakeCanvas');
    const ctx = canvas?.getContext('2d');
    const cards = [el('kpi0'), el('kpi1'), el('kpi2'), el('kpi3')];
    const tabContents = $$('.tab-content');

    function initCanvas() {
      if (!canvas) return;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const w = window.innerWidth;
      const h = window.innerHeight;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
      }
    }

    let isCompactClean = false;
    let isNavScrolled = false;

    function renderKpiConveyor(currentY) {
      // 1. Navbar shrink
      const shouldScrollNav = currentY > 30;
      if (shouldScrollNav !== isNavScrolled) {
        nav?.classList.toggle('scrolled', shouldScrollNav);
        isNavScrolled = shouldScrollNav;
      }

      // Check widescreen desktop viewport (Docking only on wide displays >= 1360px)
      if (!kpiBar || !kpiWrapper || window.innerWidth < 1360) {
        if (!isCompactClean) {
          if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
          cards.forEach((c, i) => {
            if (!c) return;
            c.style.transform = '';
            c.style.opacity = '';
            c.classList.remove('is-beam-morph', 'is-docked-rail');
            const snake = el(`snake${i}`);
            if (snake) snake.style.opacity = '0';
          });
          tabContents.forEach(tc => {
            tc.style.transform = '';
          });
          isCompactClean = true;
        }
        return; // Zero overhead on tablet/mobile scroll!
      }
      isCompactClean = false;

      const dpr = Math.min(2, window.devicePixelRatio || 1);

      if (canvas && ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }

      if (cards.length < 4 || !cards[0]) return;

      if (!cachedMetrics) measureMetrics();
      if (!cachedMetrics) return;

      const { scrollStart, scrollEnd, wrapperLeft, wrapperTop, colWidth } = cachedMetrics;

      if (currentY <= scrollStart || window.innerWidth < 1360) {
        cards.forEach(c => {
          if (!c) return;
          c.style.transform = '';
          c.style.opacity = '';
          c.style.transformOrigin = 'center top';
          c.classList.remove('is-beam-morph', 'is-docked-rail');
        });
        tabContents.forEach(tc => {
          tc.style.transform = '';
        });
        return;
      }

      // Calculate continuous scroll alpha (0.0 at scrollStart to 1.0 at scrollEnd)
      const alpha = Math.min(1.0, (currentY - scrollStart) / (scrollEnd - scrollStart));
      const isRight = (dockSide === 'right');

      // ─── DYNAMIC TAB SLIDE (GPU-Accelerated 60/120fps smooth glide to make room for vertical KPI rail) ───
      const tSlide = Math.max(0, Math.min(1, (alpha - 0.05) / 0.45));
      const pSlide = smootherstep(tSlide);
      const railMargin = 16;
      const dockedCardW = 205;
      const dockedEdge = railMargin + dockedCardW + 18; // 16 + 205 + 18 = 239px (Tight, tailored 18px gap)
      const clearanceNeeded = Math.max(0, dockedEdge - wrapperLeft);
      const maxOffset = clearanceNeeded; // Exact precision offset with zero excessive void
      const slideX = isRight ? (-maxOffset * pSlide) : (maxOffset * pSlide);

      tabContents.forEach(tc => {
        if (pSlide > 0.001) {
          tc.style.transform = `translate3d(${slideX.toFixed(2)}px, 0, 0)`;
        } else {
          tc.style.transform = '';
        }
      });

      const maxCardH = Math.max(...cards.map(c => c ? c.offsetHeight : 112));
      const cardH = maxCardH; // Dynamic based on actual content
      const cardW = colWidth;
      const gap = 19.2;
      const startY = 88; // Top rail baseline below nav
      const slotSpacing = cardH + 14; // Tight, crisp 14px visual gap between cards

      // Bounding span of all 4 cards in the resting horizontal row
      const spanLeft = wrapperLeft;
      const spanRight = wrapperLeft + 3 * (cardW + gap) + cardW;
      const initLen = spanRight - spanLeft;

      // Final span of all 4 cards along the vertical edge rail
      const railX = isRight ? (window.innerWidth - railMargin) : railMargin;
      const finalRailSpan = 3 * slotSpacing + cardH;

      const topY = (wrapperTop - currentY) + 3; // Center Y of 6px top border
      const R = 28; // Smooth corner bend radius

      // Total track distance for the single unified snake line
      const startX = isRight ? spanRight : spanLeft;
      const cornerX = isRight ? (railX - R) : (railX + R);
      const L1 = Math.max(1, Math.abs(startX - cornerX));
      const L2 = (Math.PI / 2) * R; // 90° corner fillet arc
      const bottomSlotY = startY + 3 * slotSpacing + cardH;
      const L3 = Math.max(1, bottomSlotY - (topY + R));
      const totalPathDist = L1 + L2 + L3;

      function getTrackPoint(d) {
        if (d <= L1) {
          // 1. Horizontal track along top grid
          const x = isRight ? (startX + d) : (startX - d);
          return { x, y: topY };
        } else if (d <= L1 + L2) {
          // 2. Smooth 90° Corner Fillet (Flexes naturally like a rope/snake!)
          const arcDist = d - L1;
          const angle = (arcDist / L2) * (Math.PI / 2);
          const cx = isRight ? (railX - R) : (railX + R);
          const cy = topY + R;
          const x = isRight ? (cx + R * Math.sin(angle)) : (cx - R * Math.sin(angle));
          const y = cy - R * Math.cos(angle);
          return { x, y };
        } else {
          // 3. Vertical rail track down the edge
          const vertDist = d - (L1 + L2);
          return { x: railX, y: (topY + R) + vertDist };
        }
      }

      // Draw Bold 6px Unified Single Snake Ribbon on Canvas (120 FPS GPU Streamlined)
      function drawUnifiedSnakeRibbon(sHead, sTail, alphaGlow) {
        if (!ctx || sHead <= sTail) return;
        const numPts = 24; // Streamlined 24-point spline for ultra-fast GPU throughput
        const pts = [];
        for (let k = 0; k <= numPts; k++) {
          const dist = sTail + (sHead - sTail) * (k / numPts);
          pts.push(getTrackPoint(dist));
        }

        ctx.save();
        ctx.scale(dpr, dpr);
        ctx.globalAlpha = Math.max(0, Math.min(1, alphaGlow));

        const isDark = document.body.classList.contains('dark');
        const tealColor = isDark ? '#2dd4bf' : '#0d9488';

        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let k = 1; k < pts.length; k++) ctx.lineTo(pts[k].x, pts[k].y);
        ctx.strokeStyle = tealColor;
        ctx.lineWidth = 6.0;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();

        ctx.restore();
      }

      // ═══ 5-PHASE TWO-AXIS SEQUENTIAL WATER-DROPLET RELEASE & SHORTENING SNAKE ENGINE ═══
      if (alpha <= 0.28) {
        // PHASE 1 (Horizontal Axis): Sequential Droplet Fold
        const foldProgress = [0, 0, 0, 0];

        cards.forEach((card, i) => {
          const foldOrder = isRight ? (cards.length - 1 - i) : i;
          const foldStart = foldOrder * 0.055;
          const foldEnd = foldStart + 0.09;
          const tFold = Math.max(0, Math.min(1, (alpha - foldStart) / (foldEnd - foldStart)));
          const pFold = smootherstep(tFold);
          foldProgress[i] = pFold;

          const scaleY = 1.0 - (1.0 - 0.05) * pFold;
          card.style.transformOrigin = 'center top';
          card.style.transform = `translate3d(0, 0, 0) scaleY(${scaleY})`;
          card.style.opacity = '1';
          card.classList.remove('is-docked-rail');

          if (pFold > 0.35) {
            card.classList.add('is-beam-morph');
          } else {
            card.classList.remove('is-beam-morph');
          }
        });

        // Dynamic Horizontal Line Growth / Shortening as cards fold/unfold one by one
        const totalFolded = foldProgress[0] + foldProgress[1] + foldProgress[2] + foldProgress[3];
        if (totalFolded > 0.15) {
          const uGlide = smootherstep(Math.max(0, (alpha - 0.15) / 0.13));
          const sHead = (L1 * 0.4) * uGlide;
          const curLen = Math.min(initLen, (colWidth + gap) * totalFolded);
          const sTail = sHead - curLen;
          drawUnifiedSnakeRibbon(sHead, sTail, Math.min(1.0, totalFolded / 1.5));
        }

      } else {
        // PHASES 2-5 (Vertical Rail Axis): Snake Plunges to Bottom Slot, Drops Card 0 First, Then Stacks Upward!
        const uPlunge = smootherstep(Math.min(1.0, (alpha - 0.28) / 0.22));
        const sPlungeHead = totalPathDist * uPlunge;

        const dropProgress = [0, 0, 0, 0];

        cards.forEach((card, i) => {
          const orderIndex = isRight ? (cards.length - 1 - i) : i;
          const slotIndex = isRight ? i : (cards.length - 1 - i);

          const dropStart = 0.44 + orderIndex * 0.125;
          const dropEnd = dropStart + 0.125;
          const tDrop = Math.max(0, Math.min(1, (alpha - dropStart) / (dropEnd - dropStart)));
          const pDrop = smootherstep(tDrop);
          dropProgress[orderIndex] = pDrop;

          const naturalX = i * (colWidth + gap);
          const dockedScreenX = isRight ? (window.innerWidth - dockedCardW - railMargin) : railMargin;
          const dockedScreenY = startY + slotIndex * slotSpacing;

          const totalDeltaX = dockedScreenX - (wrapperLeft + naturalX);
          const totalDeltaY = dockedScreenY - (wrapperTop - currentY);

          if (alpha < dropStart) {
            card.style.opacity = '0';
            card.classList.remove('is-beam-morph', 'is-docked-rail');
          } else {
            const scaleX = 0.04 + (1.0 - 0.04) * pDrop;
            card.classList.add('is-docked-rail');
            card.style.transformOrigin = isRight ? 'right center' : 'left center';
            card.style.transform = `translate3d(${totalDeltaX}px, ${totalDeltaY}px, 0) scaleX(${scaleX})`;
            card.style.opacity = pDrop.toFixed(3);
            card.classList.remove('is-beam-morph');
          }
        });

        // Dynamic Snake Line Shortening on the vertical rail:
        const totalReleased = dropProgress[0] + dropProgress[1] + dropProgress[2] + dropProgress[3];
        const unreleasedCount = Math.max(0, 4.0 - totalReleased);

        let sHead = 0;
        let curLen = 0;

        if (alpha < 0.44) {
          sHead = sPlungeHead;
          const uTurn = smootherstep((alpha - 0.28) / 0.16);
          curLen = initLen - (initLen - (4 * (cardH + slotSpacing * 0.25))) * uTurn;
        } else {
          sHead = totalPathDist - (totalReleased * slotSpacing * 0.95);
          curLen = (cardH + slotSpacing * 0.25) * unreleasedCount;
        }

        const sTail = sHead - curLen;

        if (curLen > 3 && alpha < 0.98) {
          drawUnifiedSnakeRibbon(sHead, sTail, Math.min(1.0, unreleasedCount));
        }
      }

      if (alpha >= 1.0) {
        cards.forEach((card, i) => {
          const slotIndex = isRight ? i : (cards.length - 1 - i);
          const naturalX = i * (colWidth + gap);
          const dockedScreenX = isRight ? (window.innerWidth - dockedCardW - railMargin) : railMargin;
          const dockedScreenY = startY + slotIndex * slotSpacing;

          const totalDeltaX = dockedScreenX - (wrapperLeft + naturalX);
          const totalDeltaY = dockedScreenY - (wrapperTop - currentY);

          card.classList.add('is-docked-rail');
          card.style.transformOrigin = isRight ? 'right center' : 'left center';
          card.style.transform = `translate3d(${totalDeltaX}px, ${totalDeltaY}px, 0) scale(1, 1)`;
          card.style.opacity = '1';
          card.classList.remove('is-beam-morph');
        });
      }
    }

    const capsule = el('controlCapsule');
    
    let isScrolledPast = false;

    // Dynamically calculate and set height so CSS transition is perfectly smooth
    // between collapsed (48px) and expanded (actual content height)
    function applyCapsuleState(expanded) {
      if (!capsule) return;
      window.isUserExpanded = expanded;
      const bodyCard = document.getElementById('capsuleBodyCard');
      
      if (expanded) {
        capsule.classList.remove('is-collapsed');
        capsule.classList.add('is-expanded');
        // Explicitly set exact pixel height of the inner content so it wraps perfectly without dead space
        if (bodyCard) {
            capsule.style.height = (bodyCard.scrollHeight + 8) + 'px';
        }
        setTimeout(() => document.getElementById('skuSelect')?.focus(), 140);
      } else {
        capsule.classList.remove('is-expanded');
        capsule.classList.add('is-collapsed');
        const isMob = window.innerWidth <= 767;
        capsule.style.height = isMob ? '72px' : '48px';
      }
    }

        let lastScrollYForMorph = 0;
    let autoCollapsedOnScroll = false;

    function updateCapsuleScroll(y) {
        if (!capsule) return;
        
        const anchor = el('capsuleAnchor');
        const threshold = 45;
        const past = y > threshold;
        const scrollingDown = y > lastScrollYForMorph;
        lastScrollYForMorph = y;
        
        if (past !== isScrolledPast) {
          isScrolledPast = past;
          capsule.classList.toggle('is-floating', isScrolledPast);
          if (anchor) anchor.classList.toggle('is-active', isScrolledPast);
        }
        
        // 1. Auto-collapse when scrolling down past threshold
        if (scrollingDown && y > threshold && window.isUserExpanded) {
          autoCollapsedOnScroll = true;
          applyCapsuleState(false);
        }
        
        // 2. Auto-expand when scrolling back to absolute top
        if (!scrollingDown && y <= 10 && !window.isUserExpanded && autoCollapsedOnScroll) {
          autoCollapsedOnScroll = false;
          applyCapsuleState(true);
        }
    }

    window.renderKpiConveyorGlobal = renderKpiConveyor;
    window.updateStickyPillGlobal = updateCapsuleScroll;
      window.applyCapsuleStateGlobal = applyCapsuleState;

    let isRafScheduled = false;

    function onScrollFrame() {
      if (!activeScrollAnim) {
        const y = window.scrollY;
        renderKpiConveyor(y);
        updateCapsuleScroll(y);
      }
      isRafScheduled = false;
    }

    function handleScroll() {
      if (!isRafScheduled && !activeScrollAnim) {
        isRafScheduled = true;
        requestAnimationFrame(onScrollFrame);
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', () => {
      initCanvas();
      cachedMetrics = null;
      isCompactClean = false;
      handleScroll();
      if (window.isUserExpanded) applyCapsuleState(true);
    }, { passive: true });

    initCanvas();
    measureMetrics();
    applyCapsuleState(window.scrollY <= 10);
    renderKpiConveyor(window.scrollY);
  }

  // ═══ FILTERS & DYNAMIC ISLAND MORPHING CONTROLLER ═══
  function updateCollapsedSummary() {
    const skuObj = state.config?.products?.find(p => p.sku_id === state.sku);
    const skuFullLabel = skuObj ? `${skuObj.sku_id} — ${skuObj.name}` : state.sku;
    const regionObj = state.config?.regions?.find(r => r.id === state.region);
    const regionShort = state.region === 'ALL' ? 'National' : (regionObj ? regionObj.name.split(' ')[0] : state.region);

    // Preset mapping
    const presetNames = { 3: '3 Days (Air)', 7: '7 Days (Std)', 14: '14 Days (Rail)', 21: '21 Days (Sea)' };
    const ltLabel = presetNames[state.leadTime] || `${state.leadTime} Days`;

    const slPcts = { 'C': '90%', 'B': '95%', 'A': '98%' };
    const slShort = `${slPcts[state.serviceLevel] || '98%'} SLA`;
    const stockLabel = `${(state.stock || 0).toLocaleString()} Units`;

    // Smart Floating Dynamic Island Pill (on scroll)
    if (el('pillSku')) el('pillSku').textContent = skuFullLabel;
    if (el('pillRegion')) el('pillRegion').textContent = regionShort;
    if (el('pillLeadTime')) el('pillLeadTime').textContent = ltLabel;
    if (el('pillSla')) el('pillSla').textContent = slShort;
    if (el('pillStock')) el('pillStock').textContent = stockLabel;
  }

  window.isUserExpanded = true;
  function setupCollapsibleFilterPanel() {
      const capsule = el('controlCapsule');
      const collapseBtn = el('capsuleCollapseBtn');
      const editBtn = el('pillEditBtn');
  
      // Toggle Dynamic Island in-place
      capsule?.addEventListener('click', (e) => {
        // If user clicks anywhere on the collapsed pill, expand it
        if (capsule.classList.contains('is-collapsed')) {
          window.applyCapsuleStateGlobal(true);
        }
      });
  
      editBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        window.applyCapsuleStateGlobal(true);
      });
  
      collapseBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        window.applyCapsuleStateGlobal(false);
      });
      
      // Click outside to collapse IF floating overlay
      document.addEventListener('click', (e) => {
        if (window.isUserExpanded && capsule && capsule.classList.contains('is-floating') && !capsule.contains(e.target)) {
          window.applyCapsuleStateGlobal(false);
        }
      });
  
      // Escape key collapses island back to pill
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && capsule?.classList.contains('is-expanded')) {
          window.applyCapsuleStateGlobal(false);
        }
      });
    }

    function populateFilters(config) {
    if (!config) return;

    // SKU
    const skuSel = el('skuSelect');
    if (skuSel && config.products) {
      skuSel.innerHTML = '';
      config.products.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.sku_id;
        opt.textContent = `${p.sku_id} — ${p.name}`;
        skuSel.appendChild(opt);
      });
      skuSel.value = state.sku;
    }

    // Region
    const regSel = el('regionSelect');
    if (regSel && config.regions) {
      regSel.innerHTML = '';
      const allOpt = document.createElement('option');
      allOpt.value = 'ALL';
      allOpt.textContent = 'ALL — National Aggregation';
      regSel.appendChild(allOpt);
      config.regions.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = `${r.id} — ${r.name}`;
        regSel.appendChild(opt);
      });
      regSel.value = state.region;
    }

    // Lead time
    if (config.default_lead_time !== undefined) {
      if (el('leadTimeSlider')) el('leadTimeSlider').value = config.default_lead_time;
      state.leadTime = config.default_lead_time;
      if (el('leadTimeValue')) el('leadTimeValue').textContent = `${state.leadTime} Days`;
    }

    // Initialize summary
    updateCollapsedSummary();
  }

  const debouncedParamLoad = debounce(() => {
    // Parameter changes (lead_time, service_level, stock) re-use same ML forecast
    // but recompute KPI/impact server-side — so force a fresh fetch
    loadForecast(false);
  }, 80);

  const debouncedSkuLoad = debounce(() => {
    // SKU/region changes need fresh tab-specific data too
    state.decompData = null;
    state.festivalData = null;
    state.regionalData = null;
    state.fiData = null;
    state.simData = null;
    loadForecast(false);
  }, 80);

  function setupFilters() {
    // 1. SKU Selector
    el('skuSelect')?.addEventListener('change', e => {
      state.sku = e.target.value;
      updateCollapsedSummary();
      debouncedSkuLoad();
    });

    // 2. Region Selector
    el('regionSelect')?.addEventListener('change', e => {
      state.region = e.target.value;
      updateCollapsedSummary();
      debouncedSkuLoad();
    });

    // 3. Lead Time Slider & Preset Buttons (Two-Way Sync + Tick Highlights)
    const slider = el('leadTimeSlider');
    const valPill = el('leadTimeValue');
    const presetBtns = $$('#leadTimePresets .segmented-btn');

    function updateLeadTimeUI(days) {
      state.leadTime = days;
      if (slider) slider.value = days;
      if (valPill) valPill.textContent = `${days} Days`;
      presetBtns.forEach(btn => {
        const isMatch = parseInt(btn.dataset.val) === days;
        btn.classList.toggle('is-selected', isMatch);
        btn.classList.toggle('active', isMatch);
      });
      updateCollapsedSummary();
    }

    slider?.addEventListener('input', e => {
      updateLeadTimeUI(parseInt(e.target.value));
      debouncedParamLoad();
    });
    slider?.addEventListener('change', debouncedParamLoad);

    presetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const days = parseInt(btn.dataset.val);
        updateLeadTimeUI(days);
        debouncedParamLoad();
      });
    });

    // 4. Service Level Unified Segmented Control
    const segBtns = $$('#serviceLevelSegmented .segmented-btn');
    const levelSelect = el('serviceLevelSelect');

    function updateServiceLevelUI(lvl) {
      state.serviceLevel = lvl;
      if (levelSelect) levelSelect.value = lvl;
      segBtns.forEach(btn => {
        const isMatch = btn.dataset.val === lvl;
        btn.classList.toggle('is-selected', isMatch);
        btn.classList.toggle('active', isMatch);
      });
      updateCollapsedSummary();
    }

    segBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        updateServiceLevelUI(btn.dataset.val);
        debouncedParamLoad();
      });
    });

    levelSelect?.addEventListener('change', e => {
      updateServiceLevelUI(e.target.value);
      debouncedParamLoad();
    });

    // 5. Stock Input Stepper (- / + buttons)
    const stockInput = el('stockInput');
    const stockDec = el('stockDecBtn');
    const stockInc = el('stockIncBtn');

    function updateStock(val) {
      const clamped = Math.max(0, val);
      state.stock = clamped;
      if (stockInput) stockInput.value = clamped;
      updateCollapsedSummary();
      debouncedParamLoad();
    }

    stockInput?.addEventListener('change', e => {
      updateStock(parseInt(e.target.value) || 0);
    });

    stockDec?.addEventListener('click', () => {
      const current = parseInt(stockInput?.value) || 0;
      updateStock(current - 1000);
    });

    stockInc?.addEventListener('click', () => {
      const current = parseInt(stockInput?.value) || 0;
      updateStock(current + 1000);
    });

    // 6. Reset Defaults Button
    el('resetParamsBtn')?.addEventListener('click', () => {
      if (state.config) {
        state.sku = state.config.products?.[0]?.sku_id || 'SKU001';
        state.region = 'ALL';
        state.leadTime = state.config.default_lead_time || 7;
        state.serviceLevel = 'A';
        state.stock = 25000;

        if (el('skuSelect')) el('skuSelect').value = state.sku;
        if (el('regionSelect')) el('regionSelect').value = state.region;
        updateLeadTimeUI(state.leadTime);
        updateServiceLevelUI(state.serviceLevel);
        if (stockInput) stockInput.value = state.stock;

        updateCollapsedSummary();
        toast('Parameters reset to default', false);
        debouncedParamLoad();
      }
    });

    // 7. CSV Upload with File Name Feedback
    el('csvUpload')?.addEventListener('change', async e => {
      const file = e.target.files[0];
      if (!file) return;
      if (el('uploadText')) el('uploadText').textContent = file.name;
      const form = new FormData();
      form.append('file', file);
      try {
        const res = await fetch('/api/upload-csv', { method: 'POST', body: form });
        if (!res.ok) {
          const err = await res.json();
          toast(err.detail || 'Upload failed', true);
          return;
        }
        const data = await res.json();
        toast(`Uploaded: ${data.rows} rows, ${data.skus} SKUs (${data.date_range})`);
        if (el('datasetNameText')) {
          el('datasetNameText').textContent = `${file.name} · ${data.skus} SKUs`;
        }
        if (el('sumDataset')) {
          el('sumDataset').textContent = `${file.name} (${data.skus} SKUs)`;
        }
        clearCachedData();
        loadForecast();
      } catch (err) {
        toast('Upload error: ' + err.message, true);
      }
    });

    // 8. Collapsible Panel
    setupCollapsibleFilterPanel();

    // Range toggle (Tab 1)
    $$('.range-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        $$('.range-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.historyRange = parseInt(btn.dataset.range);
        if (state.forecastData) renderHeroChart();
      });
    });
  }

  function clearCachedData() {
    state.forecastData = null;
    state.decompData = null;
    state.festivalData = null;
    state.abcData = null;
    state.regionalData = null;
    state.fiData = null;
    state.simData = null;
  }

  // ═══ LOADING STATES ═══
  function showLoading(containerId) {
    const c = el(containerId);
    if (c) {
      c.innerHTML = `
        <div class="chart-shimmer">
          <div class="shimmer-line w-60"></div>
          <div class="shimmer-block"></div>
          <div class="shimmer-line w-40"></div>
        </div>
      `;
    }
  }

  function showKpiLoading() {
    for (let i = 0; i < 4; i++) {
      const card = el(`kpi${i}`);
      if (card) {
        card.innerHTML = `
          <div class="kpi-skeleton">
            <div class="kpi-sk-top">
              <div class="kpi-sk-chip"></div>
              <div class="kpi-sk-badge"></div>
            </div>
            <div class="kpi-sk-label"></div>
            <div class="kpi-sk-val"></div>
            <div class="kpi-sk-spark"></div>
          </div>
        `;
      }
    }
  }


  // ═══ MAIN FORECAST LOAD ═══
  async function loadForecast(isInitial = false) {
    if (isInitial || !state.forecastData) {
      showKpiLoading();
      showLoading('heroChart');
      if (el('lastUpdated')) el('lastUpdated').textContent = 'Connecting to AI Inference Engine...';
    }

    const promise = API.get(`/api/forecast?${_qs()}`);
    activeForecastPromise = promise;

    try {
      const data = await promise;
      // Guard against stale race condition if a newer request was dispatched
      if (activeForecastPromise !== promise && activeForecastPromise !== null) return;

      state.forecastData = data;
      _forecastRetryCount = 0;
      renderKpiBar();
      renderHeroChart();
      renderSkuInfo();
      renderLastUpdated();

      // Initialize Tab 4 baseline simulation data so it displays immediately
      if (state.forecastData?.impact_data) {
        state.simData = {
          base_trajectory: state.forecastData.impact_data.inventory_trajectory,
          sim_impact: state.forecastData.impact_data,
          eff_lt: state.leadTime,
          eff_dem_scale: 1.0,
        };
      }

      // Also load tab-specific data for visible tab
      if (state.activeTab === 'tab1') {
        if (!state.decompData) loadDecomp();
        if (!state.festivalData) loadFestival();
      }
      if (state.activeTab === 'tab2') {
        renderTab2();
        if (!state.fiData) loadFeatureImportance();
      }
      if (state.activeTab === 'tab3') {
        renderInventory();
        if (!state.abcData) loadAbc();
        if (!state.regionalData) loadRegional();
      }
      if (state.activeTab === 'tab4') {
        renderSimSliders();
        renderSimMetrics();
        renderSimChart(false);
      }
      if (state.activeTab === 'tab5') {
        renderTab5();
      }
    } catch (e) {
      if (activeForecastPromise !== promise && activeForecastPromise !== null) return;
      console.warn('Forecast fetch attempt failed:', e);
      if (_forecastRetryCount < 3) {
        _forecastRetryCount++;
        if (!state.forecastData && el('lastUpdated')) {
          el('lastUpdated').textContent = `Connecting to AI Inference Engine (${_forecastRetryCount}/3)...`;
        }
        setTimeout(() => loadForecast(isInitial), 2000);
        return;
      }

      // If we already have valid data showing, do NOT destroy the UI cards!
      if (!state.forecastData) {
        if (el('lastUpdated')) {
          el('lastUpdated').innerHTML = `<span style="color:var(--amber)">Server cold start. <a href="javascript:void(0)" onclick="window.DemandSenseApp?.retryLoad()" style="color:var(--teal);text-decoration:underline">Click to Retry</a></span>`;
        }
        for (let i = 0; i < 4; i++) {
          const card = el(`kpi${i}`);
          if (card) {
            card.innerHTML = `
              <div style="padding:14px 6px;text-align:center;color:var(--text3);font-size:0.75rem">
                <span style="font-size:1.1rem;display:block;margin-bottom:3px">⏳</span>
                Waking up
              </div>
            `;
          }
        }
        const hero = el('heroChart');
        if (hero) {
          hero.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:280px;color:var(--text2);gap:10px;text-align:center;padding:1rem">
              <div style="font-size:1.6rem">⚡</div>
              <div style="font-size:0.95rem;font-weight:600">Instance Warming Up (~15s)</div>
              <div style="font-size:0.78rem;color:var(--text3);max-width:320px">The free cloud container was sleeping. Please click below to refresh data.</div>
              <button class="export-btn primary" onclick="window.DemandSenseApp?.retryLoad()" style="font-size:0.8rem;padding:6px 18px;margin-top:4px">Retry Connection</button>
            </div>
          `;
        }
      }
    } finally {
      if (activeForecastPromise === promise) {
        activeForecastPromise = null;
      }
    }
  }

  // ═══ KPI BAR RENDERING ═══
  function renderKpiBar() {
    const kpis = state.forecastData?.kpi_bar?.kpis || [];
    kpis.forEach((kpi, i) => {
      const card = el(`kpi${i}`);
      const deltaClass = kpi.favorable ? 'up' : (kpi.delta_pct === 0 ? 'neutral' : 'down');
      const arrow = kpi.delta_pct > 0 ? '▲' : (kpi.delta_pct < 0 ? '▼' : '—');

      // SVG sparkline
      const spark = kpi.sparkline?.length > 2 ? generateSparkline(kpi.sparkline) : '';

      card.innerHTML = `
        <div class="kpi-header-row">
          <div class="kpi-icon-chip ${kpi.chip_color}">${kpi.chip}</div>
          <span class="kpi-delta ${deltaClass}">${arrow} ${Math.abs(kpi.delta_pct).toFixed(1)}%</span>
        </div>
        <div class="kpi-label">${kpi.label}</div>
        <div class="kpi-value">${kpi.value_fmt}</div>
        <div class="kpi-sparkline">${spark}</div>
      `;
    });
  }

  function generateSparkline(values) {
    if (!values || values.length < 2) return '';
    const w = 100, h = 22, pad = 2;
    const min = Math.min(...values), max = Math.max(...values);
    const range = max - min || 1;
    const points = values.map((v, i) =>
      `${pad + (i / (values.length - 1)) * (w - 2 * pad)},${pad + (1 - (v - min) / range) * (h - 2 * pad)}`
    ).join(' ');

    return `<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
      <polyline fill="none" stroke="var(--teal)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" points="${points}"/>
    </svg>`;
  }

  // ═══ SKU INFO & DATA FRESHNESS ═══
  function renderSkuInfo() {
    const ds = state.forecastData?.data_summary;
    if (ds) {
      if (el('dataFreshness')) {
        el('dataFreshness').innerHTML = `📅 Historical Baseline: <strong>${ds.data_start}</strong> → <strong>${ds.data_end}</strong> (1,095 days) · <strong>30-Day Forecast Window: Jan 01 → Jan 30, 2026</strong> · ${ds.total_skus} SKUs`;
      }
      if (el('datasetNameText')) {
        el('datasetNameText').textContent = `Enterprise FMCG · ${ds.total_skus} SKUs · ${ds.total_days}d`;
      }
      if (el('sumDataset')) {
        el('sumDataset').textContent = `Enterprise FMCG (${ds.total_skus} SKUs)`;
      }
    }
    updateCollapsedSummary();
  }

  function renderLastUpdated() {
    const d = state.forecastData;
    if (!d) return;
    const name = d.forecast_res?.winning_model_name || 'Auto-ML';
    const now = new Date().toLocaleTimeString();
    el('lastUpdated').textContent = `Last updated ${now} · Winner: ${name} · ${d.data_summary?.total_days || '—'} days of data`;
  }

  // ═══ TAB 1 CHARTS ═══
  function renderHeroChart() {
    const d = state.forecastData;
    if (!d) return;

    let history = d.chart_history || [];
    if (state.historyRange > 0) {
      history = history.slice(-state.historyRange);
    }

    Charts.heroChart('heroChart', history, d.forecast_res.winning_forecast, d.impact_data, state.festivalData?.festivals, state.festivalFilter);

    // Dynamic subtitle
    const subtitle = el('tab1Subtitle');
    if (d.forecast_res?.winning_model_name) {
      subtitle.textContent = `${d.forecast_res.winning_model_name} Winning Model · 30-Day Forward Forecast: Jan 01 → Jan 30, 2026 · MAPE ${d.forecast_res.winning_metrics.mape.toFixed(2)}%`;
    }
  }

  async function loadDecomp() {
    showLoading('decompTrend');
    showLoading('decompSeasonal');
    showLoading('decompResidual');
    try {
      state.decompData = await API.get(`/api/decomposition?sku=${state.sku}&region=${state.region}&_t=${Date.now()}`);
      const { dates, trend, seasonal, residual } = state.decompData;
      Charts.decompChart('decompTrend', 'decompSeasonal', 'decompResidual', dates, trend, seasonal, residual);
    } catch (e) {
      el('decompTrend').innerHTML = `<div style="color:var(--text3);padding:20px">Decomposition unavailable</div>`;
    }
  }

  async function loadFestival() {
    showLoading('festivalChart');
    try {
      state.festivalData = await API.get(`/api/festival-impact?sku=${state.sku}&_t=${Date.now()}`);
      Charts.festivalChart('festivalChart', state.festivalData.festivals, (festName) => {
        state.festivalFilter = state.festivalFilter === festName ? null : festName;
        renderHeroChart();
      });
    } catch (e) {
      el('festivalChart').innerHTML = `<div style="color:var(--text3);padding:20px">Festival data unavailable</div>`;
    }
  }

  // ═══ TAB 2: AUTO-ML ═══
  function renderTab2() {
    const d = state.forecastData;
    if (!d) return;
    renderLeaderboard(d.forecast_res.leaderboard, d.forecast_res.winning_model_name);
    renderRadar(d.forecast_res.radar || [], d.forecast_res.leaderboard, d.forecast_res.winning_model_name);
    renderScatter(d.forecast_res.leaderboard, d.chart_history, d.forecast_res.winning_forecast);
  }

  function renderLeaderboard(leaderboard, winner) {
    const rows = leaderboard.map(m => {
      const isW = m.model_name === winner;
      return `<tr class="${isW ? 'winner' : ''}" style="cursor:pointer" onclick="DetailDrawer.open('Model: ${m.model_name}', DetailDrawer.buildMetricTable([{label:'MAPE',value:'${(m.mape ?? 0).toFixed(4)}%'},{label:'RMSE',value:'${(m.rmse ?? 0).toFixed(2)}'},{label:'MAE',value:'${(m.mae ?? 0).toFixed(2)}'},{label:'WAPE',value:'${(m.wape ?? 0).toFixed(4)}%'},{label:'Fit Time',value:'${(m.fit_time_sec ?? 0).toFixed(2)}s'}]))">
        <td>${isW ? '🏆 ' : ''}${m.model_name}</td>
        <td>${(m.mape ?? 0).toFixed(2)}%</td>
        <td>${(m.rmse ?? 0).toFixed(1)}</td>
        <td>${(m.mae ?? 0).toFixed(1)}</td>
        <td>${(m.wape ?? 0).toFixed(2)}%</td>
      </tr>`;
    }).join('');

    el('leaderboardTable').innerHTML = `<table class="data-table">
      <thead><tr><th>Model</th><th>MAPE ↓</th><th>RMSE ↓</th><th>MAE ↓</th><th>WAPE ↓</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;

    const wm = leaderboard.find(m => m.model_name === winner);
    el('winnerBanner').className = 'badge healthy';
    el('winnerBanner').innerHTML = `🏆 ${winner} wins — MAPE ${(wm?.mape ?? 0).toFixed(2)}%`;
  }

  function renderRadar(radarData, leaderboard, winner) {
    Charts.radarChart('radarChart', radarData, leaderboard, winner);
  }

  async function loadFeatureImportance() {
    showLoading('fiChart');
    try {
      state.fiData = await API.get(`/api/feature-importance?sku=${state.sku}&region=${state.region}&_t=${Date.now()}`);
      Charts.featureImportanceChart('fiChart', state.fiData.features);
    } catch (e) {
      el('fiChart').innerHTML = `<div style="color:var(--text3);padding:20px">Feature importance unavailable</div>`;
    }

    // Also render Tab 2 leaderboard/radar/scatter if data available
    if (state.forecastData) renderTab2();
  }

  function renderScatter(leaderboard, history, forecast) {
    Charts.scatterChart('scatterChart', leaderboard, history, forecast);
  }

  // ═══ TAB 3: INVENTORY ═══
  function renderInventory() {
    const d = state.forecastData;
    if (!d?.impact_data) return;
    const traj = d.impact_data.inventory_trajectory || [];
    const ss = d.impact_data.safety_stock_units || 0;
    const rop = d.impact_data.reorder_point_units || 0;

    Charts.inventoryChart('inventoryChart', traj, ss, rop);

    // Stockout annotation text
    const soDay = traj.findIndex(d => d.projected_stock <= 0);
    if (soDay >= 0) {
      el('stockoutAnnotation').innerHTML = `⚠ <span style="color:var(--red)">STOCKOUT IN ${soDay + 1} DAYS (${traj[soDay].date})</span>`;
    } else {
      el('stockoutAnnotation').innerHTML = `✓ <span style="color:var(--green)">Stock covers full 30-day horizon</span>`;
    }
  }

  async function loadAbc() {
    showLoading('abcTreemap');
    try {
      state.abcData = await API.get('/api/abc-classification');
      Charts.abcTreemap('abcTreemap', state.abcData.table);
      renderAbcTable();
    } catch (e) {
      el('abcTreemap').innerHTML = '<div style="color:var(--text3);padding:20px">ABC data unavailable</div>';
    }
  }

  function renderAbcTable() {
    if (!state.abcData?.table) return;
    const rows = state.abcData.table.map(r => {
      const cls = (r.abc_class || '').toUpperCase();
      const isSel = r.sku_id === state.sku;
      let trClass = '';
      if (isSel) trClass = 'selected-sku';
      else if (cls === 'A') trClass = 'abc-a';
      else if (cls === 'B') trClass = 'abc-b';
      else if (cls === 'C') trClass = 'abc-c';

      return `<tr class="${trClass}">
        <td>${r.sku_id || ''}</td>
        <td>${r.sku_name || ''}</td>
        <td>₹${(r.revenue_inr || 0).toLocaleString()}</td>
        <td>${(r.cum_pct || 0).toFixed(1)}%</td>
        <td><span class="badge ${cls === 'A' ? 'critical' : cls === 'B' ? 'warning' : 'healthy'}">${cls}</span></td>
      </tr>`;
    }).join('');

    el('abcTable').innerHTML = `<table class="data-table">
      <thead><tr><th>SKU ID</th><th>Name</th><th>Revenue</th><th>Cum %</th><th>Class</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  async function loadRegional() {
    showLoading('mapChart');
    try {
      state.regionalData = await API.get(`/api/regional-summary?sku=${state.sku}`);
      Charts.mapChart('mapChart', state.regionalData.regions);
    } catch (e) {
      el('mapChart').innerHTML = '<div style="color:var(--text3);padding:20px">Regional data unavailable</div>';
    }
    // Also render inventory chart
    renderInventory();
  }

  // ═══ TAB 4: WHAT-IF SIMULATOR ═══
  const PRESETS = {
    monsoon: { simLt: 10, simDem: -20, simPrc: 0, simElast: -12, simPromo: 0 },
    diwali:  { simLt: 3,  simDem: 80,  simPrc: 10, simElast: -8,  simPromo: 40 },
    pricewar:{ simLt: 0,  simDem: 0,   simPrc: -25,simElast: -20, simPromo: 0 },
    reset:   { simLt: 0,  simDem: 0,   simPrc: 0,  simElast: -12, simPromo: 0 },
  };

  function renderSimSliders() {
    // Attach slider event listeners
    ['simLt', 'simDem', 'simPrc', 'simElast', 'simPromo'].forEach(id => {
      const slider = el(id);
      slider.addEventListener('input', () => updateSimLabels());
      slider.addEventListener('change', debounce(runSimulation, 500));
    });

    // Preset buttons
    $$('.preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const p = PRESETS[btn.dataset.preset];
        if (!p) return;
        $$('.preset-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        el('simLt').value = p.simLt;
        el('simDem').value = p.simDem;
        el('simPrc').value = p.simPrc;
        el('simElast').value = p.simElast;
        el('simPromo').value = p.simPromo;
        updateSimLabels();
        runSimulation();
      });
    });

    updateSimLabels();
  }

  function updateSimLabels() {
    el('simLtVal').textContent = `${el('simLt').value > 0 ? '+' : ''}${el('simLt').value} days`;
    el('simDemVal').textContent = `${el('simDem').value > 0 ? '+' : ''}${el('simDem').value}%`;
    el('simPrcVal').textContent = `${el('simPrc').value > 0 ? '+' : ''}${el('simPrc').value}%`;
    el('simElastVal').textContent = (parseInt(el('simElast').value) / 10).toFixed(1);
    el('simPromoVal').textContent = `${el('simPromo').value}%`;
  }

  async function runSimulation() {
    try {
      const body = {
        sku: state.sku, region: state.region,
        lead_time: state.leadTime, service_level: state.serviceLevel, stock: state.stock,
        sim_lt_add: parseInt(el('simLt').value),
        sim_demand_mult: parseInt(el('simDem').value),
        sim_price_mult: parseInt(el('simPrc').value),
        sim_elasticity: parseInt(el('simElast').value) / 10,
        sim_promo: parseInt(el('simPromo').value),
      };

      state.simData = await API.post('/api/simulate', body);
      renderSimChart(true);
      renderSimMetrics();
    } catch (e) {
      toast('Simulation error: ' + e.message, true);
    }
  }

  function renderSimChart(merge = false) {
    const d = state.simData;
    if (!d) return;
    const baseTraj = d.base_trajectory || [];
    const simTraj = d.sim_impact?.inventory_trajectory || [];
    const baseSS = state.forecastData?.impact_data?.safety_stock_units || 0;
    const simSS = d.sim_impact?.safety_stock_units || 0;
    const simRop = d.sim_impact?.reorder_point_units || 0;

    Charts.simChart('simChart', baseTraj, simTraj, baseSS, simSS, simRop, merge);
  }

  function renderSimMetrics() {
    const d = state.simData;
    const base = state.forecastData?.impact_data;
    if (!d?.sim_impact || !base) return;

    const s = d.sim_impact;
    if (el('simMetricLt')) el('simMetricLt').textContent = `${d.eff_lt} Days`;
    if (el('simMetricSs')) el('simMetricSs').textContent = `${(s.safety_stock_units || 0).toLocaleString()} Units`;
    if (el('simMetricRop')) el('simMetricRop').textContent = `${(s.reorder_point_units || 0).toLocaleString()} Units`;
    const rarLakhs = ((s.revenue_at_risk_inr || 0) / 100000);
    if (el('simMetricRar')) el('simMetricRar').textContent = `₹${rarLakhs >= 0.01 ? rarLakhs.toFixed(2) : '0.00'} Lakhs`;
    if (el('simMetricPo')) el('simMetricPo').textContent = `${(s.recommended_po_qty_units || 0).toLocaleString()} Units`;
    if (el('simMetricScale')) el('simMetricScale').textContent = `${d.eff_dem_scale?.toFixed(2)}× Multiplier`;
  }

  // ═══ TAB 5: AI PRESCRIPTIVE CONTROL ROOM ═══
  function renderTab5() {
    const d = state.forecastData;
    if (!d) return;

    const impact = d.impact_data || {};
    const llm = d.llm_report || {};
    const statusStr = impact.po_trigger_status || 'STABLE';
    const priority = llm.priority_level || 'INFO';

    // Alert banner
    let cls, icon, title, sub;
    const skuName = d.sku_info?.name || state.sku;
    if (statusStr.includes('CRITICAL') || priority === 'CRITICAL') {
      cls = 'critical'; icon = '🚨'; title = 'CRITICAL STOCKOUT RISK DETECTED';
      sub = `Immediate procurement action required for ${skuName} — stock below safety threshold.`;
    } else if (statusStr.includes('WARNING') || priority === 'WARNING') {
      cls = 'warning'; icon = '⚠️'; title = 'REORDER POINT BREACH IMMINENT';
      sub = `Stock approaching reorder point for ${skuName} — review procurement pipeline.`;
    } else {
      cls = 'healthy'; icon = '✅'; title = 'HEALTHY — INVENTORY BALANCED';
      sub = `Stock levels healthy for ${skuName} — no immediate action needed.`;
    }

    el('alertBanner').className = `alert-banner ${cls}`;
    el('alertBanner').innerHTML = `
      <span class="alert-icon">${icon}</span>
      <div>
        <div class="alert-title" style="color:var(--${cls === 'critical' ? 'red' : cls === 'warning' ? 'amber' : 'green'})">${title}</div>
        <div class="alert-sub">${sub}</div>
      </div>
    `;

    // Update Model Provenance Badge
    const wm = d.forecast_res?.winning_model_name || 'Auto-ML Winner';
    const wmape = d.forecast_res?.winning_metrics?.mape != null ? d.forecast_res.winning_metrics.mape.toFixed(2) : '—';
    if (el('modelProvenanceBadge')) {
      el('modelProvenanceBadge').innerHTML = `🏆 Model Provenance: <strong>${wm}</strong> (Backtest MAPE: ${wmape}%)`;
    }

    // AI Action Cards
    const cards = [
      { chip: 'AI', chipColor: 'indigo', label: 'Executive Summary', text: llm.executive_summary, icon: '📊' },
      { chip: 'PO', chipColor: 'gold', label: 'Procurement Directive', text: llm.recommended_action || llm.procurement_directive, icon: '📦' },
      { chip: '₹', chipColor: 'red', label: 'Financial Risk & Rupee Impact', text: llm.financial_risk_narrative || llm.financial_risk, icon: '💰' },
      { chip: 'ML', chipColor: 'teal', label: 'AI Model Selection Rationale', text: llm.model_rationale, icon: '🧠' },
    ];

    cards.forEach((card, i) => {
      const bullets = textToBullets(card.text || 'No data available.', card.icon);
      el(`aiCard${i}`).innerHTML = `
        <div class="kpi-icon-chip ${card.chipColor}">${card.chip}</div>
        <div class="kpi-label" style="text-transform:none;letter-spacing:0">${card.label}</div>
        <ul class="ai-bullets">${bullets}</ul>
      `;
    });

    // PO Preview
    const rec = impact.recommended_po_qty_units || 0;
    const poVal = impact.recommended_po_value_inr || rec * (d.sku_info?.base_price || 100) * 0.7;
    const poPriority = statusStr.includes('CRITICAL') ? 'URGENT' : (statusStr.includes('WARNING') ? 'HIGH' : 'NORMAL');
    const prioColor = poPriority === 'URGENT' ? 'var(--red)' : poPriority === 'HIGH' ? 'var(--amber)' : 'var(--green)';

    el('poPreview').innerHTML = `
      <div style="font-weight:700;font-size:0.85rem;color:var(--accent);margin-bottom:10px">📋 PURCHASE ORDER PREVIEW</div>
      <div class="po-row"><span class="po-label">PO ID</span><span class="po-val">PO-2026-${state.sku}-01</span></div>
      <div class="po-row"><span class="po-label">SKU</span><span class="po-val">${skuName} (${state.sku})</span></div>
      <div class="po-row"><span class="po-label">Order Qty</span><span class="po-val">${rec.toLocaleString()} units</span></div>
      <div class="po-row"><span class="po-label">Unit Cost</span><span class="po-val">₹${((d.sku_info?.base_price || 100) * 0.7).toLocaleString()}</span></div>
      <div class="po-row"><span class="po-label">Total Value</span><span class="po-val">₹${poVal.toLocaleString()}</span></div>
      <div class="po-row"><span class="po-label">Lead Time</span><span class="po-val">${state.leadTime} days</span></div>
      <div class="po-row"><span class="po-label">Priority</span><span class="po-val" style="color:${prioColor};font-weight:700">${poPriority}</span></div>
    `;

    // Export links
    el('exportCsv').href = `/api/export/po-csv?${_qs()}`;
    el('exportPdf').href = `/api/export/brief-pdf?${_qs()}`;

    // Raw brief
    el('rawBrief').textContent = `DEMANDSENSE AI — EXECUTIVE PROCUREMENT BRIEF
Generated for SKU: ${skuName} (${state.sku})
Region: ${state.region === 'ALL' ? 'National Aggregation' : state.region}

EXECUTIVE SUMMARY:
${llm.executive_summary || 'N/A'}

RECOMMENDED PROCUREMENT DIRECTIVE:
${llm.recommended_action || llm.procurement_directive || 'N/A'}

FINANCIAL RISK & RUPEE IMPACT:
${llm.financial_risk_narrative || llm.financial_risk || 'N/A'}

AI MODEL SELECTION RATIONALE:
${llm.model_rationale || 'N/A'}`;
  }

  function textToBullets(text, defaultIcon) {
    if (!text || text === 'N/A') return `<li><span style="color:var(--text3);font-style:italic">No data available.</span></li>`;
    const sentences = text.replace(/\. /g, '.\n').split('\n').filter(s => s.trim()).slice(0, 5);
    return sentences.map(s => {
      let icon = defaultIcon;
      const lower = s.toLowerCase();
      if (/recommend|order|procure|action|should|must/.test(lower)) icon = '✅';
      else if (/risk|warn|critical|stockout|loss|danger/.test(lower)) icon = '⚠️';
      else if (/₹|revenue|cost|margin|profit|lakh|crore/.test(lower)) icon = '💰';
      return `<li><span style="flex-shrink:0">${icon}</span><span>${s.trim()}</span></li>`;
    }).join('');
  }

  // ═══ FOCUS MODAL ═══
  function setupModal() {
    const overlay = el('focusModal');
    el('modalClose').addEventListener('click', () => overlay.classList.remove('active'));
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.classList.remove('active'); });

    // Escape key
    document.addEventListener('keydown', e => { if (e.key === 'Escape') overlay.classList.remove('active'); });

    // Expand buttons
    $$('.expand-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const chartId = btn.dataset.chart;
        openFocusModal(chartId);
      });
    });
  }

  function openFocusModal(chartId) {
    const overlay = el('focusModal');
    const titles = {
      hero: 'Historical vs. 30-Day AI Forecast',
      decomp: 'Time-Series Decomposition',
      festival: 'Festival Demand Impact',
      radar: 'Performance Radar',
      fi: 'Feature Importance (XGBoost)',
      scatter: 'Actual vs. Predicted',
      inventory: 'Projected Stock Trajectory',
      map: 'Regional Demand Hubs',
      sim: 'Baseline vs. Simulated Trajectory',
      abcTreemap: 'ABC Revenue Classification Matrix',
    };

    el('modalTitle').textContent = titles[chartId] || chartId;
    overlay.classList.add('active');

    // Render chart in modal at larger size
    setTimeout(() => {
      const d = state.forecastData;
      if (!d) return;

      switch (chartId) {
        case 'hero': {
          let hist = d.chart_history || [];
          if (state.historyRange > 0) hist = hist.slice(-state.historyRange);
          Charts.heroChart('modalChart', hist, d.forecast_res.winning_forecast, d.impact_data, state.festivalData?.festivals, state.festivalFilter);
          break;
        }
        case 'festival':
          if (state.festivalData) Charts.festivalChart('modalChart', state.festivalData.festivals);
          break;
        case 'radar':
          Charts.radarChart('modalChart', d.forecast_res.radar || [], d.forecast_res.leaderboard, d.forecast_res.winning_model_name);
          break;
        case 'fi':
          if (state.fiData) Charts.featureImportanceChart('modalChart', state.fiData.features);
          break;
        case 'scatter':
          Charts.scatterChart('modalChart', d.forecast_res.leaderboard, d.chart_history, d.forecast_res.winning_forecast);
          break;
        case 'inventory':
          Charts.inventoryChart('modalChart', d.impact_data.inventory_trajectory, d.impact_data.safety_stock_units, d.impact_data.reorder_point_units);
          break;
        case 'map':
          if (state.regionalData) Charts.mapChart('modalChart', state.regionalData.regions);
          break;
        case 'abcTreemap':
          if (state.abcData) Charts.abcTreemap('modalChart', state.abcData.table);
          break;
        case 'sim':
          if (state.simData) {
            const baseTraj = state.simData.base_trajectory || [];
            const simTraj = state.simData.sim_impact?.inventory_trajectory || [];
            Charts.simChart('modalChart', baseTraj, simTraj,
              d.impact_data.safety_stock_units, state.simData.sim_impact?.safety_stock_units, state.simData.sim_impact?.reorder_point_units);
          }
          break;
      }
    }, 100);
  }

  // ═══ RE-RENDER ACTIVE CHARTS ON THEME CHANGE ═══
  function reRenderAllCharts() {
    if (!window.ChartTheme) return;

    ChartTheme.applyTheme(() => {
      // Re-render ONLY the active tab's charts
      if (state.activeTab === 'tab1') {
        if (state.forecastData) renderHeroChart();
        if (state.decompData) {
          const { dates, trend, seasonal, residual } = state.decompData;
          Charts.decompChart('decompTrend', 'decompSeasonal', 'decompResidual', dates, trend, seasonal, residual);
        }
        if (state.festivalData) {
          Charts.festivalChart('festivalChart', state.festivalData.festivals, (festName) => {
            state.festivalFilter = state.festivalFilter === festName ? null : festName;
            renderHeroChart();
          });
        }
      } else if (state.activeTab === 'tab2') {
        if (state.forecastData) renderTab2();
        if (state.fiData) Charts.featureImportanceChart('fiChart', state.fiData.features);
      } else if (state.activeTab === 'tab3') {
        renderInventory();
        if (state.abcData) Charts.abcTreemap('abcTreemap', state.abcData.table);
        if (state.regionalData) Charts.mapChart('mapChart', state.regionalData.regions);
      } else if (state.activeTab === 'tab4') {
        if (state.simData) renderSimChart(false);
      } else if (state.activeTab === 'tab5') {
        renderTab5();
      }
    });

    renderKpiBar();
  }

  // ═══ GLOBAL CONTROLLER EXPORT ═══
  window.DemandSenseApp = {
    retryLoad: () => {
      clearCachedData();
      loadForecast();
    },
    state,
    switchTab
  };

  // ═══ BOOT ═══
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
