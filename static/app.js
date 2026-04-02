function formToJson(form) {
  const fd = new FormData(form);
  const o = {};
  for (const [k, v] of fd.entries()) {
    if (v === "") continue;
    o[k] = v;
  }
  for (const k of [
    "jitter_us",
    "cpu_threads",
    "fixed_delay_ms",
    "byte_delay_us",
    "tag_len",
    "repetitions_per_guess",
    "alpha",
    "top_k",
    "coarse_repetitions",
  ]) {
    if (o[k] !== undefined) {
      const n = Number(o[k]);
      if (!Number.isNaN(n)) o[k] = n;
    }
  }
  return o;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setStatus(line) {
  const el = document.querySelector("#status .status__line");
  if (el) el.textContent = line;
}

let isRunning = false;

function formatMetricNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? '—');
  return new Intl.NumberFormat('en-US').format(n);
}

function getMetricText(value, options = {}) {
  if (value === null || value === undefined) return '—';
  return options.formatNumber ? formatMetricNumber(value) : String(value);
}

function fitMetricText(el) {
  if (!el) return;
  el.style.whiteSpace = 'nowrap';
  el.style.overflow = 'visible';
  el.style.textOverflow = 'clip';

  const parent = el.closest('.kpi');
  const maxWidth = parent ? parent.clientWidth - 28 : el.clientWidth;
  if (maxWidth <= 0) return;

  const length = el.textContent.length;
  let fontSize = 30;
  if (length >= 14) fontSize = 21;
  else if (length >= 12) fontSize = 23;
  else if (length >= 10) fontSize = 25;
  else if (length >= 8) fontSize = 27;

  el.style.fontSize = `${fontSize}px`;

  while (el.scrollWidth > maxWidth && fontSize > 15) {
    fontSize -= 1;
    el.style.fontSize = `${fontSize}px`;
  }
}

function setMetricValue(id, value, options = {}) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = getMetricText(value, options);
  fitMetricText(el);
}

function animateMetricValue(id, finalValue, options = {}) {
  const el = document.getElementById(id);
  if (!el) return;

  if (el._metricFrame) {
    cancelAnimationFrame(el._metricFrame);
    el._metricFrame = null;
  }

  if (finalValue === null || finalValue === undefined || finalValue === '—') {
    el.textContent = '—';
    fitMetricText(el);
    return;
  }

  const target = Number(finalValue);
  if (!Number.isFinite(target)) {
    el.textContent = getMetricText(finalValue, options);
    fitMetricText(el);
    return;
  }

  const duration = options.duration ?? 900;
  const decimals = options.decimals ?? 0;
  const suffix = options.suffix ?? '';
  const formatter = options.formatNumber
    ? (n) => formatMetricNumber(decimals > 0 ? Number(n.toFixed(decimals)) : Math.round(n))
    : (n) => (decimals > 0 ? n.toFixed(decimals) : Math.round(n).toString());

  const start = performance.now();
  const startValue = 0;

  const tick = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    const current = startValue + (target - startValue) * eased;
    el.textContent = `${formatter(current)}${suffix}`;
    fitMetricText(el);

    if (t < 1) {
      el._metricFrame = requestAnimationFrame(tick);
    } else {
      el.textContent = `${formatter(target)}${suffix}`;
      fitMetricText(el);
      el._metricFrame = null;
    }
  };

  el._metricFrame = requestAnimationFrame(tick);
}

function setRunState(running) {
  isRunning = running;
  const runBtn = document.getElementById('runAttackBtn');
  const runLabel = document.getElementById('runAttackLabel');
  if (runBtn) {
    runBtn.disabled = running;
    runBtn.setAttribute('aria-disabled', running ? 'true' : 'false');
    runBtn.classList.toggle('is-running', running);
  }
  if (runLabel) {
    runLabel.textContent = running ? 'Running…' : 'Run attack';
  }
}

function resetPlotCard(imgId, placeholderId) {
  const img = document.getElementById(imgId);
  const placeholder = document.getElementById(placeholderId);
  if (img) {
    img.hidden = true;
    img.removeAttribute('src');
  }
  if (placeholder) placeholder.hidden = false;
}

