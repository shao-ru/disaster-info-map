# Git・GitHub の手順（VS Code）

このプロジェクトに参加するための操作をまとめました。

- **1. 最初の準備**：最初に 1 回だけ
- **2. 変更を提案する（Pull Request）**：作業のたびに毎回

画面の名前は、VS Code の日本語表示の場合です（かっこ内は英語表示）。
うまくいかないときは、出たメッセージをそのまま Issue に書いてください。

---

## 1. 最初の準備（1 回だけ）

### 1.1 GitHub のアカウントを作り、管理者に伝える

1. https://github.com でアカウントを作る
2. **GitHub のユーザー名** を、リポジトリの管理者（先生）に伝える
3. 管理者がプロジェクトのメンバー（Collaborator）に招待します。メールか GitHub の通知に届く招待で
   **Accept invitation** を押す（または https://github.com/shao-ru/disaster-info-map/invitations を開く）

招待を受けないと、あとで push するときに「許可がない（Permission denied / 403）」と出ます。

### 1.2 Git と uv をインストールする

次のページを見て、自分の PC（Windows / Mac）に合った方法でインストールします。

| ソフト | 使い道 | インストールの説明 |
|---|---|---|
| Git | 変更の記録と GitHub とのやりとり | https://git-scm.com/downloads |
| uv | Python の実行環境（アプリを手元で動かす、データ処理） | https://docs.astral.sh/uv/getting-started/installation/ |

インストールが終わったら、**VS Code を一度閉じて開き直し**、ターミナル（メニューの「ターミナル」→「新しいターミナル」）で次を実行します。

```
git --version
uv --version
```

`git version 2.xx.x`、`uv 0.x.x` のようにバージョンが表示されれば OK です。
「コマンドが見つかりません」（not found / not recognized）と出たら、インストールできていないか、VS Code を開き直していません。

### 1.3 GitHub のメールアドレスを非公開にする

公開リポジトリでは、記録（コミット）に書いた名前とメールアドレスを誰でも見られます。
個人のメールアドレスを出さないように、GitHub が用意している匿名のアドレスを使います。

1. GitHub の右上のアイコン → **Settings** → 左のメニューの **Emails**
2. **Keep my email addresses private** にチェックを入れる
3. その下に表示される `12345678+ユーザー名@users.noreply.github.com` の形のアドレスをコピーしておく

### 1.4 プロジェクトを自分の PC にコピーする（clone）

1. VS Code で `Ctrl+Shift+P`（Mac は `Cmd+Shift+P`）→ 「**Git: クローン**（Git: Clone）」
2. 次の URL を貼り付けて Enter
   ```
   https://github.com/shao-ru/disaster-info-map.git
   ```
3. 保存する場所（例：`ドキュメント` の中）を選ぶ
4. 「クローンしたリポジトリを開きますか？」→ **開く**
5. 「このフォルダー内のファイルの作成者を信頼しますか？」と出たら → **はい、作成者を信頼します**
   （画面の上に「制限モード」と出ている場合は、そこをクリックして「信頼する」を選ぶ）

GitHub へのログインを求められたら、ブラウザーが開くので GitHub のアカウントでログインします。

### 1.5 Git に自分の名前とメールアドレスを設定する

VS Code の **ターミナル**（メニューの「ターミナル」→「新しいターミナル」）で、次を実行します。
プロジェクトのフォルダーで実行してください（`--global` を付けないので、このプロジェクトだけの設定になります）。

```
git config user.name "GitHubのユーザー名"
git config user.email "12345678+ユーザー名@users.noreply.github.com"
```

確認：次の 2 つで、設定した名前とアドレスが表示されれば OK です。

```
git config user.name
git config user.email
```

### 1.6 アプリが手元で動くか確かめる

ターミナルで次を実行し、ブラウザーで http://localhost:8000/web/ を開きます。地図が出れば OK です。

```
uv run ./code/serve.py
```

止めるときは、ターミナルで `Ctrl+C` を押します（Mac も `Ctrl+C`）。

---

## 2. 変更を提案する（作業のたびに）

`main`（みんなで使う本番のブランチ）には、直接 push できません。
**自分のブランチ** を作って作業し、**Pull Request（PR）** で「この変更を取り込んでください」と提案します。
管理者が確認して OK なら、`main` に取り込まれ（マージ）、公開中のアプリに反映されます。

