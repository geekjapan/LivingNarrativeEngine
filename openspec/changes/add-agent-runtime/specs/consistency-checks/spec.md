## ADDED Requirements

### Requirement: Checker レジストリと finding 契約
Checker は D108 に従いレジストリ辞書へ名前キーで登録されなければならない(SHALL)。各 checker はターンの成果物(narration・resolved events・state diff 候補)を入力として受け取り、finding のリストを返さなければならない(SHALL)。各 finding は checker 名・severity(`info` | `warn` | `error`)・message・related ids(関連する character/event/fact 等の id リスト)を持たなければならない(SHALL)。

#### Scenario: checker がレジストリから解決される
- **WHEN** checker フレームワークが登録済み checker 名の一覧を実行する
- **THEN** レジストリに登録された各 checker が名前で解決され、実行される

#### Scenario: finding が必須フィールドを持つ
- **WHEN** いずれかの checker が1件の finding を返す
- **THEN** その finding は checker 名・severity・message・related ids を持つ

### Requirement: error 級 finding によるブロッキング
severity `error` を持つ finding が1件でも存在する場合、checker フレームワークはそのターンを auto-apply 可能な状態として扱ってはならず(SHALL NOT)、`stopped_for_review` を要求するブロッキングフラグを立てなければならない(SHALL)。stop 処理そのものの配線(session-autonomy への通知)は本 capability の対象外であり、本 capability はブロッキングフラグと finding 契約の提供までを責務とする。

#### Scenario: error 級 finding が auto-apply をブロックする
- **WHEN** いずれかの checker が severity `error` の finding を1件以上返す
- **THEN** checker フレームワークの実行結果はブロッキングフラグを真として返す

#### Scenario: info/warn のみでは auto-apply がブロックされない
- **WHEN** 全ての checker が severity `info` または `warn` の finding のみを返す(または finding がない)
- **THEN** checker フレームワークの実行結果のブロッキングフラグは偽である

### Requirement: Leak Checker — gm_vault fact id の機械的検出
Leak Checker は、narration 本文および reader 可視イベントのテキストに対し、`gm_vault.yaml` に定義された fact id が(文字列としてであれ引用としてであれ)出現していないかを機械的に検査しなければならない(SHALL)。出現が検出された場合、severity `error` の finding を生成しなければならない(SHALL)。

#### Scenario: gm_vault fact id の混入を検出する
- **WHEN** narration 本文に `gm_vault.yaml` 上の fact id がそのまま出現する
- **THEN** Leak Checker は severity `error` の finding を生成し、該当箇所の related ids に当該 fact id を含める

### Requirement: Leak Checker — hidden_facts / secrets の正規化部分文字列一致検出
Leak Checker は、narration 本文および reader 可視イベントのテキストに対し、現シーンの `hidden_facts`(id/text/visibility/known_by を持つ構造化型。D115)の各要素の `text` フィールド、および他キャラクターの `private_mind`/`secrets` テキストとの正規化(空白正規化・大文字小文字/全角半角統一等)後の部分文字列一致を検査しなければならない(SHALL)。一致が検出された場合、severity `error` の finding を生成しなければならない(SHALL)。この検査は完全一致・部分一致ベースの機械的検査であり、言い換え(パラフレーズ)による漏洩は検出できない制約を持つ(この制約は design.md に明記する)。

#### Scenario: hidden_facts テキストの直接混入を検出する
- **WHEN** narration 本文に現シーンの `hidden_facts` のいずれかの要素の `text` 値が正規化後に部分文字列として出現する
- **THEN** Leak Checker は severity `error` の finding を生成する

#### Scenario: 他キャラクターの secrets 混入を検出する
- **WHEN** reader 可視イベントのテキストに、シーン内の別キャラクターの `secrets` テキストが正規化後に部分文字列として出現する
- **THEN** Leak Checker は severity `error` の finding を生成する

#### Scenario: パラフレーズされた漏洩は機械的検査では検出されない
- **WHEN** narration 本文が hidden_facts の内容を言い換えて(同一文字列を含まない形で)表現している
- **THEN** 機械的検査のみでは finding は生成されない(この既知の限界を補うのが任意の LLM ベース評価である)

