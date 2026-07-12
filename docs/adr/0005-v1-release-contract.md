# ADR-0005: 1.0リリース契約(persona・配布経路・判定原則・gate構造)

## Context

Issue 001〜051完了時点で機能は豊富だが、`project_plan` §26のα/β/1.0定義は定性的
(「日常利用可能」「一通り安定」)で検証不能であり、E9完了と1.0完成が混同されていた。
次の作業を選ぶには、誰の何の体験を保証し、何を満たしたら出荷可能かを先に固定する
必要がある。Issue 053のassisted grillingで決定した(決定台帳D1〜D4)。

## Decision

### D1: primary personaと代表ジャーニー

- primary persona: 自分のPCへ導入しWeb UIで一人遊びする物語シミュレーション愛好者
  (uv/dockerを扱える技術中級者、GM兼観測者として介入)。
- 代表ジャーニー: install → `living-narrative init` → `serve` → Web UIで観測+介入を
  複数turn → `export`で小説原案化。
- 開発者CLI体験・非技術者向け配布・PyPI publish・GUIインストーラはnon-gating
  (post-1.0候補)。

### D2: 正式対応経路とmigration互換保証

- install: ①`git clone` + `uv sync --extra web` ②`docker compose up`の2経路。
- 起動: `living-narrative init` + `serve`(Web UI)。
- upgrade: `git pull` + `uv sync`(または`docker compose pull/build`)+ 既存projectの
  schema_version自動migration(Issue 044)。
- migration互換保証の起点はβschema。βschema以降のprojectは1.0まで自動migrationを
  保証し、α以前はbest-effort(保証外)とする。

### D3: must / should / post-1.0 判定原則

- **must(1.0 gating)** — いずれか該当:
  - (i) 欠落でD1ジャーニー正常系が完走不能。
  - (ii) データ損失・replay再現性破壊・disclosure漏洩(`gm_vault`等)・
    plugin trust boundary侵害を招く。
  - (iii) 後から変更するとD2のmigration保証か公開契約(schema・CLI引数・export形式)を
    破るhard-to-reverse事項。
- **should**: ジャーニー品質を上げるが手動回避策があり、互換を破らず後付け可能。
  1.0に入らなければ1.1.0(additive minor)へ。
- **post-1.0**: persona(b)(c)向け機能、派生レイヤ(TRPG深掘り・画像化・TTS)、
  plugin sandbox/network隔離、PyPI publish。
- patch(1.0.x)は互換を保つ修正のみ。
- 安全性・永続互換性のmust未達は、回避策の有無にかかわらず出荷阻止条件とする。

### D4: α/β/1.0 gate構造

- **α(遡及認定)**: 全test green + mock providerでD1ジャーニーのE2E自動走行
  (init→serve→介入込み複数turn→export)がCIでpass。自動検証のみ。
- **β**: α + D2の2経路clean install smoke(CI) + βschema凍結宣言(D2保証起点の発効)
  + 実LLMでのジャーニー人手smoke 1回合格(合否基準はIssue 057 rubricの簡易版を流用)。
- **1.0**: β + D3のmust全充足 + βschema→1.0 migration regression test pass
  + Issue 057の実LLM品質gate pass + Issue 058のUX受入pass
  + Issue 059のrelease checklist完了 + version 1.0.0。
- 委譲境界: 057=品質rubric/SLO閾値、058=UX受入項目表、059=release手順と
  βschema凍結の宣言形式。
- 定義: **1.0 = must全充足 ∧ 全gate green**。

## Consequences

- mock provider journey E2E test(CI常設)が唯一の新規実装mustとして確定する
  (Issue 063)。
- `project_plan` §26.2〜26.4の定性定義は本ADRのgate定義で置換される。
- 「1.0はいつか」は「must残数とgate状態」という機械的な問いになる。
- 実LLM品質・UX・release checklistのいずれか1つでも未達なら1.0は出荷できない。
- βschema凍結後のschema変更はすべてmigration対象となり、β以降のprojectを1.0まで
  移行可能に保つ継続的なテスト・保守義務が生じる。
