const API_ORIGIN = 'http://127.0.0.1:8000';
const API_BASE_URL = `${API_ORIGIN}/api`;
const allStepSlugs = ['descubrir', 'filtrar', 'elegir', 'crear', 'publicar', 'medir'];
const stepNameBySlug = {
  descubrir: 'Descubrir',
  filtrar: 'Filtrar',
  elegir: 'Elegir',
  crear: 'Crear',
  publicar: 'Publicar',
  medir: 'Medir',
};
const pipelineStepDescriptions = {
  Descubrir: { pending: 'Esperando ejecución.', current: 'Trayendo tendencias.', complete: 'Tendencias generadas.' },
  Filtrar: { pending: 'Esperando ejecución.', current: 'Filtrando duplicados.', complete: 'Duplicados filtrados.' },
  Elegir: { pending: 'Esperando ejecución.', current: 'Seleccionando tema.', complete: 'Tema elegido.' },
  Crear: { pending: 'Esperando ejecución.', current: 'Generando contenido con IA.', complete: 'Contenido generado.' },
  Publicar: { pending: 'Esperando ejecución.', current: 'Persistiendo post.', complete: 'Post persistido.' },
  Medir: { pending: 'Esperando ejecución.', current: 'Validando resultado.', complete: 'Calidad validada.' },
};

const themeToggle = document.querySelector('[data-theme-toggle]');
const historyTotal = document.querySelector('[data-history-total]');
const historyStatus = document.querySelector('[data-history-status]');
const historySession = document.querySelector('[data-history-session]');
const historyCompleted = document.querySelector('[data-history-completed]');
const historyQuality = document.querySelector('[data-history-quality]');
const historyRuns = document.querySelector('[data-history-runs]');
const historyDetail = document.querySelector('[data-history-detail]');
const historyDetailTitle = document.querySelector('[data-history-detail-title]');
const historyDetailCopy = document.querySelector('[data-history-detail-copy]');
const historyDetailStatus = document.querySelector('[data-history-detail-status]');
const historyTimeline = document.querySelector('[data-history-timeline]');
const historyPost = document.querySelector('[data-history-post]');
const historyImage = document.querySelector('[data-history-image]');
const historyPublication = document.querySelector('[data-history-publication]');
const historyAudit = document.querySelector('[data-history-audit]');
const historyFilters = document.querySelector('[data-history-filters]');
const historyDateFrom = document.querySelector('[data-history-date-from]');
const historyDateTo = document.querySelector('[data-history-date-to]');
const historyTopicFilter = document.querySelector('[data-history-topic-filter]');
const historyFilterResult = document.querySelector('[data-history-filter-result]');
const historyReuse = document.querySelector('[data-history-reuse]');
const historyActionStatus = document.querySelector('[data-history-action-status]');
const historySearch = document.querySelector('[data-history-search]');
const refreshButtons = Array.from(document.querySelectorAll('[data-refresh-history]'));

let historyItems = [];
let historyMeta = {};
let selectedRunId = null;
let reuseConfirmationTopicId = null;

function applyTheme(theme) {
  const isDark = theme === 'dark';
  document.documentElement.dataset.theme = theme;
  themeToggle.setAttribute('aria-pressed', String(isDark));
  themeToggle.setAttribute('aria-label', isDark ? 'Activar tema claro' : 'Activar tema oscuro');
  themeToggle.querySelector('.theme-toggle__icon').textContent = isDark ? '☀' : '☾';
  window.localStorage.setItem('trending-theme', theme);
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message || 'No se pudo completar la operación');
  return payload;
}

function shortSession(runId) {
  return runId ? `Sesión ${String(runId).slice(0, 8)}` : 'Sesión nueva';
}

function badgeClassForStatus(status) {
  if (status === 'error' || status === 'cancelled') return 'badge error';
  if (status === 'completed' || status === 'published' || status === 'success') return 'badge success';
  return 'badge draft';
}

function completedLabel(steps) {
  return `${Array.isArray(steps) ? steps.length : 0}/${allStepSlugs.length}`;
}

