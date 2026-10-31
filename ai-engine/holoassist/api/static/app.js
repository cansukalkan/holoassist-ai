'use strict';

const result = document.querySelector('#result');
const runButton = document.querySelector('#evaluate');
const storage = document.querySelector('#storage-status');
const topHealthPill = document.querySelector('#top-health-pill');
const sidebarOrb = document.querySelector('#sidebar-orb');
const sidebarApiText = document.querySelector('#sidebar-api-text');
const safetyLatencyTag = document.querySelector('#safety-latency-tag');

const sqBox = document.querySelector('#scenario-quick-data');
const sqTitle = document.querySelector('#sq-title');
const sqHttp = document.querySelector('#sq-http');
const sqBody = document.querySelector('#sq-body');
const sqMeta = document.querySelector('#sq-meta');

const rigPartBadge = document.querySelector('#rig-part-badge');
const reticleLabel = document.querySelector('#motor-reticle-label');
const reticleCritical = document.querySelector('#motor-reticle-critical');
const calloutText = document.querySelector('#motor-callout-text');
const trackingChip = document.querySelector('#motor-tracking-chip');
const trackingChipText = document.querySelector('#motor-chip-text');

const expPillSafety = document.querySelector('#exp-pill-safety');
const expPillSensor = document.querySelector('#exp-pill-sensor');
const expPillDiag = document.querySelector('#exp-pill-diag');

const scenarios = {
  information: {
    label: 'Kaynaklı bilgi kartı',
    payload: {
      schema_version: '1.0',
      review_id: 'web-demo-information',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'tracked',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-information', part_id: 'demo-label' }]
    }
  },
  critical: {
    label: 'Kritik müdahale adımı',
    payload: {
      schema_version: '1.0',
      review_id: 'web-demo-critical',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'tracked',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-critical', part_id: 'demo-critical-part' }]
    }
  },
  tracking: {
    label: 'Parça takip kaybı',
    payload: {
      schema_version: '1.0',
      review_id: 'web-demo-tracking',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'lost',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-information', part_id: 'demo-label' }]
    }
  },
  unknown: {
    label: 'Bilinmeyen parça',
    payload: {
      schema_version: '1.0',
      review_id: 'web-demo-unknown',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'tracked',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-information', part_id: 'unknown-part' }]
    }
  },
  injection: {
    label: 'Yetkisiz alan testi (422)',
    payload: {
      schema_version: '1.0',
      review_id: 'web-demo-injection',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'tracked',
      approval: 'client-bypass-attempt',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-critical', part_id: 'demo-critical-part' }]
    }
  }
};

const verdicts = {
  display_allowed: [
    'Bilgi kartı gösterilebilir',
    'Kaynak alıntısı, sayfa/bölüm ve katalog parça eşleşmesi doğrulandı. Yalnızca sentetik bilgilendirme içeriği gösteriliyor.',
    'success'
  ],
  needs_approval: [
    'Kalıcı insan onayı gerekli',
    'Kritik adımın metni ve kaynak alıntıları atomik olarak gizlendi. Sunucu tarafında yetkili inceleme kaydı olmadan gösterim açılamaz.',
    'warning'
  ],
  needs_information: [
    'Takip doğrulanamadı (Ek bilgi gerekli)',
    'Parça takibi "lost" durumunda olduğu için bilgi kartı ve parça vurgusu güvenlik gereği kaldırıldı.',
    'warning'
  ],
  blocked: [
    'Güvenlik kapısı tarafından engellendi',
    'Gönderilen parça veya talimat kimliği doğrulanmış katalogla eşleşmedi. İşlem metni gösterilmiyor.',
    'blocked'
  ]
};

const reasons = {
  synthetic_information_only: 'Kaynağa bağlı sentetik bilgilendirme',
  persistent_approval_required: 'Kalıcı insan onayı zorunluluğu',
  tracking_required: 'Doğrulanmış parça takibi gerekiyor',
  part_mismatch: 'Parça kimliği katalogla eşleşmiyor',
  unknown_instruction: 'Talimat kimliği katalogda bulunamadı',
  source_binding_missing: 'Zorunlu kaynak bağı eksik',
  contradictory_source: 'Kaynaklar arasında çelişki var'
};

const riskLabels = {
  informational: 'Bilgilendirme (informational)',
  critical: 'Kritik (critical)',
  prohibited: 'Yasaklanmış (prohibited)',
  unknown: 'Sınıflandırılmamış (unknown)'
};

let chosen = 'information';
let selectedSensorKey = 'current';
let selectedDiagKey = 'complete';
let generation = 0;
let controller;

function hasKey(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

function fetchWithTimeout(url, options, timeoutMs) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  const merged = Object.assign({}, options || {}, { signal: ctrl.signal });
  return fetch(url, merged).finally(() => clearTimeout(timer));
}

function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function kvItem(label, value) {
  const wrap = node('div', 'kv-item');
  wrap.append(node('small', '', label), node('strong', '', value));
  return wrap;
}

function updateQuickScenarioBox(tone, titleText, httpText, bodyText, metaText) {
  if (!sqBox) return;
  sqBox.dataset.tone = tone;
  if (sqTitle) sqTitle.textContent = titleText;
  if (sqHttp) sqHttp.textContent = httpText;
  if (sqBody) sqBody.textContent = bodyText;
  if (sqMeta) sqMeta.textContent = metaText;
}

function updateExportPills() {
  const exportableSafety = chosen === 'injection'
    ? 'Kaynaklı bilgi kartı (422 testi rapora dahil edilmez)'
    : scenarios[chosen].label;
  const sensorTitle = { current: 'Akım (A)', temperature: 'Sıcaklık (°C)', vibration: 'Titreşim (m/s²)' }[selectedSensorKey];
  const diagTitle = selectedDiagKey === 'complete' ? 'Tüm test kayıtları' : 'Karşıt kayıt eksik';
  if (expPillSafety) expPillSafety.textContent = `01 Güvenlik: ${exportableSafety}`;
  if (expPillSensor) expPillSensor.textContent = `02 Sensör: ${sensorTitle}`;
  if (expPillDiag) expPillDiag.textContent = `03 Kanıt: ${diagTitle}`;
}

