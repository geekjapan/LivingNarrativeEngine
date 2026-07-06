---
id: 014
title: 未解決スレッド台帳のランタイム化(伏線が張られるだけで回収されない)
status: done
created: 2026-07-07
---

# 014: 未解決スレッド台帳(thread_updates)

## 背景

DAG Track A。20ターン評価の物語所見: カイの「聞いたことがある/あの日」既視感ビートが約6回、お守り・案内板・水滴と対象を替えて反復され、どれも回収されない。`UnresolvedThread` スキーマ(id/description/status/related_event_ids、`state/models.py:326`)と `unresolved_threads.yaml` のload/saveは存在するが**ランタイム消費ゼロ**(D109: データ形式のみ、Phase 5でランタイム — 今がそのPhase 5相当)。

## 設計

ナレーター経由(007のscene_summary_updateと同型 = leak-safe by construction):

1. **ナレーター出力拡張**: `thread_updates: list[ThreadUpdateCandidate] = []`(default空)。`ThreadUpdateCandidate(action: Literal["open","advance","resolve"], thread_id: str | None, description: str | None, note: str | None)`:
   - `open`: description必須、新しい謎・未回収の糸を登録(ナレーターがreader可視情報から起票 → リーク不能)
   - `advance`: thread_id必須、進展をnoteで記録(related_event_idsに当ターンイベントを紐付け)
   - `resolve`: thread_id必須、status=resolved
2. **State Manager変換**: threads を diff target 化(timeline方式: COLLECTION_TARGETSに`threads`追加 or 専用target)。open=add(id採番 `thread_{turn:04d}{index:02d}`)、advance=related_event_ids add+note追記、resolve=status set。不明thread_id・resolved済みへのadvanceはreject
3. **ナレーター文脈供給**: open threads(id+description+経過ターン)をNarratorContextへ。プロンプトに「未回収の糸を意識し、長く放置された糸は進展か回収を優先する」
4. **pacing連携**: `detect_stall` の前進シグナルに thread の advance/resolve を追加(openは前進とみなさない — 新しい謎を積むだけでは前進ではない)
5. キャラクター文脈には入れない(メタ情報。キャラは糸を「知らない」のが正)
6. mist_stationの `unresolved_threads.yaml` は空のまま(ナレーターが実ランで起票する)

## 完了条件

- [x] ThreadUpdateCandidate + ナレーター出力拡張(default空、テンプレートフォールバックは無更新)
- [x] State Manager変換 + diff apply/rollback + reject(不明id/resolved済みadvance)
- [x] NarratorContextにopen threads供給、プロンプト指示
- [x] detect_stallがthread advance/resolveを前進と数える(openは数えない)
- [x] mock全テストpass(498+)
- [x] 実LLM 10ターン(`sandbox/issue014_llm`): turn 3でthread起票→6回advance(notes蓄積・related_event_ids紐付け)、後続ターンのナレーター文脈にopen_threads+turns_open供給確認。物語は収束型に(発生源調査→線路の先と特定→錆びた扉発見)。pacing連携も実地確認(turn 4停滞検知=openは前進と数えない仕様通り、以後advanceが停滞防止)。resolveと複数thread並行は本ランでは未発生 — 長尺ランで別途観測

## 関連ファイル

- `src/living_narrative/state/models.py:326`(UnresolvedThread)/ `state/store.py`(load/save済み)
- `src/living_narrative/narration/llm_narrator.py` / `narration/models.py`(007と同型)
- `src/living_narrative/agents/state_manager.py` / `state/diff.py`(threads target)
- `src/living_narrative/agents/pacing.py`(前進シグナル)
- `src/living_narrative/pipeline/driver.py`(narrate→build_diff配線、007と同じ経路)
- DAG: `docs/plan/feature-dag.md`
