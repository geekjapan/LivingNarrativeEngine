## ADDED Requirements

### Requirement: Character Agent コンテキストのスコープ限定
Context Builder は、Character Agent 用コンテキストを構築する際、spec-foundation §4.3(1) に定める不変条件を満たさなければならない(SHALL)。すなわち、対象キャラクター本人の state・knowledge・本人が参加する scene の可視情報(`reader_visible_facts` および `hidden_facts` のうち visibility/known_by 上本人が見てよいもののみ。`hidden_facts` は id/text/visibility/known_by を持つ構造化型である。D115)・本人宛 directive のみを含み、他キャラクターの `private_mind`、`gm_vault`、本人が `hidden_from` または未知である event・fact は一切含めてはならない(SHALL NOT)。この不変条件は `WorldStateBundle` を入力とする純粋関数として実装され、LLM 呼び出しなしに単体テスト可能でなければならない(SHALL)。

#### Scenario: 他者の private_mind が含まれない
- **WHEN** シーンに char_001 と char_002 が参加しており、char_002 の `private_mind` に秘密が設定されている状態で char_001 用コンテキストを構築する
- **THEN** 構築されたコンテキストに char_002 の `private_mind` の内容が一切含まれない

#### Scenario: hidden_from 指定のイベントが除外される
- **WHEN** あるイベントが `hidden_from: [char_001]` を持つ状態で char_001 用コンテキストを構築する
- **THEN** 構築されたコンテキストに当該イベントが含まれない

#### Scenario: gm_vault の内容が含まれない
- **WHEN** `gm_vault.yaml` に隠された真実が存在する状態で任意のキャラクター用コンテキストを構築する
- **THEN** 構築されたコンテキストに gm_vault の内容が一切含まれない

#### Scenario: 本人の可視情報は正しく含まれる
- **WHEN** char_001 が参加するシーンの `reader_visible_facts` および char_001 の `knowledge.knows` に事実が存在する状態で char_001 用コンテキストを構築する
- **THEN** 構築されたコンテキストにそれらの事実が含まれる

### Requirement: World Simulator / State Manager の全状態参照と出力タグ付け
Context Builder は、World Simulator および State Manager に対しては全状態を参照可能なコンテキストを構築してよい(MAY)。ただし spec-foundation §4.3(3) に基づき、これらのコンポーネントが生成する出力(イベント候補・state diff 候補)は、各項目に `visibility` を必ず付与しなければならない(SHALL)。`visibility` が付与されていない出力は不正な出力として扱われ、そのまま後続フェーズへ渡してはならない(SHALL NOT)。

#### Scenario: World Simulator 出力に visibility が付与される
- **WHEN** World Simulator が背景イベント候補を1件生成する
- **THEN** 生成された候補は `visibility` フィールドを持つ

#### Scenario: visibility 欠落の出力は拒否される
- **WHEN** World Simulator または State Manager の出力候補に `visibility` が欠落している
- **THEN** その候補は妥当な出力として受理されず、検証エラーとして扱われる

### Requirement: コンテキストサイズの直近 N 件切り詰め
Context Builder は、コンテキストに含めるイベント履歴を、直近 N 件(既定値 20。Context Builder 関数の引数として呼び出し側から上書き可能とする。`project.yaml` にはこの設定キーを追加しない — プロジェクト単位の設定化は project-workspace スキーマの変更を伴うため将来 change の対象)+ 現在シーン + 関連関係性(対象キャラクターと `relationships.yaml` 上に有向ペアが存在する相手)に単純な切り詰めルールで制限しなければならない(SHALL)。要約(memory summary)による圧縮は行わない(Phase 5 の対象外)。

#### Scenario: イベント数が N を超える場合に切り詰められる
- **WHEN** 対象キャラクターの可視イベント数が設定された N を超える
- **THEN** 構築されたコンテキストには直近 N 件のイベントのみが含まれ、それより古いイベントは含まれない

#### Scenario: 関連関係性が含まれる
- **WHEN** 対象キャラクターが `relationships.yaml` 上で他のキャラクターと有向ペア関係を持つ
- **THEN** 構築されたコンテキストにその関係性データ(trust/affection/tension/suspicion)が含まれる

### Requirement: Character Agent の出力スキーマ
Character Agent は、スコープ済みコンテキストを入力とし、構造化出力として行動候補のリストを生成しなければならない(SHALL)。各行動候補は種別(`action` | `dialogue` | `inner_reaction`)、内容、`visibility`、任意の対象参照(`target_id`。Conflict Resolver が同一対象への衝突を検出するための character/scene/faction 等の id。対象を持たない行動では省略可)を持たなければならない(SHALL)。加えて、感情変化候補(emotion delta candidates)と目標更新候補(goal update candidates)を、それぞれ `visibility` 付きで出力しなければならない(SHALL)。すべての出力は Pydantic スキーマに準拠した構造化出力として llm-provider 経由で検証されなければならない(SHALL)。

