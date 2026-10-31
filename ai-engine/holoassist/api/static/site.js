'use strict';

function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function svgEl(tag, attrs, text) {
  const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, String(value)));
  if (text !== undefined) element.textContent = text;
  return element;
}

const trNumber = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 3 });

// --- 1. Live System Telemetry (/health & /ready) ---
const apiDot = document.querySelector('#api-dot');
const apiLiveLabel = document.querySelector('#api-live-label');
const heroHealthValue = document.querySelector('#hero-health-value');
const heroReadyValue = document.querySelector('#hero-ready-value');

async function checkSystemStatus() {
  try {
    const [healthRes, readyRes] = await Promise.all([
      fetch('/health', { credentials: 'omit', signal: AbortSignal.timeout(6000) }),
      fetch('/ready', { credentials: 'omit', signal: AbortSignal.timeout(6000) })
    ]);
    if (!healthRes.ok) throw new Error('health_failed');
    const health = await healthRes.json();
    if (health.schema_version !== '1.0' || health.guidance_allowed !== false) {
      throw new Error('invalid_health_contract');
    }
    apiDot.classList.remove('offline');
    apiDot.classList.add('online');
    apiLiveLabel.textContent = 'API çevrimiçi · synthetic_demo · guidance_allowed: false';
    heroHealthValue.textContent = 'Çevrimiçi (sürüm 1.0 · sentetik)';

    if (readyRes.ok) {
      const ready = await readyRes.json();
      heroReadyValue.textContent = ready.storage === 'reachable'
        ? 'Erişilebilir (kalıcı tablo bağlı)'
        : 'Salt değerlendirme kipi';
    } else {
      heroReadyValue.textContent = 'Depolama erişilemiyor (503)';
    }
  } catch {
    apiDot.classList.remove('online');
    apiDot.classList.add('offline');
    apiLiveLabel.textContent = 'API bağlantısı doğrulanamadı';
    heroHealthValue.textContent = 'Bağlantı yok';
    heroReadyValue.textContent = 'Doğrulanamadı';
  }
}

// --- 2. Module Tab Navigation ---
const moduleTabs = document.querySelectorAll('[data-module]');
const modulePanels = {
  safety: document.querySelector('#panel-safety'),
  sensors: document.querySelector('#panel-sensors'),
  diagnostic: document.querySelector('#panel-diagnostic'),
  benchmark: document.querySelector('#panel-benchmark')
};
let sensorsInitialized = false;
let diagnosticInitialized = false;
let benchmarkInitialized = false;

moduleTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const selectedModule = tab.dataset.module;
    moduleTabs.forEach(item => {
      const isSelected = item === tab;
      item.classList.toggle('active', isSelected);
      item.setAttribute('aria-selected', String(isSelected));
    });
    Object.entries(modulePanels).forEach(([key, panel]) => {
      if (panel) panel.classList.toggle('hidden', key !== selectedModule);
    });
    if (selectedModule === 'sensors' && !sensorsInitialized) {
      sensorsInitialized = true;
      loadSensorSeries(activeSensor);
    }
    if (selectedModule === 'diagnostic' && !diagnosticInitialized) {
      diagnosticInitialized = true;
      loadDiagnosticScenario(activeDiagnostic);
    }
    if (selectedModule === 'benchmark' && !benchmarkInitialized) {
      benchmarkInitialized = true;
      loadSiteBenchmark();
    }
  });
});

// --- 3. Safety Gate Live Sandbox ---
const safetyScenarios = {
  information: {
    payload: {
      schema_version: '1.0',
      review_id: 'site-demo-information',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'tracked',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-information', part_id: 'demo-label' }]
    },
    rigBadge: 'Parça: demo-label',
    rigCallout: 'demo-label · Kaynak doğrulandı'
  },
  critical: {
    payload: {
      schema_version: '1.0',
      review_id: 'site-demo-critical',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'tracked',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-critical', part_id: 'demo-critical-part' }]
    },
    rigBadge: 'Parça: demo-critical-part',
    rigCallout: 'Kritik adım · İnsan onayı gerekli'
  },
  tracking: {
    payload: {
      schema_version: '1.0',
      review_id: 'site-demo-tracking',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'lost',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-information', part_id: 'demo-label' }]
    },
    rigBadge: 'Takip: lost',
    rigCallout: 'Takip kaybı · Kart gizlendi'
  },
  unknown: {
    payload: {
      schema_version: '1.0',
      review_id: 'site-demo-unknown',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'tracked',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-information', part_id: 'unknown-part' }]
    },
    rigBadge: 'Parça: unknown-part',
    rigCallout: 'Katalog uyuşmazlığı · Engellendi'
  },
  injection: {
    payload: {
      schema_version: '1.0',
      review_id: 'site-demo-injection',
      analysis_request_id: 'synthetic-analysis-demo-1',
      tracking_status: 'tracked',
      approval: 'client-bypass-attempt',
      steps: [{ step_id: 'step-1', instruction_id: 'demo-critical', part_id: 'demo-critical-part' }]
    },
    rigBadge: 'Protokol: HTTP 422',
    rigCallout: 'Yetkisiz alan reddedildi (422)'
  }
};

