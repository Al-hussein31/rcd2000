"""Autodesk Platform Services (APS) DWG export — Batch 11 cloud backend.

Uses the APS **Automation API v3** to run AutoCAD's AccoreConsole in
the cloud: open the DXF, SaveAs DWG. This is the only official
Autodesk path that needs no local AutoCAD and produces a native DWG.

Workflow (documented in the module docstring and research plan):
  auth -> ensure bucket -> upload DXF (signed S3) -> submit workitem
  -> poll -> download DWG.

Pricing: 300 free AutoCAD processing minutes/month, then 1 token /
$3 per 12 minutes. A single DXF->DWG conversion is usually < 1 min.

Credentials come from environment variables (never committed):
  APS_CLIENT_ID, APS_CLIENT_SECRET

Pure `requests` client — no third-party SDK dependency. Optional
dependency: ``pip install "rcd2000[aps]"`` (requests).
"""
from __future__ import annotations

import base64
import os
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

import requests

AUTH_URL = "https://developer.api.autodesk.com/authentication/v2/token"
DA_BASE = "https://developer.api.autodesk.com/da/us-east/v3"
OSS_BASE = "https://developer.api.autodesk.com/oss/v2"

# Activity created once on your APS account (see provision_activity).
# Format: "<NICKNAME>.Rcd2000DxfToDwg+prod"
ACTIVITY_ID = os.environ.get(
    "RCD2000_APS_ACTIVITY", "Rcd2000DxfToDwg+prod"
)

SCOPES = (
    "code:all bucket:create bucket:read "
    "data:create data:write data:read"
)


class ApsError(RuntimeError):
    """Raised for any APS API failure."""


def get_token(client_id: str, client_secret: str) -> str:
    """OAuth2 client-credentials token (valid ~1 hour)."""
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        AUTH_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth}",
        },
        data={"grant_type": "client_credentials", "scope": SCOPES},
        timeout=30,
    )
    if resp.status_code != 200:
        raise ApsError(f"token failed: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def ensure_bucket(token: str, bucket_key: str) -> None:
    """Create a transient bucket if it doesn't exist (idempotent)."""
    resp = requests.post(
        f"{OSS_BASE}/buckets",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"bucketKey": bucket_key, "policyKey": "transient"},
        timeout=30,
    )
    # 409 = bucket already exists -> fine
    if resp.status_code not in (200, 201, 409):
        raise ApsError(f"bucket create failed: {resp.status_code} {resp.text}")


def upload_dxf(token: str, bucket: str, key: str, dxf_path: str) -> None:
    """Upload DXF to OSS via signed S3 URL."""
    # 1) request signed upload
    resp = requests.get(
        f"{OSS_BASE}/buckets/{bucket}/objects/{key}/signeds3upload",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise ApsError(f"signed upload get failed: {resp.status_code} {resp.text}")
    data = resp.json()
    upload_key = data["uploadKey"]
    url = data["urls"][0]

    # 2) PUT raw bytes (no auth header on S3)
    with open(dxf_path, "rb") as f:
        put = requests.put(url, data=f.read(), timeout=60)
    if put.status_code not in (200, 201):
        raise ApsError(f"s3 put failed: {put.status_code}")

    # 3) confirm
    confirm = requests.post(
        f"{OSS_BASE}/buckets/{bucket}/objects/{key}/signeds3upload",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"uploadKey": upload_key},
        timeout=30,
    )
    if confirm.status_code != 200:
        raise ApsError(f"signed upload confirm failed: {confirm.status_code}")


