# ことばクエスト (Kotoba Quest)

小学1年生向けの楽しい国語学習アプリケーションです。AIが生成する問題で楽しく言葉を学べます。

![ことばクエスト](https://img.shields.io/badge/Django-4.2.7-green)
![ことばクエスト](https://img.shields.io/badge/Python-3.8+-blue)
![ことばクエスト](https://img.shields.io/badge/OpenAI-API-orange)

## 🌟 特徴

- **AI生成問題**: OpenAI APIを使用した高品質な問題自動生成
- **小学1年生向け**: ひらがな・カタカナ中心の年齢に適した内容
- **ゲーミフィケーション**: ポイント制・ランクシステムで学習意欲向上
- **学習履歴**: 詳細な学習記録と統計情報の表示
- **レスポンシブデザイン**: スマートフォン・タブレット対応

## 🎯 問題の種類

- 動物の鳴き声・特徴
- 色の名前・混色
- 反対語（対義語）
- 擬音語・擬態語
- 日常のあいさつ・マナー
- 身近な物の名前
- 基本的な助詞の使い方

## 🛠 技術スタック

- **バックエンド**: Django 4.2.7
- **フロントエンド**: HTML5, CSS3, JavaScript, Bootstrap 5
- **データベース**: SQLite (開発環境)
- **AI**: OpenAI GPT-4o-mini
- **認証**: Django Auth
- **スタイリング**: カスタムCSS + Bootstrap

## 📋 セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/kotoba-quest.git
cd kotoba-quest
```

### 2. 仮想環境の作成と有効化

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集して以下を設定
SECRET_KEY=your-secret-key-here
DEBUG=True
OPENAI_API_KEY=your-openai-api-key-here
```

#### OpenAI APIキーの取得方法

1. [OpenAI Platform](https://platform.openai.com/)にアクセス
2. アカウントを作成またはログイン
3. API keysページでAPIキーを生成
4. 生成されたキーを`.env`ファイルの`OPENAI_API_KEY`に設定

### 5. データベースのマイグレーション

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. スーパーユーザーの作成（任意）

```bash
python manage.py createsuperuser
```

### 7. サーバーの起動

```bash
python manage.py runserver
```

ブラウザで `http://localhost:8000` にアクセスしてアプリケーションを使用できます。

## 🎮 使用方法

### 基本的な流れ

1. **アカウント登録**: 新規ユーザー登録またはログイン
2. **クイズ開始**: 「クイズを始める」ボタンをクリック
3. **問題回答**: 10問の3択問題に回答
4. **結果確認**: スコアとランクアップをチェック
5. **履歴確認**: 学習履歴で成長を確認

### ランクシステム

- **ノーマル**: 0-99pt
- **コモン**: 100-299pt
- **レア**: 300-699pt
- **エピック**: 700-1499pt
- **レジェンダリー**: 1500pt以上

## 🏗 プロジェクト構造

```
kotoba-quest/
├── kotoba_quest_project/     # Django設定
├── accounts/                 # ユーザー管理アプリ
├── quiz/                     # クイズ機能アプリ
├── templates/               # HTMLテンプレート
├── static/                  # 静的ファイル
├── requirements.txt         # 依存関係
├── manage.py               # Django管理コマンド
└── README.md               # このファイル
```

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙏 謝辞

- OpenAI APIによる問題生成機能
- Bootstrap による美しいUI
- Django コミュニティのサポート

## 📞 サポート

質問やサポートが必要な場合は、[Issues](https://github.com/yourusername/kotoba-quest/issues)ページで新しい課題を作成してください。 