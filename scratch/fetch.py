import urllib.request
url = 'https://raw.githubusercontent.com/earlephilhower/arduino-pico/refs/tags/5.6.1/boards.txt'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8')
        names = ['Raspberry Pi Pico', 'Raspberry Pi Pico W', 'Raspberry Pi Pico 2', 'Raspberry Pi Pico 2W', 'Seeed XIAO RP2040', 'Seeed XIAO RP2350', 'VCC-GND YD RP2040', 'Waveshare RP2040 Zero', 'Waveshare RP2350 Zero', 'Generic RP2040', 'Generic RP2350']
        found = {}
        for line in content.split('\n'):
            if '.name=' in line:
                id, name = line.strip().split('.name=', 1)
                for target in names:
                    if name.strip() == target:
                        found[target] = id
        print('FOUND IDS:')
        for target in names:
            print(f'{target} -> {found.get(target, "NOT_FOUND")}')
except Exception as e:
    print('Error:', e)
