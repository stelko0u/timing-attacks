from __future__ import annotations

import threading
from dataclasses import asdict
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

from .attack import result_to_dict, run_attack
from .config import AttackConfig, NoiseConfig, VerifyConfig
from .crypto import load_key, parse_tag_hex
from .experiment import measure_overhead_ms, overhead_sweep, serialize_configs
from .noise import start_noise, stop_noise
from .plotting import plot_means, plot_overhead, plot_pvalues
from .storage import RunStore
from .verify import verify_measurement


def create_app() -> Flask:
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
        static_url_path="/static",
    )

    key = load_key()
    runs = RunStore(root / "runs")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/v1/verify")
    def api_verify():
        data = request.get_json(force=True, silent=True) or {}
        message = (data.get("message") or "").encode("utf-8", "ignore")
        tag_hex = data.get("provided_tag_hex") or ""
        mode = data.get("mode") or "naive"
        byte_delay_us = int(data.get("byte_delay_us") or 800)
        fixed_delay_ms = float(data.get("fixed_delay_ms") or 0.0)
        noise_profile = (data.get("noise_profile") or "none").strip()
        jitter_us = int(data.get("jitter_us") or 0)
        cpu_threads = int(data.get("cpu_threads") or 0)

        try:
            provided = parse_tag_hex(tag_hex)
        except Exception:
            provided = b""

        cfg = VerifyConfig(
            mode=mode,
            byte_delay_us=byte_delay_us,
            fixed_delay_ms=fixed_delay_ms,
            noise=NoiseConfig(profile=noise_profile, jitter_us=jitter_us, cpu_threads=cpu_threads),
        )

        rt = start_noise(cfg.noise.profile, cpu_threads=cfg.noise.cpu_threads)
        try:
            dt_ns, _ = verify_measurement(key=key, message=message, provided_tag=provided, cfg=cfg)
        finally:
            stop_noise(rt)

        return jsonify({"status": "done", "elapsed_ns": int(dt_ns)})

    @app.post("/api/v1/attack")
    def api_attack():
        data = request.get_json(force=True, silent=True) or {}

        message = (data.get("message") or "hello")
        mode = data.get("mode") or "naive"
        noise_profile = data.get("noise_profile") or "none"
        jitter_us = int(data.get("jitter_us") or 0)
        cpu_threads = int(data.get("cpu_threads") or 0)
        fixed_delay_ms = float(data.get("fixed_delay_ms") or 0.0)
        byte_delay_us = int(data.get("byte_delay_us") or 800)

        tag_len = int(data.get("tag_len") or 8)
        repetitions_per_guess = int(data.get("repetitions_per_guess") or 30)
        alpha = float(data.get("alpha") or 0.01)
        max_r = int(data.get("max_repetitions_per_guess") or 5000)
        decision = data.get("decision") or "ttest"
        top_k = int(data.get("top_k") or 16)
        coarse_repetitions = int(data.get("coarse_repetitions") or 10)

        verify_cfg = VerifyConfig(
            mode=mode,
            byte_delay_us=byte_delay_us,
            fixed_delay_ms=fixed_delay_ms,
            noise=NoiseConfig(profile=noise_profile, jitter_us=jitter_us, cpu_threads=cpu_threads),
        )
        attack_cfg = AttackConfig(
            tag_len=tag_len,
            repetitions_per_guess=repetitions_per_guess,
            alpha=alpha,
            max_repetitions_per_guess=max_r,
            decision=decision,
            top_k=top_k,
            coarse_repetitions=coarse_repetitions,
        )

        st = runs.create()
        runs.update(st.run_id, status="running", progress={"byte_index": 0})
        runs.write_json(st.run_id, "config.json", serialize_configs(verify_cfg=verify_cfg, attack_cfg=attack_cfg))

        def worker():
            rt = start_noise(verify_cfg.noise.profile, cpu_threads=verify_cfg.noise.cpu_threads)
            try:
                def on_progress(p):
                    runs.update(
                        st.run_id,
                        progress={
                            "byte_index": int(p.byte_index),
                            "decided_byte": None if p.decided_byte is None else int(p.decided_byte),
                            "p_value": None if p.p_value is None else float(p.p_value),
                            "repetitions_per_guess": int(p.repetitions_per_guess),
                        },
                    )

                res = run_attack(
                    key=key,
                    message=message.encode("utf-8", "ignore"),
                    verify_cfg=verify_cfg,
                    attack_cfg=attack_cfg,
                    on_progress=on_progress,
                )

                overhead_ms = measure_overhead_ms(
                    key=key,
                    message=message.encode("utf-8", "ignore"),
                    verify_cfg=verify_cfg,
                    n=200,
                )

                sweep = overhead_sweep(
                    key=key,
                    message=message.encode("utf-8", "ignore"),
                    verify_cfg=verify_cfg,
                    fixed_delays_ms=[0.0, 1.0, 2.0, 5.0, 10.0],
                    n=120,
                )

                out = {
                    "configs": serialize_configs(verify_cfg=verify_cfg, attack_cfg=attack_cfg),
                    "result": result_to_dict(res),
                    "metrics": {
                        "attack_accuracy": float(res.attack_accuracy),
                        "samples_needed": int(res.samples_needed),
                        "overhead_ms": float(overhead_ms),
                    },
                    "overhead_sweep": sweep,
                }

                runs.write_json(st.run_id, "result.json", out)
                runs.write_csv(
                    st.run_id,
                    "results.csv",
                    header=[
                        "mode",
                        "noise",
                        "repetitions_per_guess",
                        "attack_accuracy",
                        "samples_needed",
                        "overhead_ms",
                        "alpha",
                    ],
                    rows=[
                        {
                            "mode": verify_cfg.mode,
                            "noise": verify_cfg.noise.profile,
                            "repetitions_per_guess": attack_cfg.repetitions_per_guess,
                            "attack_accuracy": res.attack_accuracy,
                            "samples_needed": res.samples_needed,
                            "overhead_ms": overhead_ms,
                            "alpha": attack_cfg.alpha,
                        }
                    ],
                )
                runs.write_csv(
                    st.run_id,
                    "overhead.csv",
                    header=["fixed_delay_ms", "mean_ms"],
                    rows=sweep,
                )

                run_dir = runs.run_dir(st.run_id)
                plot_pvalues(res.decisions, alpha=attack_cfg.alpha, out_path=run_dir / "pvalues.png")
                plot_means(res.decisions, out_path=run_dir / "means.png")
                plot_overhead(sweep, out_path=run_dir / "overhead.png")

                runs.update(st.run_id, status="done", result=out, progress={"byte_index": int(res.total_bytes)})
            except Exception as e:
                runs.update(st.run_id, status="error", error=str(e))
            finally:
                stop_noise(rt)

        threading.Thread(target=worker, name=f"attack-{st.run_id}", daemon=True).start()
        return jsonify({"run_id": st.run_id})

    @app.get("/api/v1/runs/<run_id>")
    def api_run_status(run_id: str):
        st = runs.get(run_id)
        if not st:
            return jsonify({"error": "not_found"}), 404
        return jsonify(asdict(st))

    @app.get("/runs/<run_id>/<path:name>")
    def run_artifact(run_id: str, name: str):
        p = runs.run_dir(run_id)
        return send_from_directory(p, name)

    @app.get("/health")
    def health():
        return Response("ok\n", mimetype="text/plain")

    return app
