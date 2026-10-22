// 검토 화면: 시간창(LOT 전체 → 끌어서 확대), 채널 그래프, 정비 기록 줄, 판단 메모

var state = {
  series: null,      // LOT 전체 1분 평균 (위쪽 작은 띠)
  seriesX: [],       // 위 시각들을 숫자(ms)로
  channels: ['TC-Z3', 'TC-Z4', 'OP-Z4', 'CP-Z4'],
  showBand: true,
  candidate: null,
  view: null,        // 지금 보는 시간창 {start, end} (ms)
  win: null,         // 시간창 값 (/api/window)
  records: [],       // 시간창의 정비, 조업 기록
  hover: null,       // 세로선 시각 (ms)
  drag: null,        // 끌고 있는 구간 {a, b, chart}
  charts: [],
  mini: null,
  lanes: null
};

// ---------------------------------------------------------------- 시각 바꾸기 ('2024-07-07 18:40:00' ↔ ms)
function toMs(text) {
  return new Date(text.replace(' ', 'T')).getTime();
}
function two(n) {
  return (n < 10 ? '0' : '') + n;
}
function toText(ms) {
  var d = new Date(ms);
  return d.getFullYear() + '-' + two(d.getMonth() + 1) + '-' + two(d.getDate()) + ' ' +
    two(d.getHours()) + ':' + two(d.getMinutes()) + ':' + two(d.getSeconds());
}
function spanText(ms) {
  var min = Math.round(ms / 60000);
  if (min < 60) return min + '분';
  return Math.floor(min / 60) + '시간' + (min % 60 ? ' ' + (min % 60) + '분' : '');
}
// x축 글자: 2시간 이하면 시:분:초, 길면 월-일 시:분
function tickText(value) {
  var t = toText(value);
  if (state.view && state.view.end - state.view.start <= 2 * 3600000) return t.slice(11, 19);
  return t.slice(5, 16);
}

// ---------------------------------------------------------------- 채널 버튼 (TC, OP, CP끼리 한 줄씩 묶음)
var CHANNEL_GROUPS = [
  { key: 'tc', name: 'TC', prefix: 'TC-' },
  { key: 'op', name: 'OP', prefix: 'OP-' },
  { key: 'cp', name: 'CP', prefix: 'CP-' },
  { key: 'etc', name: '기타', prefix: '' }
];

// Z1, Z2, ... Z9 다음에 OUT1, OUT2 순서
function channelOrder(name) {
  var m = name.match(/Z(\d+)/);
  if (m) return Number(m[1]);
  m = name.match(/OUT(\d+)/);
  if (m) return 100 + Number(m[1]);
  return 200;
}

function drawChips() {
  var box = document.getElementById('channel-chips');
  box.innerHTML = '';
  var left = Object.keys(state.series.sensors);

  CHANNEL_GROUPS.forEach(function (group) {
    var names = [];
    var rest = [];
    left.forEach(function (name) {
      if (name.indexOf(group.prefix) === 0) names.push(name);
      else rest.push(name);
    });
    left = rest;
    if (!names.length) return;
    names.sort(function (a, b) { return channelOrder(a) - channelOrder(b); });

    var row = document.createElement('div');
    row.className = 'ch-group g-' + group.key;
    var label = document.createElement('span');
    label.className = 'ch-label';
    label.textContent = group.name;
    var chips = document.createElement('div');
    chips.className = 'ch-chips';

    names.forEach(function (name) {
      var on = state.channels.indexOf(name) >= 0;
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip' + (on ? ' on' : '');
      // 묶음 이름(TC-)은 줄 앞에 있으니 칩에는 뒷부분만
      b.textContent = group.prefix ? name.slice(group.prefix.length) : name;
      b.setAttribute('aria-label', name);
      b.setAttribute('aria-pressed', String(on));
      b.addEventListener('click', function () {
        var at = state.channels.indexOf(name);
        if (at >= 0) state.channels.splice(at, 1);
        else state.channels.push(name);
        drawChips();
        loadWindow();
      });
      chips.appendChild(b);
    });

    row.appendChild(label);
    row.appendChild(chips);
    box.appendChild(row);
  });
}