function syncMotorSchematic(mode) {
  if (!reticleLabel || !reticleCritical || !trackingChip) return;
  reticleLabel.classList.add('svg-hidden');
  reticleCritical.classList.add('svg-hidden');
  trackingChip.className = 'device-chip';

  if (mode === 'information') {
    reticleLabel.classList.remove('svg-hidden');
    rigPartBadge.textContent = 'Hedef: demo-label';
    calloutText.textContent = 'demo-label · Doğrulandı';
    trackingChipText.textContent = 'Takip simülasyonu: tracked · Gövde etiketi';
  } else if (mode === 'critical') {
    reticleCritical.classList.remove('svg-hidden');
    rigPartBadge.textContent = 'Hedef: demo-critical-part';
    calloutText.textContent = 'Kritik parça · Onay gerekli';
    trackingChip.classList.add('warn');
    trackingChipText.textContent = 'Takip: tracked · Kritik adım metni gizlendi';
  } else if (mode === 'tracking') {
    rigPartBadge.textContent = 'Takip: lost';
    calloutText.textContent = 'Takip kaybı · İşaret kaldırıldı';
    trackingChip.classList.add('warn');
    trackingChipText.textContent = 'Takip kaybı (lost) · Eski kart düşürüldü';
  } else if (mode === 'unknown') {
    rigPartBadge.textContent = 'Hedef: unknown-part';
    calloutText.textContent = 'Katalog dışı · Engellendi';
    trackingChip.classList.add('err');
    trackingChipText.textContent = 'Parça katalogla uyuşmuyor · Vurgu yok';
  } else {
    rigPartBadge.textContent = 'Protokol: HTTP 422';
    calloutText.textContent = 'Yetkisiz alan reddedildi';
    trackingChip.classList.add('err');
    trackingChipText.textContent = 'İstemci approval alanı sınırda engellendi';
  }
}

function clear(message) {
  result.replaceChildren(node('div', 'empty', message));
}

function validate(report) {
  if (
    report.schema_version !== '1.0' ||
    report.guidance_allowed !== false ||
    report.source_kind !== 'synthetic' ||
    !hasKey(verdicts, report.status) ||
    !Array.isArray(report.steps) ||
    !report.steps.length
  ) {
    throw new Error('invalid_report');
  }
  if (
    report.status === 'display_allowed' &&
    report.steps.some(
      step =>
        step.status !== 'display_allowed' ||
        step.risk !== 'informational' ||
        !step.display_text ||
        !Array.isArray(step.citations) ||
        !step.citations.some(
          c =>
            c.relation === 'supports' &&
            c.quote === step.display_text &&
            c.evidence_id &&
            c.document_id &&
            c.document_version &&
            (c.page || c.section)
        )
    )
  ) {
    throw new Error('invalid_report');
  }
}

function appendProtocolDetails(fragment, requestPayload, responsePayload) {
  const details = node('details', 'protocol-details');
  details.open = true;
  details.append(node('summary', '', 'Canlı HTTP JSON sözleşme verisi (Gönderilen İstek & Sunucu Yanıtı)'));
  const split = node('div', 'protocol-split');

  const reqCol = node('div');
  reqCol.append(node('div', 'content-label', 'GÖNDERİLEN İSTEK (POST)'), node('pre', '', JSON.stringify(requestPayload, null, 2)));

  const resCol = node('div');
  resCol.append(node('div', 'content-label', 'SUNUCU YANITI'), node('pre', '', JSON.stringify(responsePayload, null, 2)));

  split.append(reqCol, resCol);
  details.append(split);
  fragment.append(details);
}

