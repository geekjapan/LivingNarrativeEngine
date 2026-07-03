## 1. Provider Protocol とレジストリ

- [ ] 1.1 `Provider` Protocol(`complete(messages, response_schema: type[BaseModel], **params) -> BaseModel`)を定義する
- [ ] 1.2 呼び出しメタデータ用の型(model 名・所要時間・token 使用量・prompt テンプレート名・prompt hash)を Pydantic モデルとして定義する
- [ ] 1.3 provider を名前キーで登録・解決するレジストリ辞書を実装する(D108: plugin loader は作らない)
- [ ] 1.4 未登録 provider 名指定時に起動時エラーを送出する処理を実装する

## 2. 構造化出力の検証・retry ラッパー

- [ ] 2.1 LLM 生応答から JSON を抽出するユーティリティを実装する(コードブロック混入・前後テキスト混入への耐性を含む)
- [ ] 2.2 抽出した JSON を `response_schema` で Pydantic 検証するラッパーを実装する
- [ ] 2.3 検証失敗時にバリデーションエラー内容を含む修正指示付きメッセージで再試行するロジックを実装する(最大2回)
- [ ] 2.4 retry 上限到達時に送出する型付き例外(`StructuredOutputError` 等: provider 名・model・schema 名・最終バリデーションエラーを保持)を実装する
- [ ] 2.5 例外メッセージに秘密情報(api_key)が含まれないことを保証する

## 3. Mock Provider

- [ ] 3.1 `response_schema` の Pydantic field 定義から plausible なデフォルト値を機械的に構築する generator を実装する
- [ ] 3.2 `random_seed` に基づく決定的バリエーション付与ロジックを実装する
- [ ] 3.3 テスト fixture(schema 名 + prompt hash をキーとする scripted response)のロードと優先解決を実装する
- [ ] 3.4 mock provider を Provider Protocol・レジストリに接続する

## 4. OpenAI 互換 Provider

- [ ] 4.1 `openai` SDK クライアントを `base_url`・`api_key`(環境変数のみ)・timeout を設定可能にラップする
- [ ] 4.2 接続/タイムアウトエラーに対するバックオフ付き transient retry(最大2回)を実装する
- [ ] 4.3 retry 上限到達時に送出する型付き例外を実装し、例外メッセージから秘密情報を除去する
- [ ] 4.4 OpenAI 互換 provider を Provider Protocol・レジストリに接続する

## 5. メタデータ・prompt 記録

- [ ] 5.1 各呼び出しの所要時間・model 名・token 使用量(取得可能な場合)・prompt テンプレート名・prompt hash を収集し呼び出し元へ返す実装を行う
- [ ] 5.2 prompt 全文保存(既定)/ hash-only 保存(設定フラグ)の切り替えを実装する
- [ ] 5.3 収集したメタデータを turn `meta.yaml` 形式(spec-foundation §6)に整形するヘルパーを実装する

## 6. テスト

- [ ] 6.1 構造化出力検証の成功パス(1回で成功)のテストを書く
- [ ] 6.2 構造化出力の retry パス(1回失敗→2回目成功)のテストを書く
- [ ] 6.3 retry 上限到達で型付き例外が送出されることのテストを書く
- [ ] 6.4 mock provider の決定性(同一 seed/schema/prompt hash → 同一出力)のテストを書く
- [ ] 6.5 mock provider の scripted response 優先解決のテストを書く
- [ ] 6.6 OpenAI 互換 provider の transient retry(モック HTTP エラーで検証)のテストを書く
- [ ] 6.7 ログ・例外メッセージ・artifact のいずれにも api_key が出現しないことを検証するテストを書く
- [ ] 6.8 全テストスイートがネットワークアクセスなし(mock provider のみ)で実行できることを smoke test で確認する

## 7. ドキュメント

- [ ] 7.1 `llm-provider` capability の使い方(provider 設定・mock 切り替え・OpenAI 互換 base_url 設定例)を README または docs に追記する