const verdictCopy = {
  display_allowed: [
    'Gösterim Onaylandı (Yalnızca Sentetik Bilgi)',
    'Kaynak alıntısı, sayfa/bölüm ve parça eşleşmesi doğrulandı. Fiziksel işlem izni kapalıdır.',
    'ok'
  ],
  needs_approval: [
    'Kalıcı İnsan Onayı Gerekli',
    'Kritik adım içeriği ve alıntıları atomik olarak gizlendi. Yalnızca sunucu tarafı yetkili inceleyici kaydıyla değerlendirilebilir.',
    'warning'
  ],
  needs_information: [
    'Takip Doğrulanamadı (Ek Bilgi Gerekli)',
    'Parça takibi "lost" durumunda olduğu için önceki bilgi kartı güvenlik gereği düşürüldü.',
    'warning'
  ],
  blocked: [
    'Güvenlik Kapısı Tarafından Engellendi',
    'Gönderilen parça veya talimat kimliği doğrulanmış katalogla eşleşmedi; metin gösterilmiyor.',
    'blocked'
  ]
};

const reasonCopy = {
  synthetic_information_only: 'Kaynağa bağlı sentetik bilgilendirme',
  persistent_approval_required: 'Kalıcı insan onayı zorunluluğu',
  tracking_required: 'Doğrulanmış parça takibi zorunluluğu',
  part_mismatch: 'Parça kimliği katalogla uyuşmuyor',
  unknown_instruction: 'Talimat kimliği katalogda tanımsız',
  source_binding_missing: 'Zorunlu kaynak bağı eksik',
  contradictory_source: 'Kaynaklar arası çelişki saptandı'
};

let activeSafety = 'information';
let safetyGen = 0;
let safetyAbort;

const safetyRendered = document.querySelector('#safety-rendered');
const safetyHttpMeta = document.querySelector('#safety-http-meta');
const safetyDigestShort = document.querySelector('#safety-digest-short');
const safetyReqJson = document.querySelector('#safety-req-json');
const safetyResJson = document.querySelector('#safety-res-json');
const rigActiveBadge = document.querySelector('#rig-active-badge');
const svgCalloutText = document.querySelector('#svg-callout-text');

function validateSafetyReport(report) {
  if (
    report.schema_version !== '1.0' ||
    report.guidance_allowed !== false ||
    report.source_kind !== 'synthetic' ||
    !Object.hasOwn(verdictCopy, report.status) ||
    !Array.isArray(report.steps) ||
    !report.steps.length
  ) {
    throw new Error('invalid_safety_contract');
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
    throw new Error('invalid_display_citations');
  }
}

