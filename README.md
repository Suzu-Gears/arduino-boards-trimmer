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

### フォーク後の GitHub Actions 有効化と初期設定手順

リポジトリをフォークした直後は、セキュリティ保護のため自動実行が無効化されています。以下の手順で Actions を有効化し、Release作成の権限を付与してください。

**1. Actionsの有効化と権限設定**
GitHubのブラウザ画面で、対象のリポジトリを開きます。
1. 上部のタブメニューから **[Settings]** をクリックします。
2. 左側のサイドバーを下へスクロールし、**[Actions]** > **[General]** をクリックします。
3. 「Actions permissions」 の項目で、**[Allow all actions and reusable workflows]** にチェックを入れます。
   （すぐ下にある [Save] ボタンをクリックします）

**2. ワークフローへの書き込み権限（Read and write）の付与**
リポジトリ自体の設定でもReleaseアップロードのための書き込みが許可されている必要があります。
1. 先ほどと同じ **[Actions]** > **[General]** の画面をさらに下へスクロールします。
2. 「Workflow permissions」 という項目を見つけます。
3. デフォルトでは「Read repository contents and packages permissions」になっていることが多いので、これを上の **[Read and write permissions]** に変更します。
4. そのすぐ下にある [Save] ボタンをクリックして保存します。

**3. ワークフローの手動トリガー（動作確認）**
設定が完了し、作成したファイルをPush（またはフォーク）すると、上部タブの [Actions] にワークフローが表示されるようになります。

今回のワークフローには手動トリガーが設定されていますので、初回のテストは以下の手順で行えます。
1. リポジトリ上部の **[Actions]** タブを開きます。
   （※初回アクセス時は「I understand my workflows, go ahead and enable them」という緑のボタンが出ることがあります。その場合はクリックしてください）
2. 左側のメニューからワークフロー名（**Sync Custom Pico Core**）をクリックします。
3. 画面右側の青い帯にある **[Run workflow]** ボタンをクリックし、緑色の [Run workflow] を押すと、即座にビルドとリリース作成のテストが開始されます。
   しばらく待って処理が完了すると、自動的に最初のReleaseが作成され、JSONファイルが配信可能になります。