function render(report, requestPayload, elapsedMs, spatialReport) {
  validate(report);
  const [title, explanation, tone] = verdicts[report.status];
  const step0 = report.steps[0];
  const spatialCard = spatialReport && Array.isArray(spatialReport.cards) ? spatialReport.cards[0] : null;
  const anchorTag = spatialCard && spatialCard.anchor_id
    ? ` · 3D Anchor: ${spatialCard.anchor_id}`
    : ' · 3D Anchor: bastırıldı';
  const quickBody = report.status === 'display_allowed'
    ? step0.display_text
    : `⊘ Metin gizlendi (${reasons[step0.reason_code] || step0.reason_code}). Kaynak ve karar verileri yandaki/aşağıdaki paneldedir.`;
  updateQuickScenarioBox(
    tone,
    `${title} (${report.status})`,
    `HTTP 200 · ${elapsedMs} ms`,
    quickBody,
    `Parça: ${step0.part_id} · Takip: ${requestPayload.tracking_status} · Risk: ${step0.risk}${anchorTag} · guidance_allowed: false`
  );

  const fragment = document.createDocumentFragment();

  const verdict = node('div', 'verdict');
  verdict.dataset.tone = tone;
  verdict.append(node('small', '', 'GÜVENLİK KAPISI KARARI'), node('h3', '', title), node('p', '', explanation));
  fragment.append(verdict);

  fragment.append(node('div', 'content-label', 'İSTEMCİ GÖSTERİM İÇERİĞİ'));
  if (report.status === 'display_allowed') {
    report.steps.forEach(step => fragment.append(node('div', 'information-card', step.display_text)));
  } else {
    fragment.append(
      node(
        'div',
        'hidden-card',
        `⊘ Atomik gizleme aktif (${report.status}): Adım metni ve alıntı cümlesi istemciye açılmadı; ancak denetim ve kaynak üstverileri aşağıda korunmaktadır.`
      )
    );
  }

  if (spatialReport && spatialCard) {
    fragment.append(node('div', 'content-label', 'SENTETİK 3D ANCHOR PROJEKSİYONU (T14 · GET /v1/demo/spatial)'));
    const spCard = node('div', 'source-card');
    const spHead = node('div', 'source-title');
    spHead.append(
      node('span', '', spatialCard.anchor_label || '3D Anchor Çizimi Bastırıldı'),
      node('span', 'source-pill', `Mod: ${spatialCard.render_mode}`)
    );
    spCard.append(spHead);
    const poseText = spatialCard.pose
      ? `(${spatialCard.pose.x}, ${spatialCard.pose.y}, ${spatialCard.pose.z}) · offset_y: ${spatialCard.pose.callout_offset_y}`
      : 'Gizlendi (pose: null)';
    const spGrid = node('div', 'kv-grid');
    spGrid.append(
      kvItem('Anchor Kimliği', spatialCard.anchor_id || 'Yok (suppressed)'),
      kvItem('3D Sahne Konumu', poseText),
      kvItem('Aktif Anchor Sayısı', String(spatialReport.active_anchor_count)),
      kvItem('Fiziksel AR Oturumu', `Kapalı (ar_session_active: ${spatialReport.ar_session_active})`)
    );
    spCard.append(spGrid);
    fragment.append(spCard);
  }

  fragment.append(node('div', 'content-label', 'DOĞRULANAN ADIM VE KAYNAK ZİNCİRİ'));
  report.steps.forEach(step => {
    const card = node('div', 'source-card');
    const heading = node('div', 'source-title');
    heading.append(
      node('span', '', reasons[step.reason_code] || 'Gösterim kontrolü'),
      node('span', 'source-pill', `Köken: ${report.source_kind}`)
    );
    card.append(heading);

    const grid = node('div', 'kv-grid');
    grid.append(
      kvItem('Hedef Parça Kimliği', step.part_id),
      kvItem('Talimat Kimliği', step.instruction_id),
      kvItem('Risk Sınıfı', riskLabels[step.risk] || step.risk),
      kvItem('Takip Durumu Girdisi', requestPayload.tracking_status),
      kvItem('Adım Durumu', step.status),
      kvItem('Neden Kodu', step.reason_code)
    );
    card.append(grid);

    if (step.citations && step.citations.length) {
      step.citations.forEach(citation => {
        const citGrid = node('div', 'kv-grid');
        citGrid.append(
          kvItem('Kaynak Belge ve Sürüm', `${citation.document_id} · v${citation.document_version}`),
          kvItem('Belge Konumu', [citation.page ? `Sayfa ${citation.page}` : '', citation.section || ''].filter(Boolean).join(' · ')),
          kvItem('Alıntı İlişkisi', citation.relation),
          kvItem('Alıntı Metni Durumu', citation.quote ? 'Açık (Doğrulandı)' : 'Gizlendi (quote: null)')
        );
        card.append(citGrid);
        card.append(node('div', 'source-detail', `Kanıt Kimliği: ${citation.evidence_id}`));
        card.append(node('div', 'source-detail', `Belge SHA-256: ${citation.checksum}`));
      });
    } else {
      card.append(node('div', 'source-meta', 'Katalog dışı parça/talimat nedeniyle eşleşen kaynak alıntısı bulunmuyor (citations: []).'));
    }

    card.append(node('div', 'source-detail', `İnceleme Bağlam Özeti (context_digest): ${report.context_digest}`));
    fragment.append(card);
  });

  appendProtocolDetails(fragment, requestPayload, report);

  const foot = node('div', 'result-foot');
  foot.append(
    node('span', '', `Katalog: ${report.catalog_id} · sürüm ${report.catalog_version}`),
    node('strong', '', 'Fiziksel işlem izni: kapalı (guidance_allowed = false)')
  );
  fragment.append(foot);
  result.replaceChildren(fragment);
}

function renderInjectionRejected(errorBody, requestPayload, elapsedMs) {
  if (errorBody.schema_version !== '1.0' || errorBody.code !== 'invalid_request') {
    throw new Error('unexpected_error_contract');
  }
  updateQuickScenarioBox(
    'blocked',
    'Yetkisiz Alan Reddedildi (invalid_request)',
    `HTTP 422 · ${elapsedMs} ms`,
    'İstemcinin gönderdiği "approval" alanı sınırda engellendi ve yanıt gövdesine yansıtılmadı.',
    'Alan: approval · Kural: extra="forbid" · guidance_allowed: false'
  );

  const fragment = document.createDocumentFragment();
  const verdict = node('div', 'verdict');
  verdict.dataset.tone = 'blocked';
  verdict.append(
    node('small', '', 'PROTOKOL SINIRI KORUMASI (HTTP 422)'),
    node('h3', '', 'Yetkisiz istemci alanı reddedildi'),
    node(
      'p',
      '',
      'İstemcinin gönderdiği "approval" alanı Pydantic extra="forbid" kuralıyla yakalandı. Gönderilen değer hata gövdesine yansıtılmadı (sanitized error).'
    )
  );
  fragment.append(verdict);

  const card = node('div', 'source-card');
  const heading = node('div', 'source-title');
  heading.append(
    node('span', '', 'Şema Doğrulama Koruması'),
    node('span', 'source-pill', 'HTTP 422 · Sanitized')
  );
  card.append(heading);
  const grid = node('div', 'kv-grid');
  grid.append(
    kvItem('Reddedilen Alan', 'approval ("client-bypass-attempt")'),
    kvItem('Sunucu Hata Kodu', errorBody.code),
    kvItem('Şema Sürümü', errorBody.schema_version),
    kvItem('Yansıma Koruması', 'Gönderilen değer yanıta yazılmadı')
  );
  card.append(grid);
  fragment.append(card);

  appendProtocolDetails(fragment, requestPayload, errorBody);
  result.replaceChildren(fragment);
}

