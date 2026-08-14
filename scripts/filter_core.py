"""Build trimmed Arduino board manager packages.

Modes:
  --matrix       platforms.yml から GitHub Actions 用のマトリクス JSON を出力
  --get-version  最新バージョンを取得し upstream index をキャッシュ
  --build        コアをダウンロード・フィルタ・再パッケージし index JSON を生成

環境変数 (--get-version / --build):
  PLATFORM_NAME, JSON_URL, TARGET_BOARDS, GITHUB_REPOSITORY, PACKAGER_SUFFIX
"""

import copy
import gzip
import json
import os
import sys
import tarfile
import tempfile
import zipfile

from core_utils import (
    download_file,
    fetch_json,
    latest_platform_entry,
    load_config,
    parse_targets,
    sha256_of,
    verify_checksum,
)


# ---------------------------------------------------------------------------
# boards.txt filtering (pure function -> unit testable)
# ---------------------------------------------------------------------------

def filter_boards_txt(lines, target_boards):
    """Filter boards.txt lines, keeping only target boards.

    Returns (filtered_lines, kept_board_names, seen_board_ids).
    - コメント・空行・menu.* 行・ボードIDを持たない大域プロパティ行は常に保持
    - target_boards が空なら全行保持(ミラーモード)
    """
    filtered = []
    kept_names = set()
    seen_ids = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("menu."):
            filtered.append(line)
            continue

        key = stripped.split("=", 1)[0]
        if "." not in key:
            # 例: "version=1.0" のようなボードIDを持たない大域プロパティ
            filtered.append(line)
            continue

        board_id = key.split(".", 1)[0]
        seen_ids.add(board_id)

        if not target_boards or board_id in target_boards:
            filtered.append(line)
            if key == f"{board_id}.name":
                kept_names.add(stripped.split("=", 1)[1].strip())

    return filtered, kept_names, seen_ids


def validate_targets(target_boards, seen_ids, platform_name):
    """指定した Board ID が1つも存在しない場合は即座に失敗させる。"""
    missing = target_boards - seen_ids
    if missing:
        raise SystemExit(
            f"ERROR [{platform_name}]: these target board IDs were not found in "
            f"boards.txt: {', '.join(sorted(missing))}\n"
            f"Check AVAILABLE_BOARDS.md for valid IDs. Aborting to avoid "
            f"publishing a broken package."
        )


# ---------------------------------------------------------------------------
# Archive handling
# ---------------------------------------------------------------------------

def extract_archive(archive_path, dest_dir):
    """zip / tar.gz を展開。zip では実行権限ビットを復元する。"""
    if archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            for info in zf.infolist():
                extracted = zf.extract(info, dest_dir)
                perm = (info.external_attr >> 16) & 0o7777
                if perm:
                    os.chmod(extracted, perm)
    else:
        with tarfile.open(archive_path, "r:*") as tar:
            tar.extractall(path=dest_dir, filter="tar")


def find_extracted_dir(tmpdir, archive_name):
    for name in os.listdir(tmpdir):
        full = os.path.join(tmpdir, name)
        if name != archive_name and os.path.isdir(full):
            return full
    raise SystemExit("ERROR: could not find extracted directory")


def create_reproducible_targz(src_dir, out_path, root_name):
    """決定論的 tar.gz を生成する。

    同じ入力からは常に同じバイト列(=同じチェックサム)が得られるよう、
    mtime / uid / gid / ファイル順序 / gzip ヘッダを固定する。
    """
    entries = [(root_name, src_dir)]
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames.sort()
        rel = os.path.relpath(dirpath, src_dir)
        for name in sorted(dirnames + filenames):
            full = os.path.join(dirpath, name)
            arc = os.path.join(root_name, name) if rel == "." else os.path.join(root_name, rel, name)
            entries.append((arc, full))

    def normalize(ti):
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = ""
        ti.mtime = 0
        return ti

    with open(out_path, "wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for arcname, fullpath in sorted(entries, key=lambda e: e[0]):
                    tar.add(fullpath, arcname=arcname, recursive=False, filter=normalize)


# ---------------------------------------------------------------------------
# Index JSON manipulation
# ---------------------------------------------------------------------------

def rename_packager(data, suffix):
    """公式 index との名前衝突を避けるため packager 名を変更する。

    packages[0].name を '<name>-<suffix>' に変更し、同一パッケージ内の
    ツールを参照している toolsDependencies / discoveryDependencies /
    monitorDependencies の packager フィールドも追従させる。
    (packager が 'arduino' 等の外部参照の場合は変更しない)
    """
    pkg = data["packages"][0]
    original = pkg["name"]
    new_name = f"{original}-{suffix}"
    pkg["name"] = new_name

    for platform in pkg.get("platforms", []):
        for dep_key in ("toolsDependencies", "discoveryDependencies", "monitorDependencies"):
            for dep in platform.get(dep_key, []) or []:
                if dep.get("packager") == original:
                    dep["packager"] = new_name
    return original, new_name


def mark_trimmed(platform_entry, mirror=False):
    label = " (Mirror)" if mirror else " (Trimmed)"
    if not platform_entry.get("name", "").endswith(label):
        platform_entry["name"] = platform_entry.get("name", "") + label


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def get_env():
    platform_name = os.environ.get("PLATFORM_NAME")
    json_url = os.environ.get("JSON_URL")
    if not platform_name or not json_url:
        raise SystemExit("Missing required environment variables: PLATFORM_NAME, JSON_URL")
    targets = parse_targets(os.environ.get("TARGET_BOARDS", ""))
    my_repo = os.environ.get("GITHUB_REPOSITORY", "user/repo")
    suffix = os.environ.get("PACKAGER_SUFFIX", "trimmed")
    return platform_name, json_url, targets, my_repo, suffix


def cache_path(platform_name):
    return os.path.join(os.getcwd(), f"upstream_{platform_name}_index.json")


def mode_matrix():
    config = load_config()
    include = [
        {
            "platform": p["platform"],
            "json_url": p["json_url"],
            "targets": p["targets"],
        }
        for p in config["platforms"]
    ]
    print(json.dumps({"include": include}))


def mode_get_version():
    platform_name, json_url, _, _, _ = get_env()
    data = fetch_json(json_url)
    latest = latest_platform_entry(data)
    version = latest["version"]

    # --build と同じ index を使うようキャッシュ (TOCTOU 対策)
    with open(cache_path(platform_name), "w", encoding="utf-8") as f:
        json.dump(data, f)

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"version={version}\n")
    print(f"version={version}")


