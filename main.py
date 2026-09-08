from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
EMULATOR = ROOT / "emulator"
PROCESSING = ROOT / "processing"
SCREEN = ROOT / "screen"
RUNTIME = ROOT / "runtime"
CONTRACTS = RUNTIME / "contracts"
REFRESH = RUNTIME / "refresh_requests"
PROCESSING_RUNTIME = RUNTIME / "processing"
PROCESSING_STATUS = PROCESSING_RUNTIME / "refresh_status.json"
SHUTDOWN_REQUESTED = threading.Event()
PROJECT_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
BUILD_ID = "V4.2_FINAL_R10_GROK_RADAR_HF3.1"
# Contract compatibility is independent from the HMI build. R5 introduced the
# current contract semantics; R6 was visual-only. Do not rebuild eight families
# merely because Screen/CSS changed.
CONTRACT_SCHEMA_ID = "V4.2_CONTRACT_SCHEMA_R5"
CONTRACT_COMPATIBLE_BUILD_IDS = {"V4.2_FINAL_R5", "V4.2_FINAL_R6", "V4.2_FINAL_R7", "V4.2_FINAL_R8", "V4.2_FINAL_R9", "V4.2_FINAL_R10", "V4.2_FINAL_R10_GROK_RADAR", "V4.2_FINAL_R10_GROK_RADAR_HF1", "V4.2_FINAL_R10_GROK_RADAR_HF2", "V4.2_FINAL_R10_GROK_RADAR_HF3", "V4.2_FINAL_R10_GROK_RADAR_HF3.1"}
BOOTSTRAP_BUILD_MARKER = RUNTIME / "bootstrap_build.json"
ENV_FILE = ROOT / ".env"
INTEGRATION_LOCK = RUNTIME / "integration.lock.json"


def _pid_is_alive(pid: object) -> bool:
    """Return whether a PID is alive without signalling or terminating it."""
    if type(pid) is not int or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                process_query_limited_information, False, pid
            )
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except (AttributeError, OSError):
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # A process owned by another account is still a live process.
        return True
    return True


