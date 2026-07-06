---
id: 012
title: 文体・口調の検証が無い(リナの一人称が「僕」になる、checkerは事実のみ検証)
status: done
created: 2026-07-06
---

# 012: 口調プロファイル + 文体checker

## 背景

20ターン評価で発見(replay 49・55行目): リナの一人称が「僕」になる箇所2つ。leak/continuity checkerは事実のみ検証し、文体(register)を見ない。キャラクターの口調はpromptの「その人物らしい口調」頼みで、データとして定義されていない。

## 設計

1. **スキーマ**: `CharacterState.speech: SpeechProfile = SpeechProfile()`(後方互換):
   - `first_person: str | None = None`(例: 私/俺/僕)
   - `forbidden_terms: list[str] = []`(このキャラの台詞に出てはいけない語。一人称の誤りは典型例)
2. **予防(生成側)**: character contextのscoped_stateにspeechを含め、プロンプトのペルソナ節に「speech.first_person を一人称として使う」を明記
3. **検知(checker側)**: `speech_register_checker`(safety/、registry登録):
   - `character_dialogue` イベント(character id + content)を対象に、そのキャラの `forbidden_terms` が含まれたら `Finding(severity="warn", checker="speech_register_check", related_ids=[event.id])`
   - `first_person` 設定済みかつ台詞に他キャラのfirst_personや典型一人称(私/俺/僕/あたし/わし)のうち**forbidden指定されたもの**が出た場合のみ警告(過検知回避のため判定はforbidden_termsベースに限定)
   - narration本文は対象外(話者帰属が不確実。dialogueイベントで十分)
4. **mist_station**: リナ `first_person: 私, forbidden_terms: [僕, 俺]`、カイ `first_person: 俺, forbidden_terms: [僕]`(他キャラも同様に)

## 完了条件

- [x] `SpeechProfile` スキーマ(後方互換default)、mist_station設定込み
- [x] character contextとプロンプトにspeechが入る(プロンプトv4バンプ)
- [x] checkerがforbidden_terms含有dialogueにwarnを出し、非該当では沈黙。auto-applyは止めない
- [x] mock全テストpass
- [x] 実LLM 12ターン(`sandbox/issue012_llm`、2026-07-07): 一人称違反ゼロ(「僕」出現ゼロ、「俺」はカイのみ)、v4プロンプト有効、checkerは正しく沈黙

## 関連ファイル

- `src/living_narrative/state/models.py`(CharacterState)
- `src/living_narrative/safety/registry.py`(checker登録)
- `src/living_narrative/agents/context_builder.py` / `agents/character.py`(scoped_state・プロンプト)
- `src/living_narrative/templates/mist_station/state/characters/*.yaml`
- 評価: `docs/evaluations/2026-07-06-replay-20turn-eval.md`(replay 49/55行目)
