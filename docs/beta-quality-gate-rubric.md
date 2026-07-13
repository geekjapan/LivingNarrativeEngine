# β/1.0 人手品質rubric運用手順

## 目的と適用範囲

この文書は、ADR-0010で定めた実LLM長期品質ゲートのうち、人手読解を再現可能に
実施するための手順書である。β gateでは実LLM 30ターンの人手smokeに、1.0 gate
では実LLM品質gateの人手判定に使用する。

機械SLO、clean install、βschema凍結、UX受入、release checklistの判定はこの文書の
代替ではない。最終判定は、それらのgateとこのrubricの全項目がpassした場合だけ
`PASS`とする。

判定の正本は次のとおりである。

- [ADR-0010: 実LLM長期品質ゲートと物語SLO](adr/0010-quality-gate-narrative-slo.md)
- [ADR-0005: 1.0リリース契約](adr/0005-v1-release-contract.md)
- 実LLM 30ターンの実行・JSON artifact・`docs/evaluations/`転記手順は
  [Issue 072](issues/072-real-llm-bench.md) と[実行手順](real-llm-benchmark.md)に従う。

## 判定ルール

- 人手rubricは8項目すべてを`YES`または`NO`で判定する。
- `N/A`、未確認、証跡なしは`NO`として扱う。
- 8項目のうち1項目でも`NO`ならrubric全体を`FAIL`とする。
- provider failure、途中停止、ターン欠落があるrunはrubric判定前に`FAIL`とする。
  発生したturn番号を評価記録に残す。
- 判定は推測ではなく、読解対象のturn番号またはartifactのフィールドを根拠にする。
  根拠を特定できない場合は`NO`とする。
- 判定後に本文やartifactを差し替えた場合は、別の評価IDで再判定する。

## 入力artifactの確認

評価者は読解前に、実行担当者から次を受け取る。

1. Issue 072の30ターン実行artifact(JSON)。seed、provider、model、git revision、
   成功turn数、provider failureの有無を確認する。
2. 同じrunの`docs/evaluations/`転記。turnごとのnarrationと、reader-visibleな
   event/state情報を含むものを使用する。
3. rollbackまたはresumeの実行結果。対象turn、再開後のturn、終了状態が分かる
   artifactを使用する。
4. thread、game機能、leak scanの結果。機械SLOの結果を人手rubricの補助証跡として
   参照する。

次を満たさないartifactは読み始めず、実行担当者へ差し戻す。

- 対象runが30ターン完了している。
- seed、provider、model、git revision、実行日時が記録されている。
- provider failureがない。ある場合は発生turnとエラーが記録され、runは`FAIL`である。
- 転記とJSONのturn番号・narrationが一致している。
- 読解用の本文に`gm_vault`、`hidden_facts`、character secret、`private_mind`など
  の非reader-visible情報が混入していない。

## 15ターンの抜粋方法

30ターンrunから、次の3ブロックを固定で抽出する。境界の近くで都合のよいturnへ
置き換えてはならない。

| ブロック | 対象turn | 読解の目的 |
|---|---:|---|
| 冒頭 | 1–5 | 初期設定、人物、視点、最初のthreadを確認する |
| 中盤 | 13–17 | 状態変化、threadの進展、感情の連続性を確認する |
| 終盤 | 26–30 | threadの回収、game機能、終盤の継続性を確認する |

各ブロックではturnを飛ばさず、次の順で読む。

1. turnのnarrationを読む。
2. そのturnのreader-visible event/stateと直前turnとの差分を読む。
3. 人物の発話・行動・視点を識別し、前後の因果と感情を記録する。
4. 疑わしい箇所は`turn_NNNN`と短い事実の要約を記録する。本文の長い引用は不要。

抜粋だけでは判定できない項目は、30ターン全体のartifactを確認する。特にthreadの
回収、同一フレーズの3連続反復、game機能の発火、rollback/resumeは全runを対象に
判定する。

## 8項目YES/NO判定表

