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

      setText("acc", `${metrics.attack_accuracy.toFixed(1)}%`);
      setText("samples", String(metrics.samples_needed));
      setText("overhead", `${metrics.overhead_ms.toFixed(2)} ms`);

      const tags = document.getElementById("tags");
      if (tags) {
        tags.textContent = `recovered: ${res.recovered_tag_hex}\ntrue:      ${res.true_tag_hex}`;
      }

      if (csvBtn) {
        csvBtn.href = `/runs/${encodeURIComponent(runId)}/results.csv`;
        csvBtn.setAttribute("aria-disabled", "false");
      }

      if (plots && plotP && plotM && plotO) {
        plotP.src = `/runs/${encodeURIComponent(runId)}/pvalues.png`;
        plotM.src = `/runs/${encodeURIComponent(runId)}/means.png`;
        plotO.src = `/runs/${encodeURIComponent(runId)}/overhead.png`;
        plots.hidden = false;
      }
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 650));
  }
}

document.getElementById("runForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const payload = formToJson(form);

  setStatus("Queued...");
  setMeter(0);
  setText("acc", "-");
  setText("samples", "-");
  setText("overhead", "-");
  const tags = document.getElementById("tags");
  if (tags) tags.textContent = "";

  const csvBtn = document.getElementById("openCsv");
  if (csvBtn) {
    csvBtn.href = "#";
    csvBtn.setAttribute("aria-disabled", "true");
  }
  const plots = document.getElementById("plots");
  if (plots) plots.hidden = true;

  const resp = await fetch("/api/v1/attack", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const out = await resp.json();
  const runId = out.run_id;
  const totalBytes = Number(payload.tag_len || 32);
  setStatus(`Running... (run_id=${runId})`);
  await pollRun(runId, totalBytes);
});
