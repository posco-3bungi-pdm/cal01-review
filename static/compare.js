// LOT 나란히 비교: 고른 LOT 수만큼 열을 만들어 가로로 놓음

var params = new URLSearchParams(location.search);
var picked = (params.get('lots') || '240024,240108').split(',').filter(function (x) { return x; });
var sensor = params.get('sensor') || 'CP-Z4';
var axis = 'elapsed';
var cache = {};
var charts = [];

document.getElementById('sensor').value = sensor;

function getSeries(lot) {
  if (cache[lot]) return Promise.resolve(cache[lot]);
  return fetch('/api/series?lot=' + encodeURIComponent(lot))
    .then(function (r) { return r.json(); })
    .then(function (data) { cache[lot] = data; return data; });
}

function saveUrl() {
  history.replaceState(null, '', '?lots=' + picked.join(',') + '&sensor=' + encodeURIComponent(sensor));
}

function drawChips() {
  document.querySelectorAll('#lot-chips .chip').forEach(function (b) {
    var on = picked.indexOf(b.dataset.lot) >= 0;
    b.classList.toggle('on', on);
    b.setAttribute('aria-pressed', String(on));
  });
  document.getElementById('count').textContent = '선택 ' + picked.length + '개 · 고른 만큼 열이 생겨요';
}

function draw() {
  drawChips();
  saveUrl();
  charts.forEach(function (c) { c.destroy(); });
  charts = [];
  var box = document.getElementById('columns');
  box.innerHTML = '';
  box.style.gridTemplateColumns = 'repeat(' + Math.max(picked.length, 1) + ', minmax(0, 1fr))';
  if (!picked.length) {
    box.textContent = '위에서 LOT을 골라 주세요.';
    return;
  }

  Promise.all(picked.map(getSeries)).then(function (list) {
    // 모든 열이 같은 세로 눈금을 쓰도록 최솟값, 최댓값을 함께 구함
    var low = Infinity;
    var high = -Infinity;
    list.forEach(function (s) {
      (s.sensors[sensor] || []).forEach(function (v) {
        if (v === null) return;
        low = Math.min(low, v);
        high = Math.max(high, v);
      });
    });
    var pad = (high - low) * 0.05 || 1;

    list.forEach(function (s) {
      var values = s.sensors[sensor] || [];
      var stat = s.stats[sensor];
      var labels = [];
      s.time.forEach(function (t, i) { labels.push(axis === 'elapsed' ? i + '분' : t.slice(5, 16)); });

      var usable = values.filter(function (v) { return v !== null; });
      var max = usable.length ? Math.max.apply(null, usable) : null;
      var min = usable.length ? Math.min.apply(null, usable) : null;

      var col = document.createElement('article');
      col.className = 'card column';

      var head = document.createElement('div');
      head.className = 'row-between';
      var title = document.createElement('div');
      title.innerHTML = '<strong></strong><br><span class="muted small"></span>';
      title.querySelector('strong').textContent = s.lot;
      title.querySelector('span').textContent = s.grade + ' · ' + s.start.slice(5, 10) + ' · ' + s.time.length + '분';
      var remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'icon-btn small';
      remove.setAttribute('aria-label', 'LOT ' + s.lot + ' 비교에서 빼기');
      remove.textContent = '×';
      remove.addEventListener('click', function () {
        picked = picked.filter(function (p) { return p !== s.lot; });
        draw();
      });
      head.appendChild(title);
      head.appendChild(remove);

      var holder = document.createElement('div');
      holder.className = 'chart-holder tall';
      var canvas = document.createElement('canvas');
      canvas.setAttribute('role', 'img');
      canvas.setAttribute('aria-label', 'LOT ' + s.lot + ' ' + sensor + ' 그래프');
      holder.appendChild(canvas);

      var nums = document.createElement('div');
      nums.className = 'nums';
      [['중앙값', stat ? stat.median : null], ['최고', max], ['최저', min]].forEach(function (pair) {
        var cell = document.createElement('div');
        cell.className = 'soft-box';
        var name = document.createElement('span');
        name.className = 'muted small';
        name.textContent = pair[0];
        var value = document.createElement('strong');
        value.textContent = pair[1] === null ? '-' : pair[1].toFixed(3);
        if (stat && pair[1] !== null && pair[0] !== '중앙값' &&
            (pair[1] > stat.mean + 3 * stat.std || pair[1] < stat.mean - 3 * stat.std)) {
          value.className = 'red';
        }
        cell.appendChild(name);
        cell.appendChild(value);
        nums.appendChild(cell);
      });

      col.appendChild(head);
      col.appendChild(holder);
      col.appendChild(nums);
      box.appendChild(col);

      var band = stat ? { low: stat.mean - 3 * stat.std, high: stat.mean + 3 * stat.std } : null;
      charts.push(lineChart(canvas, labels, values, band, [], { min: low - pad, max: high + pad }));
    });
  });
}

// ---------------------------------------------------------------- 버튼
document.querySelectorAll('#lot-chips .chip').forEach(function (b) {
  b.addEventListener('click', function () {
    var at = picked.indexOf(b.dataset.lot);
    if (at >= 0) picked.splice(at, 1);
    else picked.push(b.dataset.lot);
    draw();
  });
});

var grades = [];
document.querySelectorAll('#lot-chips .chip').forEach(function (b) {
  if (grades.indexOf(b.dataset.grade) < 0) grades.push(b.dataset.grade);
});
grades.forEach(function (grade) {
  var count = document.querySelectorAll('#lot-chips .chip[data-grade="' + grade + '"]').length;
  if (count < 2) return;
  var b = document.createElement('button');
  b.type = 'button';
  b.className = 'pill small';
  b.textContent = grade + ' 모두';
  b.addEventListener('click', function () {
    picked = [];
    document.querySelectorAll('#lot-chips .chip[data-grade="' + grade + '"]').forEach(function (c) { picked.push(c.dataset.lot); });
    draw();
  });
  document.getElementById('grade-buttons').appendChild(b);
});

document.getElementById('sensor').addEventListener('change', function (e) {
  sensor = e.target.value;
  draw();
});
document.querySelectorAll('[data-axis]').forEach(function (b) {
  b.addEventListener('click', function () {
    axis = b.dataset.axis;
    document.querySelectorAll('[data-axis]').forEach(function (x) { x.classList.toggle('on', x === b); });
    draw();
  });
});
document.addEventListener('themechange', draw);

draw();