async function evaluate() {
  if (controller) controller.abort();
  controller = new AbortController();
  const activeController = controller;
  const current = ++generation;
  const scenario = scenarios[chosen];
  runButton.disabled = true;
  safetyLatencyTag.className = 'live-tag';
  safetyLatencyTag.textContent = 'Doğrulanıyor…';
  updateQuickScenarioBox(
    'neutral',
    `${scenario.label} doğrulanıyor…`,
    'POST…',
    'Sunucu kaynak, katalog ve şema kontrollerini çalıştırıyor…',
    `İnceleme: ${scenario.payload.review_id}`
  );
  clear('Kaynak, katalog ve şema kontrolleri çalışıyor…');
  updateExportPills();

  const startedAt = performance.now();
  const timeout = setTimeout(() => activeController.abort(), 10000);
  try {
    const spatialFetch = chosen !== 'injection'
      ? fetch(`/v1/demo/spatial/${chosen}`, { credentials: 'omit', signal: activeController.signal })
      : Promise.resolve(null);
    const [response, spatialRes] = await Promise.all([
      fetch('/v1/demo/safety/evaluate', {
        method: 'POST',
        credentials: 'omit',
        signal: activeController.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenario.payload)
      }),
      spatialFetch
    ]);
    const elapsedMs = Math.round(performance.now() - startedAt);
    const body = await response.json();
    const spatialBody = spatialRes && spatialRes.ok ? await spatialRes.json() : null;
    if (current !== generation) return;

    if (chosen === 'injection' && response.status === 422) {
      safetyLatencyTag.className = 'live-tag rejected';
      safetyLatencyTag.textContent = `HTTP 422 · ${elapsedMs} ms`;
      syncMotorSchematic('injection');
      renderInjectionRejected(body, scenario.payload, elapsedMs);
      return;
    }

    if (!response.ok) throw new Error('api_unavailable');
    if (
      spatialBody &&
      (spatialBody.schema_version !== '1.0' ||
        spatialBody.guidance_allowed !== false ||
        spatialBody.ar_session_active !== false)
    ) {
      throw new Error('invalid_spatial_contract');
    }
    safetyLatencyTag.className = 'live-tag ok';
    safetyLatencyTag.textContent = `HTTP 200 · ${elapsedMs} ms`;
    syncMotorSchematic(chosen);
    render(body, scenario.payload, elapsedMs, spatialBody);
  } catch {
    if (current === generation) {
      safetyLatencyTag.className = 'live-tag rejected';
      safetyLatencyTag.textContent = 'Hata';
      syncMotorSchematic('tracking');
      updateQuickScenarioBox(
        'blocked',
        'API yanıtı alınamadı',
        'Bağlantı Hatası',
        'Sunucu bağlantısını kontrol edip yeniden deneyin.',
        'Önceki kart güvenlik gereği gizlendi'
      );
      clear('Sonuç alınamadı. API bağlantısını kontrol edip yeniden deneyin. Önceki içerik güvenlik gereği gizlendi.');
    }
  } finally {
    clearTimeout(timeout);
    if (current === generation) runButton.disabled = false;
  }
}