### Requirement: Leak Checker — 任意の LLM ベース漏洩評価
Leak Checker は、llm-provider を用いた LLM ベースの漏洩可能性評価をオプション機能として提供してよい(MAY)。有効/無効は checker 呼び出し時に受け取る真偽値パラメータとして切り替え可能でなければならない(SHALL)。この評価はヒューリスティックであることを明示し、既定の severity は `warn` としなければならない(SHALL)。この評価が無効化されている場合でも、機械的検査は常に実行されなければならない(SHALL)。具体的な `project.yaml` 側の設定キー名・既定 ON/OFF は本 capability の範囲外とする(design.md Open Questions 参照)。

#### Scenario: LLM ベース評価が warn 級として記録される
- **WHEN** LLM ベース漏洩評価が有効な状態で narration に疑わしい表現が検出される
- **THEN** 生成される finding の severity は既定で `warn` であり、ヒューリスティックである旨が message に示される

#### Scenario: LLM ベース評価が無効でも機械的検査は動作する
- **WHEN** LLM ベース漏洩評価が無効化されている
- **THEN** gm_vault fact id 検査および hidden_facts/secrets 部分文字列一致検査は通常どおり実行される

### Requirement: Continuity Checker — 構造データに基づく機械的矛盾検出
Continuity Checker は、resolved events / state diff 候補を canon および現在状態と突き合わせ、次の構造データ矛盾を機械的に検出しなければならない(SHALL): (a) 死亡または不在(current scene の `active_characters` に含まれない)キャラクターがシーン内で行動している、(b) `active_characters` に含まれないキャラクターが発言イベントを持つ、(c) `source_event` を持たない knowledge 追加。検出された矛盾は severity `error` の finding としなければならない(SHALL)。

#### Scenario: 不在キャラクターの行動を検出する
- **WHEN** あるキャラクターが現シーンの `active_characters` に含まれないにもかかわらず、そのシーンでの行動を表す resolved event を持つ
- **THEN** Continuity Checker は severity `error` の finding を生成する

#### Scenario: 非登場キャラクターの発言を検出する
- **WHEN** `active_characters` に含まれないキャラクターの発言(dialogue)イベントが存在する
- **THEN** Continuity Checker は severity `error` の finding を生成する

#### Scenario: source_event のない knowledge 追加を検出する
- **WHEN** state diff 候補に `source_event` を持たない knowledge 追加の変更が含まれる
- **THEN** Continuity Checker は severity `error` の finding を生成する

### Requirement: Continuity Checker — 任意の LLM ベース canon 矛盾検査
Continuity Checker は、llm-provider を用いた LLM ベースの canon 矛盾検査をオプション機能として提供してよい(MAY)。有効/無効は checker 呼び出し時に受け取る真偽値パラメータとして切り替え可能でなければならない(SHALL)。この検査の既定 severity は `warn` としなければならない(SHALL)。具体的な `project.yaml` 側の設定キー名・既定 ON/OFF は本 capability の範囲外とする(design.md Open Questions 参照)。

#### Scenario: LLM ベース canon 矛盾検査が warn 級として記録される
- **WHEN** LLM ベース canon 矛盾検査が有効な状態で narration が canon と矛盾する可能性を示す
- **THEN** 生成される finding の severity は既定で `warn` である

### Requirement: checks.yaml への findings 永続化
checker フレームワークは、そのターンで実行された全 checker の finding を、そのターンの turn artifact 内 `checks.yaml` に保存しなければならない(SHALL)。`checks.yaml` は少なくとも各 finding の checker 名・severity・message・related ids のリストを含まなければならない(SHALL)。

#### Scenario: 全 finding が checks.yaml に記録される
- **WHEN** あるターンで Leak Checker と Continuity Checker がそれぞれ finding を生成する
- **THEN** そのターンの `checks.yaml` に両方の checker の finding が記録される

#### Scenario: finding がない場合も checks.yaml は生成される
- **WHEN** あるターンで全 checker が finding を1件も生成しない
- **THEN** そのターンの `checks.yaml` は空の findings リストを持つ状態で生成される