// ---------------------------------------------------------------- 그래프 공통: 세로선, 끌기, 왼쪽 눈금 폭
var Y_WIDTH = 64;  // 모든 그래프와 정비 줄의 왼쪽 눈금 폭을 같게 해서 세로선이 한 줄로 맞음

function fixedYWidth(scale) {
  scale.width = Y_WIDTH;
}

var crossPlugin = {
  id: 'cross',
  afterDatasetsDraw: function (chart) {
    var area = chart.chartArea;
    var x = chart.scales.x;
    var ctx = chart.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.rect(area.left, area.top, area.right - area.left, area.bottom - area.top);
    ctx.clip();
    // 끌고 있는 구간
    if (state.drag) {
      var a = x.getPixelForValue(Math.min(state.drag.a, state.drag.b));
      var b = x.getPixelForValue(Math.max(state.drag.a, state.drag.b));
      ctx.fillStyle = cssVar('--accent-glow');
      ctx.fillRect(a, area.top, b - a, area.bottom - area.top);
    }
    // 같은 시각 세로선
    if (state.hover !== null && state.hover >= x.min && state.hover <= x.max) {
      var px = x.getPixelForValue(state.hover);
      ctx.strokeStyle = cssVar('--accent');
      ctx.lineWidth = 1.3;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(px, area.top);
      ctx.lineTo(px, area.bottom);
      ctx.stroke();
    }
    ctx.restore();
  }
};

var redrawWaiting = false;
function redrawSoon() {
  if (redrawWaiting) return;
  redrawWaiting = true;
  requestAnimationFrame(function () {
    redrawWaiting = false;
    state.charts.forEach(function (c) { c.draw(); });
    if (state.mini) state.mini.draw();
    if (state.lanes) state.lanes.draw();
  });
}

// 마우스: 올리면 세로선, 가로로 끌면 그 구간 확대
function watchChart(chart) {
  var canvas = chart.canvas;
  function msAt(e) {
    var r = canvas.getBoundingClientRect();
    var px = Math.max(chart.chartArea.left, Math.min(chart.chartArea.right, e.clientX - r.left));
    return chart.scales.x.getValueForPixel(px);
  }
  canvas.addEventListener('mousedown', function (e) {
    e.preventDefault();
    var t = msAt(e);
    state.drag = { a: t, b: t, chart: chart };
  });
  canvas.addEventListener('mousemove', function (e) {
    state.hover = msAt(e);
    if (state.drag) state.drag.b = state.hover;
    redrawSoon();
  });
  canvas.addEventListener('mouseleave', function () {
    state.hover = null;
    redrawSoon();
  });
}
window.addEventListener('mouseup', function (e) {
  if (!state.drag) return;
  // 손을 뗀 자리까지를 끝으로 (중간 움직임이 없었어도)
  var chart = state.drag.chart;
  var r = chart.canvas.getBoundingClientRect();
  var px = Math.max(chart.chartArea.left, Math.min(chart.chartArea.right, e.clientX - r.left));
  state.drag.b = chart.scales.x.getValueForPixel(px);
  var a = Math.min(state.drag.a, state.drag.b);
  var b = Math.max(state.drag.a, state.drag.b);
  var x = chart.scales.x;
  state.drag = null;
  if (x.getPixelForValue(b) - x.getPixelForValue(a) >= 8) setView(a, b);
  else redrawSoon();
});

function timeAxis(min, max) {
  return {
    type: 'linear', min: min, max: max,
    grid: { color: cssVar('--grid') },
    ticks: { color: cssVar('--muted'), maxTicksLimit: 8, maxRotation: 0, callback: tickText }
  };
}

