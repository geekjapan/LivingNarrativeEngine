## Context

Random Engine は、後続の全ての「不確実性を伴う判定」(ダイス、確率判定、weighted table)が経由する共通基盤である。spec-foundation §7 により、seed + 介入列が同じであれば完全再現できることが回帰テストの前提となっている。本 change はこの契約を満たす最小実装を確立する。

## Goals

- 文字列 `random_seed` から決定的な乱数列を得る。
- 任意の消費数から RNG 状態を再構築でき、resume 後も乱数列が破綻しない。
- ダイス・確率判定・weighted table を薄い共通インターフェースの上に実装する。
- 全 roll を `rolls.yaml` に追記し、reroll/override は履歴を破壊しない。

## Non-Goals

- 乱数アルゴリズム自体の暗号学的品質(本用途は非暗号用途であり Python 標準の `random.Random`(Mersenne Twister)で十分)。
- 複数プロセス・複数スレッドからの並行 draw の同期(第1バッチは単一プロセス・単一ターン逐次実行が前提。turn-pipeline 側の制約に従う)。
- weighted table の condition 評価(呼び出し側の責務、proposal.md の Non-Goals 参照)。

## Decisions

### D1: Seed ハッシュ方式 — 文字列 seed を SHA-256 で整数化する

`random_seed` は人間が読みやすい文字列(例: `20260703-mist-city`)として `project.yaml` に保持される(企画書 §14.1)。これを `random.Random` の内部シードとして使うには整数化が必要。

- 決定: `int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)` を `random.Random` のシードに渡す。
- 理由: Python バージョン・プラットフォームに依存せず安定。標準 `hash()` は組み込みのソルト化(`PYTHONHASHSEED`)により実行ごとに変わるため使用不可。
- 代替案: `zlib.crc32` — 衝突耐性が低く、異なる seed 文字列が同じ整数シードに落ちるリスクがあり不採用。

### D2: 単一 project-level RNG ストリーム(サブシステム別ストリームは第1バッチでは作らない)

- 決定: project 全体で単一の RNG ストリームを持ち、全ての draw(ダイス・確率判定・table 選択)がこの1本のシーケンスを消費する。roll ログの id(`roll_NNNN`)は、この RNG draw 消費数とは独立した、project 全体で単調増加する別カウンタから採番する(詳細は D4)。
- 理由: 第1バッチの実行モデルはターン内で逐次的(spec-foundation §6 の 8 フェーズは順序実行)であり、呼び出し順序が決定的であれば単一ストリームで完全な再現性を得られる。サブシステムごとに独立したストリームを持つと、どのサブシステムが何回 draw したかを resume 時に個別追跡する必要が生じ、状態が複雑化する。
- 代替案(将来検討): サブシステム別(例: World Simulator 用・Character Agent 用)に独立ストリームを分離する設計。並列実行や、あるサブシステムだけをスキップ/再実行したい場合に有利だが、第1バッチでは並列実行も部分再実行も要件にないため YAGNI。将来必要になった時点で `add-random-engine` の後続 change として提案する。

### D3: RNG 状態は「seed + 消費数」のみから再構築する(内部状態の直接シリアライズはしない)

- 決定: `random.Random` オブジェクトの内部状態(`getstate()`)を保存・復元するのではなく、`random_seed` から新規初期化した RNG に対して「これまでの消費数と同じ回数だけ draw を空撃ちして進める」ことで状態を再構築する。
- 理由: `getstate()` のバイナリ形式は Python バージョン間の互換性が保証されない。消費数(単純な整数)を turn meta に記録する方式は human-readable で、spec-foundation の「artifact は YAML で人間可読」という方針(D103)とも整合する。
- トレードオフ: 消費数が非常に大きい場合、空撃ちによる再構築コストが線形に増える。第1バッチのターン数規模(数十〜百ターン程度、1ターンあたり数回〜数十回の draw)では無視できるコストであり、許容する。

### D4: roll id(roll_NNNN)と RNG draw 消費数は別カウンタとする

- 決定: `roll_NNNN` の採番に使う通番(roll id カウンタ)と、RNG 状態再構築に使う「消費数」(RNG draw カウンタ)を別々に管理する。roll id カウンタは roll レコードが1件生成されるたびに1つずつ単調増加し、巻き戻されることはない。RNG draw カウンタは `random.Random` から実際に値を draw した回数であり、resume や add-session-autonomy の `--replay-same-seed` 巻き戻しによって過去の値まで戻ることがある。
- 理由: (a) `NdM` 記法の1 roll はダイス N 個ぶん、複数回の RNG draw を消費しうる(D5)。roll id が draw 消費数と1対1であれば、この対応が崩れる。(b) `--replay-same-seed` は RNG 消費数を巻き戻して同じ乱数列を再現するが、roll id は project 全体で重複してはならない(本 spec「Roll ログの永続化」要件)。両者を同一カウンタにすると、巻き戻し後の再実行で roll id が衝突する。(c) GM override は RNG を一切消費しないが、新しい roll id は必要とする。
- 代替案: roll id = RNG 消費数(単一カウンタ)。実装は単純だが上記 (a)〜(c) のいずれとも両立しないため不採用。

