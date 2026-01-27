/* EcoSea Admin – small UX helpers (no dependencies) */

function $(sel, root=document) { return root.querySelector(sel); }
function $all(sel, root=document) { return Array.from(root.querySelectorAll(sel)); }

function initSidebar() {
  const sidebar = $('.sidebar');
  const overlay = $('.overlay');
  const hamb = $('#hamburger');
  if (!sidebar || !overlay || !hamb) return;

  const close = () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  };

  hamb.addEventListener('click', () => {
    const isOpen = sidebar.classList.toggle('open');
    overlay.classList.toggle('show', isOpen);
  });

  overlay.addEventListener('click', close);

  // Close on navigation click (mobile)
  $all('.side-nav a', sidebar).forEach(a => a.addEventListener('click', close));
}

function initClampToggles() {
  $all('[data-clamp-toggle]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-clamp-toggle');
      const el = document.getElementById(id);
      if (!el) return;
      const expanded = el.classList.toggle('expanded');
      btn.textContent = expanded ? 'Tutup' : 'Lihat';
    });
  });
}

function initTableFilter() {
  // Generic: any container with data-table-tools="<tableId>"
  $all('[data-table-tools]').forEach(toolbox => {
    const tableId = toolbox.getAttribute('data-table-tools');
    const table = document.getElementById(tableId);
    if (!table) return;

    const search = toolbox.querySelector('input[type="search"], input[data-role="search"]');
    const status = toolbox.querySelector('select[data-role="status"]');

    const rows = $all('tbody tr', table);

    const apply = () => {
      const q = (search?.value || '').trim().toLowerCase();
      const st = (status?.value || 'all').toLowerCase();

      rows.forEach(r => {
        const rowText = r.innerText.toLowerCase();
        const rowStatus = (r.getAttribute('data-status') || '').toLowerCase();

        const matchQ = !q || rowText.includes(q);
        const matchS = st === 'all' || rowStatus === st;

        r.style.display = (matchQ && matchS) ? '' : 'none';
      });
    };

    if (search) search.addEventListener('input', apply);
    if (status) status.addEventListener('change', apply);

    apply();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initClampToggles();
  initTableFilter();
});