| ID | 判定項目 | `YES`の条件 | 主な証跡 |
|---|---|---|---|
| R1 | 継続性矛盾なし | 抜粋15ターンで、人物・場所・時系列・既知事実が相互に矛盾しない | turn番号、reader-visible state/event |
| R2 | GM情報漏洩なし | narrationとreader-visible出力に、GM専用情報・hidden fact・character secret・private mindが現れない | leak scan、該当turn、公開出力 |
| R3 | threadを1件以上回収 | 30ターン内に少なくとも1つのthreadが`resolved`へ遷移し、回収内容がnarrationまたは公開eventで確認できる | thread ID、解決turn、該当turn |
| R4 | 人物同定 | 抜粋15ターンを読んだ読者が、主要人物と発話者・行動者・視点を一意に識別できる | 該当turn、人物名、識別理由 |
| R5 | 同一フレーズ3連続反復なし | 同じ意味の説明や同一フレーズが、3ターン連続で物語上の新情報なしに反復されない | 全30ターンのturn番号、反復箇所 |
| R6 | 感情整合 | 抜粋15ターンで、人物の感情表現が直前の出来事とreader-visible stateに整合し、根拠なく反転しない | 人物、turn番号、事象、感情の根拠 |
| R7 | game機能1件以上発火 | run中にcombat、skill check、quest、inventoryなどのgame機能が少なくとも1回発火し、結果がartifactにある | 機能名、event/roll ID、turn番号 |
| R8 | rollbackまたはresume正常動作 | run中のrollbackまたはresumeが成功し、その後のturnが継続して記録される | 操作、対象turn、再開turn、artifact |

R3、R7、R8は、narrationに描写があるだけでは`YES`にしない。状態、event、roll、
操作結果のartifactで発火または成功を確認する。R2はleak scanがpassでも、抜粋読解で
漏洩を発見した場合は`NO`とする。

## 実施手順

### 1. runを固定する

実行担当者は30ターンrunを完了し、JSONと`docs/evaluations/`転記を保存する。評価者は
評価IDを発行し、git revision、seed、provider、model、日時、artifactのパスを記録する。

### 2. 機械的な事前確認をする

成功turn数、provider failure、JSONと転記の整合、leak scan、thread/game/rollbackまたは
resumeのartifactを確認する。事前確認に失敗したrunは人手判定を進めず`FAIL`とする。

### 3. 抜粋15ターンを読む

1–5、13–17、26–30の順に読み、R1、R2、R4、R5、R6の根拠を記録する。読解中に
artifactの非公開情報を参照する必要がある場合は、秘密値そのものを評価記録へ転記せず、
項目ID・turn番号・判定理由だけを残す。

### 4. 全runの補助証跡を確認する

30ターン全体からR3、R5、R7、R8を確認する。rollbackとresumeの両方を実施した場合は、
各操作を別々に記録し、どちらか一方の成功だけでR8を`YES`にしてよい。

### 5. 判定を確定する

8項目すべてに判定と根拠を記入する。1つでも`NO`なら全体を`FAIL`とし、再実行が必要な
項目を列挙する。全項目が`YES`で、事前確認も成功している場合だけ`PASS`とする。

### 6. 記録を保存する

評価記録を`docs/evaluations/YYYY-MM-DD-<run-id>-human-rubric.md`として保存する。
JSON artifactへの相対パスと、読解に使用した転記のパスを記録し、本文に秘密値を含めない。

## 評価記録テンプレート

次のテンプレートをコピーし、`<...>`を置き換えて保存する。

```markdown
# 人手rubric評価 — <run-id>

- gate: beta | 1.0
- result: PASS | FAIL
- evaluated_at: <ISO-8601>
- reviewer: <name>
- git_revision: <commit>
- seed: <seed>
- provider: <provider>
- model: <model>
- completed_turns: 30
- benchmark_json: <path>
- benchmark_markdown: <path>
- provider_failure: none | turn <N>: <short reason>

## 事前確認

- [ ] 30ターン完了
- [ ] JSONとMarkdownのturn番号・narrationが一致
- [ ] provider failureなし
- [ ] reader-visible出力に非公開情報なし
- [ ] 補助artifactを確認

## 8項目判定

| ID | 判定 | 根拠turn / artifact | 判定理由 |
|---|---|---|---|
| R1 | YES / NO | <turn or path> | <短い事実ベースの根拠> |
| R2 | YES / NO | <turn or path> | <短い事実ベースの根拠> |
| R3 | YES / NO | <turn or path> | <短い事実ベースの根拠> |
| R4 | YES / NO | <turn or path> | <短い事実ベースの根拠> |
| R5 | YES / NO | <turn or path> | <短い事実ベースの根拠> |
| R6 | YES / NO | <turn or path> | <短い事実ベースの根拠> |
| R7 | YES / NO | <turn or path> | <短い事実ベースの根拠> |
| R8 | YES / NO | <turn or path> | <短い事実ベースの根拠> |

## 結論

- failed_items: <none or IDs>
- rerun_required: YES | NO
- notes: <再現に必要な最小限の補足>
```

`result`は、事前確認が全て成功し、R1–R8が全て`YES`のときだけ`PASS`にする。
評価者の印象や未確認事項を`notes`で補って`PASS`にしてはならない。
