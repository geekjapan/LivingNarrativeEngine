---
id: 058
title: 1.0の日常利用UXとaccessibility合格基準を決定する
status: done
created: 2026-07-12
type: wayfinder:prototype
priority: P1
parent: 052
blocked_by: [053]
---

# 058: 1.0の日常利用UXとaccessibility合格基準を決定する

## 問い

primary personaが「init→遊ぶ→介入→review→停止／再開→export→backup」を迷わず完遂できるために、CLIとWebのどのjourneyを1.0必須とし、何を観察して合否を判断するか。

## 背景

FastAPI UIと主要APIは実装済みだが、`web/page.py`は単一の大きなinline UIで、実ユーザーの日常利用評価、accessibility、error recovery、全機能discoverabilityは未証明。Web reviewの`edit`／`rerun_turn`はCLI限定である。

## 解決条件

- primary journeyと補助journeyを固定する
- task completion、誤操作、復旧、情報scope、accessibilityの観察項目を決める
- Web必須、CLI必須、片方だけでよい機能を分ける
- 3つ目の実用sampleとonboardingの必要性を評価する
- UI全面rewriteを避け、合格に必要な最小変更を切れる状態にする

## 関連ファイル

- `src/living_narrative/web/page.py`
- `src/living_narrative/web/app.py`
- `src/living_narrative/cli/`
- `README.md`
- `docs/issues/020-web-ui-skeleton.md`
- `docs/issues/025-diff-review-ui.md`


## 決定(2026-07-13承認済)

事実確認: journey中核(turn/auto/介入free-text+構造化/review 3決定/停止/再開/観測+GMパネル)はWebで完結済。init・export・backup/restore・rollback/branch・review edit/rerun_turnはCLI限定(`app.py:259`で意図的)。disclosure gateはサーバー側で機能+test済。063 E2EはAPI+CLIハッピーパスのみでブラウザUI/accessibility/エラー復旧は未カバー。

### 決定

- (a) **primary journey(1.0 gating)**: D1に忠実 — install→init(CLI)→serve→Webで観測+複数turn+介入+review 3決定+停止/再開→export(CLI)。initとexportは「CLIで完遂+Web/READMEから導線が見える」ことでmust充足(Web実装不要)。補助journey: backup/restore(should)、rollback/branch(post)、edit/rerun_turn(should)、設定編集(Web既存)。
- (b) **観察項目合否表**: task completion=各step補助なし1回成功・ヘルプ参照≤1/step・詰まり0 / 誤操作=破壊的操作後もartifact残存・正本非破壊 / 復旧=failed turn後のreview復帰+backup→破壊→restoreを1回通す / 情報scope=reader可視Web全応答にgm_vault系leak 0件+player_character 403網羅 / accessibility=キーボードのみ完遂+コントラスト4.5:1+全controlにラベル(**WCAG全面準拠はnon-goal**)。
- (c) **面の分割**: Web必須=turn/auto/停止/再開/介入/review 3決定/観測/disclosure gate。CLI必須(Web任意)=init/export/backup。CLI必須(片方でよい)=edit/rerun_turn/rollback/branch。片方でよい=設定編集。
- (d) **3つ目sample=不要(post-1.0)**(実用2つで十分)。onboarding=Web空状態に`living-narrative init`案内を出す最小ガイダンス(should強め)。フルonboardingは不要。
- (e) **最小UI変更(page.py追記のみ、rewriteなし)**: 空状態ガイダンス/input可視ラベル・aria-label/`#status`にaria-live/export・backupのCLI導線テキスト/コントラスト実測調整(必要時)/panel toggle focus(should)。
- **人手評価**: persona代理1名(可能なら実装者以外含む)×2セッション(clean新規journey/既存project継続+復旧)。βの人手smoke1回はセッション(1)を流用。チェックリストにstep×y/n・所要秒・ヘルプ回数・詰まり・復帰可否を記録。

### 実装Issue分割

- 058-A(must): 最小UX/a11yパッチ(page.pyのみ)+回帰test
- 058-B(must): disclosure leak-scan testを全reader可視エンドポイントへ横展開+player_character 403網羅
- 058-C(must): UX受入チェックリスト+人手smoke手順の文書確定
- 058-D(should): E2E拡張(停止/再開・review partial・backup/restore・replay決定性比較)
- 058-E(post-1.0): Web export/backup/init、edit/rerun Web化、framework検討

### 承認事項

- backupの線引き: 「CLI+導線テキストのみでmust充足、Web実装はpost」の解釈
- exportの線引き: 「CLI完遂+導線でmust充足」の解釈