// 시각(ms)과 값으로 선 그래프 하나
function timeChart(canvas, points, band, marks) {
  var red = cssVar('--red');
  var line = cssVar('--line');
  function outside(v) {
    return band && v !== null && v !== undefined && (v > band.high || v < band.low);
  }
  var datasets = [{
    data: points,
    borderColor: line,
    borderWidth: 1.4,
    pointRadius: 0,
    spanGaps: false,
    segment: {
      borderColor: function (c) { return outside(c.p0.parsed.y) || outside(c.p1.parsed.y) ? red : line; },
      borderWidth: function (c) { return outside(c.p0.parsed.y) || outside(c.p1.parsed.y) ? 2.4 : 1.4; }
    }
  }];
  if (band) {
    datasets.push({ data: [{ x: state.view.start, y: band.high }, { x: state.view.end, y: band.high }], borderColor: red, borderDash: [6, 5], borderWidth: 1.2, pointRadius: 0 });
    datasets.push({ data: [{ x: state.view.start, y: band.low }, { x: state.view.end, y: band.low }], borderColor: red, borderDash: [6, 5], borderWidth: 1.2, pointRadius: 0 });
  }
  var chart = new Chart(canvas, {
    type: 'line',
    data: { datasets: datasets },
    plugins: [shadePlugin, crossPlugin],
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      parsing: false,
      normalized: true,
      interaction: { mode: 'nearest', axis: 'x', intersect: false },
      plugins: {
        legend: { display: false },
        shade: { marks: marks },
        tooltip: {
          filter: function (item) { return item.datasetIndex === 0; },
          callbacks: { title: function (items) { return toText(items[0].parsed.x).slice(5); } }
        }
      },
      scales: {
        x: timeAxis(state.view.start, state.view.end),
        y: { afterFit: fixedYWidth, grid: { color: cssVar('--grid') }, ticks: { color: cssVar('--muted'), maxTicksLimit: 5 } }
      }
    }
  });
  watchChart(chart);
  return chart;
}

// ---------------------------------------------------------------- 시간창 정하기, 불러오기
function setView(a, b) {
  var first = state.seriesX[0];
  var last = state.seriesX[state.seriesX.length - 1];
  a = Math.max(first, Math.round(a / 1000) * 1000);
  b = Math.min(last, Math.round(b / 1000) * 1000);
  if (b - a < 60000) {
    // 최소 1분
    var c = (a + b) / 2;
    a = Math.max(first, c - 30000);
    b = Math.min(last, a + 60000);
  }
  state.view = { start: a, end: b };
  loadWindow();
}

var loadCount = 0;
function loadWindow() {
  loadCount = loadCount + 1;
  var mine = loadCount;
  var start = toText(state.view.start);
  var end = toText(state.view.end);
  document.getElementById('win-info').textContent = start.slice(5) + ' ~ ' + end.slice(5) + ' · 불러오는 중';
  var q = '/api/window?lot=' + encodeURIComponent(window.PAGE.lot) + '&start=' + encodeURIComponent(start) +
    '&end=' + encodeURIComponent(end) + '&channels=' + encodeURIComponent(state.channels.join(','));
  var w = '/api/work-records?start=' + encodeURIComponent(start) + '&end=' + encodeURIComponent(end);
  Promise.all([
    fetch(q).then(function (r) { return r.json(); }),
    fetch(w).then(function (r) { return r.json(); })
  ]).then(function (res) {
    if (mine !== loadCount) return;  // 더 나중에 누른 요청만 그림
    state.win = res[0];
    state.records = res[1];
    drawWindow();
  });
}

// 제외 구간(회색)과 고른 후보(노란색) 칠하기
function windowMarks(xs) {
  var marks = [];
  var step = state.win.mode === 'raw' ? 1000 : 60000;
  var from = -1;
  state.win.excluded.forEach(function (ex, i) {
    if (ex && from < 0) from = i;
    var last = i === state.win.excluded.length - 1;
    if ((!ex || last) && from >= 0) {
      var to = ex ? i : i - 1;
      marks.push({ from: xs[from], to: xs[to] + step, color: cssVar('--exclude') });
      from = -1;
    }
  });
  if (state.candidate) {
    marks.push({ from: toMs(state.candidate.start), to: toMs(state.candidate.end), color: cssVar('--pick') });
  }
  return marks;
}