document.querySelectorAll('[data-scenario]').forEach(button => {
  button.addEventListener('click', () => {
    chosen = button.dataset.scenario;
    document.querySelectorAll('[data-scenario]').forEach(item => {
      const selected = item === button;
      item.classList.toggle('selected', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    evaluate();
  });
});

runButton.addEventListener('click', evaluate);

async function checkReadinessAndHealth() {
  try {
    const [healthRes, readyRes] = await Promise.all([
      fetchWithTimeout('/health', { credentials: 'omit' }, 7000),
      fetchWithTimeout('/ready', { credentials: 'omit' }, 7000)
    ]);
    if (!healthRes.ok) throw new Error('health_unavailable');
    const health = await healthRes.json();
    if (health.schema_version !== '1.0' || health.guidance_allowed !== false) {
      throw new Error('invalid_health');
    }
    sidebarOrb.classList.remove('offline');
    sidebarApiText.textContent = 'API çevrimiçi (v1.0)';
    topHealthPill.classList.remove('offline');
    topHealthPill.textContent = '● API çevrimiçi · Sentetik kip';

    if (readyRes.ok) {
      const ready = await readyRes.json();
      storage.textContent = ready.storage === 'reachable'
        ? 'Kayıt tablolarına erişiliyor (PostgreSQL/SQLite)'
        : 'Salt değerlendirme sunucusu (tablo bağlı değil)';
    } else {
      storage.textContent = 'Depolama erişilemiyor (503)';
      storage.classList.add('error-text');
    }
  } catch {
    sidebarOrb.classList.add('offline');
    sidebarApiText.textContent = 'API erişilemiyor';
    topHealthPill.classList.add('offline');
    topHealthPill.textContent = '● Bağlantı hatası';
    storage.textContent = 'Bağlantı doğrulanamadı';
    storage.classList.add('error-text');
  }
}

// --- Section 03: Deterministic Sensor Analytics ---
const sensorResult = document.querySelector('#sensor-result');
let sensorGeneration = 0;
let sensorController;
const sensorLabels = { current: 'Akım', temperature: 'Sıcaklık', vibration: 'Titreşim' };
const sensorUnits = { A: 'A', degC: '°C', 'm/s2': 'm/s²' };
const slopeUnits = { 'A/s': 'A/sn', 'degC/s': '°C/sn', '(m/s2)/s': '(m/s²)/sn' };
const slopeDirections = { positive: 'Artan eğilim (+)', negative: 'Azalan eğilim (−)', zero: 'Sabit (0)' };
const numberFormat = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 4 });

function svgNode(tag, attributes, text) {
  const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
  if (text !== undefined) element.textContent = text;
  return element;
}

function drawSeries(samples, report) {
  const chart = svgNode('svg', {
    viewBox: '0 0 620 250',
    class: 'sensor-chart',
    role: 'img',
    'aria-labelledby': 'sensor-chart-title'
  });
  chart.append(
    svgNode(
      'title',
      { id: 'sensor-chart-title' },
      `${sensorLabels[report.quantity]}: ${report.sample_count} sentetik örnek. Ham veriler aşağıdaki tabloda bulunur.`
    )
  );
  const values = samples.map(sample => sample.value);
  const start = Date.parse(samples[0].timestamp_utc);
  const times = samples.map(sample => (Date.parse(sample.timestamp_utc) - start) / 1000);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const margin = (max - min) * 0.15 || Math.max(Math.abs(max) * 0.05, 0.01);
  const low = min - margin;
  const high = max + margin;
  const lastTime = times.length ? times[times.length - 1] : 1;
  const x = time => 58 + (time / (lastTime || 1)) * 536;
  const y = value => 202 - ((value - low) / (high - low)) * 168;

  for (let i = 0; i < 4; i++) {
    const value = low + ((high - low) * i) / 3;
    const position = y(value);
    chart.append(svgNode('line', { x1: 58, x2: 594, y1: position, y2: position, stroke: '#e1eaed', 'stroke-dasharray': '3 4' }));
    chart.append(svgNode('text', { x: 48, y: position + 4, 'text-anchor': 'end' }, numberFormat.format(value)));
  }

  chart.append(svgNode('text', { x: 58, y: 18, class: 'axis-title' }, `Birim: ${sensorUnits[report.unit]} (simulated)`));
  const line = samples.map((sample, i) => `${i ? 'L' : 'M'}${x(times[i])},${y(sample.value)}`).join(' ');
  chart.append(svgNode('path', { d: line, fill: 'none', stroke: '#0a8774', 'stroke-width': 2.6, 'stroke-linejoin': 'round' }));

  const candidates = new Set(report.outliers.sample_indices);
  samples.forEach((sample, i) => {
    const isCandidate = candidates.has(i);
    const circle = svgNode('circle', {
      cx: x(times[i]),
      cy: y(sample.value),
      r: isCandidate ? 6.5 : 4.3,
      fill: isCandidate ? '#c38a31' : '#0a8774',
      stroke: '#ffffff',
      'stroke-width': 2
    });
    circle.append(
      svgNode(
        'title',
        {},
        `${i + 1}. örnek · ${times[i]} sn · ${numberFormat.format(sample.value)} ${sensorUnits[report.unit]}${isCandidate ? ' · MAD aykırı aday' : ''}`
      )
    );
    chart.append(circle);
    chart.append(svgNode('text', { x: x(times[i]), y: 225, 'text-anchor': 'middle' }, `${numberFormat.format(times[i])} sn`));
  });

  chart.append(svgNode('text', { x: 594, y: 245, 'text-anchor': 'end', class: 'axis-title' }, 'Başlangıçtan geçen süre (saniye)'));
  return chart;
}

function showSensor(payload, selected) {
  const series = payload.series;
  const report = payload.report;
  const samples = series ? series.observations : null;
  if (
    payload.schema_version !== '1.0' ||
    payload.scope !== 'synthetic_demo' ||
    payload.fixture_id !== selected ||
    !report ||
    report.quantity !== selected ||
    report.provenance !== 'simulated' ||
    report.guidance_allowed !== false ||
    !Array.isArray(samples) ||
    !samples.length ||
    samples.some(sample => sample.provenance !== 'simulated')
  ) {
    throw new Error('invalid_sensor_demo');
  }

  if (report.status !== 'summary_available') {
    sensorResult.replaceChildren(
      node('div', 'hidden-card', 'Seri özeti üretilemedi. Eksik veya geçersiz kalite nedeniyle grafik ve istatistikler gizlendi.')
    );
    return;
  }

  const fragment = document.createDocumentFragment();
  const layout = node('div', 'sensor-layout');
  const figure = node('div');
  figure.append(drawSeries(samples, report));

  const legend = node('div', 'sensor-legend');
  legend.append(
    node('i'),
    document.createTextNode('Sentetik örnek (valid)'),
    node('i'),
    document.createTextNode('MAD istatistiksel aykırı aday (eşik: 3,5)')
  );
  figure.append(legend);
  figure.append(node('div', 'source-detail', 'Dikey eksen veri aralığına göre ölçeklenir; gerçek motor çalışma sınırı gösterilmez.'));

  const stats = node('div', 'sensor-stats');
  const unit = sensorUnits[report.unit];
  const sUnit = slopeUnits[report.statistics.slope_unit] || report.statistics.slope_unit;

  const statItems = [
    ['ORTALAMA', numberFormat.format(report.statistics.mean), unit],
    ['MEDYAN', numberFormat.format(report.statistics.median), unit],
    ['EN YÜKSEK', numberFormat.format(report.statistics.maximum), unit],
    ['EN DÜŞÜK', numberFormat.format(report.statistics.minimum), unit],
    ['ZAMAN EĞİMİ', numberFormat.format(report.statistics.slope_per_second), sUnit],
    ['SÜRE VE ÖRNEK', `${numberFormat.format(report.statistics.duration_seconds)} sn`, `· ${report.sample_count} örnek`]
  ];

  statItems.forEach(([label, val, suffix]) => {
    const stat = node('div', 'sensor-stat');
    const valueNode = node('strong', '', val);
    if (suffix) valueNode.append(node('span', '', suffix));
    stat.append(node('small', '', label), valueNode);
    stats.append(stat);
  });

  const candidates = report.outliers.sample_indices;
  let description;
  if (report.outliers.status === 'zero_mad') {
    description = 'Medyan mutlak sapma (MAD) sıfır olduğu için aykırı aday hesaplanmadı.';
  } else if (report.outliers.status === 'insufficient_samples') {
    description = 'Aykırı aday değerlendirmesi için örnek sayısı yetersiz.';
  } else if (candidates.length) {
    description = `Aykırı aday: ${candidates.map(index => index + 1).join(', ')}. örnek (${slopeDirections[report.statistics.slope_direction] || ''}). Bu istatistiksel işarettir; arıza kararı değildir.`;
  } else {
    description = `Aykırı aday işaretlenmedi (${slopeDirections[report.statistics.slope_direction] || ''}). Bu durum güvenlik onayı anlamına gelmez.`;
  }
  stats.append(node('div', `sensor-candidate${candidates.length ? '' : ' neutral'}`, description));

  layout.append(figure, stats);
  fragment.append(layout);

  fragment.append(
    node(
      'div',
      'sensor-metadata',
      `Sensör Kimliği: ${report.sensor_id} · Ekipman: ${report.equipment_id} · Köken: simulated · UTC Aralığı: ${report.start_utc} → ${report.end_utc}`
    )
  );
  fragment.append(node('div', 'source-detail', `Fixture SHA-256: ${payload.fixture_checksum}`));

  const details = node('details', 'sample-details');
  details.append(node('summary', '', `Tüm ham örnek tablosunu görüntüle (${samples.length} kayıt)`));
  const table = node('table', 'sample-table');
  table.append(node('caption', '', 'Tablodaki tüm değerler simulated kökenlidir; gerçek sensör ölçümü değildir.'));
  const head = node('thead');
  const titles = node('tr');
  ['Örnek #', 'UTC Zaman Damgası', 'Geçen Süre (sn)', `Değer (${unit})`, 'Veri Kalitesi', 'MAD Durumu'].forEach(label => {
    const heading = node('th', '', label);
    heading.scope = 'col';
    titles.append(heading);
  });
  head.append(titles);
  table.append(head);

  const body = node('tbody');
  samples.forEach((sample, index) => {
    const candidate = candidates.includes(index);
    const row = node('tr', candidate ? 'candidate-row' : '');
    const elapsedSec = (Date.parse(sample.timestamp_utc) - Date.parse(samples[0].timestamp_utc)) / 1000;
    [
      index + 1,
      sample.timestamp_utc,
      numberFormat.format(elapsedSec),
      numberFormat.format(sample.value),
      sample.quality,
      candidate ? 'Aykırı aday (MAD > 3,5)' : 'Normal dağılım'
    ].forEach(value => row.append(node('td', '', String(value))));
    body.append(row);
  });
  table.append(body);
  const scroll = node('div', 'sample-scroll');
  scroll.append(table);
  details.append(scroll);
  fragment.append(details);
  sensorResult.replaceChildren(fragment);
}

async function loadSensor(selected) {
  selectedSensorKey = selected;
  updateExportPills();
  if (sensorController) sensorController.abort();
  const active = new AbortController();
  sensorController = active;
  const current = ++sensorGeneration;
  sensorResult.replaceChildren(node('div', 'empty', 'Sentetik seri analiz ediliyor…'));
  const timeout = setTimeout(() => active.abort(), 10000);
  try {
    const response = await fetch(`/v1/demo/sensors/${selected}`, { credentials: 'omit', signal: active.signal });
    if (!response.ok) throw new Error('unavailable');
    const payload = await response.json();
    if (current === sensorGeneration) showSensor(payload, selected);
  } catch {
    if (current === sensorGeneration) {
      sensorResult.replaceChildren(
        node('div', 'hidden-card', 'Sensör demosu alınamadı. Önceki grafik gizlendi; sayfayı yenileyerek yeniden deneyin.')
      );
    }
  } finally {
    clearTimeout(timeout);
  }
}

document.querySelectorAll('[data-sensor]').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('[data-sensor]').forEach(item => {
      item.classList.toggle('selected', item === button);
      item.setAttribute('aria-pressed', String(item === button));
    });
    loadSensor(button.dataset.sensor);
  });
});

