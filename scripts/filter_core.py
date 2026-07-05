import json
import urllib.request
import tarfile
import hashlib
import os
import tempfile
import re
import shutil
import sys

def parse_version(v):
    return [int(x) if x.isdigit() else x for x in re.split(r'[\.\-]', v)]

def get_env_vars():
    platform_name = os.environ.get('PLATFORM_NAME')
    json_url = os.environ.get('JSON_URL')
    targets_str = os.environ.get('TARGET_BOARDS')
    my_repo = os.environ.get('GITHUB_REPOSITORY', 'user/repo')

    if not platform_name or not json_url or not targets_str:
        print("Missing required environment variables: PLATFORM_NAME, JSON_URL, TARGET_BOARDS")
        sys.exit(1)

    target_boards = {t.strip() for t in targets_str.split(',') if t.strip()}
    return platform_name, json_url, target_boards, my_repo

def fetch_json(json_url):
    print(f"Downloading {json_url}...")
    req = urllib.request.Request(json_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['--get-version', '--build']:
        print("Usage: python filter_core.py [--get-version | --build]")
        sys.exit(1)

    mode = sys.argv[1]
    platform_name, json_url, target_boards, my_repo = get_env_vars()

    data = fetch_json(json_url)

    platforms = data['packages'][0]['platforms']
    latest_platform = max(platforms, key=lambda p: parse_version(p['version']))
    version = latest_platform['version']

    if mode == '--get-version':
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"version={version}\n")
        else:
            print(f"version={version}")
        return

    # --build mode
    print(f"Latest version: {version}")

    download_url = latest_platform.get('url')
    if not download_url and 'systems' in latest_platform:
        download_url = latest_platform['systems'][0]['url']

    archive_name = download_url.split('/')[-1]

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = os.path.join(tmpdir, archive_name)
        print(f"Downloading archive from {download_url}...")

        req_arch = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_arch) as response, open(archive_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

        print("Extracting archive...")
        if archive_name.endswith('.zip'):
            import zipfile
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
        else:
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(path=tmpdir)

        extracted_dir = None
        for name in os.listdir(tmpdir):
            if name != archive_name and os.path.isdir(os.path.join(tmpdir, name)):
                extracted_dir = os.path.join(tmpdir, name)
                break

        if not extracted_dir:
            raise Exception("Could not find extracted directory.")

        boards_txt_path = os.path.join(extracted_dir, 'boards.txt')
        if not os.path.exists(boards_txt_path):
            raise Exception("boards.txt not found inside the archive.")

        print("Filtering boards.txt...")
        with open(boards_txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        filtered_lines = []
        kept_board_names = set()
        for line in lines:
            stripped = line.strip()
            if not stripped:
                filtered_lines.append(line)
            elif stripped.startswith('#'):
                filtered_lines.append(line)
            elif stripped.startswith('menu.'):
                filtered_lines.append(line)
            else:
                board_id = stripped.split('.')[0]
                if board_id in target_boards:
                    filtered_lines.append(line)
                    if stripped.startswith(f"{board_id}.name="):
                        kept_board_names.add(stripped.split('=', 1)[1].strip())

        with open(boards_txt_path, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)

        print("Recompressing archive...")
        new_archive_name = f'custom-{platform_name}-{version}.tar.gz'
        new_archive_path = os.path.join(os.getcwd(), new_archive_name)

        root_dir_name = os.path.basename(extracted_dir)
        with tarfile.open(new_archive_path, 'w:gz') as tar:
            tar.add(extracted_dir, arcname=root_dir_name)

        print("Calculating hash and size...")
        size = os.path.getsize(new_archive_path)
        with open(new_archive_path, 'rb') as f:
            sha256_hash = hashlib.sha256(f.read()).hexdigest()

        print(f"Size: {size}, SHA-256: {sha256_hash}")

        print("Updating JSON...")
        # Keep only the latest version in the JSON
        data['packages'][0]['platforms'] = [latest_platform]

        latest_platform['archiveFileName'] = new_archive_name
        latest_platform['checksum'] = f'SHA-256:{sha256_hash}'
        latest_platform['size'] = str(size)
        latest_platform['url'] = f'https://github.com/{my_repo}/releases/download/{platform_name}-{version}/{new_archive_name}'

        if 'boards' in latest_platform:
            latest_platform['boards'] = [b for b in latest_platform['boards'] if b.get('name') in kept_board_names]

        out_json = f'package_custom_{platform_name}_index.json'
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"Done. Saved {new_archive_name} and {out_json}")

if __name__ == '__main__':
    main()
