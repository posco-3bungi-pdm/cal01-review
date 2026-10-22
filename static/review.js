// 검토 화면: 채널 그래프, 작업 기록, 판단 메모

var state = {
  series: null,
  channels: ['TC-Z3', 'TC-Z4', 'OP-Z4', 'CP-Z4'],
  showBand: true,
  candidate: null,
  charts: []
};

// ---------------------------------------------------------------- 시각 계산
function toMinute(text) {
  return text.slice(0, 16) + ':00';
}
function indexRange(start, end) {
  var times = state.series.time;
  var from = -1;
  var to = -1;
  for (var i = 0; i < times.length; i++) {
    if (from < 0 && times[i] >= toMinute(start)) from = i;
    if (times[i] <= end) to = i;
  }
  if (from < 0 || to < from) return null;
  return { from: from, to: to };
}

// ---------------------------------------------------------------- 채널 버튼
function drawChips() {
  var box = document.getElementById('channel-chips');
  box.innerHTML = '';
  Object.keys(state.series.sensors).forEach(function (name) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip' + (state.channels.indexOf(name) >= 0 ? ' on' : '');
    b.textContent = name;
    b.setAttribute('aria-pressed', String(state.channels.indexOf(name) >= 0));
    b.addEventListener('click', function () {
      var at = state.channels.indexOf(name);
      if (at >= 0) state.channels.splice(at, 1);
      else state.channels.push(name);
      drawChips();
      drawCharts();
    });
    box.appendChild(b);
  });
}

// ---------------------------------------------------------------- 그래프
function drawCharts() {
  state.charts.forEach(function (c) { c.destroy(); });
  state.charts = [];
  var box = document.getElementById('charts');
  box.innerHTML = '';

  var labels = [];
  state.series.time.forEach(function (t) { labels.push(t.slice(5, 16)); });

  // 제외 구간(회색)과 고른 후보(노란색) 표시
  var marks = [];
  var from = -1;
  state.series.excluded.forEach(function (ex, i) {
    if (ex && from < 0) from = i;
    if ((!ex || i === state.series.excluded.length - 1) && from >= 0) {
      marks.push({ from: from, to: ex ? i : i - 1, color: cssVar('--exclude') });
      from = -1;
    }
  });
  if (state.candidate) {
    var r = indexRange(state.candidate.start, state.candidate.end);
    if (r) marks.push({ from: r.from, to: r.to, color: cssVar('--pick') });
  }

  state.channels.forEach(function (name) {
    var values = state.series.sensors[name];
    if (!values) return;
    var stat = state.series.stats[name];
    var band = null;
    if (state.showBand && stat) band = { low: stat.mean - 3 * stat.std, high: stat.mean + 3 * stat.std };

    var wrap = document.createElement('div');
    wrap.className = 'chart-box';
    var head = document.createElement('div');
    head.className = 'chart-head';
    head.textContent = name + (stat ? '  ·  평균 ' + stat.mean.toFixed(3) + ', 표준편차 ' + stat.std.toFixed(3) : '');
    var holder = document.createElement('div');
    holder.className = 'chart-holder';
    var canvas = document.createElement('canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', name + ' 1분 평균 그래프');
    holder.appendChild(canvas);
    wrap.appendChild(head);
    wrap.appendChild(holder);
    box.appendChild(wrap);
    state.charts.push(lineChart(canvas, labels, values, band, marks));
  });
}

// ---------------------------------------------------------------- 작업 기록 (그래프 아래 막대)
function drawTimeline() {
  var s = state.series;
  fetch('/api/work-records?start=' + encodeURIComponent(s.start) + '&end=' + encodeURIComponent(s.end))
    .then(function (r) { return r.json(); })
    .then(function (rows) {
      var box = document.getElementById('timeline');
      box.innerHTML = '';
      var t0 = new Date(s.start.replace(' ', 'T')).getTime();
      var t1 = new Date(s.end.replace(' ', 'T')).getTime();
      var kinds = ['조업', '정기수리', '정비 감지', '정비 작업'];

      kinds.forEach(function (kind) {
        var name = document.createElement('span');
        name.className = 'muted small';
        name.textContent = kind;
        var track = document.createElement('div');
        track.className = 'track';
        rows.forEach(function (r) {
          if (r.kind !== kind) return;
          var a = new Date(r.start_at.replace(' ', 'T')).getTime();
          var b = new Date(r.end_at.replace(' ', 'T')).getTime();
          var left = Math.max(0, (a - t0) / (t1 - t0) * 100);
          var right = Math.min(100, (b - t0) / (t1 - t0) * 100);
          var mark = document.createElement('span');
          mark.className = 'mark k-' + kinds.indexOf(kind);
          mark.style.left = left + '%';
          mark.style.width = Math.max(right - left, 0.8) + '%';
          mark.title = r.start_at.slice(5, 16) + ' · ' + r.title + (r.detail ? '\n' + r.detail : '');
          track.appendChild(mark);
        });
        box.appendChild(name);
        box.appendChild(track);
      });
    });
}