#### Scenario: 行動候補が visibility 付きで出力される
- **WHEN** Character Agent が1つの行動候補を生成する
- **THEN** その候補は種別(action/dialogue/inner_reaction)・内容・`visibility` を持つ

#### Scenario: 感情変化候補と目標更新候補が出力される
- **WHEN** Character Agent がターンを実行する
- **THEN** 出力に感情変化候補のリストと目標更新候補のリストが含まれ、各要素は `visibility` を持つ

#### Scenario: スキーマ不一致出力は受理されない
- **WHEN** Character Agent の LLM 出力が定義済み Pydantic スキーマに準拠しない
- **THEN** llm-provider の構造化出力検証によりリトライまたはエラーとして扱われ、未検証の出力は Character Agent の結果として確定しない

### Requirement: agent の LLM 呼び出し binding key
各 agent コンポーネントが llm-provider を呼び出す際は、spec-foundation D122 の binding key を用いてプロファイルを解決しなければならない(SHALL): Character Agent は対象キャラクター自身の `character:<char_id>` を、World Simulator は `world_simulator` を、Conflict Resolver は `conflict_resolver` を、State Manager は `state_manager` を用いる。

#### Scenario: 異なるプロファイルに binding された2キャラクターが同一ターン内で異なる model を使う
- **WHEN** char_001 の binding key `character:char_001` が `llm_profiles["large_model"]` に、char_002 は binding が無く既定 `llm` に、それぞれ解決される状態で同一ターン内の Character Agent 実行を行う
- **THEN** char_001 の呼び出しメタデータには `large_model` プロファイルに対応する model 名が、char_002 の呼び出しメタデータには既定 `llm` の model 名が記録され、両者は異なる

### Requirement: World Simulator の出力
World Simulator は、時間経過・世界パラメータドリフト候補・勢力行動候補・背景イベント候補を生成しなければならない(SHALL)。背景イベント候補の生成には random-engine の weighted table 機能を使用しなければならない(SHALL)。生成される全ての候補は確定済みの状態変更ではなく「候補」として扱われ、`visibility` と任意の対象参照(`target_id`。Character Agent の行動候補と同一対象を指す場合、Conflict Resolver の衝突検出に用いる)を持たなければならない(SHALL)。

#### Scenario: weighted table から背景イベントが選択される
- **WHEN** World Simulator が背景イベントテーブルから1件選択する
- **THEN** random-engine の weighted table 選択機能が呼び出され、選択されたイベント候補が rolls.yaml に記録される roll と対応付けられる

#### Scenario: 世界パラメータドリフト候補が生成される
- **WHEN** World Simulator が1ターン分の処理を実行する
- **THEN** 出力に世界パラメータ(例: `danger_level`)へのドリフト候補が `visibility` 付きで含まれうる

### Requirement: Conflict Resolver の衝突検出と判定要求
Conflict Resolver は、Character Agent の行動候補と World Simulator のイベント候補をマージし、同一 `target_id` を持つ複数候補または結果が排他的な候補の組を衝突として検出しなければならない(SHALL)。検出された衝突は例外なく contested(争われている)として扱い、Conflict Resolver は random-engine に判定(roll)を要求しなければならない(SHALL、D121)。判定は、1件の衝突に属する候補を順序付けポリシー(design.md D4)で並べた上で、隣接する候補ペアごとに確率判定(chance、RNG 消費 1 draw)をちょうど1回要求する方式でなければならず(SHALL、候補 n 件の衝突は n−1 回の判定で解決し、success なら順序が先の候補が優越する)、衝突解決による RNG 消費数・`rolls.yaml` のレコード数が実装によって変動してはならない(MUST NOT、spec-foundation §7 の再現性契約)。roll なしに機械的に解決する決定的除外ルールは本 capability の範囲外とする(将来拡張の対象)。

#### Scenario: 同一対象への複数行動が衝突として検出される
- **WHEN** 2人のキャラクターが同一シーン内の同一 `target_id` に対して排他的な行動候補を提出する
- **THEN** Conflict Resolver はこれを衝突として検出し、単純なマージでは解決しない

#### Scenario: 検出された衝突は例外なく roll で解決される
- **WHEN** Conflict Resolver が衝突を検出する
- **THEN** Conflict Resolver は例外なく random-engine に判定を要求し、その roll 結果が rolls.yaml に記録される

