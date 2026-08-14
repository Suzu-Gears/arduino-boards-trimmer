"""Generate AVAILABLE_BOARDS.md from platforms.yml."""

import os
import tempfile

from core_utils import download_file, fetch_json, latest_platform_entry, load_config
from filter_core import extract_archive, find_extracted_dir


def fetch_boards(json_url):
    data = fetch_json(json_url)
    latest = latest_platform_entry(data)
    version = latest["version"]

    download_url = latest.get("url")
    if not download_url:
        print("Platform entry has no 'url'; skipping")
        return version, []
    archive_name = download_url.split("/")[-1]

    boards = []
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = os.path.join(tmpdir, archive_name)
        download_file(download_url, archive_path)

        print("Extracting archive to find boards.txt...")
        extract_archive(archive_path, tmpdir)
        try:
            extracted_dir = find_extracted_dir(tmpdir, archive_name)
        except SystemExit:
            print("Could not find extracted directory.")
            return version, []

        boards_txt_path = os.path.join(extracted_dir, "boards.txt")
        if not os.path.exists(boards_txt_path):
            print("boards.txt not found inside the archive.")
            return version, []

        with open(boards_txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("menu."):
                    continue
                if ".name=" in line:
                    board_id, _, name = line.partition(".name=")
                    if "." not in board_id:
                        boards.append((name.strip(), board_id.strip()))

    boards.sort(key=lambda x: x[0].lower())
    return version, boards


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_file = os.path.join(base_dir, "AVAILABLE_BOARDS.md")

    config = load_config(base_dir)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# Available Boards\n\n")
        f.write("フォークして独自にカスタマイズする際、`platforms.yml` の "
                "`targets` に以下の **Board ID** をカンマ区切りで指定してください。\n\n")

        for p in config["platforms"]:
            try:
                version, boards = fetch_boards(p["json_url"])
                f.write(f"## {p['platform'].upper()}\n\n")
                f.write(f"Based on release version `{version}`\n\n")
                f.write("| Board Name | Board ID |\n")
                f.write("| --- | --- |\n")
                for name, board_id in boards:
                    f.write(f"| {name} | `{board_id}` |\n")
                f.write("\n")
            except Exception as e:
                print(f"Failed to process {p['platform']}: {e}")

    print(f"Generated {out_file}")


if __name__ == "__main__":
    main()
