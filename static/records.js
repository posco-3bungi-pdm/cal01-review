// 팀원 기록 화면: 격자형, 패널형, 폴더 색

// ---------------------------------------------------------------- 보기 방식
function setView(name) {
  document.getElementById('grid-view').hidden = name !== 'grid';
  document.getElementById('panel-view').hidden = name !== 'panel';
  document.querySelectorAll('[data-view]').forEach(function (b) { b.classList.toggle('on', b.dataset.view === name); });
  try { localStorage.setItem('recordsView', name); } catch (e) {}
}
document.querySelectorAll('[data-view]').forEach(function (b) {
  b.addEventListener('click', function () { setView(b.dataset.view); });
});

// ---------------------------------------------------------------- 패널형에서 고른 구간 보여 주기
function showDetail(id) {
  document.querySelectorAll('.panel-detail').forEach(function (d) { d.hidden = d.dataset.id !== id; });
  document.querySelectorAll('.panel-item').forEach(function (b) { b.classList.toggle('on', b.dataset.id === id); });
}
document.querySelectorAll('.panel-item').forEach(function (b) {
  b.addEventListener('click', function () { showDetail(b.dataset.id); });
});
document.querySelectorAll('.open-panel').forEach(function (b) {
  b.addEventListener('click', function () {
    setView('panel');
    showDetail(b.dataset.id);
  });
});

var first = document.querySelector('.panel-item');
if (first) showDetail(first.dataset.id);
var savedView = 'grid';
try { savedView = localStorage.getItem('recordsView') || 'grid'; } catch (e) {}
setView(savedView);

// ---------------------------------------------------------------- 하루 안에 올라온 글은 '새 글'
document.querySelectorAll('.new-badge').forEach(function (b) {
  var created = new Date(b.dataset.created.replace(' ', 'T')).getTime();
  if (Date.now() - created < 24 * 60 * 60 * 1000) b.hidden = false;
});

// ---------------------------------------------------------------- 폴더 색, 새 폴더, 폴더 옮기기
var palette = document.getElementById('palette');
var paletteFolder = null;

document.querySelectorAll('.dot-btn').forEach(function (b) {
  b.addEventListener('click', function () {
    paletteFolder = b.dataset.folder;
    palette.hidden = false;
    b.parentElement.after(palette);
  });
});
document.querySelectorAll('.swatch').forEach(function (s) {
  s.addEventListener('click', function () {
    postJSON('/api/folders/' + encodeURIComponent(paletteFolder), { color: s.dataset.color })
      .then(function () { location.reload(); });
  });
});

document.getElementById('folder-add').addEventListener('click', function () {
  var name = prompt('새 폴더 이름');
  if (!name) return;
  postJSON('/api/folders', { name: name }).then(function () { location.reload(); });
});

document.querySelectorAll('.move-folder').forEach(function (sel) {
  sel.addEventListener('change', function () {
    postJSON('/api/snapshots/' + encodeURIComponent(sel.dataset.id), { folder: sel.value })
      .then(function () { showToast('폴더를 옮겼어요'); });
  });
});