def _read_integration_lock(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _acquire_integration_lock(path: Path, env: Mapping[str, str]) -> str:
    """Atomically claim the runtime; recover only demonstrably stale locks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    payload = {
        "pid": os.getpid(),
        "token": token,
        "build_id": BUILD_ID,
        "contracts_dir": str(CONTRACTS.resolve()),
        "emulator_port": int(env["TRADELATIN_EMULATOR_PORT"]),
        "screen_port": int(env["TRADELATIN_PORT"]),
        "created_at_epoch": time.time(),
    }
    for _attempt in range(3):
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            existing = _read_integration_lock(path)
            existing_pid = existing.get("pid")
            if _pid_is_alive(existing_pid):
                raise RuntimeError(
                    "another TradELATIN Integration is already running "
                    f"(pid={existing_pid}, build={existing.get('build_id', 'unknown')}, "
                    f"contracts={existing.get('contracts_dir', 'unknown')}, "
                    f"screen_port={existing.get('screen_port', 'unknown')})"
                )
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            try:
                path.unlink()
            except OSError:
                pass
            raise
        return token
    raise RuntimeError(f"could not acquire Integration runtime lock: {path}")


def _release_integration_lock(path: Path, token: str | None) -> None:
    """Release only the lock owned by this exact launcher instance."""
    if not token:
        return
    existing = _read_integration_lock(path)
    if existing.get("pid") != os.getpid() or existing.get("token") != token:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _load_project_environment() -> None:
    """Load the shared provider/UI environment before spawning services.

    Existing shell variables win over values in ``.env`` so deployments can
    inject secrets without changing files.  Every child receives the same
    resulting environment through ``_build_environment``.
    """
    load_dotenv(dotenv_path=ENV_FILE, override=False, encoding="utf-8")


def _run_with_project_python() -> int | None:
    """Delegate ``python main.py`` to .venv when a different Python invoked it."""
    if not PROJECT_PYTHON.is_file():
        return None
    try:
        if Path(sys.executable).resolve() == PROJECT_PYTHON.resolve():
            return None
    except OSError:
        pass

    print(f"[INTEGRATION] using project environment: {PROJECT_PYTHON}", flush=True)
    child = subprocess.Popen([str(PROJECT_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
    try:
        return child.wait()
    except KeyboardInterrupt:
        # The delegated launcher normally receives Ctrl+C itself. Give it a
        # moment to perform its tree cleanup before using a direct fallback.
        try:
            return child.wait(timeout=12.0)
        except subprocess.TimeoutExpired:
            child.terminate()
            return child.wait(timeout=5.0)

# Integration boundary only: filenames published by Processing and consumed by Screen.
EXPECTED_CONTRACTS: tuple[tuple[str, str], ...] = (
    ("prices", "prices_VR1_FINAL.json"),
    ("cvd", "cvd_volume_orderflow_VR1_FINAL.json"),
    ("open_interest", "open_interest_and_funding_VR1_FINAL.json"),
    ("etf", "etf_exchange_flows_VR1_FINAL.json"),
    ("on_chain", "on_chain_miners_VR1_FINAL.json"),
    ("volatility", "volatility_market_regimes_VR1_FINAL.json"),
    ("liquidations", "long_short_liquidations_VR1_FINAL.json"),
    ("liquidity", "liquidity_microstructure_VR1_FINAL.json"),
)

PROCESSING_FAMILY_BY_LABEL: dict[str, str] = {
    "prices": "prices_ohlcv",
    "cvd": "cvd_volume_orderflow",
    "open_interest": "open_interest_and_funding",
    "etf": "etf_exchange_flows",
    "on_chain": "on_chain_miners",
    "volatility": "volatility_market_regimes",
    "liquidations": "long_short_liquidations",
    "liquidity": "liquidity_microstructure",
}
AUTOMATIC_CONTRACT_LABELS = frozenset({"prices", "cvd", "liquidity"})
STARTUP_REQUIRED_LABELS = frozenset({"prices"})


def _probe_host(host: str) -> str:
    """Return a connectable local host for services bound to wildcard addresses."""
    return "127.0.0.1" if host in {"0.0.0.0", "::", "[::]"} else host


def _reserve_available_screen_port(env: dict[str, str], *, attempts: int = 20) -> None:
    """Select a free local HMI port before starting expensive services.

    A terminal closed without stopping Integration can leave an older Screen
    process on 8002. Falling forward keeps startup usable without terminating
    an unidentified process that might belong to another application.
    """
    host = _probe_host(env["TRADELATIN_HOST"])
    requested = int(env["TRADELATIN_PORT"])
    for port in range(requested, requested + attempts):
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        try:
            with socket.socket(family, socket.SOCK_STREAM) as candidate:
                candidate.bind((host, port))
        except OSError:
            continue
        env["TRADELATIN_PORT"] = str(port)
        if port != requested:
            print(
                f"[SCREEN] port {requested} occupied; using available port {port}",
                flush=True,
            )
        return
    raise RuntimeError(
        f"No available Screen port found in range {requested}-{requested + attempts - 1}"
    )


def _wait_for_http(
    url: str,
    *,
    process: subprocess.Popen | None = None,
    service_name: str,
    timeout: float = 30.0,
    expected_json: Mapping[str, object] | None = None,
    expected_text: str | None = None,
) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not ready"
    while time.monotonic() < deadline:
        if process is not None:
            code = process.poll()
            if code is not None:
                raise RuntimeError(f"{service_name} exited before READY with code {code}")
        try:
            with urlopen(url, timeout=1.0) as response:
                body = response.read()
                if not (200 <= response.status < 300):
                    last_error = f"HTTP {response.status}"
                elif expected_json is not None:
                    payload = json.loads(body.decode("utf-8"))
                    if not isinstance(payload, Mapping):
                        last_error = "health response is not a JSON object"
                    else:
                        mismatch = {
                            key: (payload.get(key), value)
                            for key, value in expected_json.items()
                            if payload.get(key) != value
                        }
                        if not mismatch:
                            return
                        last_error = f"health identity mismatch: {mismatch}"
                elif expected_text is not None:
                    text = body.decode("utf-8", errors="replace")
                    if expected_text in text:
                        return
                    last_error = f"response does not contain {expected_text!r}"
                else:
                    return
        except (OSError, URLError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.2)
    raise RuntimeError(f"{service_name} did not become ready at {url}: {last_error}")


def _http_json_status(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 2.0,
) -> tuple[int, object | None]:
    request = Request(url, headers=dict(headers or {}))
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            body = response.read()
    except HTTPError as exc:
        status = int(exc.code)
        body = exc.read()
    except (OSError, URLError):
        return 0, None

    try:
        return status, json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None


def _emulator_is_compatible(base_url: str) -> bool:
    """Verify that a running :8000 service matches the frozen VR1 CVD surface."""
    headers = {
        "Accept": "application/json",
        "X-TradELATIN-Provider": "coinglass",
        "X-TradELATIN-Endpoint": "spot_aggregated_cvd",
        "X-TradELATIN-Family": "cvd_volume_orderflow",
    }
    endpoint = f"{base_url.rstrip('/')}/api/spot/aggregated-cvd/history"

    old_status, _ = _http_json_status(f"{endpoint}?interval=1m&limit=500", headers=headers)
    if old_status != 400:
        return False

    # The first 500-record CVD request warms the deterministic history cache
    # and can legitimately take several seconds on Windows.  The generic
    # two-second probe misclassified a healthy freshly-started Emulator.
    current_status, payload = _http_json_status(
        f"{endpoint}?interval=5m&limit=500",
        headers=headers,
        timeout=20.0,
    )
    if current_status != 200 or not isinstance(payload, Mapping):
        return False
    records = payload.get("data")
    return isinstance(records, list) and len(records) == 500


def _wait_for_file(
    path: Path,
    *,
    process: subprocess.Popen,
    service_name: str,
    timeout: float = 15.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise RuntimeError(f"{service_name} exited before READY with code {code}")
        if path.is_file() and path.stat().st_size > 0:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, Mapping):
                return
        time.sleep(0.1)
    raise RuntimeError(f"{service_name} did not initialize runtime status: {path}")


def _service_popen(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    console_output: bool = False,
) -> subprocess.Popen:
    """Launch a top-level service in its own process group for tree cleanup.

    On Windows, Processing can stay attached to the parent console so its
    scheduler telemetry is visible. Emulator and Screen remain windowless to
    avoid flooding the launcher with HTTP/server logs.
    """
    kwargs: dict[str, object] = {"cwd": cwd, "env": env}
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if not console_output:
            flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(command, **kwargs)


def _signal_process_tree(process: subprocess.Popen, *, force: bool) -> None:
    """Terminate a service and every worker it spawned."""
    if os.name == "nt":
        # /T includes descendants.  Use /F only for the fallback pass.
        command = ["taskkill", "/PID", str(process.pid), "/T"]
        if force:
            command.append("/F")
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        # Restricted terminals can deny taskkill even for a process launched by
        # this interpreter.  Terminate the direct child as a reliable fallback.
        if completed.returncode != 0 and process.poll() is None:
            try:
                process.kill() if force else process.terminate()
            except OSError:
                pass
        return

    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def _terminate(processes: list[subprocess.Popen]) -> None:
    for process in reversed(processes):
        _signal_process_tree(process, force=False)

    deadline = time.monotonic() + 8.0
    for process in reversed(processes):
        timeout = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _signal_process_tree(process, force=True)
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                pass


def _request_shutdown(signum: int, _frame: object) -> None:
    """Convert console control events into one launcher-owned shutdown path."""
    if not SHUTDOWN_REQUESTED.is_set():
        print(f"\n[INTEGRATION] stop requested (signal {signum})...", flush=True)
        SHUTDOWN_REQUESTED.set()


def _install_signal_handlers() -> None:
    for signal_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        candidate = getattr(signal, signal_name, None)
        if candidate is not None:
            signal.signal(candidate, _request_shutdown)

    if os.name == "nt":
        # Some Windows terminals/PTYs deliver Ctrl+C as an input character
        # instead of raising SIGINT.  Watch console input as a fallback.
        def watch_console_input() -> None:
            import msvcrt

            while not SHUTDOWN_REQUESTED.is_set():
                key = msvcrt.getwch()
                if key in {"\x03", "\x1c"}:  # Ctrl+C / Ctrl+Break
                    _request_shutdown(getattr(signal, "SIGINT", 2), None)
                    return

        threading.Thread(
            target=watch_console_input,
            name="integration-console-stop",
            daemon=True,
        ).start()


def _selector_values(selector: object) -> set[str]:
    if not isinstance(selector, Mapping):
        return set()
    options = selector.get("options")
    if not isinstance(options, list):
        return set()
    values: set[str] = set()
    for option in options:
        if isinstance(option, str):
            values.add(option)
        elif isinstance(option, Mapping):
            candidate = option.get("value", option.get("id"))
            if isinstance(candidate, str):
                values.add(candidate)
    return values


def _timeframe_contract_is_exact(payload: Mapping[str, object], expected: set[str]) -> bool:
    selectors = payload.get("selectors")
    timeframe_selector = selectors.get("timeframe") if isinstance(selectors, Mapping) else None
    if _selector_values(timeframe_selector) != expected:
        return False

    context = payload.get("context")
    if isinstance(context, Mapping):
        for key in ("available_timeframes", "timeframes"):
            available = context.get(key)
            if isinstance(available, list) and {str(value) for value in available} != expected:
                return False
    return True


def _prices_contract_is_current(payload: Mapping[str, object]) -> bool:
    """Reject stale mixed histories that would render a detached live candle."""
    try:
        timeframes = payload["charts"]["ohlcv"]["markets"]["spot"]["timeframes"]
    except (KeyError, TypeError):
        return False
    if not isinstance(timeframes, Mapping):
        return False
    now = int(time.time())
    for timeframe, seconds in (("1m", 60), ("5m", 300)):
        block = timeframes.get(timeframe)
        records = block.get("records") if isinstance(block, Mapping) else None
        if not isinstance(records, list) or len(records) < 2:
            return False
        timestamps = [
            int(row["timestamp"])
            for row in records[-120:]
            if isinstance(row, Mapping) and type(row.get("timestamp")) is int
        ]
        if len(timestamps) < 2 or now - timestamps[-1] > seconds * 2:
            return False
        if any(current - previous > seconds * 2 for previous, current in zip(timestamps, timestamps[1:])):
            return False
    return True


def _contract_is_valid(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, Mapping):
        return False

    if path.name == "prices_VR1_FINAL.json" and not _prices_contract_is_current(payload):
        return False

    # V4.2 CVD/OI invariant: 1m was intentionally removed end-to-end.
    # Reject stale contracts so startup performs a clean BOOTSTRAP instead of
    # letting Screen resurrect a removed timeframe from old runtime JSON.
    if path.name in {
        "cvd_volume_orderflow_VR1_FINAL.json",
        "open_interest_and_funding_VR1_FINAL.json",
    }:
        if not _timeframe_contract_is_exact(payload, {"5m", "15m", "4h"}):
            return False
    return True


def _contract_check() -> tuple[list[str], list[str]]:
    ok: list[str] = []
    bad: list[str] = []
    for label, filename in EXPECTED_CONTRACTS:
        if _contract_is_valid(CONTRACTS / filename):
            ok.append(label)
        else:
            bad.append(label)
    return ok, bad


def _bootstrap_marker_matches() -> bool:
    try:
        payload = json.loads(BOOTSTRAP_BUILD_MARKER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, Mapping):
        return False
    if payload.get("contract_schema_id") == CONTRACT_SCHEMA_ID:
        return True
    # Migration path from R5/R6 markers written before schema/build were split.
    return payload.get("build_id") in CONTRACT_COMPATIBLE_BUILD_IDS


def _write_bootstrap_marker() -> None:
    BOOTSTRAP_BUILD_MARKER.parent.mkdir(parents=True, exist_ok=True)
    BOOTSTRAP_BUILD_MARKER.write_text(
        json.dumps(
            {
                "build_id": BUILD_ID,
                "contract_schema_id": CONTRACT_SCHEMA_ID,
                "written_at_epoch": time.time(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _run_family_bootstrap(env: dict[str, str], labels: list[str], *, console_output: bool = True) -> subprocess.CompletedProcess[str]:
    families = [PROCESSING_FAMILY_BY_LABEL[label] for label in labels]
    command = [
        sys.executable,
        "main.py",
        "--once",
        "--families",
        ",".join(families),
        "--source",
        "emulator",
        "--mode",
        "bootstrap",
        "--contracts-root",
        str(CONTRACTS),
    ]
    kwargs: dict[str, object] = {"cwd": PROCESSING, "env": env, "text": True}
    if not console_output:
        kwargs.update({"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL})
    return subprocess.run(command, **kwargs)


def _prepare_startup_contracts(env: dict[str, str]) -> list[str]:
    """Make only the landing-page contract blocking; everything else may warm later.

    Contract files are validated directly. The bootstrap marker is advisory and
    must never force all eight families to run before the HMI can open.
    """
    existing, missing = _contract_check()
    force_bootstrap = env.get("TRADELATIN_FORCE_BOOTSTRAP", "").strip().lower() in {"1", "true", "yes", "on"}

    if force_bootstrap:
        print("[BOOTSTRAP] FORCED — rebuilding all 8 families before HMI", flush=True)
        completed = _run_family_bootstrap(env, [label for label, _ in EXPECTED_CONTRACTS])
        if completed.returncode != 0:
            raise RuntimeError(f"Processing bootstrap failed with code {completed.returncode}")
        _, missing_after = _contract_check()
        if missing_after:
            raise RuntimeError("forced bootstrap completed but contracts remain missing/invalid: " + ", ".join(missing_after))
        _write_bootstrap_marker()
        print(f"[BOOTSTRAP] OK 8/8 schema={CONTRACT_SCHEMA_ID} build={BUILD_ID}", flush=True)
        return []

    required_missing = [label for label in missing if label in STARTUP_REQUIRED_LABELS]
    if required_missing:
        print(
            "[BOOTSTRAP] LANDING ONLY — building " + ", ".join(required_missing),
            flush=True,
        )
        completed = _run_family_bootstrap(env, required_missing)
        if completed.returncode != 0:
            raise RuntimeError(f"landing bootstrap failed with code {completed.returncode}")

    existing_after, missing_after = _contract_check()
    if not missing_after:
        _write_bootstrap_marker()
        if _bootstrap_marker_matches():
            print(
                f"[BOOTSTRAP] FAST SKIP — 8/8 compatible contracts schema={CONTRACT_SCHEMA_ID}",
                flush=True,
            )
        return []

    # The HMI can start with the valid subset. Automatic families are filled by
    # ContinuousRuntime immediately. Manual-only missing families warm after READY.
    print(
        f"[BOOTSTRAP] FAST START — valid={len(existing_after)}/8 pending={len(missing_after)}/8; HMI will not wait",
        flush=True,
    )
    if not _bootstrap_marker_matches():
        print(
            f"[BOOTSTRAP] marker/schema metadata is stale or absent; direct contract validation wins for startup",
            flush=True,
        )
    return missing_after


def _start_background_warmup(
    env: dict[str, str],
    pending_labels: list[str],
    processes: list[subprocess.Popen],
) -> subprocess.Popen | None:
    manual_labels = [label for label in pending_labels if label not in AUTOMATIC_CONTRACT_LABELS]
    if not manual_labels:
        return None
    families = [PROCESSING_FAMILY_BY_LABEL[label] for label in manual_labels]
    command = [
        sys.executable,
        "main.py",
        "--once",
        "--families",
        ",".join(families),
        "--source",
        "emulator",
        "--mode",
        "bootstrap",
        "--contracts-root",
        str(CONTRACTS),
    ]
    print(
        "[WARMUP] BACKGROUND — " + ", ".join(manual_labels),
        flush=True,
    )
    warmup = _service_popen(command, cwd=PROCESSING, env=env, console_output=False)
    processes.append(warmup)

    def report() -> None:
        code = warmup.wait()
        if code == 0:
            _, missing = _contract_check()
            if not missing:
                _write_bootstrap_marker()
                print("[WARMUP] COMPLETE — 8/8 contracts available", flush=True)
            else:
                print("[WARMUP] COMPLETE — still pending: " + ", ".join(missing), flush=True)
        else:
            print(f"[WARMUP] ERROR exit_code={code}; HMI remains available", flush=True)

    threading.Thread(target=report, name="integration-contract-warmup", daemon=True).start()
    return warmup


def _build_environment() -> dict[str, str]:
    env = os.environ.copy()
    emulator_host = env.get("TRADELATIN_EMULATOR_HOST", "127.0.0.1")
    emulator_port = env.get("TRADELATIN_EMULATOR_PORT", "8000")
    screen_host = env.get("TRADELATIN_HOST", "127.0.0.1")
    screen_port = env.get("TRADELATIN_PORT", "8002")
    emulator_base_url = env.get("TRADELATIN_EMULATOR_BASE_URL", "").strip()
    if not emulator_base_url:
        emulator_base_url = f"http://{_probe_host(emulator_host)}:{emulator_port}"

    env.update(
        {
            "PYTHONUNBUFFERED": "1",
            "TRADELATIN_EMULATOR_HOST": emulator_host,
            "TRADELATIN_EMULATOR_PORT": emulator_port,
            "TRADELATIN_EMULATOR_BASE_URL": emulator_base_url.rstrip("/"),
            "TRADELATIN_CONTRACT_DIR": str(CONTRACTS),
            "TRADELATIN_REFRESH_DIR": str(REFRESH),
            "TRADELATIN_RUNTIME_DIR": str(PROCESSING_RUNTIME),
            "TRADELATIN_HOST": screen_host,
            "TRADELATIN_PORT": screen_port,
            "TRADELATIN_SCREEN_BUILD_ID": BUILD_ID,
            "TRADELATIN_BUILD_ID": BUILD_ID,
            "TRADELATIN_LIQUIDITY_TABLE_SECONDS": env.get(
                "TRADELATIN_LIQUIDITY_TABLE_SECONDS", "5"
            ),
            "TRADELATIN_PRICES_TABLE_SECONDS": env.get(
                "TRADELATIN_PRICES_TABLE_SECONDS", "5"
            ),
        }
    )
    return env


def main() -> int:
    _load_project_environment()
    delegated_result = _run_with_project_python()
    if delegated_result is not None:
        return delegated_result
    SHUTDOWN_REQUESTED.clear()
    _install_signal_handlers()
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    REFRESH.mkdir(parents=True, exist_ok=True)
    PROCESSING_RUNTIME.mkdir(parents=True, exist_ok=True)
    env = _build_environment()
    _reserve_available_screen_port(env)

    try:
        integration_lock_token = _acquire_integration_lock(INTEGRATION_LOCK, env)
    except Exception as exc:
        print(f"[INTEGRATION] ERROR {type(exc).__name__}: {exc}", flush=True)
        return 1

    processes: list[subprocess.Popen] = []
    try:
        emulator_url = f"{env['TRADELATIN_EMULATOR_BASE_URL']}/health"
        emulator: subprocess.Popen | None = None
        running_emulator_detected = False
        try:
            _wait_for_http(
                emulator_url,
                service_name="Emulator",
                timeout=2.0,
                expected_json={"status": "ok", "endpoint_records": 500},
            )
            running_emulator_detected = True
            if not _emulator_is_compatible(env["TRADELATIN_EMULATOR_BASE_URL"]):
                raise RuntimeError(
                    "port 8000 is occupied by an incompatible Emulator; "
                    "stop/update that service before starting Integration"
                )
            print("[EMULATOR] READY (reusing compatible running service)", flush=True)
        except RuntimeError:
            if running_emulator_detected:
                raise
            print("[EMULATOR] START", flush=True)
            emulator = _service_popen([sys.executable, "main.py"], cwd=EMULATOR, env=env)
            processes.append(emulator)
            _wait_for_http(
                emulator_url,
                process=emulator,
                service_name="Emulator",
                timeout=30.0,
                expected_json={"status": "ok", "endpoint_records": 500},
            )
            if not _emulator_is_compatible(env["TRADELATIN_EMULATOR_BASE_URL"]):
                raise RuntimeError("started Emulator does not satisfy CVD compatibility checks")
            print("[EMULATOR] READY", flush=True)

        pending_contracts = _prepare_startup_contracts(env)

        # Do not accept a stale status file from a previous Integration run as READY.
        try:
            PROCESSING_STATUS.unlink()
        except FileNotFoundError:
            pass

        print("[PROCESSING] START continuous runtime", flush=True)
        processing = _service_popen(
            [sys.executable, "main.py", "--source", "emulator", "--contracts-root", str(CONTRACTS)],
            cwd=PROCESSING,
            env=env,
            console_output=True,
        )
        processes.append(processing)

        screen_probe_host = _probe_host(env["TRADELATIN_HOST"])
        screen_base_url = f"http://{screen_probe_host}:{env['TRADELATIN_PORT']}"
        screen_health_url = f"{screen_base_url}/__tradelatin__/health"
        existing_screen_status, existing_screen_payload = _http_json_status(screen_health_url, timeout=0.8)
        if existing_screen_status != 0:
            existing_build = existing_screen_payload.get("build_id") if isinstance(existing_screen_payload, Mapping) else None
            raise RuntimeError(
                f"Screen port {env['TRADELATIN_PORT']} is already occupied "
                f"(detected build={existing_build or 'unknown'}). Stop the stale Screen process before starting Integration."
            )

        print(f"[SCREEN] START build={BUILD_ID}", flush=True)
        screen = _service_popen([sys.executable, "main.py"], cwd=SCREEN, env=env)
        processes.append(screen)

        # Screen and Processing initialize concurrently. The HMI no longer waits
        # for manual-family ETL to finish before becoming reachable.
        _wait_for_http(
            screen_health_url,
            process=screen,
            service_name="Screen",
            timeout=30.0,
            expected_json={"status": "ok", "service": "screen", "build_id": BUILD_ID},
        )
        _wait_for_file(
            PROCESSING_STATUS,
            process=processing,
            service_name="Processing",
            timeout=15.0,
        )
        print("[PROCESSING] READY", flush=True)
        print("", flush=True)
        print("[RUNTIME]", flush=True)
        print("Prices    5s", flush=True)
        print("Prices 1m/5m/current price 5s fast lane", flush=True)
        print("Liquidity KPI/table contract writes 5s", flush=True)
        print("Liquidity structural graphs 10s", flush=True)
        print("CVD       15s", flush=True)
        print("Manual only: Open Interest, ETF, On-Chain, Volatility, Liquidations", flush=True)
        print("", flush=True)
        screen_url = f"{screen_base_url}/prices?lang=en"
        print(f"[SCREEN] READY build={BUILD_ID}", flush=True)
        print(f"[INTEGRATION] READY HMI={screen_url}", flush=True)

        _start_background_warmup(env, pending_contracts, processes)

        while not SHUTDOWN_REQUESTED.wait(0.25):
            monitored = [("Processing", processing), ("Screen", screen)]
            if emulator is not None:
                monitored.insert(0, ("Emulator", emulator))
            for name, process in monitored:
                code = process.poll()
                if code is not None:
                    raise RuntimeError(f"{name} exited with code {code}")
        print("[INTEGRATION] stopping...", flush=True)
        return 0
    except KeyboardInterrupt:
        print("[INTEGRATION] stopping...", flush=True)
        return 0
    except Exception as exc:
        print(f"[INTEGRATION] ERROR {type(exc).__name__}: {exc}", flush=True)
        return 1
    finally:
        _terminate(processes)
        _release_integration_lock(INTEGRATION_LOCK, integration_lock_token)
        print("[INTEGRATION] stopped", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