def mode_build():
    platform_name, json_url, target_boards, my_repo, suffix = get_env()

    cached = cache_path(platform_name)
    if os.path.exists(cached):
        print(f"Using cached upstream index: {cached}")
        with open(cached, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = fetch_json(json_url)

    latest = copy.deepcopy(latest_platform_entry(data))
    version = latest["version"]
    print(f"Latest version: {version}  (platform={platform_name}, "
          f"mode={'filter' if target_boards else 'mirror'})")

    # 配信 JSON は最新1バージョンのみに絞る
    data["packages"][0]["platforms"] = [latest]
    original_packager, new_packager = rename_packager(data, suffix)
    print(f"Packager renamed: {original_packager} -> {new_packager}")

    if not target_boards:
        # ミラーモード: 再パッケージせず元アーカイブをそのまま参照する
        mark_trimmed(latest, mirror=True)
        write_index(data, platform_name)
        print("Mirror mode: original archive URL and checksum kept as-is. "
              "No release asset needed.")
        return

    download_url = latest.get("url")
    if not download_url:
        raise SystemExit("ERROR: platform entry has no 'url' field")
    archive_name = download_url.split("/")[-1]

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = os.path.join(tmpdir, archive_name)
        download_file(download_url, archive_path)
        verify_checksum(archive_path, latest.get("checksum"))

        print("Extracting archive...")
        extract_archive(archive_path, tmpdir)
        extracted_dir = find_extracted_dir(tmpdir, archive_name)

        boards_txt_path = os.path.join(extracted_dir, "boards.txt")
        if not os.path.exists(boards_txt_path):
            raise SystemExit("ERROR: boards.txt not found inside the archive")

        print("Filtering boards.txt...")
        with open(boards_txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        filtered, kept_names, seen_ids = filter_boards_txt(lines, target_boards)
        validate_targets(target_boards, seen_ids, platform_name)
        print(f"Kept {len(kept_names)} boards: {', '.join(sorted(kept_names))}")

        with open(boards_txt_path, "w", encoding="utf-8") as f:
            f.writelines(filtered)

        print("Creating reproducible archive...")
        new_archive_name = f"custom-{platform_name}-{version}.tar.gz"
        new_archive_path = os.path.join(os.getcwd(), new_archive_name)
        create_reproducible_targz(extracted_dir, new_archive_path,
                                  os.path.basename(extracted_dir))

        size = os.path.getsize(new_archive_path)
        digest = sha256_of(new_archive_path)
        print(f"Size: {size}, SHA-256: {digest}")

        latest["archiveFileName"] = new_archive_name
        latest["checksum"] = f"SHA-256:{digest}"
        latest["size"] = str(size)
        latest["url"] = (f"https://github.com/{my_repo}/releases/download/"
                         f"{platform_name}-{version}/{new_archive_name}")
        mark_trimmed(latest)

        if "boards" in latest:
            latest["boards"] = [b for b in latest["boards"] if b.get("name") in kept_names]

        write_index(data, platform_name)
        print(f"Done. Saved {new_archive_name}")


def write_index(data, platform_name):
    out_json = f"package_custom_{platform_name}_index.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {out_json}")


def main():
    modes = {
        "--matrix": mode_matrix,
        "--get-version": mode_get_version,
        "--build": mode_build,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in modes:
        print(f"Usage: python filter_core.py [{' | '.join(modes)}]")
        sys.exit(1)
    modes[sys.argv[1]]()


if __name__ == "__main__":
    main()