// --- Section 04: Evidence & Contradiction Matrix ---
const diagnosticResult = document.querySelector('#diagnostic-result');
let diagnosticGeneration = 0;
let diagnosticController;

const hypothesisLabels = {
  demo_environment_state: 'Çevresel Koşul Test Olasılığı (demo_environment_state)',
  demo_load_state: 'Mekanik Yük Durumu Test Olasılığı (demo_load_state)'
};

const missingLabels = {
  real_motor_model: 'Seçilmiş gerçek DC motor modeli (T01)',
  reviewed_manufacturer_source: 'İncelenmiş ve lisanslı üretici teknik kılavuzu',
  validated_sensor_series: 'Gerçek düzenekten doğrulanmış sensör serisi'
};

function showDiagnostic(report) {
  if (
    report.schema_version !== '1.0' ||
    report.source_kind !== 'synthetic' ||
    report.guidance_allowed !== false ||
    !['hypotheses_available', 'needs_information', 'blocked'].includes(report.status) ||
    !Array.isArray(report.hypotheses) ||
    !Array.isArray(report.assertion_matches)
  ) {
    throw new Error('invalid_diagnostic_report');
  }

  const fragment = document.createDocumentFragment();
  if (report.status !== 'hypotheses_available') {
    const stop = node('div', 'evidence-stop');
    const incomplete = report.status === 'needs_information';
    stop.append(
      node('h3', '', incomplete ? 'Karşıt kanıt eksik: Tüm test olasılıkları gizlendi' : 'Bağlam uygun değil: Değerlendirme durduruldu'),
      node(
        'p',
        '',
        incomplete
          ? 'Katalogda tanımlı karşıt doküman kaydı değerlendirme girdisinde bulunmadığında, sistem tek taraflı doğrulama yanlılığı yaratmamak için destekleyici alıntıları tek başına göstermez.'
          : 'Analiz durumu ve katalog bağlamı değerlendirme koşullarını karşılamıyor.'
      )
    );
    report.missing_information.forEach(item => {
      stop.append(node('div', 'source-detail', `Beklenen eksik kayıt anahtarı: ${item}`));
    });
    fragment.append(stop);
  } else {
    const overview = node('div', 'diagnostic-state');
    overview.append(
      node('strong', '', `${report.hypotheses.length} doğrulanmamış katalog olasılığı listelendi`),
      document.createTextNode(' · Kart sırası olasılık derecesi belirtmez; kalibre edilmemiş yüzde güven puanı üretilmez.')
    );
    fragment.append(overview);

    const grid = node('div', 'hypothesis-grid');
    report.hypotheses.forEach(hypothesis => {
      const card = node('article', 'hypothesis');
      const head = node('div', 'hypothesis-header');
      const conflicting = hypothesis.uncertainty === 'conflicting_evidence';
      const sourceMatches = report.assertion_matches.filter(match => match.rule_code === hypothesis.code);
      if (!sourceMatches.some(match => match.relation === 'supports')) throw new Error('unbound_hypothesis');

      const supCount = sourceMatches.filter(m => m.relation === 'supports').length;
      const conCount = sourceMatches.filter(m => m.relation === 'contradicts').length;

      head.append(
        node(
          'span',
          `hypothesis-badge${conflicting ? ' conflicting' : ''}`,
          conflicting
            ? `ÇELİŞKİLİ KANIT (${supCount} Destek · ${conCount} Karşıt)`
            : `DOĞRULANMADI (${supCount} Destek · 0 Karşıt)`
        ),
        node('h3', '', hypothesisLabels[hypothesis.code] || hypothesis.code),
        node('p', '', hypothesis.explanation)
      );

      const citations = node('div', 'hypothesis-citations');
      sourceMatches.forEach(match => {
        if (!['supports', 'contradicts'].includes(match.relation) || !match.evidence_id || !match.document_version || !(match.page || match.section)) {
          throw new Error('invalid_citation');
        }
        const citation = node('div', `diagnostic-citation ${match.relation}`);
        citation.append(
          node('div', 'relation-label', match.relation === 'supports' ? '＋ DESTEKLEYEN DOKÜMAN KAYDI' : '− KARŞIT (DIŞLAYICI) DOKÜMAN KAYDI'),
          node('p', 'diagnostic-quote', match.quote),
          node('div', 'source-meta', `Belge: ${match.document_id} · sürüm ${match.document_version} · ${[match.page ? `Sayfa ${match.page}` : '', match.section].filter(Boolean).join(' · ')}`),
          node('div', 'source-detail', `Kanıt Kimliği: ${match.evidence_id}`),
          node('div', 'source-detail', `Belge SHA-256: ${match.checksum}`)
        );
        citations.append(citation);
      });

      const missing = node('div', 'diagnostic-missing');
      missing.append(node('strong', '', 'Gerçek mühendislik doğrulaması için hâlâ gerekenler:'));
      hypothesis.missing_information.forEach(item => {
        missing.append(node('div', '', `• ${missingLabels[item] || item}`));
      });
      citations.append(missing);
      card.append(head, citations);
      grid.append(card);
    });
    fragment.append(grid);
  }

  const foot = node('div', 'result-foot');
  foot.append(
    node('span', '', `İstek: ${report.request_id} · Katalog: ${report.catalog_id} (${report.catalog_version})`),
    node('strong', '', 'Fiziksel işlem izni: kapalı (guidance_allowed = false)')
  );
  fragment.append(foot);
  diagnosticResult.replaceChildren(fragment);
}

