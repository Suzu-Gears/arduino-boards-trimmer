# Arduino Boards Trimmer

公式の [earlephilhower/arduino-pico](https://github.com/earlephilhower/arduino-pico) (RP2040) や [espressif/arduino-esp32](https://github.com/espressif/arduino-esp32) (ESP32) などのサードパーティコアから、特定のボードのみを抽出して最小化したカスタムボードマネージャーパッケージを自動生成・配信するリポジトリです。

Arduino IDEのボード選択メニューに不要なボードが大量に表示されるのを防ぎ、スッキリと使うことができます。

現在、以下のプラットフォームとボードのみが有効化されています：

**RP2040**
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

**ESP32**
- ESP32 Dev Module
- ESP32S3 Dev Module

## Arduino IDE での使い方

1. Arduino IDE を起動します。
2. **ファイル** > **基本設定** (macOSの場合は **Arduino IDE** > **Settings...**) を開きます。
3. **追加のボードマネージャのURL** に以下のURLを追加します。
   *(※両方追加することも、必要な方だけ追加することも可能です)*

   **RP2040 (Raspberry Pi Pico系) の場合:**
   ```text
   https://Suzu-Gears.github.io/arduino-boards-trimmer/package_custom_rp2040_index.json
   ```
   **ESP32 の場合:**
   ```text
   https://Suzu-Gears.github.io/arduino-boards-trimmer/package_custom_esp32_index.json
   ```
4. **ツール** > **ボード** > **ボードマネージャ...** を開きます。
5. 検索欄に `pico` または `esp32` と入力し、このリポジトリから配信されているカスタム版パッケージをインストールしてください。

### ⚠️ Arduino IDEのキャッシュの罠
IDEのボードマネージャーは、JSONのURLを読み込むと手元のPCに強くキャッシュします。
テスト中に「新しいJSONが生成されたはずなのに、IDEのリストが変わらない」という現象が起きたら、IDEのキャッシュが原因の可能性が高いです。
その場合は、キーボードの `Ctrl + Shift + P` (Macは `Cmd + Shift + P`) でコマンドパレットを開き、「**Arduino: Clear Cache**」などを実行するか、PC内のキャッシュフォルダ（Windowsなら `%LOCALAPPDATA%\Arduino15`、Macなら `~/Library/Arduino15`）にある `package_..._index.json` を直接削除してみてください。

## 仕組みについて

GitHub Actions のワークフローが毎日自動的に実行され、アップストリームのリポジトリの最新リリースを確認します。
新しいリリースが見つかると、自動的にコアをダウンロードして `boards.txt` をフィルタリングし、不要なボード定義を削除した状態の `tar.gz` アーカイブと JSON インデックスファイルを再生成します。アーカイブは Release アセットとして自動公開され、JSONファイルは `gh-pages` ブランチにプッシュされます。

## フォークしてカスタマイズする

このリポジトリをフォークし、ご自身で使用するボードだけを有効化したり、新しいプラットフォームを追加することも簡単です。

### 既存のプラットフォームのボードを変更する場合

デフォルトで `sync.yml` に登録されているプラットフォームのすべてのボード名と内部ID（Board ID）のリストは **[AVAILABLE_BOARDS.md](./AVAILABLE_BOARDS.md)** にまとめてあります。
有効化したいボードの内部IDを `.github/workflows/sync.yml` の `targets` に追記・変更するだけで、独自の最小限パッケージを構築できます。

### 新しいプラットフォームをまるごと追加する場合

もし全く別のサードパーティコア（例: `avr` や `stm32` など）を追加したい場合は、以下の手順で新しいリストを生成して設定します。

1. `.github/workflows/sync.yml` の `matrix` に新しい `platform` 名と公式の `json_url` を追加してリポジトリにプッシュします（この時点では `targets` は一旦空にしておきます）。
2. GitHub Actions (`Update Available Boards`) が自動的に走り、新しいコアのアーカイブを解析して `AVAILABLE_BOARDS.md` に新しいプラットフォームのID一覧を追記して自動コミットしてくれます。
   *(※ローカル環境で直接 `python scripts/update_board_list.py` を実行して確認することも可能です)*
3. 更新されたリストを見て必要な内部IDを把握し、`sync.yml` の `targets` にカンマ区切りで記入して再度プッシュしてください。

### 💡 全く加工せずに「まるごとミラーリング配信」したい場合

`sync.yml` の `targets` を完全に「空」にした状態でメインのワークフロー（Sync Custom Cores）を実行すると、ボードの削除（フィルタリング）処理は一切行われず、**オリジナルと全く同じ構成の無改造コアがそのままパッケージングされて配信されます**。

この機能を使えば、ボードを減らす用途だけでなく、「ダウンロードが遅い外部サーバーの野良パッケージを、高速なGitHub（ご自身のリポジトリ）に自動ミラーリングしてArduino IDEで利用する」といった使い方も可能です。

### 配信URLの決まり方（新しいプラットフォームの追加）

このシステムは、フォークした際や新しいコアを追加した際に、`.github/workflows/sync.yml` 内の `platform` の名前に基づいて配信用のJSONファイルを自動生成します。

Arduino IDEに設定する「追加のボードマネージャのURL」は、以下のルールで決まります。

```text
https://<あなたのGitHubユーザー名>.github.io/<リポジトリ名>/package_custom_<platform>_index.json
```

例えば、`sync.yml` の設定が以下のようになっている場合：
```yaml
          - platform: rp2040
            json_url: ...
```
生成されるURLは末尾が `package_custom_rp2040_index.json` となります。
もし設定ファイルに `platform: avr` のような新しい項目を追加してビルドした場合、自動的に `.../package_custom_avr_index.json` というURLが有効になり、全く新しい独自パッケージとしてArduino IDEに登録できるようになります。

### フォーク後の GitHub Actions 有効化と初期設定手順

リポジトリをフォークした直後は、セキュリティ保護のため自動実行が無効化されています。以下の手順で Actions を有効化し、設定を行ってください。

**1. Actionsの有効化と権限設定**
GitHubのブラウザ画面で、対象のリポジトリを開きます。
1. 上部のタブメニューから **[Settings]** をクリックします。
2. 左側のサイドバーを下へスクロールし、**[Actions]** > **[General]** をクリックします。
3. 「Actions permissions」 の項目で、**[Allow all actions and reusable workflows]** にチェックを入れます。
   （すぐ下にある [Save] ボタンをクリックします）

**2. ワークフローへの書き込み権限（Read and write）の付与**
リポジトリ自体の設定でもReleaseアップロード等のための書き込みが許可されている必要があります。
1. 先ほどと同じ **[Actions]** > **[General]** の画面をさらに下へスクロールします。
2. 「Workflow permissions」 という項目を見つけます。
3. デフォルトでは「Read repository contents and packages permissions」になっていることが多いので、これを上の **[Read and write permissions]** に変更します。
4. そのすぐ下にある [Save] ボタンをクリックして保存します。

**3. ワークフローの手動トリガー（動作確認）**
設定が完了し、作成したファイルをPush（またはフォーク）すると、上部タブの [Actions] にワークフローが表示されるようになります。
1. リポジトリ上部の **[Actions]** タブを開きます。
   （※初回アクセス時は「I understand my workflows, go ahead and enable them」という緑のボタンが出ることがあります。その場合はクリックしてください）
2. 左側のメニューからワークフロー名（**Sync Custom Cores**）をクリックします。
3. 画面右側の青い帯にある **[Run workflow]** ボタンをクリックし、緑色の [Run workflow] を押すと、即座にビルドとリリース作成のテストが開始されます。

**4. GitHub Pages の有効化（重要: 初回のみ手動設定が必要）**
Actionsが `gh-pages` ブランチを作成してJSONをプッシュしても、それだけでは自動的にURLは公開されません。初回のActions実行が終わった後に、一度だけ手動で設定をオンにする必要があります。
1. リポジトリの **[Settings]** > 左側メニューの **[Pages]** を開きます。
2. 「Build and deployment」 の Source を **[Deploy from a branch]** にします。
3. その下の Branch のプルダウンで **`gh-pages`** を選び、`/ (root)` のまま **[Save]** を押します。
4. 数分待つとURLが有効になり、Arduino IDEからアクセスできるようになります。
