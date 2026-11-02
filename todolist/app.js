/*
 * 오늘의 할일 - 상태 하나를 기준으로 "변경 → 저장 → 다시 그리기" 흐름을 따른다.
 * (prd.md 8.3 참고)
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'todayTodo.v1';
  const MAX_LEN = 100;
  const UNDO_MS = 5000;

  const $ = (id) => document.getElementById(id);
  const els = {
    storageWarning: $('storage-warning'),
    themeToggle: $('theme-toggle'),
    greeting: $('greeting'),
    today: $('today'),
    progress: $('progress'),
    progressBar: $('progress-bar'),
    progressText: $('progress-text'),
    carry: $('carry-over'),
    carryText: $('carry-over-text'),
    carryAccept: $('carry-accept'),
    carryDiscard: $('carry-discard'),
    form: $('add-form'),
    input: $('new-todo'),
    inputError: $('input-error'),
    filters: document.querySelectorAll('[data-filter]'),
    list: $('todo-list'),
    empty: $('empty'),
    emptyText: $('empty-text'),
    celebrate: $('celebrate'),
    remaining: $('remaining'),
    toggleAll: $('toggle-all'),
    clearCompleted: $('clear-completed'),
    toast: $('toast'),
    toastText: $('toast-text'),
    toastUndo: $('toast-undo'),
  };

  // ---------------------------------------------------------------------
  // utils
  // ---------------------------------------------------------------------
  function todayKey(d = new Date()) {
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${m}-${day}`;
  }

  function formatDate(d) {
    const weekday = '일월화수목금토'[d.getDay()];
    return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 (${weekday})`;
  }

  function greetingFor(hour) {
    if (hour < 12) return '좋은 아침이에요 ☀️';
    if (hour < 18) return '오후도 힘내세요 💪';
    return '오늘 하루 수고했어요 🌙';
  }

  function newId() {
    if (window.crypto && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function validateText(raw) {
    const text = raw.trim();
    if (!text) return { error: '할일 내용을 입력해 주세요.' };
    if (text.length > MAX_LEN) return { error: `최대 ${MAX_LEN}자까지 입력할 수 있어요.` };
    return { text };
  }

  // ---------------------------------------------------------------------
  // storage
  // ---------------------------------------------------------------------
  const storage = {
    available: (function () {
      try {
        const k = '__todayTodo_test__';
        localStorage.setItem(k, k);
        localStorage.removeItem(k);
        return true;
      } catch (e) {
        return false;
      }
    })(),

    load() {
      if (!this.available) return null;
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return null;
        const data = JSON.parse(raw);
        if (!data || data.version !== 1 || !Array.isArray(data.todos)) {
          throw new Error('알 수 없는 저장 형식');
        }
        return data;
      } catch (e) {
        console.warn('저장된 데이터를 읽지 못해 새로 시작합니다.', e);
        return null;
      }
    },

    save(s) {
      if (!this.available) return;
      const data = {
        version: 1,
        date: s.date,
        theme: s.theme,
        todos: s.todos,
        carryOver: s.carryOver,
      };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      } catch (e) {
        this.available = false;
        els.storageWarning.hidden = false;
        console.warn('저장에 실패했습니다.', e);
      }
    },
  };

  function sanitizeTodo(t, i) {
    if (!t || typeof t.text !== 'string') return null;
    const text = t.text.trim().slice(0, MAX_LEN);
    if (!text) return null;
    return {
      id: typeof t.id === 'string' && t.id ? t.id : newId(),
      text,
      done: !!t.done,
      important: !!t.important,
      createdAt: Number.isFinite(t.createdAt) ? t.createdAt : Date.now(),
      completedAt: t.done && Number.isFinite(t.completedAt) ? t.completedAt : null,
      order: Number.isFinite(t.order) ? t.order : i,
    };
  }

  function sanitizeList(list) {
    return (Array.isArray(list) ? list : []).map(sanitizeTodo).filter(Boolean);
  }

  // ---------------------------------------------------------------------
  // state
  // ---------------------------------------------------------------------
  const state = {
    date: todayKey(),
    theme: 'system',      // 'system' | 'light' | 'dark'
    todos: [],
    carryOver: [],        // 지난 날짜에서 넘어온, 아직 처리 안 한 미완료 항목
    filter: 'all',        // 'all' | 'active' | 'done'
    editingId: null,
    error: '',
  };
  let lastDeleted = null;
  let toastTimer = null;
  let dragId = null;

  /** 날짜가 바뀌었으면 미완료 항목을 이월 대기 목록으로 옮긴다. */
  function rollover() {
    const today = todayKey();
    if (state.date === today) return false;
    state.carryOver = state.carryOver.concat(state.todos.filter((t) => !t.done));
    state.todos = [];
    state.date = today;
    state.editingId = null;
    return true;
  }

  // ---------------------------------------------------------------------
  // selectors
  // ---------------------------------------------------------------------
  function sortTodos(list) {
    return list.slice().sort((a, b) =>
      (b.important - a.important) || (a.done - b.done) || (a.order - b.order));
  }

  function visibleTodos() {
    const list = sortTodos(state.todos);
    if (state.filter === 'active') return list.filter((t) => !t.done);
    if (state.filter === 'done') return list.filter((t) => t.done);
    return list;
  }

  function stats() {
    const total = state.todos.length;
    const done = state.todos.filter((t) => t.done).length;
    return {
      total,
      done,
      remaining: total - done,
      percent: total ? Math.round((done / total) * 100) : 0,
    };
  }

  // ---------------------------------------------------------------------
  // actions
  // ---------------------------------------------------------------------
  function commit(focus) {
    storage.save(state);
    render(focus);
  }

  function findTodo(id) {
    return state.todos.find((t) => t.id === id);
  }

  function nextOrder() {
    return state.todos.reduce((max, t) => Math.max(max, t.order), -1) + 1;
  }

  function addTodo(raw) {
    const result = validateText(raw);
    if (result.error) {
      state.error = result.error;
      renderError();
      return false;
    }
    state.error = '';
    state.todos.push({
      id: newId(),
      text: result.text,
      done: false,
      important: false,
      createdAt: Date.now(),
      completedAt: null,
      order: nextOrder(),
    });
    commit();
    return true;
  }

  function toggleTodo(id) {
    const t = findTodo(id);
    if (!t) return;
    t.done = !t.done;
    t.completedAt = t.done ? Date.now() : null;
    commit({ id, cls: 'toggle' });
  }

  function toggleImportant(id) {
    const t = findTodo(id);
    if (!t) return;
    t.important = !t.important;
    commit({ id, cls: 'star' });
  }

  function startEdit(id) {
    state.editingId = id;
    render();
  }

  function commitEdit(id, raw) {
    if (state.editingId !== id) return;
    state.editingId = null;
    const t = findTodo(id);
    const result = validateText(raw);
    if (t && !result.error) t.text = result.text;  // 빈 값이면 원래 내용 유지
    commit({ id, cls: 'edit-btn' });
  }

  function cancelEdit(id) {
    state.editingId = null;
    render({ id, cls: 'edit-btn' });
  }

  function deleteTodo(id) {
    const i = state.todos.findIndex((t) => t.id === id);
    if (i < 0) return;
    lastDeleted = state.todos.splice(i, 1)[0];
    if (state.editingId === id) state.editingId = null;
    commit();
    showToast('할일을 삭제했어요.');
  }

  function undoDelete() {
    const t = lastDeleted;
    hideToast();
    if (!t) return;
    state.todos.push(t);  // order 값이 그대로라 원래 위치로 돌아간다
    commit({ id: t.id, cls: 'delete-btn' });
  }

  function clearCompleted() {
    const n = stats().done;
    if (!n) return;
    if (!window.confirm(`완료한 할일 ${n}개를 지울까요?`)) return;
    state.todos = state.todos.filter((t) => !t.done);
    commit();
  }

  function toggleAll() {
    const allDone = state.todos.length > 0 && state.todos.every((t) => t.done);
    const now = Date.now();
    state.todos.forEach((t) => {
      t.done = !allDone;
      t.completedAt = t.done ? (t.completedAt || now) : null;
    });
    commit();
  }

  function setFilter(f) {
    state.filter = f;
    render();
  }

  function acceptCarry() {
    const base = nextOrder();
    state.carryOver.forEach((t, i) => {
      t.order = base + i;
      state.todos.push(t);
    });
    state.carryOver = [];
    commit();
  }

  function discardCarry() {
    state.carryOver = [];
    commit();
  }

  function moveTodo(fromId, toId) {
    if (fromId === toId) return;
    const sorted = sortTodos(state.todos);
    const from = sorted.findIndex((t) => t.id === fromId);
    const target = sorted.findIndex((t) => t.id === toId);
    if (from < 0 || target < 0) return;
    const [moved] = sorted.splice(from, 1);
    // 원래 인덱스에 다시 끼우면 아래로 끈 경우 대상 뒤, 위로 끈 경우 대상 앞에 놓인다
    sorted.splice(target, 0, moved);
    sorted.forEach((t, i) => { t.order = i; });
    commit();
  }

  // ---------------------------------------------------------------------
  // theme
  // ---------------------------------------------------------------------
  const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');

  function systemTheme() {
    return darkQuery.matches ? 'dark' : 'light';
  }

  function effectiveTheme() {
    return state.theme === 'system' ? systemTheme() : state.theme;
  }

  function applyTheme() {
    const root = document.documentElement;
    if (state.theme === 'system') delete root.dataset.theme;
    else root.dataset.theme = state.theme;
    const dark = effectiveTheme() === 'dark';
    els.themeToggle.textContent = dark ? '☀️' : '🌙';
    els.themeToggle.setAttribute('aria-label', dark ? '라이트 모드로 전환' : '다크 모드로 전환');
    els.themeToggle.title = els.themeToggle.getAttribute('aria-label');
  }

  function toggleTheme() {
    const next = effectiveTheme() === 'dark' ? 'light' : 'dark';
    // 시스템 설정과 같아지면 다시 '시스템 따라가기'로 돌아간다
    state.theme = next === systemTheme() ? 'system' : next;
    applyTheme();
    storage.save(state);
  }

  // ---------------------------------------------------------------------
  // render
  // ---------------------------------------------------------------------
  function render(focus) {
    if (!focus) focus = currentListFocus();
    const s = stats();
    renderHeader(s);
    renderCarry();
    renderError();
    renderFilters();
    renderList();
    renderFooter(s);
    restoreFocus(focus);
  }

  function renderHeader(s) {
    const now = new Date();
    els.greeting.textContent = greetingFor(now.getHours());
    els.today.textContent = formatDate(now);
    els.progressBar.style.width = s.percent + '%';
    els.progress.setAttribute('aria-valuenow', String(s.percent));
    els.progressText.textContent = s.total
      ? `${s.done} / ${s.total} 완료 (${s.percent}%)`
      : '아직 할일이 없어요';
    els.celebrate.hidden = !(s.total > 0 && s.done === s.total);
  }

  function renderCarry() {
    const n = state.carryOver.length;
    els.carry.hidden = n === 0;
    els.carryText.textContent = `지난번에 못 끝낸 할일 ${n}개가 있어요.`;
  }

  function renderError() {
    els.inputError.textContent = state.error;
    els.input.setAttribute('aria-invalid', state.error ? 'true' : 'false');
  }

  function renderFilters() {
    els.filters.forEach((btn) => {
      btn.setAttribute('aria-pressed', String(btn.dataset.filter === state.filter));
    });
  }

  function itemButton(cls, label, ariaLabel) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'item-btn ' + cls;
    b.textContent = label;
    b.setAttribute('aria-label', ariaLabel);
    b.title = ariaLabel;
    return b;
  }

  function renderItem(t) {
    const editing = state.editingId === t.id;
    const li = document.createElement('li');
    li.className = 'todo-item' + (t.done ? ' done' : '') + (t.important ? ' important' : '');
    li.dataset.id = t.id;
    li.draggable = !editing;

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'toggle';
    cb.checked = t.done;
    cb.setAttribute('aria-label', `"${t.text}" 완료`);

    const star = itemButton('star', t.important ? '★' : '☆', t.important ? '중요 표시 해제' : '중요 표시');
    star.setAttribute('aria-pressed', String(t.important));

    let body;
    if (editing) {
      body = document.createElement('input');
      body.type = 'text';
      body.className = 'edit-input';
      body.value = t.text;
      body.maxLength = MAX_LEN;
      body.setAttribute('aria-label', '할일 수정');
    } else {
      body = document.createElement('span');
      body.className = 'text';
      body.textContent = t.text;  // textContent 로만 넣어 XSS 방지
      body.title = '더블클릭하여 수정';
    }

    li.append(
      cb,
      star,
      body,
      itemButton('edit-btn', '✎', `"${t.text}" 수정`),
      itemButton('delete-btn', '✕', `"${t.text}" 삭제`),
    );
    return li;
  }

  function renderList() {
    const items = visibleTodos();
    els.list.replaceChildren(...items.map(renderItem));

    els.empty.hidden = items.length > 0;
    if (state.todos.length === 0) els.emptyText.textContent = '오늘 할 일을 추가해 보세요';
    else if (state.filter === 'active') els.emptyText.textContent = '진행 중인 할일이 없어요';
    else els.emptyText.textContent = '아직 완료한 할일이 없어요';
  }

  function renderFooter(s) {
    els.remaining.textContent = `남은 할일 ${s.remaining}개`;
    const allDone = s.total > 0 && s.done === s.total;
    els.toggleAll.textContent = allDone ? '모두 해제' : '모두 완료';
    els.toggleAll.disabled = s.total === 0;
    els.clearCompleted.disabled = s.done === 0;
  }

  // 다시 그린 뒤에도 키보드 포커스가 같은 항목·같은 버튼에 머물도록 한다
  const FOCUS_CLASSES = ['toggle', 'star', 'edit-btn', 'delete-btn'];

  function currentListFocus() {
    const active = document.activeElement;
    if (!active || !els.list.contains(active)) return null;
    const li = active.closest('li');
    const cls = FOCUS_CLASSES.find((c) => active.classList.contains(c));
    return li && cls ? { id: li.dataset.id, cls } : null;
  }

  function restoreFocus(focus) {
    const editInput = els.list.querySelector('.edit-input');
    if (editInput) {
      if (document.activeElement !== editInput) {
        editInput.focus();
        editInput.setSelectionRange(editInput.value.length, editInput.value.length);
      }
      return;
    }
    if (!focus) return;
    const li = els.list.querySelector(`li[data-id="${CSS.escape(focus.id)}"]`);
    const target = li && li.querySelector('.' + focus.cls);
    if (target) target.focus();
    else if (document.activeElement === document.body) els.input.focus();
  }

  // ---------------------------------------------------------------------
  // toast
  // ---------------------------------------------------------------------
  function showToast(msg) {
    els.toastText.textContent = msg;
    els.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(hideToast, UNDO_MS);
  }

  function hideToast() {
    clearTimeout(toastTimer);
    els.toast.hidden = true;
    lastDeleted = null;
  }

  // ---------------------------------------------------------------------
  // events
  // ---------------------------------------------------------------------
  function itemId(target) {
    const li = target.closest('li[data-id]');
    return li ? li.dataset.id : null;
  }

  els.form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (addTodo(els.input.value)) els.input.value = '';
    els.input.focus();
  });

  els.input.addEventListener('input', () => {
    const msg = els.input.value.length >= MAX_LEN ? `최대 ${MAX_LEN}자까지 입력할 수 있어요.` : '';
    if (msg !== state.error) {
      state.error = msg;
      renderError();
    }
  });

  els.input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      els.input.value = '';
      state.error = '';
      renderError();
    }
  });

  els.list.addEventListener('change', (e) => {
    if (e.target.classList.contains('toggle')) toggleTodo(itemId(e.target));
  });

  els.list.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const id = itemId(btn);
    if (btn.classList.contains('star')) toggleImportant(id);
    else if (btn.classList.contains('edit-btn')) startEdit(id);
    else if (btn.classList.contains('delete-btn')) deleteTodo(id);
  });

  els.list.addEventListener('dblclick', (e) => {
    if (e.target.classList.contains('text')) startEdit(itemId(e.target));
  });

  els.list.addEventListener('keydown', (e) => {
    if (!e.target.classList.contains('edit-input')) return;
    const id = itemId(e.target);
    if (e.key === 'Enter') {
      e.preventDefault();
      commitEdit(id, e.target.value);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelEdit(id);
    }
  });

  els.list.addEventListener('focusout', (e) => {
    // Enter/Esc 로 이미 끝난 편집이면 commitEdit 안에서 무시된다
    if (e.target.classList.contains('edit-input')) commitEdit(itemId(e.target), e.target.value);
  });

  // 드래그 앤 드롭으로 순서 변경
  els.list.addEventListener('dragstart', (e) => {
    const li = e.target.closest && e.target.closest('li[data-id]');
    if (!li) return;
    dragId = li.dataset.id;
    li.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragId);
  });

  els.list.addEventListener('dragover', (e) => {
    const li = e.target.closest && e.target.closest('li[data-id]');
    if (!dragId || !li) return;
    e.preventDefault();
    els.list.querySelectorAll('.drag-over').forEach((n) => { if (n !== li) n.classList.remove('drag-over'); });
    if (li.dataset.id !== dragId) li.classList.add('drag-over');
  });

  els.list.addEventListener('drop', (e) => {
    const li = e.target.closest && e.target.closest('li[data-id]');
    if (!dragId || !li) return;
    e.preventDefault();
    const from = dragId;
    dragId = null;
    moveTodo(from, li.dataset.id);
  });

  els.list.addEventListener('dragend', () => {
    dragId = null;
    els.list.querySelectorAll('.dragging, .drag-over').forEach((n) => n.classList.remove('dragging', 'drag-over'));
  });

  els.filters.forEach((btn) => btn.addEventListener('click', () => setFilter(btn.dataset.filter)));
  els.toggleAll.addEventListener('click', toggleAll);
  els.clearCompleted.addEventListener('click', clearCompleted);
  els.carryAccept.addEventListener('click', acceptCarry);
  els.carryDiscard.addEventListener('click', discardCarry);
  els.toastUndo.addEventListener('click', undoDelete);
  els.themeToggle.addEventListener('click', toggleTheme);
  darkQuery.addEventListener('change', applyTheme);

  // '/' 키로 입력창 바로 가기
  document.addEventListener('keydown', (e) => {
    if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
    const tag = document.activeElement && document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    e.preventDefault();
    els.input.focus();
  });

  // 페이지를 연 채로 자정이 지나면 날짜 변경 처리, 인사말 갱신
  setInterval(() => {
    if (rollover()) commit();
    else renderHeader(stats());
  }, 60 * 1000);

  // ---------------------------------------------------------------------
  // init
  // ---------------------------------------------------------------------
  const saved = storage.load();
  if (saved) {
    state.theme = saved.theme === 'light' || saved.theme === 'dark' ? saved.theme : 'system';
    state.date = typeof saved.date === 'string' ? saved.date : todayKey();
    state.todos = sanitizeList(saved.todos);
    state.carryOver = sanitizeList(saved.carryOver);
  }
  if (rollover()) storage.save(state);
  els.storageWarning.hidden = storage.available;
  applyTheme();
  render();
  els.input.focus();
})();