function fillPlotCard(imgId, placeholderId, src) {
  const img = document.getElementById(imgId);
  const placeholder = document.getElementById(placeholderId);
  if (!img) return;
  img.onload = () => {
    if (placeholder) placeholder.hidden = true;
    img.hidden = false;
    img.onload = null;
  };
  img.onerror = () => {
    if (placeholder) placeholder.hidden = false;
    img.hidden = true;
    img.onerror = null;
  };
  img.src = src;
}

function setMeter(pct) {
  const el = document.getElementById("meterBar");
  if (!el) return;
  el.style.width = `${Math.max(0, Math.min(100, pct))}%`;
}

async function pollRun(runId, totalBytes) {
  const csvBtn = document.getElementById("openCsv");
  const plots = document.getElementById("plots");
  const plotP = document.getElementById("plotP");
  const plotM = document.getElementById("plotM");
  const plotO = document.getElementById("plotO");

  const url = `/api/v1/runs/${encodeURIComponent(runId)}`;
  for (;;) {
    const r = await fetch(url, { cache: "no-store" });
    const st = await r.json();

    if (st.status === "error") {
      setStatus(`Error: ${st.error || "unknown"}`);
      setMeter(0);
      return;
    }

    const b = st.progress && st.progress.byte_index ? Number(st.progress.byte_index) : 0;
    const pct = totalBytes > 0 ? (b / totalBytes) * 100 : 0;
    setMeter(pct);
    const pv = st.progress && st.progress.p_value !== undefined ? st.progress.p_value : null;
    setStatus(`Running... byte ${b}/${totalBytes}${pv !== null ? `, p=${Number(pv).toExponential(2)}` : ""}`);

    if (st.status === "done" && st.result) {
      const res = st.result.result;
      const metrics = st.result.metrics;
      setStatus("Done.");
      setMeter(100);

      animateMetricValue("acc", metrics.attack_accuracy, { decimals: 1, suffix: '%', duration: 850 });
      animateMetricValue("samples", metrics.samples_needed, { formatNumber: true, duration: 1000 });
      animateMetricValue("overhead", metrics.overhead_ms, { decimals: 2, suffix: ' ms', duration: 900 });

      const tags = document.getElementById("tags");
      if (tags) {
        tags.textContent = `recovered: ${res.recovered_tag_hex}\ntrue:      ${res.true_tag_hex}`;
      }

      if (csvBtn) {
        csvBtn.href = `/runs/${encodeURIComponent(runId)}/results.csv`;
        csvBtn.setAttribute("aria-disabled", "false");
      }

      if (plots && plotP && plotM && plotO) {
        fillPlotCard("plotP", "plotPlaceholderP", `/runs/${encodeURIComponent(runId)}/pvalues.png`);
        fillPlotCard("plotM", "plotPlaceholderM", `/runs/${encodeURIComponent(runId)}/means.png`);
        fillPlotCard("plotO", "plotPlaceholderO", `/runs/${encodeURIComponent(runId)}/overhead.png`);
      }
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 650));
  }
}

document.getElementById("runForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (isRunning) return;

  const form = e.currentTarget;
  const payload = formToJson(form);
  setRunState(true);

  try {
    setStatus("Queued...");
    setMeter(0);
    setMetricValue("acc", "—");
    setMetricValue("samples", "—");
    setMetricValue("overhead", "—");
    const tags = document.getElementById("tags");
    if (tags) tags.textContent = "";

    const csvBtn = document.getElementById("openCsv");
    if (csvBtn) {
      csvBtn.href = "#";
      csvBtn.setAttribute("aria-disabled", "true");
    }

    resetPlotCard("plotP", "plotPlaceholderP");
    resetPlotCard("plotM", "plotPlaceholderM");
    resetPlotCard("plotO", "plotPlaceholderO");

    const resp = await fetch("/api/v1/attack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      throw new Error(`Request failed with status ${resp.status}`);
    }

    const out = await resp.json();
    const runId = out.run_id;
    if (!runId) {
      throw new Error("Run id missing from server response");
    }

    const totalBytes = Number(payload.tag_len || 32);
    setStatus(`Running... (run_id=${runId})`);
    await pollRun(runId, totalBytes);
  } catch (error) {
    setStatus(`Error: ${error.message || "unknown"}`);
    setMeter(0);
  } finally {
    setRunState(false);
  }
});


window.addEventListener('resize', () => {
  ['acc', 'samples', 'overhead'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) fitMetricText(el);
  });
});
