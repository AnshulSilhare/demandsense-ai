(function() {
  const DetailDrawer = {
    open(title, contentHTML) {
      const drawerTitle = document.getElementById('drawerTitle');
      const drawerBody = document.getElementById('drawerBody');
      const drawerOverlay = document.getElementById('drawerOverlay');
      const detailDrawer = document.getElementById('detailDrawer');
      const drawerClose = document.getElementById('drawerClose');

      if (drawerTitle) drawerTitle.textContent = title;
      if (drawerBody) drawerBody.innerHTML = contentHTML;
      
      if (drawerOverlay) drawerOverlay.classList.add('open');
      if (detailDrawer) detailDrawer.classList.add('open');
      
      document.body.style.overflow = 'hidden';
      
      if (drawerClose) drawerClose.focus();
    },

    openWithChart(title, introHTML, chartBuildFn) {
      const contentHTML = `
        ${introHTML}
        <div class="drawer-chart" id="drawerChart" style="width:100%;height:280px;margin-top:1rem;"></div>
      `;
      this.open(title, contentHTML);
      
      // Wait a moment for drawer to transition before building chart
      setTimeout(() => {
        if (typeof chartBuildFn === 'function') {
          chartBuildFn('drawerChart');
        }
      }, 350);
      
      this._hasChart = true;
    },

    close() {
      const drawerOverlay = document.getElementById('drawerOverlay');
      const detailDrawer = document.getElementById('detailDrawer');
      const drawerBody = document.getElementById('drawerBody');

      if (drawerOverlay) drawerOverlay.classList.remove('open');
      if (detailDrawer) detailDrawer.classList.remove('open');
      
      document.body.style.overflow = '';

      if (this._hasChart && typeof window.ChartTheme !== 'undefined' && window.ChartTheme.dispose) {
        window.ChartTheme.dispose('drawerChart');
      }
      this._hasChart = false;

      setTimeout(() => {
        if (drawerBody) drawerBody.innerHTML = '';
      }, 350);
    },

    buildMetricTable(rows) {
      if (!rows || !rows.length) return '';
      const tableRows = rows.map(row => `
        <tr class="${row.highlight ? 'highlight' : ''}">
          <td class="metric-label">${row.label}</td>
          <td class="metric-value">${row.value}${row.unit || ''}</td>
        </tr>
      `).join('');
      
      return `
        <table class="drawer-metric-table">
          ${tableRows}
        </table>
      `;
    },

    buildRankList(items) {
      if (!items || !items.length) return '';
      const listItems = items.map(item => `
        <div class="rank-item">
          <span class="rank-num">#${item.rank}</span>
          <span class="rank-name">${item.name}</span>
          ${item.bar !== undefined ? `<div class="rank-bar" style="width:${item.bar}%"></div>` : ''}
          <span class="rank-value">${item.value}</span>
        </div>
      `).join('');
      
      return `
        <div class="drawer-rank-list">
          ${listItems}
        </div>
      `;
    }
  };

  window.DetailDrawer = DetailDrawer;

  document.addEventListener('DOMContentLoaded', () => {
    const drawerClose = document.getElementById('drawerClose');
    const drawerOverlay = document.getElementById('drawerOverlay');

    if (drawerClose) {
      drawerClose.addEventListener('click', () => {
        DetailDrawer.close();
      });
    }

    if (drawerOverlay) {
      drawerOverlay.addEventListener('click', (e) => {
        if (e.target === drawerOverlay) {
          DetailDrawer.close();
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && drawerOverlay && drawerOverlay.classList.contains('open')) {
        DetailDrawer.close();
      }
    });
  });
})();