def submit_workitem(
    token: str,
    bucket: str,
    in_key: str,
    out_key: str,
    activity_id: str = ACTIVITY_ID,
) -> str:
    """Submit the DXF->DWG workitem, return workitem id."""
    payload = {
        "activityId": activity_id,
        "arguments": {
            "InputDxf": {
                "url": f"urn:adsk.objects:os.object:{bucket}/{in_key}",
                "verb": "get",
            },
            "Result": {
                "url": f"urn:adsk.objects:os.object:{bucket}/{out_key}",
                "verb": "put",
            },
        },
    }
    resp = requests.post(
        f"{DA_BASE}/workitems",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if resp.status_code != 201:
        raise ApsError(f"workitem submit failed: {resp.status_code} {resp.text}")
    return resp.json()["id"]


def poll_workitem(token: str, workitem_id: str,
                  poll_interval: float = 3.0,
                  timeout: float = 600.0,
                  on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """Poll a workitem until success/failure/cancelled."""
    start = time.time()
    while True:
        resp = requests.get(
            f"{DA_BASE}/workitems/{workitem_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise ApsError(f"workitem poll failed: {resp.status_code}")
        status = resp.json()
        st = status.get("status")
        if on_progress:
            on_progress(st)
        if st in ("success", "failed", "cancelled"):
            return status
        if time.time() - start > timeout:
            raise ApsError(f"workitem timed out after {timeout:.0f}s")
        time.sleep(poll_interval)


def download_dwg(token: str, bucket: str, out_key: str, out_path: str) -> Path:
    """Download the DWG from OSS via a signed URL."""
    resp = requests.post(
        f"{OSS_BASE}/buckets/{bucket}/objects/{out_key}/signed",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"minutesExpiration": 5},
        timeout=30,
    )
    if resp.status_code != 200:
        raise ApsError(f"signed download failed: {resp.status_code} {resp.text}")
    url = resp.json()["signedUrl"]
    dl = requests.get(url, timeout=120)
    if dl.status_code != 200:
        raise ApsError(f"download failed: {dl.status_code}")
    Path(out_path).write_bytes(dl.content)
    return Path(out_path)


def dxf_to_dwg(
    dxf_path: str | Path,
    out_path: str | Path,
    *,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    bucket: str = "rcd2000xfr",
) -> Path:
    """Full cloud pipeline: DXF -> native DWG via APS."""
    client_id = client_id or os.environ.get("APS_CLIENT_ID")
    client_secret = client_secret or os.environ.get("APS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ApsError(
            "APS credentials missing. Set APS_CLIENT_ID and APS_CLIENT_SECRET "
            "environment variables."
        )

    stem = Path(dxf_path).stem
    in_key = f"in/{stem}-{uuid.uuid4().hex[:8]}.dxf"
    out_key = f"out/{stem}-{uuid.uuid4().hex[:8]}.dwg"

    token = get_token(client_id, client_secret)
    ensure_bucket(token, bucket)
    upload_dxf(token, bucket, in_key, str(dxf_path))
    wid = submit_workitem(token, bucket, in_key, out_key)
    status = poll_workitem(token, wid)
    if status.get("status") != "success":
        raise ApsError(
            f"WorkItem failed: {status.get('status')} "
            f"report: {status.get('reportUrl')}"
        )
    return download_dwg(token, bucket, out_key, str(out_path))


def provision_activity(client_id: str, client_secret: str,
                       nickname: str) -> str:
    """One-time setup: create nickname + Activity + prod alias.

    Returns the full activity id ("<nickname>.Rcd2000DxfToDwg+prod").
    Idempotent for repeated runs (409s are ignored).
    """
    token = get_token(client_id, client_secret)

    # nickname (best-effort; may already exist)
    requests.post(
        f"{DA_BASE}/forgeapps/me",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"nickname": nickname},
        timeout=30,
    )

    activity_payload = {
        "id": "Rcd2000DxfToDwg",
        "commandLine": [
            "$(engine.path)\\accoreconsole.exe /i \"$(args[InputDxf].path)\" "
            "/s \"$(settings[script].path)\""
        ],
        "parameters": {
            "InputDxf": {"zip": False, "ondemand": False, "verb": "get",
                         "localName": "Input.dxf"},
            "Result": {"zip": False, "ondemand": False, "verb": "put",
                       "required": True, "localName": "Output.dwg"},
        },
        "engine": "Autodesk.AutoCAD+24_3",
        "appbundles": [],
        "settings": {
            "script": "(command \"_saveas\" \"2018\" \"Output.dwg\")\n"
                      "(command \"_quit\")\n"
        },
        "description": "Convert DXF to native DWG 2018 (AC1032)",
    }
    act = requests.post(
        f"{DA_BASE}/activities",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json=activity_payload,
        timeout=30,
    )
    if act.status_code not in (200, 201, 409):
        raise ApsError(f"activity create failed: {act.status_code} {act.text}")

    alias = requests.post(
        f"{DA_BASE}/activities/Rcd2000DxfToDwg/aliases",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"version": 1, "id": "prod"},
        timeout=30,
    )
    if alias.status_code not in (200, 201, 409):
        raise ApsError(f"alias create failed: {alias.status_code} {alias.text}")

    return f"{nickname}.Rcd2000DxfToDwg+prod"