function drawWindow() {
  var win = state.win;
  var xs = [];
  win.time.forEach(function (t) { xs.push(toMs(t)); });

  document.getElementById('win-info').textContent =
    toText(state.view.start).slice(5) + ' ~ ' + toText(state.view.end).slice(5) + ' · ' + spanText(state.view.end - state.view.start);
  var mode = document.getElementById('win-mode');
  mode.textContent = win.mode === 'raw' ? '1초 원본' : '1분 평균';
  mode.classList.toggle('raw', win.mode === 'raw');

  state.charts.forEach(function (c) { c.destroy(); });
  state.charts = [];
  var box = document.getElementById('charts');
  box.innerHTML = '';
  var marks = windowMarks(xs);

  state.channels.forEach(function (name) {
    var values = win.sensors[name];
    if (!values) return;
    var stat = win.stats[name];
    var band = null;
    if (state.showBand && stat) band = { low: stat.mean - 3 * stat.std, high: stat.mean + 3 * stat.std };
    var points = [];
    for (var i = 0; i < xs.length; i++) points.push({ x: xs[i], y: values[i] });

    var wrap = document.createElement('div');
    wrap.className = 'chart-box';
    var head = document.createElement('div');
    head.className = 'chart-head';
    head.textContent = name + (stat ? '  ·  평균 ' + stat.mean.toFixed(3) + ', 표준편차 ' + stat.std.toFixed(3) : '');
    var holder = document.createElement('div');
    holder.className = 'chart-holder';
    var canvas = document.createElement('canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', name + ' 그래프');
    holder.appendChild(canvas);
    wrap.appendChild(head);
    wrap.appendChild(holder);
    box.appendChild(wrap);
    state.charts.push(timeChart(canvas, points, band, marks));
  });

  drawLanes();
  drawMini();
}

// ---------------------------------------------------------------- 위쪽 작은 띠: LOT 전체에서 지금 시간창 위치
function drawMini() {
  if (state.mini) state.mini.destroy();
  var name = state.channels[0] || 'CP-Z4';
  document.getElementById('mini-name').textContent = name;
  var values = state.series.sensors[name] || [];
  var points = [];
  for (var i = 0; i < state.seriesX.length; i++) points.push({ x: state.seriesX[i], y: values[i] });

  state.mini = new Chart(document.getElementById('mini'), {
    type: 'line',
    data: { datasets: [{ data: points, borderColor: cssVar('--muted'), borderWidth: 1, pointRadius: 0 }] },
    plugins: [shadePlugin, crossPlugin],
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      parsing: false,
      normalized: true,
      events: [],
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
        shade: { marks: [{ from: state.view.start, to: state.view.end, color: cssVar('--pick') }] }
      },
      scales: {
        x: { type: 'linear', min: state.seriesX[0], max: state.seriesX[state.seriesX.length - 1], display: false },
        y: { afterFit: fixedYWidth, ticks: { display: false }, grid: { display: false }, border: { display: false } }
      }
    }
  });
  watchChart(state.mini);
}

// ---------------------------------------------------------------- 정비, 조업 기록 줄 (그래프와 같은 시간축)
var LANES = ['BM', 'TBM', 'CBM', '조업', '정기수리'];
var LANE_COLORS = { 'BM': '#C2261F', 'TBM': '#2347D6', 'CBM': '#0F8A6A', '조업': '#6B7280', '정기수리': '#7C3AED' };

function laneOf(r) {
  if (r.kind === '조업' || r.kind === '정기수리') return r.kind;
  var type = r.title.split(' · ')[0];
  return LANES.indexOf(type) >= 0 ? type : 'BM';
}

