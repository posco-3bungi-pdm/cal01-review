// 모든 화면이 같이 쓰는 기능: 밝기, 마크다운, 알림, 그래프

// ---------------------------------------------------------------- 밝기 (라이트, 다크)
function setTheme(name) {
  document.documentElement.dataset.theme = name;
  try { localStorage.setItem('theme', name); } catch (e) {}
  document.querySelectorAll('[data-theme-set]').forEach(function (b) {
    b.classList.toggle('on', b.dataset.themeSet === name);
  });
  document.dispatchEvent(new Event('themechange'));
}
document.querySelectorAll('[data-theme-set]').forEach(function (b) {
  b.addEventListener('click', function () { setTheme(b.dataset.themeSet); });
});
setTheme(document.documentElement.dataset.theme || 'light');

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ---------------------------------------------------------------- 마크다운 (줄바꿈은 그대로 살림)
function renderMarkdown(text) {
  // "08:00~09:02"처럼 물결 하나는 취소선이 아니라 글자로 보이게 함 (~~두 개~~만 취소선)
  var safe = (text || '').replace(/(^|[^~\\])~(?!~)/g, '$1\\~');
  var html = marked.parse(safe, { breaks: true, gfm: true });
  return DOMPurify.sanitize(html);
}
function renderAllMarkdown(root) {
  (root || document).querySelectorAll('[data-md]').forEach(function (el) {
    el.innerHTML = renderMarkdown(el.dataset.md);
  });
}
renderAllMarkdown();

// ---------------------------------------------------------------- 서버 요청
function postJSON(url, data) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {})
  }).then(function (r) {
    if (!r.ok) throw new Error('저장하지 못했어요 (' + r.status + ')');
    return r.json();
  });
}

// ---------------------------------------------------------------- 오른쪽 아래 작은 알림
function showToast(text, sub) {
  var box = document.getElementById('toast');
  box.innerHTML = '';
  var strong = document.createElement('strong');
  strong.textContent = text;
  box.appendChild(strong);
  if (sub) {
    var span = document.createElement('span');
    span.textContent = sub;
    box.appendChild(span);
  }
  box.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(function () { box.hidden = true; }, 6000);
}

// ---------------------------------------------------------------- 종 버튼 알림 (히어로를 가리지 않게 버튼 아래에만 열림)
(function () {
  var bell = document.getElementById('bell');
  if (!bell) return;
  var panel = document.getElementById('bell-panel');
  var count = document.getElementById('bell-count');
  var items = [];

  fetch('/api/notifications').then(function (r) { return r.json(); }).then(function (data) {
    items = data.items;
    if (data.unread > 0) {
      count.textContent = data.unread;
      count.hidden = false;
      // 토스트는 아직 안 띄운 새 알림이 있을 때만 (페이지를 옮길 때마다 같은 알림이 뜨지 않게)
      var shown = '';
      try { shown = localStorage.getItem('toastShown') || ''; } catch (e) {}
      if (items[0].time > shown) {
        showToast(items[0].text, items[0].sub);
        try { localStorage.setItem('toastShown', items[0].time); } catch (e) {}
      }
    }
  });

  bell.addEventListener('click', function () {
    var open = panel.hidden;
    panel.hidden = !open;
    bell.setAttribute('aria-expanded', String(open));
    if (!open) return;

    panel.innerHTML = '';
    if (!items.length) panel.textContent = '새 알림이 없어요.';
    items.forEach(function (it) {
      var a = document.createElement('a');
      a.href = it.link;
      a.className = 'bell-item' + (it.new ? ' new' : '');
      var t = document.createElement('strong');
      t.textContent = it.text;
      var s = document.createElement('span');
      s.textContent = it.sub + ' · ' + it.time.slice(5, 16);
      a.appendChild(t);
      a.appendChild(s);
      panel.appendChild(a);
    });
    postJSON('/api/notifications/read');
    count.hidden = true;
  });
})();

// ---------------------------------------------------------------- 그래프 하나 그리기
// values: 값 목록, labels: x축 글자, band: {low, high} 또는 null
// marks: [{from, to, color}] 배경으로 칠할 구간 (점 번호 기준)
var shadePlugin = {
  id: 'shade',
  beforeDatasetsDraw: function (chart, args, opts) {
    var area = chart.chartArea;
    var x = chart.scales.x;
    (opts.marks || []).forEach(function (m) {
      var left = x.getPixelForValue(m.from);
      var right = x.getPixelForValue(m.to);
      chart.ctx.save();
      chart.ctx.fillStyle = m.color;
      chart.ctx.fillRect(left, area.top, Math.max(right - left, 3), area.bottom - area.top);
      chart.ctx.restore();
    });
  }
};

function lineChart(canvas, labels, values, band, marks, yRange) {
  var red = cssVar('--red');
  var line = cssVar('--line');
  var datasets = [{
    data: values,
    borderColor: line,
    borderWidth: 1.6,
    pointRadius: 0,
    spanGaps: false,
    segment: {
      // 기준선 밖으로 나간 부분은 빨간 선
      borderColor: function (ctx) {
        if (!band) return line;
        var a = ctx.p0.parsed.y;
        var b = ctx.p1.parsed.y;
        var out = a > band.high || a < band.low || b > band.high || b < band.low;
        return out ? red : line;
      },
      borderWidth: function (ctx) {
        if (!band) return 1.6;
        var a = ctx.p0.parsed.y;
        var b = ctx.p1.parsed.y;
        return (a > band.high || a < band.low || b > band.high || b < band.low) ? 2.6 : 1.6;
      }
    }
  }];
  if (band) {
    var hi = [];
    var lo = [];
    for (var i = 0; i < values.length; i++) { hi.push(band.high); lo.push(band.low); }
    datasets.push({ data: hi, borderColor: red, borderDash: [6, 5], borderWidth: 1.2, pointRadius: 0 });
    datasets.push({ data: lo, borderColor: red, borderDash: [6, 5], borderWidth: 1.2, pointRadius: 0 });
  }
  var y = { grid: { color: cssVar('--grid') }, ticks: { color: cssVar('--muted'), maxTicksLimit: 5 } };
  if (yRange) { y.min = yRange.min; y.max = yRange.max; }

  return new Chart(canvas, {
    type: 'line',
    data: { labels: labels, datasets: datasets },
    plugins: [shadePlugin],
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        shade: { marks: marks || [] },
        tooltip: { filter: function (item) { return item.datasetIndex === 0; } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: cssVar('--muted'), maxTicksLimit: 8, maxRotation: 0 } },
        y: y
      }
    }
  });
}