function loadSeries() {
  return fetch('/api/series?lot=' + encodeURIComponent(window.PAGE.lot))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      state.series = data;
      document.getElementById('lot-info').textContent =
        'LOT ' + data.lot + ' · ' + data.grade + ' · ' + data.start.slice(5, 16) + ' ~ ' + data.end.slice(5, 16);
      drawChips();
      drawCharts();
      drawTimeline();
    });
}

document.getElementById('z-toggle').addEventListener('change', function (e) {
  state.showBand = e.target.checked;
  drawCharts();
});
document.addEventListener('themechange', function () { if (state.series) drawCharts(); });

// ---------------------------------------------------------------- 후보 고르기, 고정
document.querySelectorAll('.cand-open').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.cand.selected').forEach(function (el) { el.classList.remove('selected'); });
    btn.parentElement.classList.add('selected');
    state.candidate = { id: btn.dataset.id, sensor: btn.dataset.sensor, start: btn.dataset.start, end: btn.dataset.end };
    if (state.channels.indexOf(btn.dataset.sensor) < 0) state.channels.unshift(btn.dataset.sensor);
    drawChips();
    drawCharts();
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
  if (!c.comments.length) comments.textContent = '아직 의견이 없어요.';

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
    showToast('왼쪽에서 후보를 먼저 골라 주세요.');
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
    showToast('판단을 저장했어요', '다른 팀원에게 알림이 가요');
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

// ---------------------------------------------------------------- 구간 스냅샷 (보이는 그래프를 그림 한 장으로 저장)
var snapBackdrop = document.getElementById('snap-backdrop');

function snapRange() {
  if (state.candidate) return { start: state.candidate.start, end: state.candidate.end };
  return { start: state.series.start, end: state.series.end };
}

document.getElementById('snap-open').addEventListener('click', function () {
  var r = snapRange();
  document.getElementById('snap-sub').textContent =
    'LOT ' + state.series.lot + ' · ' + state.channels.join(', ') + ' · ' + r.start.slice(5, 16) + ' ~ ' + r.end.slice(5, 16);
  document.getElementById('snap-name').value = state.series.lot.slice(3) + ' · ' + (state.candidate ? state.candidate.sensor : state.channels[0]);
  snapBackdrop.hidden = false;
});
document.getElementById('snap-cancel').addEventListener('click', function () { snapBackdrop.hidden = true; });

document.getElementById('snap-save').addEventListener('click', function () {
  var canvases = document.querySelectorAll('#charts canvas');
  var width = 0;
  var height = 0;
  canvases.forEach(function (c) { width = Math.max(width, c.width); height += c.height; });
  var out = document.createElement('canvas');
  out.width = width || 10;
  out.height = height || 10;
  var ctx = out.getContext('2d');
  ctx.fillStyle = cssVar('--surface');
  ctx.fillRect(0, 0, out.width, out.height);
  var y = 0;
  canvases.forEach(function (c) { ctx.drawImage(c, 0, y); y += c.height; });

  var r = snapRange();
  postJSON('/api/snapshots', {
    title: document.getElementById('snap-name').value,
    note: document.getElementById('snap-note').value,
    lot: state.series.lot,
    sensor: state.candidate ? state.candidate.sensor : state.channels[0],
    channels: state.channels,
    start: r.start,
    end: r.end,
    image: out.toDataURL('image/png')
  }).then(function () {
    snapBackdrop.hidden = true;
    document.getElementById('snap-note').value = '';
    showToast('구간을 공유했어요', '팀원 기록에서 볼 수 있어요');
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
