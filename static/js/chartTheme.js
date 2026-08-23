'use strict';

(function(global) {
    // Map to track ECharts instances by container ID
    const _instances = new Map();
    // Map to store options for re-application on theme switch
    const _options = new Map();
    // Map to store ResizeObserver instances by container ID
    const _observers = new Map();

    const ChartTheme = {
        /**
         * Reads CSS custom properties from the document and returns a resolved colors object.
         * @returns {Object} Colors object
         */
        getColors: function() {
            const isDark = document.body.classList.contains('dark');
            const targetEl = document.body || document.documentElement;
            const rootStyle = getComputedStyle(targetEl);
            const getVar = (name) => rootStyle.getPropertyValue(name).trim();

            return {
                text: getVar('--text') || (isDark ? '#f8fafc' : '#0f172a'),
                text2: getVar('--text2') || (isDark ? '#cbd5e1' : '#475569'),
                text3: getVar('--text3') || (isDark ? '#94a3b8' : '#94a3b8'),
                border: getVar('--border') || (isDark ? 'rgba(255,255,255,.06)' : 'rgba(15,23,42,.08)'),
                border2: getVar('--border2') || (isDark ? 'rgba(255,255,255,.12)' : 'rgba(15,23,42,.15)'),
                accent: getVar('--accent') || (isDark ? '#3b82f6' : '#1e3a5f'),
                accentTitle: getVar('--accent-title') || (isDark ? '#38bdf8' : '#1d4ed8'),
                accent2: getVar('--accent2') || (isDark ? '#2dd4bf' : '#0d9488'),
                teal: getVar('--teal') || (isDark ? '#2dd4bf' : '#0d9488'),
                amber: getVar('--amber') || (isDark ? '#fbbf24' : '#d97706'),
                green: getVar('--green') || (isDark ? '#34d399' : '#16a34a'),
                red: getVar('--red') || (isDark ? '#f87171' : '#dc2626'),
                surface: getVar('--surface') || (isDark ? '#1e293b' : '#ffffff'),
                bg: getVar('--bg') || (isDark ? '#0b0f19' : '#f8fafc'),
                bg2: getVar('--bg2') || (isDark ? '#111827' : '#f1f5f9'),
                bg3: getVar('--bg3') || (isDark ? '#161f30' : '#e2e8f0'),
                tooltipBg: isDark ? 'rgba(15, 23, 42, 0.90)' : 'rgba(255, 255, 255, 0.92)',
                tooltipBorder: isDark ? 'rgba(255, 255, 255, 0.14)' : 'rgba(15, 23, 42, 0.12)',
                displayFont: getVar('--display') || "'Syne', sans-serif",
                bodyFont: getVar('--body') || "'DM Sans', sans-serif",
                monoFont: getVar('--mono') || "'JetBrains Mono', monospace"
            };
        },

        /**
         * Builds an ECharts theme object using current CSS variables.
         * @returns {Object} ECharts theme object
         */
        buildTheme: function() {
            const colors = this.getColors();
            return {
                backgroundColor: 'transparent',
                textStyle: {
                    color: colors.text,
                    fontFamily: colors.bodyFont
                },
                title: {
                    textStyle: {
                        color: colors.text,
                        fontFamily: colors.displayFont,
                        fontWeight: 700
                    }
                },
                legend: {
                    textStyle: {
                        color: colors.text2,
                        fontFamily: colors.bodyFont
                    }
                },
                tooltip: {
                    confine: true,
                    backgroundColor: colors.tooltipBg,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    textStyle: { color: colors.text, fontFamily: colors.bodyFont, fontSize: 12 },
                    extraCssText: 'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border-radius: 10px; box-shadow: 0 12px 36px rgba(0,0,0,.22); padding: 10px 14px;'
                },
                color: [colors.accent, colors.teal, colors.amber, colors.green, colors.red, colors.accentTitle, '#8b5cf6'],
                categoryAxis: {
                    axisLine: { lineStyle: { color: colors.border2 } },
                    splitLine: { lineStyle: { color: colors.border } },
                    axisLabel: { color: colors.text3, fontFamily: colors.monoFont, fontSize: 11 }
                },
                valueAxis: {
                    axisLine: { lineStyle: { color: colors.border2 } },
                    splitLine: { lineStyle: { color: colors.border } },
                    axisLabel: { color: colors.text3, fontFamily: colors.monoFont, fontSize: 11 }
                },
                dataZoom: {
                    dataBackgroundColor: colors.glassBg,
                    fillerColor: colors.glassBorder,
                    handleColor: colors.accent,
                    handleStyle: { borderColor: colors.border },
                    textStyle: { color: colors.text2 }
                },
                toolbox: {
                    iconStyle: { borderColor: colors.text3 }
                },
                grid: {
                    left: 48,
                    right: 24,
                    top: 48,
                    bottom: 56,
                    containLabel: true
                },
                line: {
                    smooth: true,
                    symbolSize: 4
                },
                bar: {
                    barMaxWidth: 28
                }
            };
        },

        /**
         * Registers the 'demandsense' theme with ECharts.
         */
        register: function() {
            if (typeof echarts !== 'undefined') {
                const theme = this.buildTheme();
                echarts.registerTheme('demandsense', theme);
            } else {
                console.warn('ECharts is not loaded yet.');
            }
        },

        /**
         * Creates or recreates an ECharts instance for the given container ID.
         * @param {string} containerId - The ID of the DOM element
         * @param {Object} [opts] - Additional init options
         * @returns {echarts.ECharts|null} The initialized ECharts instance
         */
        init: function(containerId, opts) {
            if (typeof echarts === 'undefined') {
                console.error('ECharts is not loaded.');
                return null;
            }

            const dom = document.getElementById(containerId);
            if (!dom) {
                console.error(`Container with id "${containerId}" not found.`);
                return null;
            }

            if (_instances.has(containerId)) {
                this.dispose(containerId);
            }

            // Clear any loading shimmer/spinner HTML before initializing ECharts canvas
            dom.innerHTML = '';
            this.register();
            this.attachOrientationListener();

            const instance = echarts.init(dom, 'demandsense', opts);
            _instances.set(containerId, instance);

            let resizeTimer;
            const observer = new ResizeObserver(() => {
                clearTimeout(resizeTimer);
                resizeTimer = setTimeout(() => {
                    if (instance && !instance.isDisposed()) {
                        instance.resize();
                    }
                }, 80);
            });
            observer.observe(dom);
            _observers.set(containerId, observer);

            return instance;
        },

        /**
         * Attaches a window orientationchange listener to automatically resize charts on mobile rotation.
         */
        attachOrientationListener: function() {
            if (this._orientationAttached) return;
            this._orientationAttached = true;
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    for (const inst of _instances.values()) {
                        if (inst && !inst.isDisposed()) inst.resize();
                    }
                }, 300);
            });
        },

        /**
         * Sets options on a chart instance and saves them for re-application.
         * @param {string} containerId - The container ID
         * @param {Object} option - The ECharts option object
         * @param {boolean} [merge=false] - Whether to merge with existing options
         */
        setOption: function(containerId, option, merge = false) {
            const instance = _instances.get(containerId);
            if (instance) {
                instance.setOption(option, { notMerge: !merge });
                _options.set(containerId, option);
            } else {
                console.warn(`Chart instance for "${containerId}" not found.`);
            }
        },

        /**
         * Returns an existing chart instance.
         * @param {string} containerId - The container ID
         * @returns {echarts.ECharts|null}
         */
        getInstance: function(containerId) {
            return _instances.get(containerId) || null;
        },

        /**
         * Disposes a chart instance and cleans up its resources.
         * @param {string} containerId - The container ID
         */
        dispose: function(containerId) {
            const instance = _instances.get(containerId);
            if (instance) {
                instance.dispose();
                _instances.delete(containerId);
                _options.delete(containerId);
            }

            const observer = _observers.get(containerId);
            if (observer) {
                observer.disconnect();
                _observers.delete(containerId);
            }
        },

        /**
         * Re-applies the theme to active charts efficiently.
         * @param {Function} [renderActiveTabFn] - Optional function to re-render the visible tab
         */
        applyTheme: function(renderActiveTabFn) {
            this.register();

            // Cleanly dispose all existing instances to release old theme canvases
            const ids = Array.from(_instances.keys());
            for (const containerId of ids) {
                this.dispose(containerId);
            }

            // Immediately re-render the active tab
            if (typeof renderActiveTabFn === 'function') {
                renderActiveTabFn();
            }
        },

        /**
         * Shows a loading indicator on the chart instance.
         * @param {string} containerId - The container ID
         */
        showLoading: function(containerId) {
            const instance = _instances.get(containerId);
            if (instance) {
                const colors = this.getColors();
                const isDark = document.body && document.body.classList.contains('dark');
                const maskColor = isDark ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.03)';
                
                instance.showLoading('default', {
                    text: '',
                    maskColor: maskColor,
                    zlevel: 0,
                    spinnerRadius: 18,
                    lineWidth: 3,
                    color: colors.teal
                });
            }
        },

        /**
         * Hides the loading indicator on the chart instance.
         * @param {string} containerId - The container ID
         */
        hideLoading: function(containerId) {
            const instance = _instances.get(containerId);
            if (instance) {
                instance.hideLoading();
            }
        }
    };

    ChartTheme._instances = _instances;
    ChartTheme._options = _options;

    global.ChartTheme = ChartTheme;

})(window);
