"""
Enterprise Observability & Alerting Module:
1. Sentry — automatic exception capturing when SENTRY_DSN is set.
2. Prometheus + Grafana — real-time request counters, cache hit rates, active load, and generation latency (avg/p95/max)
   with an optional /metrics HTTP exposition server for Prometheus scraping.
3. Telegram Admin Alert — immediately sends formatted error alerts to all ADMIN_IDS when an exception occurs.
"""
import asyncio
import logging
import time
import traceback
from typing import Dict, Any, List, Optional
import config

logger = logging.getLogger(__name__)

# Optional Sentry initialization
_sentry_enabled = False
if getattr(config, "SENTRY_DSN", None):
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=config.SENTRY_DSN, traces_sample_rate=1.0)
        _sentry_enabled = True
        logger.info("Sentry error tracking initialized successfully.")
    except Exception as e:
        logger.warning(f"Sentry SDK not initialized ({e})")

# In-memory Prometheus metrics registry
_METRICS: Dict[str, Any] = {
    "started_at": time.time(),
    "generations_total": 0,
    "cache_hits_total": 0,
    "image_cache_hits_total": 0,
    "receipts_verified_total": 0,
    "receipts_blocked_concurrent": 0,
    "fraud_flags_total": 0,
    "errors_total": 0,
    "active_generations": 0,
    "generation_latencies_sec": [],  # rolling last 500 latencies
}


def inc_metric(name: str, delta: int = 1) -> None:
    if name in _METRICS and isinstance(_METRICS[name], (int, float)):
        _METRICS[name] = max(0, _METRICS[name] + delta)


def observe_generation_latency(seconds: float) -> None:
    arr: List[float] = _METRICS["generation_latencies_sec"]
    arr.append(round(max(0.001, float(seconds)), 3))
    if len(arr) > 500:
        del arr[:-500]


def get_prometheus_metrics_snapshot() -> Dict[str, Any]:
    lat: List[float] = sorted(_METRICS["generation_latencies_sec"])
    n = len(lat)
    avg_lat = round(sum(lat) / n, 2) if n > 0 else 0.0
    p95_lat = round(lat[min(n - 1, int(n * 0.95))], 2) if n > 0 else 0.0
    max_lat = round(lat[-1], 2) if n > 0 else 0.0
    uptime_sec = int(time.time() - _METRICS["started_at"])
    gen_tot = int(_METRICS["generations_total"])
    cache_tot = int(_METRICS["cache_hits_total"])
    cache_ratio = round((cache_tot / gen_tot) * 100.0, 1) if gen_tot > 0 else 0.0

    return {
        "uptime_sec": uptime_sec,
        "generations_total": gen_tot,
        "cache_hits_total": cache_tot,
        "cache_hit_rate_pct": cache_ratio,
        "image_cache_hits_total": int(_METRICS["image_cache_hits_total"]),
        "receipts_verified_total": int(_METRICS["receipts_verified_total"]),
        "receipts_blocked_concurrent": int(_METRICS["receipts_blocked_concurrent"]),
        "fraud_flags_total": int(_METRICS["fraud_flags_total"]),
        "errors_total": int(_METRICS["errors_total"]),
        "active_generations": int(_METRICS["active_generations"]),
        "latency_avg_sec": avg_lat,
        "latency_p95_sec": p95_lat,
        "latency_max_sec": max_lat,
        "sentry_enabled": _sentry_enabled,
    }


def render_prometheus_text() -> str:
    """Formats metrics in standard Prometheus / Grafana text exposition format."""
    snap = get_prometheus_metrics_snapshot()
    lines = [
        "# HELP bot_uptime_seconds Bot process uptime in seconds",
        "# TYPE bot_uptime_seconds gauge",
        f"bot_uptime_seconds {snap['uptime_sec']}",
        "# HELP bot_generations_total Total presentations generated",
        "# TYPE bot_generations_total counter",
        f"bot_generations_total {snap['generations_total']}",
        "# HELP bot_cache_hits_total Total presentation cache hits (100 users -> 1 gen)",
        "# TYPE bot_cache_hits_total counter",
        f"bot_cache_hits_total {snap['cache_hits_total']}",
        "# HELP bot_image_cache_hits_total Total Redis/DB slide image cache hits",
        "# TYPE bot_image_cache_hits_total counter",
        f"bot_image_cache_hits_total {snap['image_cache_hits_total']}",
        "# HELP bot_active_generations Currently running presentation generations",
        "# TYPE bot_active_generations gauge",
        f"bot_active_generations {snap['active_generations']}",
        "# HELP bot_generation_latency_avg_seconds Average presentation generation latency",
        "# TYPE bot_generation_latency_avg_seconds gauge",
        f"bot_generation_latency_avg_seconds {snap['latency_avg_sec']}",
        "# HELP bot_generation_latency_p95_seconds 95th percentile generation latency",
        "# TYPE bot_generation_latency_p95_seconds gauge",
        f"bot_generation_latency_p95_seconds {snap['latency_p95_sec']}",
        "# HELP bot_errors_total Total captured errors",
        "# TYPE bot_errors_total counter",
        f"bot_errors_total {snap['errors_total']}",
        "# HELP bot_fraud_flags_total Total anti-fraud flags triggered",
        "# TYPE bot_fraud_flags_total counter",
        f"bot_fraud_flags_total {snap['fraud_flags_total']}",
    ]
    return "\n".join(lines) + "\n"


async def start_prometheus_http_server(port: Optional[int] = None) -> None:
    """Starts a lightweight async HTTP server exposing /metrics for Prometheus + Grafana."""
    listen_port = port if port is not None else getattr(config, "PROMETHEUS_PORT", 0)
    if not listen_port or listen_port <= 0:
        return

    async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            await reader.read(1024)
            body = render_prometheus_text().encode("utf-8")
            header = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain; version=0.0.4; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode("utf-8")
            writer.write(header + body)
            await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    try:
        await asyncio.start_server(_handle_client, "0.0.0.0", int(listen_port))
        logger.info(f"Prometheus /metrics HTTP server listening on port {listen_port}")
    except Exception as e:
        logger.warning(f"Could not start Prometheus server on port {listen_port}: {e}")


async def send_admin_error_alert(
    bot: Any,
    err: Exception,
    context_label: str = "Bot Runtime",
    user_id: Optional[int] = None,
) -> None:
    """
    Captures exception in Sentry (if configured), increments Prometheus error counter,
    and sends an instant Telegram alert to all ADMIN_IDS.
    """
    inc_metric("errors_total", 1)
    if _sentry_enabled:
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(err)
        except Exception:
            pass

    if not bot or not getattr(config, "ADMIN_IDS", None):
        return

    tb_str = "".join(traceback.format_exception_only(type(err), err)).strip()[:450]
    u_line = f"👤 User ID: <code>{user_id}</code>\n" if user_id else ""
    alert_text = (
        f"🚨 <b>ТЕХНИКАЛЫҚ ҚАТЕ (TELEGRAM ALERT)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Орны:</b> {context_label}\n"
        f"{u_line}"
        f"❌ <b>Қате:</b> <code>{tb_str}</code>"
    )
    for adm_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=adm_id, text=alert_text)
        except Exception:
            pass