```
main ──────────────────●（マージ）──→
   └─ feature/taro-xxx ─●─●─┘
        自分のブランチで作業 → PR → 管理者が確認
```

左のアクティビティーバーの **ソース管理**（Source Control、枝分かれのアイコン、`Ctrl+Shift+G`。Mac は `Cmd+Shift+G`）を使います。

### ① 最新の main を取ってくる（pull）

1. VS Code の左下（ステータスバー）に表示されているブランチ名をクリック → **main** を選ぶ
2. ソース管理の「…」メニュー → **プル**（Pull）

ほかの人の変更を取り込んだ、最新の状態から始めるためです。

### ② 新しいブランチを作る

1. 左下のブランチ名をクリック → **＋ 新しいブランチの作成…**（Create new branch...）
2. 名前を入力して Enter。名前は次の形にします
   ```
   feature/自分の名前-作業の内容
   例：feature/taro-region      feature/hanako-contributors
   ```
3. 左下の表示が新しいブランチ名に変わったことを確かめる

**1 つの作業（1 つの Issue）に 1 つのブランチ** を使います。

### ③ ファイルを直す

直したら、必ず動作を確かめます（アプリなら `uv run ./code/serve.py` で表示、課題なら `test.html`）。

### ④ 提出するファイルを選ぶ（ステージ）

1. ソース管理の「変更」に、直したファイルが並ぶ
2. ファイル名をクリックすると、どこを変えたかが見られる。**関係ないファイルが混ざっていないか** 確かめる
3. 提出するファイルの右の **＋**（変更をステージ / Stage Changes）を押す

### ⑤ 記録する（コミット）

1. 上の入力欄に、**何をしたか** を短く書く（日本語で OK）
   ```
   例：課題 1：getRegion を完成させた
   ```
2. **✓ コミット**（Commit）を押す

小さな区切りごとに、何回コミットしてもかまいません。

### ⑥ GitHub に送る（push）

- 新しいブランチの最初の 1 回は **ブランチの発行**（Publish Branch）を押す
- 2 回目からは **変更の同期**（Sync Changes）を押す

ターミナルで行う場合：`git push -u origin feature/taro-region`（2 回目からは `git push`）

### ⑦ Pull Request を作る（ブラウザー）

1. https://github.com/shao-ru/disaster-info-map を開く
2. 上に出る黄色い帯の **Compare & pull request** を押す
   （出ないときは「Pull requests」タブ → **New pull request** → compare に自分のブランチを選ぶ）
3. base が **main**、compare が **自分のブランチ** になっていることを確かめる
4. タイトルと説明を書いて **Create pull request**
   ```
   ## 何を変えたか
   課題 1 の getRegion() を完成させた

   ## どう確かめたか
   test.html の課題 1 がすべて ✅ になった。アプリで流山市・大阪市を選んで表示を確認した

   ## 関係する Issue
   #3
   ```

### ⑧ 管理者の確認を待つ

- **コメントが来たら**：同じブランチのまま直して、④〜⑥（ステージ → コミット → 同期）をもう一度。PR に自動で追加されます。新しい PR を作る必要はありません
- **マージされたら**：①に戻り、`main` に切り替えて **プル**。次の作業は、また新しいブランチを作って始めます

---

## 困ったとき

| メッセージ・状況 | 原因と対処 |
|---|---|
| `Please tell me who you are` / `Author identity unknown` | 1.5 の名前・メールアドレスの設定がまだ |
| `Permission denied` / `403` | 管理者からの招待を受けていない（1.1 の 3）、または GitHub にログインしていない |
| `protected branch` / main に push できない | main で作業している。②でブランチを作り、そちらで commit・push する |
| main で直してしまった（まだコミットしていない） | そのまま②で新しいブランチを作ればよい。直した内容はそのまま新しいブランチに移る |
| 変更が画面に出ない | `uv run ./code/serve.py` で開いているか確かめ、ブラウザーを再読み込み |
| `uv run` が何も表示せずに止まる | `Ctrl+C` で止め、次で起動する。PC の再起動で直ることもある<br>Windows：`.venv\Scripts\python code\serve.py`<br>Mac：`.venv/bin/python code/serve.py` |
| サーバーは動いているのに、ブラウザーに何も出ない | http://127.0.0.1:8000/web/ で開いてみる。別のブラウザー（Chrome など）でも試す |

わからないことは、Issue に「何をしたら、どんなメッセージが出たか」を書いて質問してください。