async function loadDiagnostic(selected) {
  selectedDiagKey = selected;
  updateExportPills();
  if (diagnosticController) diagnosticController.abort();
  const active = new AbortController();
  diagnosticController = active;
  const current = ++diagnosticGeneration;
  diagnosticResult.replaceChildren(node('div', 'empty', 'Kaynak ve karşıt kayıt bağları kontrol ediliyor…'));
  const timeout = setTimeout(() => active.abort(), 10000);
  try {
    const response = await fetch(`/v1/demo/diagnostic/${selected}`, { credentials: 'omit', signal: active.signal });
    if (!response.ok) throw new Error('unavailable');
    const report = await response.json();
    if (current === diagnosticGeneration) showDiagnostic(report);
  } catch {
    if (current === diagnosticGeneration) {
      diagnosticResult.replaceChildren(
        node('div', 'hidden-card', 'Kaynaklı demo raporu alınamadı. Önceki olasılıklar gizlendi; sayfayı yenileyerek yeniden deneyin.')
      );
    }
  } finally {
    clearTimeout(timeout);
  }
}

document.querySelectorAll('[data-diagnostic]').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('[data-diagnostic]').forEach(item => {
      item.classList.toggle('selected', item === button);
      item.setAttribute('aria-pressed', String(item === button));
    });
    loadDiagnostic(button.dataset.diagnostic);
  });
});

// --- Section 05: Reproducible Synthetic Benchmark & RAG Cache ---
const benchmarkResult = document.querySelector('#benchmark-result');
const runBenchmarkButton = document.querySelector('#run-benchmark');
let benchmarkGeneration = 0;

