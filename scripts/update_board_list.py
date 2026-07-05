import urllib.request
import json
import os

def get_latest_version():
    req = urllib.request.Request('https://api.github.com/repos/earlephilhower/arduino-pico/releases/latest', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        return data['tag_name']

def main():
    try:
        tag = get_latest_version()
        print(f"Latest tag: {tag}")
    except Exception as e:
        print(f"Failed to fetch latest tag: {e}")
        tag = "master"

    url = f'https://raw.githubusercontent.com/earlephilhower/arduino-pico/refs/tags/{tag}/boards.txt'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    boards = []
    print(f"Downloading {url}...")
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8')
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('menu.'):
                continue

            if '.name=' in line:
                parts = line.split('.name=', 1)
                board_id = parts[0].strip()
                name = parts[1].strip()
                # Exclude sub-properties if any (though usually it's just id.name=)
                if '.' not in board_id:
                    boards.append((name, board_id))

    # Sort by name
    boards.sort(key=lambda x: x[0].lower())

    out_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'AVAILABLE_BOARDS.md')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(f"# Available Boards\n\n")
        f.write(f"This list was automatically generated based on the `earlephilhower/arduino-pico` release `{tag}`.\n")
        f.write("フォークして独自にカスタマイズする際、`scripts/filter_core.py` の `TARGET_BOARDS` に以下の **Board ID** を指定してください。\n\n")
        f.write("| Board Name | Board ID |\n")
        f.write("| --- | --- |\n")
        for name, board_id in boards:
            f.write(f"| {name} | `{board_id}` |\n")

    print(f"Generated {out_file}")

if __name__ == '__main__':
    main()
