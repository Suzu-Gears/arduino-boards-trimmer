# Arduino Pico Minimal

公式の [earlephilhower/arduino-pico](https://github.com/earlephilhower/arduino-pico) コアから、特定のボードのみを抽出して最小化したカスタムボードマネージャーパッケージを自動生成・配信するリポジトリです。
Arduino IDEのボード選択メニューに不要なボードが大量に表示されるのを防ぎ、スッキリと使うことができます。

現在、以下のボードのみが有効化されています：
- Raspberry Pi Pico
- Raspberry Pi Pico W
- Raspberry Pi Pico 2
- Raspberry Pi Pico 2W
- Seeed XIAO RP2040
- Seeed XIAO RP2350
- VCC-GND YD RP2040
- Waveshare RP2040 Zero
- Waveshare RP2350 Zero
- Generic RP2040
- Generic RP2350

## Arduino IDE での使い方

1. Arduino IDE を起動します。
2. **ファイル** > **基本設定** (macOSの場合は **Arduino IDE** > **Settings...**) を開きます。
3. **追加のボードマネージャのURL** に以下のURLを追加します。
   ```text
   https://github.com/Suzu-Gears/arduino-pico-minimal/releases/latest/download/package_custom_pico_index.json
   ```
   *(※すでに他のURLが設定されている場合は、カンマ区切りまたは改行して追加してください)*
4. **ツール** > **ボード** > **ボードマネージャ...** を開きます。
5. 検索欄に `pico` または `rp2040` と入力し、このリポジトリから配信されているカスタム版パッケージをインストールしてください。

## 仕組みについて

GitHub Actions のワークフローが毎日自動的に実行され、アップストリームの `arduino-pico` リポジトリの最新リリースを確認します。
新しいリリースが見つかると、自動的にコアをダウンロードして `boards.txt` をフィルタリングし、不要なボード定義を削除した状態の `tar.gz` アーカイブと JSON インデックスファイルを再生成して、このリポジトリの [Releases](https://github.com/Suzu-Gears/arduino-pico-minimal/releases) に自動公開します。

## フォークしてカスタマイズする

このリポジトリをフォークし、ご自身で使用するボードだけを有効化することも簡単です。
対応しているすべてのボード名と内部ID（Board ID）のリストは **[AVAILABLE_BOARDS.md](./AVAILABLE_BOARDS.md)** にまとめています。

有効化したいボードの内部IDを `scripts/filter_core.py` 内の `TARGET_BOARDS` に追記・変更するだけで、独自の最小限パッケージを構築できます。