function qualityLabel(score) {
  return Number.isFinite(score) ? `${score}%` : 'sin medir';
}

function normalizeRun(item) {
  const topic = item?.topic && typeof item.topic === 'object' ? item.topic : null;
  const post = item?.post && typeof item.post === 'object' ? item.post : null;
  return {
    ...item,
    id: item?.id || '',
    status: item?.status || 'idle',
    session: shortSession(item?.id),
    completedSteps: Array.isArray(item?.completed_steps) ? item.completed_steps : [],
    currentStep: item?.current_step || null,
    nextStep: item?.next_step || null,
    topicId: topic?.id ?? null,
    topicTitle: topic?.title || post?.topic_title || '',
    scoreValue: Number.isFinite(item?.quality?.score) ? item.quality.score : null,
  };
}

function formatRunDate(value) {
  const parsed = value ? new Date(value) : null;
  if (!parsed || Number.isNaN(parsed.getTime())) return 'sin fecha';
  return new Intl.DateTimeFormat('es-AR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(parsed);
}

function setMessage(container, message) {
  const item = document.createElement('li');
  item.className = 'history-empty';
  item.textContent = message;
  container.replaceChildren(item);
}

function renderSummary() {
  const latest = historyItems[0] || null;
  historyTotal.textContent = String(historyMeta.available_runs ?? historyItems.length);
  historyStatus.textContent = latest?.status || 'idle';
  historySession.textContent = latest?.session || 'sesión nueva';
  historyCompleted.textContent = completedLabel(latest?.completedSteps || []);
  historyQuality.textContent = qualityLabel(latest?.scoreValue);
}

function resetReuseConfirmation() {
  reuseConfirmationTopicId = null;
  historyReuse.classList.remove('is-confirming');
  historyReuse.textContent = 'Reutilizar tema';
  historyReuse.disabled = false;
  historyActionStatus.textContent = '';
  historyActionStatus.classList.remove('is-error');
}

function clearDetail(message = 'Seleccioná una corrida para revisar su evidencia.') {
  selectedRunId = null;
  historyDetailTitle.textContent = 'Sin ejecución seleccionada';
  historyDetailCopy.textContent = message;
  historyDetailStatus.textContent = 'idle';
  historyDetailStatus.className = 'badge draft';
  setMessage(historyTimeline, 'Sin pasos para mostrar.');
  historyPost.textContent = 'sin post';
  historyImage.textContent = 'sin imagen';
  historyPublication.textContent = 'sin publicación';
  historyAudit.textContent = 'sin auditoría';
  historyReuse.hidden = true;
  resetReuseConfirmation();
}

function buildTimeline(run) {
  const completedSet = new Set(run.completedSteps);
  const fragment = document.createDocumentFragment();
  allStepSlugs.forEach((slug, index) => {
    const name = stepNameBySlug[slug];
    const isDone = completedSet.has(slug);
    const isCurrent = run.currentStep === slug;
    const status = isDone ? 'completo' : isCurrent ? 'actual' : 'pendiente';
    const description = pipelineStepDescriptions[name]?.[
      isDone ? 'complete' : isCurrent ? 'current' : 'pending'
    ] || status;
    const item = document.createElement('li');
    const mark = document.createElement('span');
    const copy = document.createElement('span');
    const title = document.createElement('strong');
    const detail = document.createElement('small');
    const state = document.createElement('span');
    mark.className = 'history-timeline__mark';
    copy.className = 'history-timeline__copy';
    state.className = 'history-timeline__status';
    mark.textContent = isDone ? '✓' : isCurrent ? '•' : String(index + 1);
    title.textContent = name;
    detail.textContent = description;
    state.textContent = status;
    copy.append(title, detail);
    item.append(mark, copy, state);
    fragment.append(item);
  });
  historyTimeline.replaceChildren(fragment);
}

function renderDetail(item) {
  const run = normalizeRun(item);
  const post = item?.post && typeof item.post === 'object' ? item.post : null;
  const log = item?.publication_log && typeof item.publication_log === 'object'
    ? item.publication_log
    : null;
  const generatedContent = item?.generated_content && typeof item.generated_content === 'object'
    ? item.generated_content
    : null;
  selectedRunId = run.id;
  historyDetailTitle.textContent = run.topicTitle || run.session;
  historyDetailCopy.textContent = run.currentStep
    ? `Ejecutando ${stepNameBySlug[run.currentStep] || run.currentStep}.`
    : `Corrida correlacionada. Próximo: ${stepNameBySlug[run.nextStep] || run.nextStep || 'sin pendientes'}.`;
  historyDetailStatus.textContent = run.status;
  historyDetailStatus.className = badgeClassForStatus(run.status);
  historyPost.textContent = post?.id
    ? `#${post.id} · ${post.topic_title || post.topic_id || run.topicTitle || 'sin tema'}`
    : 'sin post';
  historyImage.textContent = post?.image_url || generatedContent?.image_file || 'sin imagen';
  historyPublication.textContent = log?.id
    ? `log #${log.id} · ${log.status || 'registrado'}`
    : 'sin publicación';
  historyAudit.textContent = Number.isFinite(run.scoreValue)
    ? `${run.scoreValue}% · auditoría local`
    : 'sin auditoría cerrada';
  historyReuse.hidden = !run.topicId;
  historyReuse.dataset.topicId = run.topicId || '';
  historyReuse.dataset.topicTitle = run.topicTitle || '';
  resetReuseConfirmation();
  buildTimeline(run);
}

function createRunButton(run) {
  const item = document.createElement('li');
  const button = document.createElement('button');
  const top = document.createElement('span');
  const title = document.createElement('span');
  const topic = document.createElement('strong');
  const id = document.createElement('small');
  const badge = document.createElement('span');
  const meta = document.createElement('span');
  const steps = document.createElement('span');
  const quality = document.createElement('span');
  const date = document.createElement('span');

  button.className = 'history-run';
  button.type = 'button';
  button.dataset.runId = run.id;
  button.setAttribute('aria-pressed', String(run.id === selectedRunId));
  top.className = 'history-run__top';
  title.className = 'history-run__title';
  meta.className = 'history-run__meta';
  badge.className = badgeClassForStatus(run.status);
  topic.textContent = run.topicTitle || 'sin tema';
  id.textContent = run.id;
  badge.textContent = run.status;
  steps.textContent = `${completedLabel(run.completedSteps)} steps OK`;
  quality.textContent = qualityLabel(run.scoreValue);
  date.textContent = formatRunDate(run.updated_at || run.created_at);
  title.append(topic, id);
  top.append(title, badge);
  meta.append(steps, quality, date);
  button.append(top, meta);
  item.append(button);
  return item;
}

function renderRunList() {
  const filtersActive = Boolean(
    historyDateFrom.value || historyDateTo.value || historyTopicFilter.value.trim()
  );
  historyFilterResult.textContent = filtersActive
    ? `${historyMeta.available_runs ?? historyItems.length} corridas coinciden con los filtros.`
    : `${historyMeta.available_runs ?? historyItems.length} corrida${(historyMeta.available_runs ?? historyItems.length) === 1 ? '' : 's'} persistida${(historyMeta.available_runs ?? historyItems.length) === 1 ? '' : 's'}.`;

  if (!historyItems.length) {
    setMessage(
      historyRuns,
      filtersActive
        ? 'No hay corridas que coincidan con esos filtros.'
        : 'Todavía no hay corridas persistidas. Ejecutá el pipeline desde el dashboard.'
    );
    clearDetail(filtersActive ? 'Ajustá o limpiá los filtros.' : 'La primera ejecución aparecerá acá.');
    return;
  }

  if (!historyItems.some((run) => run.id === selectedRunId)) selectedRunId = historyItems[0].id;
  const fragment = document.createDocumentFragment();
  historyItems.forEach((run) => fragment.append(createRunButton(run)));
  historyRuns.replaceChildren(fragment);
}

function historyQuery() {
  const params = new URLSearchParams({ limit: '50' });
  if (historyDateFrom.value) params.set('date_from', historyDateFrom.value);
  if (historyDateTo.value) params.set('date_to', historyDateTo.value);
  if (historyTopicFilter.value.trim()) params.set('topic', historyTopicFilter.value.trim());
  return params.toString();
}

async function loadRunDetail(runId) {
  selectedRunId = runId;
  renderRunList();
  historyDetail.setAttribute('aria-busy', 'true');
  historyDetailCopy.textContent = 'Cargando evidencia correlacionada…';
  try {
    const payload = await requestJson(`/pipeline/runs/${encodeURIComponent(runId)}`);
    if (selectedRunId === runId) renderDetail(payload.data);
  } catch (error) {
    if (selectedRunId === runId) clearDetail(error.message);
  } finally {
    historyDetail.setAttribute('aria-busy', 'false');
  }
}

async function loadHistoryView() {
  historyRuns.setAttribute('aria-busy', 'true');
  setMessage(historyRuns, 'Actualizando historial persistente…');
  try {
    const payload = await requestJson(`/pipeline/runs?${historyQuery()}`);
    historyItems = Array.isArray(payload.data?.items)
      ? payload.data.items.map(normalizeRun)
      : [];
    historyMeta = payload.data?.meta || {};
    if (!historyItems.some((run) => run.id === selectedRunId)) {
      selectedRunId = historyItems[0]?.id || null;
    }
    renderSummary();
    renderRunList();
    if (selectedRunId) await loadRunDetail(selectedRunId);
  } catch (error) {
    historyItems = [];
    historyMeta = {};
    renderSummary();
    setMessage(historyRuns, `${error.message} Revisá que el backend esté levantado.`);
    clearDetail('No pude cargar el historial persistente.');
  } finally {
    historyRuns.setAttribute('aria-busy', 'false');
  }
}

async function prepareTopicReuse() {
  const topicId = Number(historyReuse.dataset.topicId);
  const topicTitle = historyReuse.dataset.topicTitle || `tema ${topicId}`;
  if (!Number.isInteger(topicId) || topicId <= 0) return;

  if (reuseConfirmationTopicId !== topicId) {
    reuseConfirmationTopicId = topicId;
    historyReuse.classList.add('is-confirming');
    historyReuse.textContent = 'Confirmar reutilización';
    historyActionStatus.textContent = `Se abrirá una rama nueva con “Crear” seleccionado para ${topicTitle}. No ejecutará el pipeline.`;
    return;
  }

  historyReuse.disabled = true;
  historyReuse.textContent = 'Preparando…';
  try {
    const payload = await requestJson(`/pipeline/topics/${topicId}/reuse`, { method: 'POST' });
    historyActionStatus.textContent = payload.message;
    window.location.href = `index.html?reuse_topic=${encodeURIComponent(topicId)}#pipeline`;
  } catch (error) {
    historyActionStatus.textContent = error.message;
    historyActionStatus.classList.add('is-error');
    historyReuse.disabled = false;
    historyReuse.textContent = 'Reintentar reutilización';
  }
}

themeToggle.addEventListener('click', () => {
  applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
});
refreshButtons.forEach((button) => button.addEventListener('click', loadHistoryView));
historyFilters.addEventListener('submit', (event) => {
  event.preventDefault();
  loadHistoryView();
});
historyFilters.addEventListener('reset', () => window.setTimeout(loadHistoryView, 0));
historyRuns.addEventListener('click', (event) => {
  const button = event.target.closest('[data-run-id]');
  if (button) loadRunDetail(button.dataset.runId);
});
historyReuse.addEventListener('click', prepareTopicReuse);
historySearch?.addEventListener('search', () => {
  historyTopicFilter.value = historySearch.value;
  loadHistoryView();
});
historySearch?.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter') return;
  event.preventDefault();
  historyTopicFilter.value = historySearch.value;
  loadHistoryView();
});

const storedTheme = window.localStorage.getItem('trending-theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
applyTheme(storedTheme || (prefersDark ? 'dark' : 'light'));
loadHistoryView();