function renderSafetySuccess(report) {
  validateSafetyReport(report);
  const [title, desc, tone] = verdictCopy[report.status];
  const frag = document.createDocumentFragment();

  const banner = el('div', 'verdict-banner');
  banner.dataset.tone = tone;
  banner.append(el('h4', '', title), el('p', '', desc));
  frag.append(banner);

  if (report.status === 'display_allowed') {
    report.steps.forEach(step => {
      frag.append(el('div', 'quote-box', step.display_text));
    });
  } else {
    frag.append(
      el(
        'div',
        'redacted-box',
        '⊘ Atomik gizleme aktif: Adım metni ve doküman alıntıları istemciye açılmadı.'
      )
    );
  }

  report.steps.forEach(step => {
    const card = el('div', 'citation-card');
    const row = el('div', 'citation-row');
    row.append(
      el('span', '', reasonCopy[step.reason_code] || step.reason_code),
      el('span', '', `Fiziksel izin: kapalı · Köken: ${report.source_kind}`)
    );
    card.append(row);

    if (step.citations && step.citations.length) {
      step.citations.forEach(cit => {
        card.append(
          el(
            'div',
            '',
            `Belge: ${cit.document_id} (sürüm ${cit.document_version}) · Sayfa ${cit.page} · ${cit.section}`
          )
        );
        card.append(el('div', 'citation-mono', `Kanıt ID: ${cit.evidence_id}`));
        card.append(el('div', 'citation-mono', `SHA-256: ${cit.checksum}`));
      });
    } else {
      card.append(el('div', 'citation-mono', 'Bu karar durumunda kaynak alıntısı paylaşılmaz.'));
    }
    frag.append(card);
  });

  safetyDigestShort.textContent = `digest: ${String(report.context_digest).slice(0, 18)}…`;
  safetyRendered.replaceChildren(frag);
}

function renderInjectionRejection(errorBody) {
  if (errorBody.schema_version !== '1.0' || errorBody.code !== 'invalid_request') {
    throw new Error('unexpected_error_contract');
  }
  const frag = document.createDocumentFragment();
  const banner = el('div', 'verdict-banner');
  banner.dataset.tone = 'blocked';
  banner.append(
    el('h4', '', 'Sözleşme Sınırında Reddedildi (HTTP 422)'),
    el(
      'p',
      '',
      'İstemcinin gönderdiği yetkisiz "approval" alanı Pydantic extra="forbid" kuralıyla yakalandı. Gönderilen değer yanıt gövdesine yansıtılmadı.'
    )
  );
  frag.append(banner);
  frag.append(
    el(
      'div',
      'redacted-box',
      '✔ Güvenlik doğrulaması başarılı: İstemci kendi kendine onay (approval) veya katalog yetkisi veremez.'
    )
  );
  safetyDigestShort.textContent = 'code: invalid_request (sanitized)';
  safetyRendered.replaceChildren(frag);
}

async function runSafetyScenario(key) {
  safetyAbort?.abort();
  const controller = new AbortController();
  safetyAbort = controller;
  const currentGen = ++safetyGen;
  const config = safetyScenarios[key];

  rigActiveBadge.textContent = config.rigBadge;
  svgCalloutText.textContent = config.rigCallout;

  safetyRendered.replaceChildren(el('div', 'placeholder-box', 'Sunucu yanıtı doğrulanıyor…'));
  safetyReqJson.textContent = JSON.stringify(config.payload, null, 2);
  safetyResJson.textContent = '// Yanıt bekleniyor…';
  safetyHttpMeta.className = 'meta-pill';
  safetyHttpMeta.textContent = 'İstek gönderiliyor…';

  const startedAt = performance.now();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch('/v1/demo/safety/evaluate', {
      method: 'POST',
      credentials: 'omit',
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config.payload)
    });
    const elapsedMs = Math.round(performance.now() - startedAt);
    const body = await response.json();
    if (currentGen !== safetyGen) return;

    safetyResJson.textContent = JSON.stringify(body, null, 2);

    if (key === 'injection' && response.status === 422) {
      safetyHttpMeta.className = 'meta-pill rejected';
      safetyHttpMeta.textContent = `HTTP 422 · ${elapsedMs} ms (yerel)`;
      renderInjectionRejection(body);
      return;
    }

    if (!response.ok) throw new Error('unexpected_http_status');
    safetyHttpMeta.className = 'meta-pill ok';
    safetyHttpMeta.textContent = `HTTP 200 · ${elapsedMs} ms (yerel)`;
    renderSafetySuccess(body);
  } catch {
    if (currentGen !== safetyGen) return;
    safetyHttpMeta.className = 'meta-pill rejected';
    safetyHttpMeta.textContent = 'Bağlantı / doğrulama hatası';
    safetyResJson.textContent = '// Yanıt doğrulanamadı';
    safetyRendered.replaceChildren(
      el('div', 'redacted-box', 'API yanıtı alınamadı veya sözleşme doğrulamasından geçemedi; önceki kart gizlendi.')
    );
  } finally {
    clearTimeout(timer);
  }
}

