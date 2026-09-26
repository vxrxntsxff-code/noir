(function () {
  var p = new URLSearchParams(window.location.search);
  var map = {
    'supp-project': p.get('project'),
    'supp-duration': p.get('duration'),
    'supp-date': p.get('date'),
    'supp-client': p.get('name'),
    'supp-phone': p.get('phone'),
    'supp-tg': p.get('tg'),
    'supp-email': p.get('email')
  };
  for (var id in map) {
    if (Object.prototype.hasOwnProperty.call(map, id)) {
      var el = document.getElementById(id);
      var val = map[id];
      if (el && val) el.textContent = val;
    }
  }

  var printBtn = document.getElementById('printBtn');
  if (printBtn) {
    printBtn.addEventListener('click', function () { window.print(); });
  }

  function repaint() {
    var d = document.documentElement;
    d.style.opacity = '0.999';
    requestAnimationFrame(function () { d.style.opacity = ''; });
  }
  window.addEventListener('pageshow', repaint);
  window.addEventListener('load', repaint);
  var once = function () { repaint(); window.removeEventListener('scroll', once); };
  window.addEventListener('scroll', once, { passive: true });
})();
