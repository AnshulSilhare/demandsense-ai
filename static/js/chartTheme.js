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
            const rootStyle = getComputedStyle(document.documentElement);
            const getVar = (name) => rootStyle.getPropertyValue(name).trim();

            return {
                text: getVar('--text') || '#0f172a',
                text2: getVar('--text2') || '#475569',
                text3: getVar('--text3') || '#94a3b8',
                border: getVar('--border') || '#e2e8f0',
                border2: getVar('--border2') || '#cbd5e1',
                accent: getVar('--accent') || '#1e3a5f',
                accentTitle: getVar('--accent-title') || '#1d4ed8',
                accent2: getVar('--accent2') || '#0d9488',
                teal: getVar('--teal') || '#0d9488',
                amber: getVar('--amber') || '#d97706',
                green: getVar('--green') || '#16a34a',
                red: getVar('--red') || '#dc2626',
                surface: getVar('--surface') || '#ffffff',
                bg: getVar('--bg') || '#f8fafc',
                bg2: getVar('--bg2') || '#f1f5f9',
                bg3: getVar('--bg3') || '#e2e8f0',
                glassBg: getVar('--glass-bg') || 'rgba(255, 255, 255, 0.7)',
                glassBorder: getVar('--glass-border') || 'rgba(255, 255, 255, 0.2)',
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
                    backgroundColor: colors.glassBg,
                    borderColor: colors.glassBorder,
                    textStyle: { color: colors.text },
                    extraCssText: 'backdrop-filter: blur(8px); border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,.18);'
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