#### Scenario: 衝突解決の RNG 消費数は候補数から決定的に定まる
- **WHEN** 候補2件からなる衝突が1件、候補3件からなる衝突が1件検出されたターンを解決する
- **THEN** 衝突解決のために要求される確率判定はちょうど3回(1 + 2)であり、`rolls.yaml` に3件の chance roll が記録される

### Requirement: Conflict Resolver による resolved event の生成
Conflict Resolver は、衝突解決の結果として、順序付けられた resolved event 列を state-model の Event 形式で生成しなければならない(SHALL)。各 resolved event は、それを生じさせた行動候補またはイベント候補を追跡可能な形で参照しなければならない(SHALL)。roll によって解決された resolved event は、判定に用いた roll id を `roll_ids`(state-model の Event フィールド)に記録しなければならない(SHALL、D121)。

#### Scenario: resolved event が Event スキーマに準拠する
- **WHEN** Conflict Resolver がターンの衝突解決を完了する
- **THEN** 出力される resolved event 列の各要素は state-model の Event スキーマ(id/turn/type/visibility 等)に準拠する

#### Scenario: resolved event は元候補を追跡できる
- **WHEN** ある resolved event がキャラクター行動候補から生成される
- **THEN** その resolved event から元の行動候補を特定できる情報が保持される

#### Scenario: roll で解決された event に roll_ids が記録される
- **WHEN** ある衝突が roll によって解決され、その結果が resolved event として生成される
- **THEN** 生成された resolved event の `roll_ids` に当該判定の roll id が含まれる

### Requirement: State Manager の state diff 候補生成と検証
State Manager は turn-pipeline の BuildDiff スロットの実装として登録されなければならない(SHALL、D113)。State Manager は、resolved event 列 + 当該ターンの intervention 群(`intervention.yaml` に確定した Intervention のリスト。無介入時は空リスト)+ 全状態を入力として state diff 候補を state-model の StateDiff 形式で生成しなければならない(SHALL)。生成された各 diff 変更は、生成時点で現在状態に対して検証されなければならない(SHALL)。`source_event` を持たない state diff の変更は、生成時点で拒否されなければならない(SHALL)。当該ターンで確定した `reveal_control`(must-not-reveal)により reader 可視への昇格が禁じられている事実を `target: reader_state` へ昇格させる変更候補は、state diff 候補に含めてはならない(SHALL NOT)。State Manager の出力は、採用された state diff 候補に加え、拒否された変更候補とその理由を保持する `rejected_changes` リストを持たなければならない(SHALL)。

#### Scenario: resolved event から state diff が生成される
- **WHEN** State Manager が resolved event 列を処理する
- **THEN** 各 event に対応する `source_event` を持つ state diff 変更が生成される

#### Scenario: source_event を持たない変更は拒否される
- **WHEN** State Manager が生成しようとした変更候補に対応する resolved event が存在しない
- **THEN** その変更候補は state diff に含めず、生成時点で拒否する

#### Scenario: 現在状態との検証に失敗した変更は拒否される
- **WHEN** 生成された変更候補が現在状態のスキーマまたは制約(例: 存在しない character id への参照)と矛盾する
- **THEN** その変更候補は state diff に含めず、拒否理由とともに記録する

#### Scenario: must-not-reveal な事実の reader_state 昇格が除外される
- **WHEN** ある事実が当該ターンの `reveal_control`(must-not-reveal)によりマークされており、その事実を reader_state へ昇格する変更候補が生成されようとする
- **THEN** State Manager はその変更候補を state diff に含めず、`rejected_changes` に理由とともに記録する

### Requirement: agent I/O のターン artifact への記録
Context Builder / Character Agent / World Simulator / Conflict Resolver / State Manager の全ての入出力は、そのターンの turn artifact 内 `agent_io/` 配下に記録されなければならない(SHALL)。記録には、少なくとも各コンポーネントの入力コンテキスト(または要約)と生成された出力候補が含まれなければならない(SHALL)。

#### Scenario: 各コンポーネントの入出力が agent_io に保存される
- **WHEN** あるターンで Character Agent と World Simulator が実行される
- **THEN** そのターンの `agent_io/` 配下に、それぞれの入力コンテキストと出力候補を含むファイルが保存される

#### Scenario: 失敗時も部分 artifact が保存される
- **WHEN** あるターンの途中で agent 実行が失敗し停止する
- **THEN** それまでに完了したコンポーネントの入出力は `agent_io/` に保存され、失われない