function showBenchmark(report) {
  if (
    report.schema_version !== '1.0' ||
    report.scope !== 'synthetic_fixture_benchmark' ||
    report.physical_device_validated !== false ||
    report.calibrated_probabilities !== false ||
    report.guidance_allowed !== false
  ) {
    throw new Error('invalid_benchmark_contract');
  }
  const fragment = document.createDocumentFragment();
  const banner = node('div', 'verdict');
  banner.dataset.tone = report.all_synthetic_gates_passed ? 'success' : 'blocked';
  banner.append(
    node('small', '', `PAKET: ${report.suite_id} · SÜRE: ${numberFormat.format(report.total_duration_ms)} ms`),
    node(
      'h3',
      '',
      report.all_synthetic_gates_passed
        ? 'Tüm dondurulmuş sentetik doğrulama kapıları başarıyla geçti'
        : 'Sentetik benchmark kapılarında ihlal saptandı'
    ),
    node(
      'p',
      '',
      'Aşağıdaki metrikler gerçek zamanlı olarak sentetik görüntü, RAG koleksiyonu, tanı matrisi, 3D anchor bağlayıcı ve SQLite kalıcı onay akışı üzerinde doğrulanmıştır.'
    )
  );
  fragment.append(banner);

  const grid = node('div', 'benchmark-grid');

  const visCard = node('article', 'bench-card');
  const visHead = node('div', 'bench-card-head');
  visHead.append(
    node('h3', '', 'Görüntü İşleme Kapısı (T05 · ORB/RANSAC)'),
    node('span', 'source-pill', `${report.vision.frames_evaluated} Sentetik Kare`)
  );
  const visKv = node('div', 'kv-grid');
  visKv.append(
    kvItem('Sentetik Precision / Recall', `${numberFormat.format(report.vision.precision)} / ${numberFormat.format(report.vision.recall)}`),
    kvItem('Sentetik F1 Skoru', numberFormat.format(report.vision.f1)),
    kvItem('Yanlış Pozitif / Negatif', `${report.vision.false_positives} / ${report.vision.false_negatives}`),
    kvItem('Perspektif Köşe Sapması', `${numberFormat.format(report.vision.warped_max_corner_error_px)} px`)
  );
  visCard.append(visHead, visKv);

  const ragCard = node('article', 'bench-card');
  const ragHead = node('div', 'bench-card-head');
  ragHead.append(
    node('h3', '', 'RAG & İçerik Adresli Önbellek (T04 · Hafta 11)'),
    node('span', 'source-pill', `${report.rag.documents_indexed} Belge · ${report.rag.chunks_indexed} Parça`)
  );
  const ragKv = node('div', 'kv-grid');
  ragKv.append(
    kvItem('Kaynak Konum Tamlığı', `%${numberFormat.format(report.rag.citation_locator_rate * 100)} (Desteksiz: ${report.rag.unsupported_claim_count})`),
    kvItem('Ekipmanlar Arası Sızıntı', `${report.rag.cross_equipment_leakage_count} kayıt`),
    kvItem('Önbellek İsabet / Iska', `${report.rag.cache_hits} hit / ${report.rag.cache_misses} miss`),
    kvItem('Soğuk vs Sıcak Sorgu', `${numberFormat.format(report.rag.cold_query_ms)} ms → ${numberFormat.format(report.rag.warm_query_ms)} ms`)
  );
  ragCard.append(ragHead, ragKv);

  const diagCard = node('article', 'bench-card');
  const diagHead = node('div', 'bench-card-head');
  diagHead.append(
    node('h3', '', 'Supervisor & Tanı Matrisi (T06–T08)'),
    node('span', 'source-pill', `${report.diagnostic.sensor_series_verified} Sensör Serisi`)
  );
  const diagKv = node('div', 'kv-grid');
  diagKv.append(
    kvItem('LangGraph Devir Durumu', report.diagnostic.supervisor_handoff_ready ? 'Hazır (ready_for_diagnostic)' : 'Hata'),
    kvItem('Karşıt Kanıt Korunumu', report.diagnostic.contradiction_preserved ? 'Korundu (page 4)' : 'Eksik'),
    kvItem('Eksik Kanıtta Susma', report.diagnostic.missing_counter_evidence_abstained ? 'Doğrulandı (0 hipotez)' : 'İhlal'),
    kvItem('Sensör Köken Doğrulaması', 'simulated (3/3 seri)')
  );
  diagCard.append(diagHead, diagKv);

  const safeCard = node('article', 'bench-card');
  const safeHead = node('div', 'bench-card-head');
  safeHead.append(
    node('h3', '', 'Güvenlik, Onay & 3D Anchor (T09–T10 · T14)'),
    node('span', 'source-pill', `${report.safety_spatial.checks_passed}/${report.safety_spatial.checks_total} Kontrol`)
  );
  const safeKv = node('div', 'kv-grid');
  safeKv.append(
    kvItem('Güvenlik İhlali Sayısı', String(report.safety_spatial.safety_violations)),
    kvItem('Takip Kaybı Anchor Silme', report.safety_spatial.tracking_loss_suppressed ? 'Doğrulandı' : 'İhlal'),
    kvItem('Bilinmeyen Parça Engeli', report.safety_spatial.unknown_anchor_suppressed ? 'Doğrulandı' : 'İhlal'),
    kvItem('Replay & Özet Kurcalama', report.safety_spatial.replay_token_rejected && report.safety_spatial.digest_tamper_rejected ? 'Reddedildi (SQLite)' : 'İhlal')
  );
  safeCard.append(safeHead, safeKv);

  grid.append(visCard, ragCard, diagCard, safeCard);
  fragment.append(grid);

  if (Array.isArray(report.open_hardware_gates) && report.open_hardware_gates.length) {
    fragment.append(node('div', 'content-label', 'AÇIK DONANIM VE SAHA DOĞRULAMA KAPILARI (BAŞARI İDDİASI YAPILMAZ)'));
    const gates = node('div', 'gate-list');
    report.open_hardware_gates.forEach(gate => {
      const item = node('div', 'gate-item');
      item.append(node('strong', '', gate.gate_id), node('p', '', gate.summary));
      gates.append(item);
    });
    fragment.append(gates);
  }

  const digestDetails = node('details', 'sample-details');
  const digestEntries = Object.entries(report.fixture_digests || {});
  digestDetails.append(node('summary', '', `Dondurulmuş sentetik girdi SHA-256 özetleri (${digestEntries.length} dosya)`));
  const digestBox = node('div', 'source-card');
  digestEntries.forEach(([path, sha]) => {
    digestBox.append(node('div', 'source-detail', `${path}: ${sha}`));
  });
  digestDetails.append(digestBox);
  fragment.append(digestDetails);

  benchmarkResult.replaceChildren(fragment);
}

async function loadBenchmark() {
  if (!benchmarkResult) return;
  const current = ++benchmarkGeneration;
  if (runBenchmarkButton) runBenchmarkButton.disabled = true;
  benchmarkResult.replaceChildren(node('div', 'empty', 'Sentetik benchmark paketi doğrulanıyor…'));
  try {
    const response = await fetchWithTimeout('/v1/demo/evaluation', { credentials: 'omit' }, 15000);
    if (!response.ok) throw new Error('benchmark_unavailable');
    const report = await response.json();
    if (current === benchmarkGeneration) showBenchmark(report);
  } catch {
    if (current === benchmarkGeneration) {
      benchmarkResult.replaceChildren(
        node('div', 'hidden-card', 'Sentetik benchmark raporu alınamadı; önceki metrikler gizlendi.')
      );
    }
  } finally {
    if (current === benchmarkGeneration && runBenchmarkButton) runBenchmarkButton.disabled = false;
  }
}

if (runBenchmarkButton) {
  runBenchmarkButton.addEventListener('click', loadBenchmark);
}

// --- Section 06: Unified Independent JSON Audit Export ---
const exportButton = document.querySelector('#export-report');
const exportStatus = document.querySelector('#export-status');

exportButton.addEventListener('click', async () => {
  const safeSafety = ['information', 'critical', 'tracking', 'unknown'].includes(chosen) ? chosen : 'information';
  const parameters = new URLSearchParams({
    safety: safeSafety,
    sensor: selectedSensorKey,
    diagnostic: selectedDiagKey
  });
  exportButton.disabled = true;
  exportStatus.textContent = 'Seçimler sunucuda yeniden değerlendiriliyor; rapor hazırlanıyor…';
  try {
    const response = await fetchWithTimeout(`/v1/demo/report?${parameters}`, { credentials: 'omit' }, 15000);
    if (!response.ok) throw new Error('export_unavailable');
    const report = await response.json();
    if (
      report.schema_version !== '1.0' ||
      report.scope !== 'synthetic_demo' ||
      report.independent_sections !== true ||
      report.guidance_allowed !== false
    ) {
      throw new Error('invalid_export');
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `holoassist-demo-${report.export_id}.json`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    exportStatus.textContent = `Rapor hazırlandı (${safeSafety} · ${selectedSensorKey} · ${selectedDiagKey}); indirme başlatıldı.`;
  } catch {
    exportStatus.textContent = 'Rapor oluşturulamadı. Hiçbir dosya indirilmedi; yeniden deneyin.';
  } finally {
    exportButton.disabled = false;
  }
});

// Boot all sections synchronously without race conditions
updateExportPills();
checkReadinessAndHealth();
evaluate();
loadSensor('current');
loadDiagnostic('complete');
loadBenchmark();
