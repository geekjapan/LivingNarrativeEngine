## 1. RNG コア

- [ ] 1.1 `random_seed`(文字列)を SHA-256 で整数化し `random.Random` を初期化する関数を実装する
- [ ] 1.2 draw のたびに project 内通番(sequence)を進める仕組みを実装する
- [ ] 1.3 seed + 消費数から RNG 状態を再構築する関数(空撃ちによる復元)を実装する
- [ ] 1.4 同一 seed からの2回初期化で同一列が得られることを検証するテストを書く
- [ ] 1.5 seed + 消費数からの状態再構築が継続 draw と一致することを検証するテストを書く

## 2. ダイス記法パーサー

- [ ] 2.1 `NdM` `NdM+K` `NdM-K` をパースする関数を実装する(N≤100, M≤1000)
- [ ] 2.2 上限超過・不正記法に対する明確なパースエラーを実装する
- [ ] 2.3 パースしたダイスを RNG から draw して結果値(出目合計+修正値)を返す関数を実装する
- [ ] 2.4 正常系・上限超過・不正記法のテストを書く(pytest, mock provider 不要のためユニットテストで十分)

## 3. 確率判定

- [ ] 3.1 base_chance + named modifiers から final_chance を算出し [0,100] にクランプする関数を実装する
- [ ] 3.2 d100 draw と outcome(success/failure)判定を実装する
- [ ] 3.3 クランプ境界(合計>100, 合計<0)のテストを書く
- [ ] 3.4 同一入力での再現性(同一 seed・同一呼び出し順で同一結果)のテストを書く

## 4. Weighted event table

- [ ] 4.1 重み付きエントリからの選択(累積分布 + RNG float draw)を実装する
- [ ] 4.2 空エントリ・重み合計0のエラーハンドリングを実装する
- [ ] 4.3 大量試行での選択比率が重み比率に収束することを検証するテストを書く

## 5. Roll ログ永続化

- [ ] 5.1 project 全体で一意な `roll_NNNN` id 採番機構を実装する
- [ ] 5.2 roll レコード(type/dice or chance/modifiers/final/result/outcome/consequences)の Pydantic スキーマを定義する
- [ ] 5.3 ターン artifact `rolls.yaml` への追記(既存レコードを保持したまま append)を実装する
- [ ] 5.4 ターン meta.yaml への rng 消費数記録を実装する
- [ ] 5.5 rolls.yaml への書き込み・追記のテストを書く

## 6. Reroll / GM override

- [ ] 6.1 reroll API(新規 roll id + `supersedes` 参照)を実装する
- [ ] 6.2 GM override API(新規 roll id + `supersedes` 参照 + override フラグ)を実装する
- [ ] 6.3 元レコードが変更されないことを検証するテストを書く

## 7. 統合・回帰テスト

- [ ] 7.1 同一 seed・同一呼び出し列に対する全体再現性の回帰テストを書く(spec-foundation §7 準拠)
- [ ] 7.2 `docs/` に random-engine の使い方(seed 設定、ダイス記法、確率判定 API)を追記する