function drawLanes() {
  if (state.lanes) state.lanes.destroy();
  var datasets = [];
  var count = 0;
  LANES.forEach(function (lane) {
    var bars = [];
    var dots = [];
    state.records.forEach(function (r) {
      if (laneOf(r) !== lane) return;
      count = count + 1;
      var a = toMs(r.start_at);
      var b = toMs(r.end_at);
      if (r.kind === '정비 작업' || r.kind === '정기수리') bars.push({ x: [a, Math.max(b, a + 60000)], y: lane, rec: r });
      else dots.push({ x: a, y: lane, rec: r });
    });
    datasets.push({ type: 'bar', data: bars, backgroundColor: LANE_COLORS[lane] + 'CC', borderColor: LANE_COLORS[lane], borderWidth: 1, borderRadius: 4, barThickness: 12, minBarLength: 5 });
    datasets.push({ type: 'scatter', data: dots, backgroundColor: LANE_COLORS[lane], borderColor: '#FFFFFF', borderWidth: 1.2, pointRadius: 7, pointHoverRadius: 9, pointStyle: lane === '조업' ? 'rectRot' : 'triangle' });
  });
  document.getElementById('lanes-note').textContent = count ? count + '건' : '· 이 시간창에 기록 없음';

  state.lanes = new Chart(document.getElementById('lanes'), {
    type: 'bar',
    data: { labels: LANES, datasets: datasets },
    plugins: [crossPlugin],
    options: {
      indexAxis: 'y',
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: function (items) { return items[0].raw.rec.title; },
            label: function (item) {
              var r = item.raw.rec;
              return r.start_at.slice(5, 16) + (r.end_at !== r.start_at ? ' ~ ' + r.end_at.slice(5, 16) : '') + (r.detail ? '  ' + r.detail : '');
            }
          }
        }
      },
      // 막대나 점을 누르면 원문을 오른쪽 아래에 띄움
      onClick: function (e, items) {
        if (!items.length) return;
        var r = state.lanes.data.datasets[items[0].datasetIndex].data[items[0].index].rec;
        showToast(r.title, r.start_at.slice(5, 16) + ' ~ ' + r.end_at.slice(5, 16) + (r.detail ? ' · ' + r.detail : ''));
      },
      scales: {
        x: timeAxis(state.view.start, state.view.end),
        y: { type: 'category', labels: LANES, afterFit: fixedYWidth, grid: { color: cssVar('--grid') }, ticks: { color: cssVar('--text'), font: { weight: '700' } } }
      }
    }
  });
  watchChart(state.lanes);
}

// ---------------------------------------------------------------- 시간창 버튼: 앞쪽, 줄이기, 늘리기, 뒤쪽, LOT 전체
function viewSpan() {
  return state.view.end - state.view.start;
}
document.getElementById('win-earlier').addEventListener('click', function () {
  setView(state.view.start - viewSpan() / 2, state.view.end);
});
document.getElementById('win-later').addEventListener('click', function () {
  setView(state.view.start, state.view.end + viewSpan() / 2);
});
document.getElementById('win-widen').addEventListener('click', function () {
  var c = (state.view.start + state.view.end) / 2;
  setView(c - viewSpan(), c + viewSpan());
});
document.getElementById('win-narrow').addEventListener('click', function () {
  var c = (state.view.start + state.view.end) / 2;
  setView(c - viewSpan() / 4, c + viewSpan() / 4);
});
document.getElementById('win-full').addEventListener('click', function () {
  setView(state.seriesX[0], state.seriesX[state.seriesX.length - 1]);
});

function loadSeries() {
  return fetch('/api/series?lot=' + encodeURIComponent(window.PAGE.lot))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      state.series = data;
      state.seriesX = [];
      data.time.forEach(function (t) { state.seriesX.push(toMs(t)); });
      document.getElementById('lot-info').textContent =
        'LOT ' + data.lot + ' · ' + data.grade + ' · ' + data.start.slice(5, 16) + ' ~ ' + data.end.slice(5, 16);
      drawChips();
      state.view = { start: state.seriesX[0], end: state.seriesX[state.seriesX.length - 1] };
      loadWindow();
    });
}

