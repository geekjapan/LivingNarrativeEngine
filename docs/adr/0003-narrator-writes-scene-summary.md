# ADR-0003: シーン現在状況の更新はナレーターが書く(追加LLM呼び出しなし)

- Status: accepted
- Date: 2026-07-06
- 関連: Issue 007(scene summary更新経路)、Issue 003/ADR-0002(LLMナレーター)、D107(state mutationは常にdiff経由)

## Context

Issue 006 解決後の実LLM 6ターンで、地の文の質は改善した一方、冒頭のシーン設定文(霧+規則正しい足音)が毎ターン逐語で再登場する現象が見つかった。原因は `SceneState` に「シーンの現在状況」を表す可変フィールドが無く、ナレーター文脈(`build_narrator_context`)が渡すのは開始時から不変の `reader_visible_facts` のみだったこと。ナレーターは毎ターン同じ静的素材から場面を再確立するしかなかった。

「現在状況の要約」をどのエージェントに書かせるかが論点になった。候補:

1. World Simulator に書かせる — ルールベース・テーブル駆動(`world_simulator.py`)であり、散文を書ける立場にない。
2. 専用の新しいLLM呼び出しを追加する — 1ターンあたりのLLM呼び出しが増える。
3. ナレーターに書かせる — ナレーターは既にLLM呼び出しを1回行っており、入力は reader 可視情報のみに制限されている。

## Decision

シーンの現在状況更新(`scene_summary_update`)は**ナレーターのLLM出力に追加フィールドとして持たせる**。新しいLLM呼び出しは追加しない。State Managerがこの出力を `StateDiff`(target=scene, path="summary", op=set, visibility=scene)に変換し、Commit相で他の変更と同様に適用する(D107: state mutationは常にdiff経由、例外なし)。

根拠:

- **追加コストゼロ**: Narrate相はBuildDiff相より前にあるため、既存のパイプライン順で自然に配線できる。ナレーターの1回のLLM呼び出しに出力フィールドを足すだけで済む。
- **構造的にleak-safe**: ナレーターの入力は reader_state_facts / scene_reader_visible_facts / reader_visible_events(+ 今回追加した scene_summary)のみで、`gm_vault` や `hidden_facts` を一切見ない。したがって生成される `scene_summary_update` は設計上 `gm_only`/隠された真相を含みようがない。追加の leak チェックロジックは不要。
- **Worldシミュレータの責務を侵さない**: ルールベースの状態遷移(scene status等)は引き続き `_changes_for_event` 側が担当。散文の要約はナレーターの領分。

State Managerでの反映:

- `build_state_diff` に `scene_summary_update: str | None = None` を追加。値がある場合のみ、現在アクティブなシーン(既存の `_active_scene_id` ヘルパーで解決)へ `set` diff(visibility=scene)を1件追加する。
- テンプレートフォールバック(非LLMの機械連結レンダラー)は更新を出力しない(`None` のまま)。フォールバック時に現在状況が更新されないのは許容(ADR-0002と同じ精神: 派生ビューの劣化はターンを止めない)。

## Consequences

- 次ターンのナレーター文脈・キャラクター文脈の両方が `scene.summary` を読めるようになり、「前ターンの状況の続きから語る」プロンプト指示が成立する。
- `SceneState.summary` はデフォルト `""` の追加フィールドなので、既存YAML/テンプレート/テストは無変更で読み込める。
- ナレーターのLLM出力スキーマが1フィールド増えるため、構造化出力検証の対象が広がる(`StructuredOutputError` リトライ枯渇時はADR-0002どおり機械連結へフォールバックし、summary更新も見送られる)。
- 将来、シーンをまたぐ複数アクティブシーンの要約管理が必要になった場合は、この仕組み(単一アクティブシーンの `summary` 1件)を拡張する必要がある(現時点ではmist_stationも含めアクティブシーンは常に1つの前提)。
