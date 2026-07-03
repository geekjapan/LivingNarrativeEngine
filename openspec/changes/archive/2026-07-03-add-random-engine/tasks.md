## 1. RNG コア

- [x] 1.1 `random_seed`(文字列)を SHA-256 で整数化し `random.Random` を初期化する関数を実装する
- [x] 1.2 roll レコード生成のたびに project 内 roll id 通番(`roll_NNNN`)を1つ進める仕組みと、RNG draw 消費数(ロール種別ごとに固定: ダイス N 回 / 確率判定1回 / table 選択1回 / GM override 0回)を独立してカウントする仕組みを実装する
- [x] 1.3 seed + RNG draw 消費数から RNG 状態を再構築する関数(空撃ちによる復元)を実装する
- [x] 1.4 同一 seed からの2回初期化で同一列が得られることを検証するテストを書く
- [x] 1.5 seed + 消費数からの状態再構築が継続 draw と一致することを検証するテストを書く
- [x] 1.6 GM override 実行時に roll id は増加するが RNG 消費数は変化しないことを検証するテストを書く

## 2. ダイス記法パーサー

- [x] 2.1 `NdM` `NdM+K` `NdM-K` をパースする関数を実装する(N≤100, M≤1000)
- [x] 2.2 上限超過・不正記法に対する明確なパースエラーを実装する
- [x] 2.3 パースしたダイスを RNG から draw して結果値(出目合計+修正値)を返す関数を実装する。省略可能な target 引数を受け取り、指定時は outcome(success/failure、結果値≥target)も返せるようにする
- [x] 2.4 正常系・上限超過・不正記法のテストを書く(pytest, mock provider 不要のためユニットテストで十分)
- [x] 2.5 target 指定時の outcome 算出(結果値≥target で success)のテストを書く

## 3. 確率判定

- [x] 3.1 base_chance + named modifiers から final_chance を算出し [0,100] にクランプする関数を実装する
- [x] 3.2 d100 draw と outcome(success/failure)判定を実装する
- [x] 3.3 クランプ境界(合計>100, 合計<0)のテストを書く
- [x] 3.4 同一入力での再現性(同一 seed・同一呼び出し順で同一結果)のテストを書く

## 4. Weighted event table

- [x] 4.1 重み付きエントリからの選択(累積分布 + RNG float draw)を実装する
- [x] 4.2 空エントリ・重み合計0・個々の重みが負のエントリに対するエラーハンドリングを実装する
- [x] 4.3 大量試行での選択比率が重み比率に収束することを検証するテストを書く

## 5. Roll ログ永続化

- [x] 5.1 project 全体で一意な `roll_NNNN` id 採番機構を実装する(RNG draw 消費数カウンタとは別管理、1.2 参照)
- [x] 5.2 roll レコード(id/turn/type[dice|chance|table]/入力[dice記法+target可、または base_chance/modifiers/final_chance、または table 情報]/結果値/target指定時または確率判定のoutcome/呼び出し側が渡す任意のlabel・consequences/任意の `severity`: `normal`|`critical` 既定 `normal`、D123・呼び出し側指定をそのまま保存し Random Engine 側では判定しない)の Pydantic スキーマを定義する
- [x] 5.3 ターン artifact `rolls.yaml` への追記(既存レコードを保持したまま append)を実装する
- [x] 5.4 そのターンで消費した RNG draw 数を問い合わせ可能にする API を実装する(実際の `meta.yaml` への書き込みは add-turn-pipeline 側の責務)
- [x] 5.5 rolls.yaml への書き込み・追記のテストを書く
- [x] 5.6 呼び出し側が `severity: critical` を指定した roll がそのまま記録され、Random Engine が
      値を自動判定・上書きしないことを検証するテストを書く(D123)

## 6. Reroll / GM override

- [x] 6.1 reroll API(新規 roll id + `supersedes` 参照。元ロールと同じ種別・消費数で、現在の RNG ストリーム位置から新規 draw する)を実装する
- [x] 6.2 GM override API(新規 roll id + `supersedes` 参照 + override フラグ。RNG は消費しない)を実装する
- [x] 6.3 元レコードが変更されないこと、reroll が現在のストリーム位置から新規 draw すること、GM override が RNG を消費しないことを検証するテストを書く

## 7. 統合・回帰テスト

- [x] 7.1 同一 seed・同一呼び出し列に対する全体再現性の回帰テストを書く(spec-foundation §7 準拠)
- [x] 7.2 `docs/` に random-engine の使い方(seed 設定、ダイス記法、確率判定 API)を追記する