document.getElementById('z-toggle').addEventListener('click', function (e) {
  state.showBand = !state.showBand;
  e.currentTarget.classList.toggle('on', state.showBand);
  e.currentTarget.setAttribute('aria-pressed', String(state.showBand));
  if (state.win) drawWindow();
});
document.addEventListener('themechange', function () { if (state.win) drawWindow(); });

// ---------------------------------------------------------------- 후보 고르기: 후보 앞뒤를 넉넉히 확대하고 판단 메모를 엶
document.querySelectorAll('.cand-open').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.cand.selected').forEach(function (el) { el.classList.remove('selected'); });
    btn.parentElement.classList.add('selected');
    state.candidate = { id: btn.dataset.id, sensor: btn.dataset.sensor, start: btn.dataset.start, end: btn.dataset.end };
    if (state.channels.indexOf(btn.dataset.sensor) < 0) state.channels.unshift(btn.dataset.sensor);
    drawChips();
    var a = toMs(btn.dataset.start);
    var b = toMs(btn.dataset.end);
    var pad = Math.max(10 * 60000, b - a);
    setView(a - pad, b + pad);
    openSheet();
  });
});

document.querySelectorAll('.pin').forEach(function (btn) {
  btn.addEventListener('click', function () {
    postJSON('/api/candidates/' + encodeURIComponent(btn.dataset.id) + '/pin').then(function () { location.reload(); });
  });
});

// ---------------------------------------------------------------- 판단 메모 시트 (왼쪽에서 나오고, 닫으면 작아지며 들어감)
var backdrop = document.getElementById('sheet-backdrop');
var sheet = document.getElementById('sheet');

function pickSegment(id, value) {
  document.querySelectorAll('#' + id + ' button').forEach(function (b) {
    b.classList.toggle('on', b.dataset.value === value);
  });
}
function segmentValue(id) {
  var on = document.querySelector('#' + id + ' button.on');
  return on ? on.dataset.value : '';
}
['label-seg', 'training-seg'].forEach(function (id) {
  document.querySelectorAll('#' + id + ' button').forEach(function (b) {
    b.addEventListener('click', function () { pickSegment(id, b.dataset.value); });
  });
});

function labelText(v) {
  if (v === '1') return '이상 1';
  if (v === '0') return '정상 0';
  if (v === '보류') return '보류';
  return '미정';
}

function fillSheet(c) {
  document.getElementById('sheet-sub').textContent =
    c.lot_no + ' · ' + c.sensor + ' · ' + c.start_at.slice(5, 16) + ' ~ ' + c.end_at.slice(11, 16);
  var who = '판단: ' + labelText(c.label || '');
  if (c.label_by) who += ' · ' + c.label_by + (c.label_note ? ' (' + c.label_note + ')' : '');
  if (c.updated_by) who += ' · 마지막 저장 ' + c.updated_by + ' ' + (c.updated_at || '').slice(5, 16);
  document.getElementById('sheet-who').textContent = who;

  pickSegment('label-seg', c.label || '');
  pickSegment('training-seg', c.training || '미결정');
  document.getElementById('operation').value = c.operation || '미정';
  document.getElementById('memo').value = c.memo || '';
  showTab('write');

  var comments = document.getElementById('comments');
  comments.innerHTML = '';
  c.comments.forEach(function (m) {
    var div = document.createElement('div');
    div.className = 'soft-box';
    var head = document.createElement('strong');
    head.textContent = m.author + ' · ' + m.created_at.slice(5, 16);
    var body = document.createElement('div');
    body.className = 'md-body';
    body.innerHTML = renderMarkdown(m.text);
    div.appendChild(head);
    div.appendChild(body);
    comments.appendChild(div);
  });
  if (!c.comments.length) comments.textContent = '의견 없음.';

  var history = document.getElementById('history');
  history.innerHTML = '';
  c.history.forEach(function (h) {
    var div = document.createElement('div');
    div.textContent = h.created_at.slice(5, 16) + ' · ' + h.author + ' · ' + h.action + (h.label ? ' · ' + labelText(h.label) : '');
    history.appendChild(div);
  });
}

