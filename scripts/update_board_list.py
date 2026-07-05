import urllib.request
import json
import os
import re
import tempfile
import tarfile
import shutil

def get_platforms_from_yaml(yaml_path):
    platforms = []
    with open(yaml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    matches = re.finditer(r'-\s+platform:\s+(\S+)\s+json_url:\s+(\S+)', content)
    for m in matches:
        plat = m.group(1)
        url = m.group(2)
        platforms.append({
            "name": plat.upper(),
            "json_url": url
        })
    return platforms

def parse_version(v):
    return [int(x) if x.isdigit() else x for x in re.split(r'[\.\-]', v)]

def fetch_boards_from_json(json_url):
    print(f"Downloading {json_url}...")
    req = urllib.request.Request(json_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))

    platforms = data['packages'][0]['platforms']
    latest_platform = max(platforms, key=lambda p: parse_version(p['version']))
    version = latest_platform['version']

    download_url = latest_platform.get('url')
    if not download_url and 'systems' in latest_platform:
        download_url = latest_platform['systems'][0]['url']

    archive_name = download_url.split('/')[-1]

    boards = []
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = os.path.join(tmpdir, archive_name)
        print(f"Downloading archive from {download_url}...")

        req_arch = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_arch) as response, open(archive_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

        print("Extracting archive to find boards.txt...")
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
            print("Could not find extracted directory.")
            return version, []

        boards_txt_path = os.path.join(extracted_dir, 'boards.txt')
        if not os.path.exists(boards_txt_path):
            print("boards.txt not found inside the archive.")
            return version, []

        with open(boards_txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('menu.'):
                continue

            if '.name=' in line:
                parts = line.split('.name=', 1)
                board_id = parts[0].strip()
                name = parts[1].strip()
                if '.' not in board_id:
                    boards.append((name, board_id))

    boards.sort(key=lambda x: x[0].lower())
    return version, boards

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    yaml_path = os.path.join(base_dir, '.github', 'workflows', 'sync.yml')
    out_file = os.path.join(base_dir, 'AVAILABLE_BOARDS.md')

    platforms = get_platforms_from_yaml(yaml_path)
    if not platforms:
        print("No platforms found in sync.yml")
        return

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("# Available Boards\n\n")
        f.write("フォークして独自にカスタマイズする際、`.github/workflows/sync.yml` の `targets` に以下の **Board ID** をカンマ区切りで指定してください。\n\n")

        for p in platforms:
            try:
                version, boards = fetch_boards_from_json(p['json_url'])

                f.write(f"## {p['name']}\n\n")
                f.write(f"Based on release version `{version}`\n\n")
                f.write("| Board Name | Board ID |\n")
                f.write("| --- | --- |\n")
                for name, board_id in boards:
                    f.write(f"| {name} | `{board_id}` |\n")
                f.write("\n")
            except Exception as e:
                print(f"Failed to process {p['name']}: {e}")

    print(f"Generated {out_file}")

if __name__ == '__main__':
    main()
