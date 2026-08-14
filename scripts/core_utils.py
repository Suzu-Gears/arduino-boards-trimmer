"""Shared utilities for arduino-boards-trimmer scripts."""

import hashlib
import json
import os
import urllib.request

import yaml
from packaging.version import InvalidVersion, Version

USER_AGENT = "arduino-boards-trimmer (github.com/Suzu-Gears/arduino-boards-trimmer)"
DOWNLOAD_TIMEOUT = 300


def load_config(base_dir=None):
    """Load platforms.yml (single source of truth)."""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "platforms.yml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config or "platforms" not in config:
        raise ValueError(f"No 'platforms' key found in {config_path}")

    for entry in config["platforms"]:
        if "platform" not in entry or "json_url" not in entry:
            raise ValueError(f"Invalid platform entry (needs platform & json_url): {entry}")
        entry.setdefault("targets", "")
        # YAML では '' が None になることがあるため正規化
        if entry["targets"] is None:
            entry["targets"] = ""

    config.setdefault("packager_suffix", "trimmed")
    return config


def parse_targets(targets_str):
    """'a,b,c' -> {'a','b','c'} (empty string -> empty set = mirror mode)."""
    return {t.strip() for t in str(targets_str).split(",") if t.strip()}


def version_key(v):
    """Sort key for Arduino platform versions.

    PEP 440 に厳密には従わない文字列でも落ちないようにフォールバックする。
    プレリリース (3.0.0-rc1) は正式版 (3.0.0) より古いと正しく判定される。
    """
    try:
        return (1, Version(str(v)))
    except InvalidVersion:
        # 数値化できる部分だけで比較するフォールバック
        parts = []
        for token in str(v).replace("-", ".").split("."):
            parts.append((0, int(token)) if token.isdigit() else (1, token))
        return (0, parts)


def latest_platform_entry(index_data):
    """Return the newest platform entry from a board manager index."""
    platforms = index_data["packages"][0]["platforms"]
    if not platforms:
        raise ValueError("Index JSON contains no platforms")
    return max(platforms, key=lambda p: version_key(p["version"]))


def fetch_json(url):
    print(f"Downloading {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url, dest_path):
    print(f"Downloading archive from {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as response, open(dest_path, "wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(path, expected):
    """expected: 'SHA-256:abcd...' 形式。照合失敗なら例外。"""
    if not expected:
        print("WARNING: upstream index has no checksum; skipping verification")
        return
    algo, _, digest = expected.partition(":")
    if algo.upper() != "SHA-256":
        print(f"WARNING: unsupported checksum algorithm '{algo}'; skipping verification")
        return
    actual = sha256_of(path)
    if actual.lower() != digest.strip().lower():
        raise RuntimeError(
            f"Checksum mismatch for {os.path.basename(path)}:\n"
            f"  expected {digest}\n  actual   {actual}\n"
            "Upstream archive may be corrupted or tampered with. Aborting."
        )
    print(f"Upstream checksum verified: {actual}")
