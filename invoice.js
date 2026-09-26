(function () {
  var p = new URLSearchParams(window.location.search);
  var price = p.get('price') || '0';
  var name = p.get('name') || '';
  var project = p.get('project') || 'Разработка сайта';
  var pkg = p.get('package') || '';

  var cleanPrice = price.replace(/[^\d]/g, '');
  var formatted = cleanPrice ? parseInt(cleanPrice, 10).toLocaleString('ru-RU') + ' ₽' : '—';

  document.getElementById('item-price').textContent = formatted;
  document.getElementById('total-price').textContent = formatted;
  document.getElementById('service-name').textContent = pkg ? 'Разработка сайта · «' + pkg + '»' : project;
  document.getElementById('invoice-date').textContent = p.get('date') || new Date().toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });

  var num = p.get('num') || String(Math.floor(Math.random() * 900000) + 100000);
  document.getElementById('invoice-num').textContent = num;

  var printBtn = document.getElementById('printBtn');
  if (printBtn) {
    printBtn.addEventListener('click', function () { window.print(); });
  }
})();
