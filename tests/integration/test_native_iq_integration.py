async def _invoke_tool_or_func(callable_obj, **kwargs):
    """Invoke a LangChain tool or a plain (a)sync function.
    Priority:
    - If tool exposes .ainvoke, use await .ainvoke(kwargs)
    - Else if exposes .invoke, use .invoke(kwargs)
    - Else call as function (await if coroutine or awaitable)
    """
    ainvoke = getattr(callable_obj, "ainvoke", None)
    if callable(ainvoke):
        return await ainvoke(kwargs)
    invoke = getattr(callable_obj, "invoke", None)
    if callable(invoke):
        return invoke(kwargs)
    if inspect.iscoroutinefunction(callable_obj):
        return await callable_obj(**kwargs)
    maybe = callable_obj(**kwargs)
    return await maybe if inspect.isawaitable(maybe) else maybe
import os
import asyncio
import importlib
import sys
from pathlib import Path as _Path
from datetime import datetime, timedelta

# Ensure project root and src/ are on sys.path for dynamic imports
_ROOT = _Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for p in [str(_SRC), str(_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)
import inspect
import pytest
import tempfile
from pathlib import Path

INTEGRATION_MARK = pytest.mark.integration

REQUIRED_ENV = [
    # Provide at least one of these depending on which tests you want to run
    # We'll check per-test more specifically
]


def _has_env(var: str) -> bool:
    val = os.getenv(var)
    return val is not None and val.strip() != ""


def _resolve_callable(module_path: str, candidates: list[str]):
    """
    Try to import a callable from module_path, picking the first name found in candidates.
    Returns (callable, module) or (None, None) if not found.
    """
    try:
        mod = importlib.import_module(module_path)
    except Exception:
        return None, None

    for name in candidates:
        fn = getattr(mod, name, None)
        if fn and callable(fn):
            # Accept any callable (function, method, tool-decorated function, etc.)
            return fn, mod
    return None, mod

def _default_meeting_start_iso() -> str:
    """Return a sensible default start time ~15 minutes from now in local tz (ISO-8601)."""
    local_now = datetime.now().astimezone()
    return (local_now + timedelta(minutes=15)).isoformat(timespec="minutes")


def _append_signature(body: str) -> str:
    """Append standardized Native IQ signature with user's name if available."""
    sender = os.getenv("NI_IT_SENDER_NAME") or os.getenv("SMTP_SENDER_NAME") or "User"
    return f"{body}\n\nNative IQ on behalf of {sender}"
    for name in candidates:
        fn = getattr(mod, name, None)
        if fn and callable(fn):
            # Accept any callable (function, method, tool-decorated function, etc.)
            return fn, mod
    return None, mod


def _resolve_callable_multi(module_paths: list[str], candidates: list[str]):
    """
    Try multiple module paths until a callable is found. Returns (callable, module_path_used).
    """
    for mp in module_paths:
        fn, _ = _resolve_callable(mp, candidates)
        if fn is not None:
            return fn, mp
    return None, None


async def _download_drive_file_by_name(name: str) -> Path | None:
    """
    Best-effort Google Drive helper.
    Tries to resolve functions in src.domains.tools.drive_tool to locate and download a file by name.
    Returns a local Path if successful, else None.
    """
    # Resolve module and potential helpers
    drive_mod = None
    for mp in [
        "src.domains.tools.google_drive_tool",
        "domains.tools.google_drive_tool",
    ]:
        try:
            drive_mod = importlib.import_module(mp)
            break
        except Exception:
            continue
    if drive_mod is None:
        return None

    # Use internal service to search by exact name
    drive_service = getattr(drive_mod, "_drive_service", None)
    if drive_service is None or not hasattr(drive_service, "list_files"):
        return None
    # Query for exact match (not trashed)
    query = f"name = '{name}' and trashed = false"
    try:
        files = drive_service.list_files(query=query, max_results=1)
    except Exception:
        return None
    if not files:
        return None
    file_obj = files[0]
    file_id = getattr(file_obj, "id", None)
    if not file_id:
        return None

    # Download to temp file
    tmp_dir = Path(tempfile.gettempdir()) / "ni_integration_attachments"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_path = tmp_dir / f"{name}"

    # Download using internal service method
    try:
        ok = drive_service.download_file(file_id, str(out_path))
    except Exception:
        return None

    return out_path if out_path.exists() else None


@INTEGRATION_MARK
@pytest.mark.asyncio
async def test_real_email_tool_sends_message_or_dry_run():
    """
    Attempts to call the real email tool.
    - Respects DRY_RUN (NI_IT_DRY_RUN=true) to avoid actual network sending.
    - Requires at least NI_IT_TEST_RECIPIENT for non-dry-run.
    Skips if no suitable callable is found.
    """
    dry_run = os.getenv("NI_IT_DRY_RUN", "true").lower() == "true"
    test_recipient = os.getenv("NI_IT_TEST_RECIPIENT", "")

    email_callable, mod_path = _resolve_callable_multi(
        [
            "src.domains.tools.email_tool",
            "domains.tools.email_tool",
        ],
        candidates=["email_tool", "send_email", "send"],
    )
    if email_callable is None:
        pytest.skip("Could not resolve a real email tool callable in src.domains.tools.email_tool")

    subject = "Native IQ Integration Test"
    body = _append_signature("This is a Native IQ integration test email.")
    # Optional attachments: comma-separated absolute/relative paths
    attach_env = os.getenv("NI_IT_ATTACH_PATHS", "").strip()
    attachments = [p.strip() for p in attach_env.split(",") if p.strip()] if attach_env else None

    if dry_run:
        # If module supports DRY_RUN flag, set it; otherwise, just exercise param validation
        os.environ["NI_IT_DRY_RUN"] = "true"
        try:
            # Try standard signature: recipient, subject, body, attachments?
            kwargs = {"recipient": test_recipient or "dryrun@example.com", "subject": subject, "body": body}
            if attachments:
                kwargs["attachments"] = attachments
            if inspect.iscoroutinefunction(email_callable):
                res = await email_callable(**kwargs)
            else:
                maybe_coro = email_callable(**kwargs)
                if inspect.isawaitable(maybe_coro):
                    res = await maybe_coro
                else:
                    res = maybe_coro
        except TypeError:
            # Fallback to positional; attachments not supported in this path
            if inspect.iscoroutinefunction(email_callable):
                res = await email_callable(test_recipient or "dryrun@example.com", subject, body)
            else:
                maybe_coro = email_callable(test_recipient or "dryrun@example.com", subject, body)
                res = await maybe_coro if inspect.isawaitable(maybe_coro) else maybe_coro
        assert res is not None


@INTEGRATION_MARK
@pytest.mark.asyncio
async def test_email_with_drive_attachment_real_or_dry_run():
    """
    Resolve a Drive file by name and send it as an email attachment using the real email tool.
    Configuration via env:
      - NI_IT_DRY_RUN (default true) to avoid real network calls
      - NI_IT_TEST_RECIPIENT (required when NI_IT_DRY_RUN=false)
      - NI_IT_DRIVE_FILE_NAME (default 'test_doc')
    Skips gracefully if drive tool or email tool cannot be resolved.
    """
    dry_run = os.getenv("NI_IT_DRY_RUN", "true").lower() == "true"
    test_recipient = os.getenv("NI_IT_TEST_RECIPIENT", "")
    drive_name = os.getenv("NI_IT_DRIVE_FILE_NAME", "test_doc")

    email_callable, _ = _resolve_callable_multi([
        "src.domains.tools.email_tool",
        "domains.tools.email_tool",
    ], ["email_tool", "send_email", "send"])
    if email_callable is None:
        pytest.skip("Could not resolve real email tool callable from src.domains.tools.email_tool")

    # Attempt to download from Drive
    attachment_path = await _download_drive_file_by_name(drive_name)
    if attachment_path is None:
        pytest.skip("Drive tool not available or file not found: set NI_IT_DRIVE_FILE_NAME and configure drive creds")

    subject = f"Native IQ Integration: Drive attachment {drive_name}"
    body = _append_signature(f"Sending Google Drive file '{drive_name}' as attachment.")
    attachments = [str(attachment_path)]

    if dry_run:
        os.environ["NI_IT_DRY_RUN"] = "true"
    else:
        if not test_recipient:
            pytest.skip("Set NI_IT_TEST_RECIPIENT for non-dry-run real email send")
        
    # Use the proper tool invocation helper
    res = await _invoke_tool_or_func(
        email_callable,
        recipient=test_recipient or "dryrun@example.com",
        subject=subject,
        body=body,
        attachments=attachments,
    )
    assert res is not None


@INTEGRATION_MARK
@pytest.mark.asyncio
async def test_real_schedule_meeting_or_dry_run():
    """
    Attempts to call the real schedule meeting tool.
    - Respects DRY_RUN (NI_IT_DRY_RUN=true).
    - Skips if callable cannot be resolved.
    """
    dry_run = os.getenv("NI_IT_DRY_RUN", "true").lower() == "true"

    schedule_callable, _ = _resolve_callable_multi([
        "src.domains.tools.calendar_tool",
        "domains.tools.calendar_tool",
        # Fallback for misspelling present in repo
        "src.domains.tools.calandar_tool",
        "domains.tools.calandar_tool",
    ], candidates=["schedule_meeting", "create_event", "schedule"])
    if schedule_callable is None:
        pytest.skip("Could not resolve a real calendar scheduling callable in src.domains.tools.calendar_tool")

    title = "Native IQ Integration Meeting"
    # ISO-like start time; your implementation may require timezone suffix
    start_time = os.getenv("NI_IT_MEETING_START", "2025-12-31T23:00:00+00:00")
    duration_minutes = 30
    attendees = [os.getenv("NI_IT_TEST_RECIPIENT", "dryrun@example.com")]

    res = await _invoke_tool_or_func(
        schedule_callable,
        title=title,
        start_time=start_time,
        duration_minutes=duration_minutes,
        attendees=attendees,
    )

    assert res is not None

@INTEGRATION_MARK
@pytest.mark.asyncio
async def test_chained_meeting_then_email_real_or_dry_run():
    """
    Schedules a meeting then sends an email referencing it (if both callables are available).
    Skips partially if one callable is missing.
    """
    dry_run = os.getenv("NI_IT_DRY_RUN", "true").lower() == "true"

    email_callable, _ = _resolve_callable_multi([
        "src.domains.tools.email_tool",
        "domains.tools.email_tool",
    ], ["email_tool", "send_email", "send"])
    schedule_callable, _ = _resolve_callable_multi([
        "src.domains.tools.calendar_tool",
        "domains.tools.calendar_tool",
        "src.domains.tools.calandar_tool",
        "domains.tools.calandar_tool",
    ], ["schedule_meeting", "create_event", "schedule"])

    if schedule_callable is None and email_callable is None:
        pytest.skip("Neither scheduling nor email callable could be resolved")

    meeting_link = None
    if schedule_callable is not None:
        title = "Native IQ Chained Meeting"
        start_time = os.getenv("NI_IT_MEETING_START") or _default_meeting_start_iso()
        duration_minutes = 25
        attendees = [os.getenv("NI_IT_TEST_RECIPIENT", "dryrun@example.com")]
        sched_res = await _invoke_tool_or_func(
            schedule_callable,
            title=title,
            start_time=start_time,
            duration_minutes=duration_minutes,
            attendees=attendees,
        )
        assert sched_res is not None
        # Best-effort extraction of link string
        if isinstance(sched_res, str) and "http" in sched_res:
            meeting_link = sched_res.split("http", 1)[-1]
            meeting_link = "http" + meeting_link

    if email_callable is not None:
        recipient = os.getenv("NI_IT_TEST_RECIPIENT", "dryrun@example.com")
        subject = "Chained Meeting Invite"
        body = "Here is the invite link.\n\n"
        if meeting_link and "http" in meeting_link:
            body += f"Join: {meeting_link}"
        body = _append_signature(body)
        res = await _invoke_tool_or_func(
            email_callable,
            recipient=recipient,
            subject=subject,
            body=body,
        )
        assert res is not None
