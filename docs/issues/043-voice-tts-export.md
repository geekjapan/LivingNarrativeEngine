---
id: 043
title: voice profileとTTS台本export
status: in_progress
created: 2026-07-11
---

# 043: voice profileとTTS台本export

## 背景

Issue 042のVN scriptには話者付き台詞と地の文があるが、読み上げ工程へ渡すvoice設定付き台本とprovider境界がない。音声生成そのものはproviderへ委譲し、reader可視の台本、任意voice profile、mock出力だけで一連の契約を固定する。

## 設計

1. character idごとの声質メモ・話速等を表すPydantic v2 voice profile collectionを追加し、`voice_profiles.yaml`をoptional load/saveにする。ファイルがない既存projectは空collectionとして扱う。
2. canonicalな`script.yaml`（Issue 042）だけを入力に、dialogueは実在speakerのprofile、narrationは明示的なnarrator profileまたはdefaultを参照する決定論的TTS台本へ変換する。warningやGM専用情報を発話本文へ混入させない。
3. `media/`へ`VoiceProvider` Protocolとplain dict registry、決定論的mock providerを追加する。mockは読み上げ予定textをasset text fileとして出力し、実TTS providerは実装しない。
4. `cli/export.py`へTTS script生成subcommandを追加し、`exports/tts_script.yaml`と`.md`をatomicに出力する。任意でmock asset生成を呼べる場合もreader可視台本だけを渡す。
5. mist_stationへcharacter/narrator voice profile実値を追加し、speaker不明・profile欠落・不正scriptを明確なwarning/errorで扱う。
6. 音声providerの権利・声の同意・利用条件がproviderに依存する注意書きをexport metadataと`docs/rights-and-security.md`へ含める。

## 完了条件

- [ ] voice profile schemaと`voice_profiles.yaml` optional load/save経路がある
- [ ] VN scriptからdialogue/narrationの決定論的TTS台本を生成できる
- [ ] dialogueはcharacter voice、地の文はnarrator/default voiceを参照する
- [ ] `VoiceProvider` Protocol、dict registry、決定論的mockだけがある
- [ ] CLIが`tts_script.yaml`と`.md`をatomicに出力する
- [ ] reader可視台本だけをproviderへ渡し、未知speaker/profileを安全に扱う
- [ ] mist_station実値と音声権利注意書きがある
- [ ] 041とのCLI/media統合後も両subcommandが動き、全テスト・ruffがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/state/models.py`
- `src/living_narrative/state/store.py`
- `src/living_narrative/state/schema_export.py`
- `src/living_narrative/media/`
- `src/living_narrative/export_replay/vn_script.py`
- `src/living_narrative/export_replay/`
- `src/living_narrative/cli/export.py`
- `src/living_narrative/templates/mist_station/`
- `docs/rights-and-security.md`
- `tests/`