function openSheet() {
  if (!state.candidate) {
    showToast('왼쪽에서 후보 먼저 선택.');
    return;
  }
  fetch('/api/candidates/' + encodeURIComponent(state.candidate.id))
    .then(function (r) { return r.json(); })
    .then(function (c) {
      fillSheet(c);
      backdrop.hidden = false;
      sheet.classList.remove('leaving');
      // 화면 밖에 둔 자리를 브라우저가 한 번 계산하게 한 뒤 빼야 미끄러지며 나옴
      sheet.classList.add('entering');
      void sheet.offsetWidth;
      sheet.classList.remove('entering');
    });
}

function closeSheet() {
  sheet.classList.add('leaving');
  setTimeout(function () {
    backdrop.hidden = true;
    sheet.classList.remove('leaving');
  }, 430);
}

document.getElementById('memo-open').addEventListener('click', openSheet);
document.getElementById('sheet-close').addEventListener('click', closeSheet);
document.getElementById('sheet-cancel').addEventListener('click', closeSheet);
backdrop.addEventListener('click', function (e) { if (e.target === backdrop) closeSheet(); });
document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !backdrop.hidden) closeSheet(); });

function showTab(name) {
  document.querySelectorAll('#memo-tabs button').forEach(function (b) { b.classList.toggle('on', b.dataset.tab === name); });
  var preview = document.getElementById('memo-preview');
  document.getElementById('memo').hidden = name !== 'write';
  preview.hidden = name !== 'preview';
  if (name === 'preview') preview.innerHTML = renderMarkdown(document.getElementById('memo').value);
}
document.querySelectorAll('#memo-tabs button').forEach(function (b) {
  b.addEventListener('click', function () { showTab(b.dataset.tab); });
});

document.getElementById('sheet-save').addEventListener('click', function () {
  var id = state.candidate.id;
  var label = segmentValue('label-seg');
  postJSON('/api/candidates/' + encodeURIComponent(id) + '/judgment', {
    label: label,
    training: segmentValue('training-seg') || '미결정',
    operation: document.getElementById('operation').value,
    memo: document.getElementById('memo').value
  }).then(function () {
    // 왼쪽 목록의 판단 표시를 바로 바꿈
    var item = document.querySelector('.cand-open[data-id="' + CSS.escape(id) + '"]');
    var chip = item.querySelector('.label-chip');
    if (!chip && label) {
      chip = document.createElement('span');
      item.appendChild(chip);
    }
    if (chip) {
      if (label) {
        chip.className = 'label-chip l' + label;
        chip.textContent = labelText(label);
      } else {
        chip.remove();
      }
    }
    closeSheet();
    showToast('판단 저장됨', '팀원에게 알림 감');
  }).catch(function (err) { showToast(err.message); });
});

document.getElementById('comment-add').addEventListener('click', function () {
  var input = document.getElementById('comment-text');
  if (!input.value.trim()) return;
  postJSON('/api/candidates/' + encodeURIComponent(state.candidate.id) + '/comments', { text: input.value })
    .then(function () {
      input.value = '';
      return fetch('/api/candidates/' + encodeURIComponent(state.candidate.id)).then(function (r) { return r.json(); });
    })
    .then(function (c) { fillSheet(c); });
});

// ---------------------------------------------------------------- 구간 스냅샷 (지금 시간창의 그래프와 정비 기록 줄을 그림 한 장으로)
var snapBackdrop = document.getElementById('snap-backdrop');