### D5: ロール種別ごとの RNG draw 消費数を固定する

- 決定: 1 draw = `random.Random` への1回の呼び出し(例: `randint` や `random()`)と定義し、ロール種別ごとの消費数を次のように固定する: ダイス roll(`NdM`)は N 回(ダイス1個につき1 draw)、確率判定は1回(d100 draw)、weighted table 選択は1回(D3 のリスク緩和策と同じ規約)、reroll は再実行する元ロールと同じ種別・同じ消費数、GM override は0回(RNG を呼び出さない)。
- 理由: 消費数がロール種別・実装ごとに揺れると、resume 後の状態再構築(D3)が同一結果を生成できなくなる。特にダイス個数 N が可変な `NdM` は、実装によって「N回に分けて draw」と「1回の draw から合成」の両方があり得るため、明文化しておかないと reproducibility(spec-foundation §7)が壊れる。
- トレードオフ: `100d6` は100回の draw を消費する。第1バッチのターン規模(D3 参照)では許容範囲。

### D6: ダイス roll は省略可能な target 比較をサポートする

- 決定: ダイス roll API は省略可能な `target`(整数の閾値)引数を受け取れるようにし、指定された場合は「結果値 ≥ target」で outcome(success/failure)を算出し、roll レコードに `target` と `outcome` を含める。`target` を省略した場合、roll レコードに `outcome` は含まれない。
- 理由: 企画書 §14.9 のロール例(`type: detection_check`, `dice: 2d6`, `target: 7`, `outcome: failure`)、`add-intervention` の `dice_roll_request`(例:「2d6で7以上なら気づく」)、`add-agent-runtime` の Conflict Resolver(contested な結果への roll 要求)は、いずれも「ダイスを振って target と比較し outcome を得る」形を前提にしている。この比較を呼び出し側ごとに個別実装させると、`outcome` の意味(以上か超過か等)がバラつくリスクがある。target 比較を Random Engine 側に持たせ、確率判定と同じ「roll → outcome」契約に統一する。
- 代替案: target 比較を持たず、常に呼び出し側が dice 結果値を見て outcome を判定する。proposal.md の Non-Goal(「上位ロジックは対象外」)はモディファイア/重みを誰が決めるかを指しており、roll 値と target の大小比較という算術操作までは含まない、と解釈し不採用とした。

### D123: roll レコードの severity は呼び出し側指定のパススルーフィールド

roll レコードに任意フィールド `severity`(`normal`/`critical`、既定 `normal`)を追加するが、Random Engine はこの値を結果から自動判定せず、Conflict Resolver 等の呼び出し側が明示的に渡した値をそのまま保存する(spec-foundation §4.4 D123。判定ロジックは agent-runtime capability 側の設計判断)。

## Risks & Trade-offs

- [Risk] 空撃ちによる状態再構築は、将来セッションが非常に長期化した場合(数万 draw)に resume 時の遅延要因になりうる。→ Mitigation: 第1バッチのスコープ外。必要になれば `getstate()` ベースのチェックポイント方式を追加 change として提案する。
- [Risk] 単一ストリーム設計は、将来 World Simulator と Character Agent の draw を独立させたくなった場合に破壊的変更(既存セッションの乱数列が変わる)を伴う。→ Mitigation: D2 に代替案として明記済み。導入する場合は新規 project でのみ有効化するなど互換性戦略を別途検討する。
- [Risk] weighted table の重み比例選択アルゴリズム(累積分布 + 一様乱数)は draw 消費数が実装依存(1 draw か複数 draw か)になりうる。→ Mitigation: 「1回の table 選択 = RNG から 1 回の float draw」に固定する規約を実装で明文化し、reproducibility の対象とする。
- [Risk] roll id カウンタと RNG 消費数カウンタを分離したことで、「reroll は過去の消費数へ巻き戻して同じ乱数列を再度使う」という誤解が生じうる。→ Mitigation: reroll は常に現在の RNG ストリーム位置から新規 draw する(過去の消費数への巻き戻しは行わない)ことを spec.md に明記する。

## Open Questions

- なし(第1バッチ実装をブロックする未決事項はない)。