document.querySelectorAll('[data-safety]').forEach(btn => {
  btn.addEventListener('click', () => {
    activeSafety = btn.dataset.safety;
    document.querySelectorAll('[data-safety]').forEach(item => {
      const selected = item === btn;
      item.classList.toggle('selected', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    runSafetyScenario(activeSafety);
  });
});

// --- 4. Deterministic Sensor Telemetry Tab ---
const sensorNames = { current: 'Akım', temperature: 'Sıcaklık', vibration: 'Titreşim' };
const unitSymbols = { A: 'A', degC: '°C', 'm/s2': 'm/s²' };
let activeSensor = 'current';
let sensorGen = 0;
let sensorAbort;
const siteSensorOutput = document.querySelector('#site-sensor-output');

function buildSensorSvg(samples, report) {
  const unit = unitSymbols[report.unit] || report.unit;
  const svg = svgEl('svg', {
    viewBox: '0 0 620 235',
    class: 'site-chart',
    role: 'img',
    'aria-label': `${sensorNames[report.quantity]} sentetik zaman serisi grafiği`
  });

  const values = samples.map(s => s.value);
  const t0 = Date.parse(samples[0].timestamp_utc);
  const times = samples.map(s => (Date.parse(s.timestamp_utc) - t0) / 1000);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const pad = (maxVal - minVal) * 0.16 || Math.max(Math.abs(maxVal) * 0.05, 0.01);
  const low = minVal - pad;
  const high = maxVal + pad;

  const mapX = t => 56 + (t / (times.at(-1) || 1)) * 536;
  const mapY = v => 192 - ((v - low) / (high - low)) * 156;

  for (let i = 0; i < 4; i++) {
    const val = low + ((high - low) * i) / 3;
    const py = mapY(val);
    svg.append(svgEl('line', { x1: 56, x2: 592, y1: py, y2: py, stroke: '#dce6ea', 'stroke-dasharray': '3 4' }));
    svg.append(svgEl('text', { x: 46, y: py + 4, 'text-anchor': 'end' }, trNumber.format(val)));
  }

  svg.append(svgEl('text', { x: 56, y: 20 }, `Birim: ${unit} (simulated)`));
  const d = samples.map((s, idx) => `${idx ? 'L' : 'M'}${mapX(times[idx])},${mapY(s.value)}`).join(' ');
  svg.append(svgEl('path', { d, fill: 'none', stroke: '#0b8a77', 'stroke-width': 2.6, 'stroke-linejoin': 'round' }));

  const outlierSet = new Set(report.outliers.sample_indices);
  samples.forEach((s, idx) => {
    const isOutlier = outlierSet.has(idx);
    svg.append(
      svgEl('circle', {
        cx: mapX(times[idx]),
        cy: mapY(s.value),
        r: isOutlier ? 6.5 : 4.2,
        fill: isOutlier ? '#d97706' : '#0b8a77',
        stroke: '#ffffff',
        'stroke-width': 2
      })
    );
    svg.append(svgEl('text', { x: mapX(times[idx]), y: 216, 'text-anchor': 'middle' }, `${trNumber.format(times[idx])}s`));
  });

  return svg;
}

function renderSensorView(payload, expected) {
  const { series, report } = payload;
  const samples = series?.observations;
  if (
    payload.schema_version !== '1.0' ||
    payload.scope !== 'synthetic_demo' ||
    payload.fixture_id !== expected ||
    report?.quantity !== expected ||
    report?.provenance !== 'simulated' ||
    report?.guidance_allowed !== false ||
    !Array.isArray(samples) ||
    !samples.length ||
    samples.some(s => s.provenance !== 'simulated')
  ) {
    throw new Error('invalid_sensor_contract');
  }

  if (report.status !== 'summary_available') {
    siteSensorOutput.replaceChildren(
      el('div', 'redacted-box', 'Veri kalitesi kısıtı nedeniyle özet istatistikler gizlendi.')
    );
    return;
  }

  const unit = unitSymbols[report.unit] || report.unit;
  const grid = el('div', 'sensor-grid');
  const left = el('div');
  left.append(buildSensorSvg(samples, report));
  left.append(
    el(
      'div',
      'citation-mono',
      `Sensör: ${report.sensor_id} · Köken: simulated · Fixture SHA-256: ${payload.fixture_checksum}`
    )
  );

  const right = el('div', 'kpi-grid');
  [
    ['ORTALAMA', `${trNumber.format(report.statistics.mean)} ${unit}`],
    ['MEDYAN', `${trNumber.format(report.statistics.median)} ${unit}`],
    ['MAKSİMUM', `${trNumber.format(report.statistics.maximum)} ${unit}`],
    ['MİNİMUM', `${trNumber.format(report.statistics.minimum)} ${unit}`],
    ['ZAMAN EĞİMİ', `${trNumber.format(report.statistics.slope_per_second)} ${report.statistics.slope_unit}`],
    ['SÜRE / ÖRNEK', `${trNumber.format(report.statistics.duration_seconds)}s · ${report.sample_count}`]
  ].forEach(([label, val]) => {
    const box = el('div', 'kpi-box');
    box.append(el('small', '', label), el('strong', '', val));
    right.append(box);
  });

  const indices = report.outliers.sample_indices;
  const note = indices.length
    ? `${indices.map(i => i + 1).join(', ')}. örnek MAD tabanlı istatistiksel aykırı adaydır. Bu bir motor arıza kararı değildir.`
    : 'İstatistiksel aykırı aday işaretlenmedi. Bu durum güvenli çalışma onayı anlamına gelmez.';
  right.append(el('div', `candidate-callout${indices.length ? '' : ' neutral'}`, note));

  grid.append(left, right);
  siteSensorOutput.replaceChildren(grid);
}

async function loadSensorSeries(sensorKey) {
  sensorAbort?.abort();
  const controller = new AbortController();
  sensorAbort = controller;
  const currentGen = ++sensorGen;
  siteSensorOutput.replaceChildren(el('div', 'placeholder-box', 'Sentetik sensör serisi analiz ediliyor…'));
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const res = await fetch(`/v1/demo/sensors/${sensorKey}`, { credentials: 'omit', signal: controller.signal });
    if (!res.ok) throw new Error('sensor_http_error');
    const data = await res.json();
    if (currentGen === sensorGen) renderSensorView(data, sensorKey);
  } catch {
    if (currentGen === sensorGen) {
      siteSensorOutput.replaceChildren(el('div', 'redacted-box', 'Sensör verisi doğrulanamadı; önceki grafik kaldırıldı.'));
    }
  } finally {
    clearTimeout(timer);
  }
}

document.querySelectorAll('[data-sensor-pick]').forEach(btn => {
  btn.addEventListener('click', () => {
    activeSensor = btn.dataset.sensorPick;
    document.querySelectorAll('[data-sensor-pick]').forEach(item => {
      const selected = item === btn;
      item.classList.toggle('selected', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    loadSensorSeries(activeSensor);
  });
});

// --- 5. Evidence & Contradiction Diagnostic Tab ---
const diagTitles = {
  demo_environment_state: 'Çevresel Koşul Test Olasılığı (demo_environment_state)',
  demo_load_state: 'Mekanik Yük Durumu Test Olasılığı (demo_load_state)'
};
const missingDict = {
  real_motor_model: 'Gerçek motor modeli',
  reviewed_manufacturer_source: 'İncelenmiş üretici kılavuzu',
  validated_sensor_series: 'Doğrulanmış sensör serisi'
};
let activeDiagnostic = 'complete';
let diagGen = 0;
let diagAbort;
const siteDiagOutput = document.querySelector('#site-diag-output');

function renderDiagnosticView(report) {
  if (
    report.schema_version !== '1.0' ||
    report.source_kind !== 'synthetic' ||
    report.guidance_allowed !== false ||
    !['hypotheses_available', 'needs_information', 'blocked'].includes(report.status) ||
    !Array.isArray(report.hypotheses) ||
    !Array.isArray(report.assertion_matches)
  ) {
    throw new Error('invalid_diagnostic_contract');
  }

  if (report.status !== 'hypotheses_available') {
    const box = el('div', 'verdict-banner');
    box.dataset.tone = 'warning';
    box.append(
      el('h4', '', 'Karşıt Kanıt Eksikliği Nedeniyle Olasılıklar Gizlendi'),
      el(
        'p',
        '',
        'Beklenen karşıt kayıt değerlendirme girdisinde bulunmadığında sistem tek taraflı destekleyici alıntıları göstermez ve tüm test olasılıklarını saklar.'
      )
    );
    report.missing_information.forEach(item => {
      box.append(el('div', 'citation-mono', `Eksik kanıt: ${item}`));
    });
    siteDiagOutput.replaceChildren(box);
    return;
  }

  const wrap = el('div', 'diag-cards');
  report.hypotheses.forEach(hyp => {
    const card = el('article', 'diag-card');
    const badgeText = hyp.uncertainty === 'conflicting_evidence' ? 'ÇELİŞKİLİ KANIT KORUNDU' : 'DOĞRULANMADI';
    card.append(
      el('span', 'diag-badge', badgeText),
      el('h4', '', diagTitles[hyp.code] || hyp.code),
      el('p', 'helper-copy', hyp.explanation)
    );

    const matches = report.assertion_matches.filter(m => m.rule_code === hyp.code);
    matches.forEach(m => {
      const ev = el('div', `evidence-item ${m.relation}`);
      ev.append(
        el('div', 'evidence-role', m.relation === 'supports' ? '＋ DESTEKLEYEN KAYIT' : '− KARŞIT KAYIT'),
        el('div', '', m.quote),
        el('div', 'citation-mono', `${m.document_id} (sürüm ${m.document_version}) · Sayfa ${m.page} · ${m.section}`)
      );
      card.append(ev);
    });

    if (hyp.missing_information?.length) {
      const reqs = hyp.missing_information.map(k => missingDict[k] || k).join(', ');
      card.append(el('div', 'citation-mono', `Gerçek doğrulama için eksik: ${reqs}`));
    }
    wrap.append(card);
  });

  siteDiagOutput.replaceChildren(wrap);
}

async function loadDiagnosticScenario(diagKey) {
  diagAbort?.abort();
  const controller = new AbortController();
  diagAbort = controller;
  const currentGen = ++diagGen;
  siteDiagOutput.replaceChildren(el('div', 'placeholder-box', 'Kaynak ve karşıt kanıt bağları denetleniyor…'));
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const res = await fetch(`/v1/demo/diagnostic/${diagKey}`, { credentials: 'omit', signal: controller.signal });
    if (!res.ok) throw new Error('diag_http_error');
    const data = await res.json();
    if (currentGen === diagGen) renderDiagnosticView(data);
  } catch {
    if (currentGen === diagGen) {
      siteDiagOutput.replaceChildren(el('div', 'redacted-box', 'Kaynaklı olasılık raporu alınamadı; önceki içerik gizlendi.'));
    }
  } finally {
    clearTimeout(timer);
  }
}

document.querySelectorAll('[data-diag-pick]').forEach(btn => {
  btn.addEventListener('click', () => {
    activeDiagnostic = btn.dataset.diagPick;
    document.querySelectorAll('[data-diag-pick]').forEach(item => {
      const selected = item === btn;
      item.classList.toggle('selected', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    loadDiagnosticScenario(activeDiagnostic);
  });
});

// --- 6. Reproducible Synthetic Benchmark Tab ---
const siteBenchOutput = document.querySelector('#site-bench-output');
const siteBenchRefresh = document.querySelector('#site-bench-refresh');

function renderSiteBenchmark(report) {
  if (
    report.schema_version !== '1.0' ||
    report.scope !== 'synthetic_fixture_benchmark' ||
    report.physical_device_validated !== false ||
    report.guidance_allowed !== false
  ) {
    throw new Error('invalid_site_benchmark');
  }
  const wrap = el('div', 'diag-grid');

  const card1 = el('article', 'diag-card');
  card1.append(
    el('span', 'diag-badge', `T05 GÖRÜNTÜ · ${report.vision.frames_evaluated} SENTETİK KARE`),
    el('h4', '', `Precision ${trNumber.format(report.vision.precision)} · Recall ${trNumber.format(report.vision.recall)}`),
    el('p', 'helper-copy', `ORB/RANSAC köşe sapması: ${trNumber.format(report.vision.warped_max_corner_error_px)} px · Yanlış pozitif: ${report.vision.false_positives} · Kalibre olasılık iddiası yok.`)
  );

  const card2 = el('article', 'diag-card');
  card2.append(
    el('span', 'diag-badge', `T04 + HAFTA 11 · RAG & LRU ÖNBELLEK`),
    el('h4', '', `Kaynak Konumu %${trNumber.format(report.rag.citation_locator_rate * 100)} · Sızıntı ${report.rag.cross_equipment_leakage_count}`),
    el('p', 'helper-copy', `Önbellek: ${report.rag.cache_hits} hit / ${report.rag.cache_misses} miss · Soğuk ${trNumber.format(report.rag.cold_query_ms)} ms → Sıcak ${trNumber.format(report.rag.warm_query_ms)} ms.`)
  );

  const card3 = el('article', 'diag-card');
  card3.append(
    el('span', 'diag-badge', 'T06–T08 · SUPERVISOR & TANI MATRİSİ'),
    el('h4', '', report.diagnostic.contradiction_preserved && report.diagnostic.missing_counter_evidence_abstained ? 'Çelişki Korunumu & Susma Doğrulandı' : 'Doğrulama Uyarısı'),
    el('p', 'helper-copy', `${report.diagnostic.sensor_series_verified}/3 simulated sensör serisi ve LangGraph ready_for_diagnostic devri doğrulandı.`)
  );

  const card4 = el('article', 'diag-card');
  card4.append(
    el('span', 'diag-badge', `T09–T10 + T14 · ${report.safety_spatial.checks_passed}/${report.safety_spatial.checks_total} GÜVENLİK KAPISI`),
    el('h4', '', `Güvenlik İhlali: ${report.safety_spatial.safety_violations} · Fiziksel Cihaz Doğrulaması: Kapalı`),
    el('p', 'helper-copy', 'Takip kaybı 3D anchor temizliği, katalog dışı parça reddi, tek-kullanımlık SQLite onay replay ve özet kurcalama korumaları geçti.')
  );

  wrap.append(card1, card2, card3, card4);
  siteBenchOutput.replaceChildren(wrap);
}

async function loadSiteBenchmark() {
  if (!siteBenchOutput) return;
  if (siteBenchRefresh) siteBenchRefresh.disabled = true;
  siteBenchOutput.replaceChildren(el('div', 'placeholder-box', 'Sentetik benchmark metrikleri doğrulanıyor…'));
  try {
    const res = await fetch('/v1/demo/evaluation', {
      credentials: 'omit',
      signal: AbortSignal.timeout(15000)
    });
    if (!res.ok) throw new Error('bench_http_error');
    const data = await res.json();
    renderSiteBenchmark(data);
  } catch {
    siteBenchOutput.replaceChildren(el('div', 'redacted-box', 'Benchmark raporu alınamadı; önceki metrikler gizlendi.'));
  } finally {
    if (siteBenchRefresh) siteBenchRefresh.disabled = false;
  }
}

if (siteBenchRefresh) {
  siteBenchRefresh.addEventListener('click', loadSiteBenchmark);
}

// --- 7. Independent JSON Audit Report Export ---
const siteExportBtn = document.querySelector('#site-export-btn');
const siteExportStatus = document.querySelector('#site-export-status');

siteExportBtn.addEventListener('click', async () => {
  const exportableSafety = ['information', 'critical', 'tracking', 'unknown'].includes(activeSafety)
    ? activeSafety
    : 'information';
  const params = new URLSearchParams({
    safety: exportableSafety,
    sensor: activeSensor,
    diagnostic: activeDiagnostic
  });
  siteExportBtn.disabled = true;
  siteExportStatus.textContent = 'Sunucuda yeniden değerlendiriliyor…';
  try {
    const res = await fetch(`/v1/demo/report?${params}`, {
      credentials: 'omit',
      signal: AbortSignal.timeout(15000)
    });
    if (!res.ok) throw new Error('export_failed');
    const bundle = await res.json();
    if (
      bundle.schema_version !== '1.0' ||
      bundle.scope !== 'synthetic_demo' ||
      bundle.independent_sections !== true ||
      bundle.guidance_allowed !== false
    ) {
      throw new Error('invalid_export_bundle');
    }
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `holoassist-demo-${bundle.export_id}.json`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    siteExportStatus.textContent = `İndirildi (${exportableSafety} / ${activeSensor} / ${activeDiagnostic}).`;
  } catch {
    siteExportStatus.textContent = 'Rapor üretilemedi; dosya indirilmedi.';
  } finally {
    siteExportBtn.disabled = false;
  }
});

// Boot initial views
checkSystemStatus();
runSafetyScenario(activeSafety);