function snapTitleLines() {
  var s = state.series;
  return [
    'LOT ' + s.lot + ' · ' + s.grade,
    toText(state.view.start).slice(5) + ' ~ ' + toText(state.view.end).slice(5) + ' · ' + spanText(viewSpan()) + ' · ' + (state.win.mode === 'raw' ? '1초 원본' : '1분 평균'),
    state.channels.join(', ')
  ];
}

document.getElementById('snap-open').addEventListener('click', function () {
  if (!state.win) return;
  document.getElementById('snap-sub').textContent = snapTitleLines().join(' · ');
  document.getElementById('snap-name').value = state.series.lot.slice(3) + ' · ' + (state.candidate ? state.candidate.sensor : state.channels[0]) +
    ' | ' + toText(state.view.start).slice(11, 16) + '~' + toText(state.view.end).slice(11, 16);
  snapBackdrop.hidden = false;
});
document.getElementById('snap-cancel').addEventListener('click', function () { snapBackdrop.hidden = true; });

document.getElementById('snap-save').addEventListener('click', function () {
  var canvases = [];
  document.querySelectorAll('#charts canvas').forEach(function (c) { canvases.push(c); });
  canvases.push(document.getElementById('lanes'));
  var scale = canvases[0] ? canvases[0].width / canvases[0].clientWidth : 1;
  var top = Math.round(96 * scale);
  var labelRow = Math.round(24 * scale);  // 그래프마다 위에 채널 이름 한 줄
  var width = 0;
  var height = top;
  canvases.forEach(function (c) { width = Math.max(width, c.width); height += labelRow + c.height; });

  var out = document.createElement('canvas');
  out.width = width || 10;
  out.height = height;
  var ctx = out.getContext('2d');
  ctx.fillStyle = cssVar('--surface');
  ctx.fillRect(0, 0, out.width, out.height);
  // 위쪽에 LOT, 시간창, 채널을 적음
  var lines = snapTitleLines();
  ctx.fillStyle = cssVar('--text');
  ctx.font = '700 ' + Math.round(20 * scale) + 'px "Noto Sans KR", sans-serif';
  ctx.fillText(lines[0], 16 * scale, 32 * scale);
  ctx.fillStyle = cssVar('--muted');
  ctx.font = Math.round(14 * scale) + 'px "Noto Sans KR", sans-serif';
  ctx.fillText(lines[1], 16 * scale, 58 * scale);
  ctx.fillText(lines[2], 16 * scale, 80 * scale);
  var y = top;
  ctx.font = '700 ' + Math.round(13 * scale) + 'px "Noto Sans KR", sans-serif';
  canvases.forEach(function (c) {
    var box = c.closest('.chart-box, .lanes-box');
    ctx.fillStyle = cssVar('--text');
    ctx.fillText(box ? box.querySelector('.chart-head').textContent : '', 16 * scale, y + 17 * scale);
    y += labelRow;
    ctx.drawImage(c, 0, y);
    y += c.height;
  });

  postJSON('/api/snapshots', {
    title: document.getElementById('snap-name').value,
    note: document.getElementById('snap-note').value,
    lot: state.series.lot,
    sensor: state.candidate ? state.candidate.sensor : state.channels[0],
    channels: state.channels,
    start: toText(state.view.start),
    end: toText(state.view.end),
    image: out.toDataURL('image/png')
  }).then(function () {
    snapBackdrop.hidden = true;
    document.getElementById('snap-note').value = '';
    showToast('구간 공유됨', '팀원 기록에 올라감');
  }).catch(function (err) { showToast(err.message); });
});

// ---------------------------------------------------------------- 시작
loadSeries().then(function () {
  // 알림에서 넘어온 경우 (#후보번호) 그 후보를 바로 엶
  if (location.hash.length > 1) {
    var btn = document.querySelector('.cand-open[data-id="' + CSS.escape(location.hash.slice(1)) + '"]');
    if (btn) btn.click();
  }
});
