# 実LLM benchmark転記 — 20260727-issue086-r4-hardening

- gate: `1.0`
- result: `PASS`
- started_at: 2026-07-27T17:32:31.392378+09:00
- finished_at: 2026-07-27T17:46:48.123505+09:00
- git_revision: 48f4c0e9542a09354656ecf909002216c8fa2c15
- sample: mist_station
- seed: issue-085-mist-station-v1
- provider: openai-compatible
- model: cx/gpt-5.6-luna-low
- completed_turns: 30 / 30
- benchmark_json: sandbox/20260727-issue086-r4-hardening/benchmark.json
- provider_failure: none
- narrator: 30 turns / 31 requests | fallback: none
- resume: turn 15 → turn 16 | PASS

## 事前確認

- [x] `run.status`が`PASS`
- [x] 30ターンが`applied`
- [x] JSONとMarkdownのturn番号・narrationが一致
- [x] provider failureなし
- [x] narrator bindingが有効でrenderer fallbackなし
- [x] reader-visible出力に非公開情報なし
- [x] `mechanical.metrics`、leak scan、resumeを確認

## Turns

## Turn 01

### Status

applied

### Narration

リナは懐中電灯を霧の向こうへ向けた。光の輪の先には、古い切符を握った子どもが立ち、こちらを見つめている。彼女は近づいてくる規則正しい足音にも耳を澄ませながら、カイのそばを離れなかった。「ねえ、あなたは誰？　その切符で、どこへ行くの？」

カイはリナをかばうように前に立ち、「リナ、俺の後ろにいて。あの足音が止まるまで、近づくな」と低く告げた。静かな時間が流れ、ホームの縁では霧がゆっくりと渦を巻いている。足音はなおも近づき、二人と子どものあいだに濃い白が沈黙を積もらせていた。

### Reader-visible events

```json
[
  {
    "id": "event_0001",
    "turn": 1,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を霧の向こうの子どもへ向け、足音のする方向にも注意を払いながら、カイのそばを離れずに様子を見守る。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0002",
    "turn": 1,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「ねえ、あなたは誰？　その切符で、どこへ行くの？」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0004",
    "turn": 1,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろにいて。あの足音が止まるまで、近づくな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0004"
    ]
  },
  {
    "id": "event_0006",
    "turn": 1,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0009",
    "turn": 1,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0003",
      "target_id": null
    },
    "roll_ids": [
      "roll_0003"
    ]
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 02

### Status

applied

### Narration

リナはカイの背後へ半歩下がり、懐中電灯の光を改札跡の鉄柵へ向けた。揺れるお守りの紐と、その周囲に異変がないかを慎重に見つめながら、霧の中から規則正しく近づく足音に耳を澄ませる。「カイ、あの鉄柵を見て。誰かが結んだお守りみたい……足音に気をつけながら、少しだけ確かめてもいい？」

カイはリナの前に立ち、霧と足音の気配を警戒しながら、鉄柵で揺れる色褪せたお守りの紐へ視線を向けた。紐は静かなホームでかすかに揺れ続けている。「リナ、動くな。あのお守り……誰かが最近、触ったのかもしれない」

### Reader-visible events

```json
[
  {
    "id": "event_0010",
    "turn": 2,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの後ろに半歩下がりながら、懐中電灯の光を改札跡の鉄柵へ向ける。揺れるお守りの紐と、その周囲に異変がないかを慎重に観察する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0011",
    "turn": 2,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、あの鉄柵を見て。誰かが結んだお守りみたい……足音に気をつけながら、少しだけ確かめてもいい？」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0013",
    "turn": 2,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ち、霧と足音の気配を警戒しながら、改札跡の鉄柵で揺れる色褪せたお守りの紐へ視線を向ける。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0014",
    "turn": 2,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、動くな。あのお守り……誰かが最近、触ったのかもしれない」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0016",
    "turn": 2,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "改札跡の鉄柵で、誰かが結んだ色褪せたお守りの紐が揺れる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 03

### Status

applied

### Narration

「カイ、視界がほとんどないよ。足音が近づくまで、ここを動かないほうがいい？」リナの声が、濃い霧の中でかすかに揺れた。

「リナ、俺から離れるな。見えなくても、足音が近づいたらすぐ知らせる」カイはそう答えた。だが霧はさらに一段と濃くなり、数歩先の景色さえ白く閉ざしていく。改札跡の鉄柵に結ばれた色褪せたお守りだけが、ぼんやりと揺れていた。その向こうから、規則正しい足音が近づいてきた。

### Reader-visible events

```json
[
  {
    "id": "event_0020",
    "turn": 3,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、視界がほとんどないよ。足音が近づくまで、ここを動かないほうがいい？」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0009"
    ]
  },
  {
    "id": "event_0022",
    "turn": 3,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺から離れるな。見えなくても、足音が近づいたらすぐ知らせる」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0010"
    ]
  },
  {
    "id": "event_0024",
    "turn": 3,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "霧が一段と濃くなり、数歩先の視界が白く閉ざされる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 04

### Status

applied

### Narration

「カイ、足音が近い。案内板を目印にして、すぐ逃げられる位置を確かめよう。何か見えたら、私に知らせて」リナの声が霧に吸われる。カイは彼女の前に立ったまま、錆びた案内板が軋み、読めない駅名を揺らす音と、霧の向こうから規則正しく近づく足音に耳を澄ました。

やがてカイは片手をわずかに上げ、動かないようリナに合図する。濃い霧のなかで、二人のすぐそばにあるはずの案内板さえ輪郭を失い、足音だけが一定の間隔で近づいてきた。

### Reader-visible events

```json
[
  {
    "id": "event_0028",
    "turn": 4,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、足音が近い。案内板を目印にして、すぐ逃げられる位置を確かめよう。何か見えたら、私に知らせて」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0013"
    ]
  },
  {
    "id": "event_0030",
    "turn": 4,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ったまま、錆びた案内板の揺れる音と霧の向こうの足音に耳を澄ます。片手をわずかに上げ、リナに動かないよう合図する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0014"
    ]
  },
  {
    "id": "event_0032",
    "turn": 4,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "錆びた案内板が軋み、読めない駅名が霧の中に揺れる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "quests",
    "op": "set",
    "path": "status",
    "value": "advanced",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0028",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0030",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0032",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 05

### Status

applied

### Narration

リナはカイの背後から動かず、懐中電灯の光を足元に絞った。濃い霧に沈むホームで、天井の亀裂から落ちる水滴が、闇の奥に一定の音を刻んでいる。彼女はその規則正しさと、近づいてくる足音の間隔を慎重に聞き分けた。

「カイ、水滴の音が一定すぎる。足音が近づくまで動かずに、音の位置だけ確かめよう」

カイはリナを背にかばい、案内板のそばから動かなかった。二人は息を潜めたまま、水滴の音と霧の奥から迫る足音とを、静かに聞き分け続けた。

### Reader-visible events

```json
[
  {
    "id": "event_0035",
    "turn": 5,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後から動かず、懐中電灯の光を足元に絞ったまま、水滴の規則的な音と近づく足音の間隔を慎重に聞き分ける。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0036",
    "turn": 5,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、水滴の音が一定すぎる。足音が近づくまで動かずに、音の位置だけ確かめよう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0037",
    "turn": 5,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、案内板のそばから動かずに、天井から落ちる水滴の間隔と霧の奥の足音を聞き分ける。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0017"
    ]
  },
  {
    "id": "event_0039",
    "turn": 5,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "天井の亀裂から水滴が落ち、闇の奥で規則正しい音を刻む",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 06

### Status

applied

### Narration

リナはカイの背後で息を潜め、懐中電灯の細い光を足元に落としたまま、水滴の音と足音の間隔をもう一度聞き分けた。濃い霧の立ち込めるホームで、天井の亀裂から落ちる水滴が闇の奥に規則正しい音を刻み、その向こうから足音が近づいてくる。「カイ、足音はまだ近づいている。水滴の音に紛れているけれど、動くなら合図して。私も離れないから」

カイはリナの前に立ったまま、水滴の音を基準に霧の奥の足音の位置を探った。片手でリナを背後に制し、いつでも案内板の陰へ退けるよう身構える。

### Reader-visible events

```json
[
  {
    "id": "event_0042",
    "turn": 6,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後で息を潜め、懐中電灯の光を足元に細く落としたまま、水滴の音と足音の間隔をもう一度聞き分ける。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0043",
    "turn": 6,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、足音はまだ近づいている。水滴の音に紛れているけれど、動くなら合図して。私も離れないから」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0045",
    "turn": 6,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ったまま、規則正しい水滴の音を基準にして霧の奥の足音の位置を探る。片手でリナを背後に制し、いつでも案内板の陰へ退けるよう身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0020"
    ]
  },
  {
    "id": "event_0047",
    "turn": 6,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "天井の亀裂から水滴が落ち、闇の奥で規則正しい音を刻む",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 07

### Status

applied

### Narration

リナはカイの背後から離れず、懐中電灯の光を足元へ絞った。規則正しい足音の間隔と方向を慎重に聞き取りながら、案内板の陰へすぐ退けるよう身を低く構える。霧はホームの縁でゆっくりと渦を巻き、水滴の音に重なる足音だけが、少しずつ近づいてきた。

「カイ、足音の方向がはっきりした。まだ動かずに、近づきすぎたら案内板の陰へ下がろう。合図は私が出すね」

「リナ、足音の向きが定まった。俺の後ろから離れるな。近づいてきたら、合図と同時に案内板の陰へ下がる」

静かな時間の果てに、二人は足音の正体を確かめるため、霧の奥へ続く階段へ進んだ。

### Reader-visible events

```json
[
  {
    "id": "event_0050",
    "turn": 7,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後から離れず、懐中電灯の光を足元に絞ったまま、近づく足音の間隔と方向を慎重に聞き取る。案内板の陰へすぐ退けるよう、身体を低く構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0051",
    "turn": 7,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、足音の方向がはっきりした。まだ動かずに、近づきすぎたら案内板の陰へ下がろう。合図は私が出すね」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0053",
    "turn": 7,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、足音の向きが定まった。俺の後ろから離れるな。近づいてきたら、合図と同時に案内板の陰へ下がる」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0023"
    ]
  },
  {
    "id": "event_0055",
    "turn": 7,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0060",
    "turn": 7,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "階段へ進み、足音の正体を確かめる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0061",
    "turn": 7,
    "type": "action_outcome",
    "cause": "action:char_001:affordance_001",
    "text": "階段へ進み、足音の正体を確かめる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action_outcome": {
        "affordance_id": "affordance_001",
        "character_id": "char_001",
        "outcomes": [
          {
            "target": "scene",
            "op": "set",
            "path": "status",
            "id": "scene_001",
            "value": "ended",
            "visibility": "reader"
          },
          {
            "target": "scene",
            "op": "set",
            "path": "status",
            "id": "scene_002",
            "value": "active",
            "visibility": "reader"
          },
          {
            "target": "scene",
            "op": "set",
            "path": "active_characters",
            "id": "scene_002",
            "value": [
              "char_001",
              "char_002"
            ],
            "visibility": "reader"
          },
          {
            "target": "canon",
            "op": "add",
            "path": "",
            "id": null,
            "value": {
              "id": "canon_003",
              "text": "二人は地下ホームの階段へ進み、追跡者の気配を確かめた。",
              "established_turn": 0,
              "source_event": null
            },
            "visibility": "canon"
          },
          {
            "target": "reader_state",
            "op": "add",
            "path": "",
            "id": null,
            "value": {
              "id": "reader_state_001",
              "text": "二人は足音を追って、駅の奥へ進んだ。",
              "established_turn": 0,
              "source_event": null,
              "disclosed_turn": 0
            },
            "visibility": "reader"
          },
          {
            "target": "quests",
            "op": "set",
            "path": "status",
            "id": "quest_001",
            "value": "advanced",
            "visibility": "reader"
          },
          {
            "target": "threads",
            "op": "add",
            "path": "",
            "id": null,
            "value": {
              "id": "thread_001",
              "description": "地下ホームに響く足音の正体",
              "status": "open",
              "related_event_ids": [],
              "notes": [],
              "opened_turn": 0
            },
            "visibility": "reader"
          }
        ],
        "consumption": {
          "recurrence": "once",
          "exclusive": true,
          "fallback": true
        }
      },
      "accepted": true,
      "advancement": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0062",
    "turn": 7,
    "type": "thread_update",
    "cause": "authored:affordance_001",
    "text": "地下ホームに響く足音の正体",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "open",
      "thread_id": "thread_001",
      "authored": true
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "scene",
    "op": "set",
    "path": "status",
    "value": "ended",
    "id": "scene_001",
    "visibility": "reader",
    "source_event": "event_0061"
  },
  {
    "target": "scene",
    "op": "set",
    "path": "status",
    "value": "active",
    "id": "scene_002",
    "visibility": "reader",
    "source_event": "event_0061"
  },
  {
    "target": "scene",
    "op": "set",
    "path": "active_characters",
    "value": [
      "char_001",
      "char_002"
    ],
    "id": "scene_002",
    "visibility": "reader",
    "source_event": "event_0061"
  },
  {
    "target": "reader_state",
    "op": "add",
    "path": "",
    "value": {
      "id": "reader_state_001",
      "text": "二人は足音を追って、駅の奥へ進んだ。",
      "established_turn": 7,
      "source_event": "event_0061",
      "disclosed_turn": 7
    },
    "id": null,
    "visibility": "reader",
    "source_event": "event_0061"
  },
  {
    "target": "threads",
    "op": "add",
    "path": "",
    "value": {
      "id": "thread_001",
      "description": "地下ホームに響く足音の正体",
      "status": "open",
      "related_event_ids": [],
      "notes": [],
      "opened_turn": 7
    },
    "id": null,
    "visibility": "reader",
    "source_event": "event_0061"
  },
  {
    "target": "quests",
    "op": "set",
    "path": "status",
    "value": "advanced",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0050",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0051",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0053",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0055",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0060",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0061",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 08

### Status

applied

### Narration

リナはカイの背後から離れず、懐中電灯を追跡者へ直接向けないまま足元に保った。濃い霧の流れと相手の手元を見つめ、閉ざされた通路のどこかに隙がないか、静かに探る。追跡者は足音を止め、逃げ場のない行き止まりで二人をじっと見据えていた。「カイ、まだ動かないで。相手の様子と霧の流れを見て、隙ができたら一緒に戻ろう」

「リナ、俺の後ろにいろ。合図するまで動くな」カイの声が低く響いた。そのとき、天井の亀裂から水滴が落ち、闇の奥で規則正しい音を刻み始める。霧は背後を塞いだまま、三人のあいだに張りつめた沈黙だけが残った。

### Reader-visible events

```json
[
  {
    "id": "event_0063",
    "turn": 8,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後から離れず、懐中電灯を追跡者へ直接向けないまま足元に保つ。霧の動きと相手の手元を観察し、逃げ道がないか静かに探る。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0064",
    "turn": 8,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。相手の様子と霧の流れを見て、隙ができたら一緒に戻ろう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0066",
    "turn": 8,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろにいろ。合図するまで動くな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0027"
    ]
  },
  {
    "id": "event_0068",
    "turn": 8,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "天井の亀裂から水滴が落ち、闇の奥で規則正しい音を刻む",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 09

### Status

applied

### Narration

リナはカイの背後を守るように立ち、懐中電灯の光を足元から逸らさなかった。明滅する電球のたびにホームの影が伸び縮みし、霧もかすかに揺らめく。その変化を手掛かりに、じっとこちらを見据える追跡者の姿勢と、濃い霧に閉ざされた退路を慎重に見定める。

「カイ、まだ動かないで。相手が先に動くまで、私たちは互いの位置を崩さない。何か見えたら、すぐに小さく合図して」

「リナ、俺から離れるな。あいつが動いたら、合図を待たずに俺の後ろをついてこい」

古い電球がどこかでまた明滅し、闇の中の影が伸びては縮んだ。追跡者は足音を止めたまま、二人を見据えて動かなかった。

### Reader-visible events

```json
[
  {
    "id": "event_0072",
    "turn": 9,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後を保ちながら、懐中電灯の光を足元に留める。明滅する電球と霧の揺らぎを手掛かりに、追跡者の姿勢と周囲の退路を慎重に見定める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0073",
    "turn": 9,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。相手が先に動くまで、私たちは互いの位置を崩さない。何か見えたら、すぐに小さく合図して」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0075",
    "turn": 9,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺から離れるな。あいつが動いたら、合図を待たずに俺の後ろをついてこい」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0030"
    ]
  },
  {
    "id": "event_0077",
    "turn": 9,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "どこかで古い電球が明滅し、ホームの影が伸び縮みする",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 10

### Status

applied

### Narration

「カイ、合図を待つ。私たちは離れないで、相手が動いたら一緒に霧の中へ下がろう」リナはカイの背後を守るように身を低くし、懐中電灯の光を足元に保ったまま、霧の揺らぎと人影の位置を慎重に見極めた。カイもまたリナを背後にかばい、霧の奥の人影から目を逸らさず、濃霧に塞がれた退路と、相手が踏み出した瞬間に彼女を横へ逃がせる位置を確かめて身構える。「リナ、俺の背中から離れるな。あいつが動いたら、俺が道を開ける」

静かな時間が流れ、ホームの縁で霧がゆっくりと渦を巻いた。明滅する電球の下、霧の奥に揺れた人影から、規則正しく響いていた足音が急に途切れる。行き止まりの通路と背後の濃霧の間で、追跡者は立ち止まり、じっと二人を見据えていた。

### Reader-visible events

```json
[
  {
    "id": "event_0080",
    "turn": 10,
    "type": "character_dialogue",
    "cause": "character:char_001:0",
    "text": "「カイ、合図を待つ。私たちは離れないで、相手が動いたら一緒に霧の中へ下がろう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0081",
    "turn": 10,
    "type": "character_action",
    "cause": "character:char_001:1",
    "text": "リナはカイの背後を守るように身を低くし、懐中電灯の光を足元に保ったまま、霧の揺らぎと人影の位置を慎重に見極める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0082",
    "turn": 10,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背後にかばい、霧の奥の人影から目を逸らさずに身構える。退路を塞ぐ濃霧にも注意を払い、相手が踏み出した瞬間にリナを横へ逃がせる位置を取る。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0083",
    "turn": 10,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の背中から離れるな。あいつが動いたら、俺が道を開ける」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0085",
    "turn": 10,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0087",
    "turn": 10,
    "type": "threat_stage",
    "cause": "world_simulator",
    "text": "霧の奥に人影が揺れ、規則正しい足音が急に止まる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "threat_id": "threat_001",
      "stage_at": 75,
      "roll_id": "roll_0032",
      "target_id": null
    },
    "roll_ids": [
      "roll_0032"
    ]
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "memory",
    "op": "add",
    "path": "",
    "value": {
      "id": "memory_0010",
      "up_to_turn": 10,
      "text": "リナとカイは霧に覆われた地下ホームで、古い切符を握る子どもや、改札跡の鉄柵に結ばれた色褪せたお守りを目にした。二人は霧と足音の正体を確かめるため、案内板や水滴の音を手掛かりに、互いに離れず進んできた。足音は次第に近づき、追跡者の存在が霧の奥に浮かび上がった。現在、行き止まりと濃霧に退路を塞がれた二人は、追跡者が動く瞬間を待っている。"
    },
    "id": null,
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 11

### Status

applied

### Narration

リナはカイの背中に触れられる距離を保ち、懐中電灯の光を足元から動かさなかった。霧の奥の人影と、左右の壁際を交互に見つめながら、彼女は低く告げた。「カイ、今度こそ一緒に動くよ。あの影が近づいたら、左側へ下がって」

カイはリナを背にかばったまま、人影から目を逸らさず、横へ退けるよう足の位置をわずかに整えた。「リナ、まだ動くな。あいつが踏み出したら、俺の合図で右へ走る」そのとき、どこかで古い電球が明滅し、ホームの影が伸び縮みした。行き止まりの先で追跡者はなお動かず、濃い霧だけが二人の背後を塞いでいた。

### Reader-visible events

```json
[
  {
    "id": "event_0090",
    "turn": 11,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背中に触れられる距離を保ち、懐中電灯を足元から動かさずに、霧の奥の人影と左右の壁際を交互に見つめる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0091",
    "turn": 11,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今度こそ一緒に動くよ。あの影が近づいたら、左側へ下がって」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0093",
    "turn": 11,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばったまま、霧の奥の人影から目を逸らさず、いつでも横へ退けるよう足の位置をわずかに整える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0094",
    "turn": 11,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、まだ動くな。あいつが踏み出したら、俺の合図で右へ走る」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0096",
    "turn": 11,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "どこかで古い電球が明滅し、ホームの影が伸び縮みする",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 12

### Status

applied

### Narration

リナはカイの背中に触れられる距離を保ち、錆びた案内板の揺れと霧の流れを見逃さなかった。追跡者が動く気配を探りながら、左へ下がれる足場を慎重に確かめる。「カイ、今。左へ下がって、壁際を抜けるよ。私から離れないで」

カイは、追跡者の影が消えた柱から視線を外さず、リナを背後にかばったまま足を止めた。霧の濃い方角へ不用意に踏み込むことはできない。「リナ、今だ。俺の右側を離れるな。影を追わず、霧の薄い方へ下がる」そのとき、錆びた案内板が軋み、読めない駅名が霧の中で揺れた。

### Reader-visible events

```json
[
  {
    "id": "event_0099",
    "turn": 12,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背中に触れられる距離を保ったまま、錆びた案内板の揺れと霧の流れを観察する。追跡者が動く気配を逃さず、左へ下がれる足場を慎重に確かめる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0100",
    "turn": 12,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今。左へ下がって、壁際を抜けるよ。私から離れないで」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0102",
    "turn": 12,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは追跡者の影が消えた柱へ視線を固定し、リナを背後にかばったまま、霧の濃い方角へ不用意に踏み込まないよう足を止める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0103",
    "turn": 12,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、今だ。俺の右側を離れるな。影を追わず、霧の薄い方へ下がる」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0105",
    "turn": 12,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "錆びた案内板が軋み、読めない駅名が霧の中に揺れる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "quests",
    "op": "set",
    "path": "status",
    "value": "advanced",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0099",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0100",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0102",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0103",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0105",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 13

### Status

applied

### Narration

リナは懐中電灯の光を追跡者の顔へ向け、カイの腕をつかんだ。二人は背中合わせになり、濃い霧に塞がれた背後を避けながら、霧の薄い側へ下がる隙を探した。「カイ、離れないで。あなたが合図したら、二人で一気に横へ抜けるよ」

カイは霧を裂いて現れた追跡者との間へ身を滑り込ませ、リナを背後にかばった。退路は濃霧に閉ざされている。それでも彼は相手の動きを見極め、リナが横へ逃げられる瞬間を探していた。「リナ、俺の合図で左へ走れ。あいつが何者でも、道は俺が作る」静かな時間が流れ、ホームの縁で霧がゆっくりと渦を巻く。やがてその霧をさらに裂き、追跡者が二人の前に姿を現した。

### Reader-visible events

```json
[
  {
    "id": "event_0109",
    "turn": 13,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を追跡者の顔へ向け、カイの腕をつかんで背中合わせになり、霧の薄い側へ下がる隙を探す。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0110",
    "turn": 13,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、離れないで。あなたが合図したら、二人で一気に横へ抜けるよ」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0112",
    "turn": 13,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは霧を裂いて現れた追跡者との間に身を滑り込ませ、リナを背後にかばう。濃霧に退路を塞がれながらも、相手の動きを見極め、リナが横へ逃げられる隙を探す。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0113",
    "turn": 13,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の合図で左へ走れ。あいつが何者でも、道は俺が作る」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0115",
    "turn": 13,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0117",
    "turn": 13,
    "type": "threat_stage",
    "cause": "world_simulator",
    "text": "霧を裂いて、追跡者が二人の前に姿を現す。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter": "threat_001",
      "scene_transition": {
        "end": "scene_001",
        "start": "scene_002"
      },
      "threat_id": "threat_001",
      "stage_at": 100,
      "roll_id": "roll_0039",
      "target_id": null
    },
    "roll_ids": [
      "roll_0039"
    ]
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 14

### Status

applied

### Narration

リナは懐中電灯の光を追跡者から逸らさず、カイの背に肩を寄せたまま、足元の段差と霧の流れを慎重に見極めた。「カイ、まだ動かないで。あいつの足が止まっているうちに、左へ抜けられる場所を探す。合図は私も見ているから」

カイはリナを背にかばい、追跡者の視線を外さずに半歩だけ左へ身をずらした。濃霧の切れ目に足場を見つけると、リナが抜けられる幅を確保する。「リナ、まだ動くな。あいつが踏み出したら、俺の合図で左へ抜ける。絶対に離れるな」そのとき、線路の奥から冷たい風が吹き、油と土の匂いが狭い行き止まりへ流れ込んできた。

### Reader-visible events

```json
[
  {
    "id": "event_0119",
    "turn": 14,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯の光を追跡者から逸らさず、カイの背に肩を寄せたまま、足元の段差と霧の流れを慎重に見極める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0120",
    "turn": 14,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。あいつの足が止まっているうちに、左へ抜けられる場所を探す。合図は私も見ているから」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0122",
    "turn": 14,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、追跡者の視線を外さずに半歩だけ左へ身をずらす。濃霧の切れ目に足場を見つけると、リナが抜けられる幅を確保する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0123",
    "turn": 14,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、まだ動くな。あいつが踏み出したら、俺の合図で左へ抜ける。絶対に離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0125",
    "turn": 14,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "冷たい風が線路の奥から吹き、油と土の匂いを運んでくる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 15

### Status

applied

### Narration

リナは懐中電灯を低く構え、追跡者の足元と霧の流れを見比べた。行き止まりの通路と背後の濃い霧に挟まれたまま、彼女はカイが左側に確保した足場を慎重に確かめる。「まだ動かないで。あいつが踏み出した瞬間に、私が先に左へ抜ける。カイはすぐ後ろについてきて」

カイはリナの前に立ち、左側の足場をもう一度確かめた。追跡者がじっとこちらを見据えるなか、彼はその踏み出す瞬間を待ち、リナを先に横へ通す構えを崩さない。「……今だ。俺が合図したら、左へ走れ。振り返るな」静かな時間だけが流れ、ホームの縁では霧がゆっくりと渦を巻いていた。

### Reader-visible events

```json
[
  {
    "id": "event_0128",
    "turn": 15,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を低く構え、追跡者の足元と霧の流れを見比べながら、カイの確保した左側の足場を慎重に確認する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0129",
    "turn": 15,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「まだ動かないで。あいつが踏み出した瞬間に、私が先に左へ抜ける。カイはすぐ後ろについてきて」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0131",
    "turn": 15,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ったまま、左側に確保した足場をもう一度確かめる。追跡者が踏み出す瞬間を逃さず、リナを先に横へ通す構えを崩さない。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0132",
    "turn": 15,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「……今だ。俺が合図したら、左へ走れ。振り返るな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0134",
    "turn": 15,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 16

### Status

applied

### Narration

リナは窓口の奥から聞こえた、紙をめくるような気配へ一瞬だけ視線を向けた。だが、すぐに追跡者の影へ目を戻し、カイの合図に合わせて左側の足場へ身を滑らせる。「今だね。私についてきて、カイ！」濃霧に追跡者の影が消えた隙を、二人は走り抜けようとした。

カイは霧の向こうを警戒しながら、窓口の奥の気配へも一瞬だけ視線を走らせた。それからリナの前へ戻り、左側の足場を塞がないよう身構える。「……窓口の奥で音がした。追跡者が消えた今が動く時かもしれない。リナ、俺の後ろから左へ。離れるな」その直後、誰もいないはずの窓口の奥で、また紙をめくるような気配がした。

### Reader-visible events

```json
[
  {
    "id": "event_0137",
    "turn": 16,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは窓口の奥から聞こえた紙をめくる気配に一瞬だけ視線を向けるが、すぐに追跡者の影へ戻す。カイの合図に合わせ、左側の足場へ身を滑らせて走り出す。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0138",
    "turn": 16,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「今だね。私についてきて、カイ！」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0140",
    "turn": 16,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは追跡者の影が消えた霧を警戒しながら、窓口の奥から聞こえた紙をめくるような気配へ一瞬だけ視線を向ける。すぐにリナの前へ戻り、左側の足場を塞がないよう身構えた。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0141",
    "turn": 16,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「……窓口の奥で音がした。追跡者が消えた今が動く時かもしれない。リナ、俺の後ろから左へ。離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0143",
    "turn": 16,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "誰もいないはずの窓口の奥で、紙をめくるような気配がする",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "quests",
    "op": "set",
    "path": "status",
    "value": "advanced",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0137",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0138",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0140",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0141",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0143",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 17

### Status

applied

### Narration

リナは懐中電灯の光を足元へ絞り、カイの袖をつかんだまま、窓口の奥から聞こえる紙をめくるような音へ慎重に近づいた。霧の流れと床の状態を確かめ、いつでも引き返せる距離を保ちながら、彼女は低く告げた。「カイ、音の正体だけ確かめよう。何か動いたら、すぐに一緒に戻るから」

カイはリナを背にかばい、濃霧と窓口の奥を交互に警戒しながら、足音を立てず左側の通路を進んだ。逃げ道を塞がない位置を保ち、すぐに彼女を後退させられるよう身構える。「音の正体は後で確かめる。今はここを抜ける。俺から離れるな」そのとき、地上から遠雷のような街のざわめきが届いたが、音はたちまち霧に吸われて消えた。行き止まりと濃霧に挟まれた二人は、追跡者の真実を確かめ、封印の行方を決めるため、なおも足を止めなかった。

### Reader-visible events

```json
[
  {
    "id": "event_0147",
    "turn": 17,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を足元に絞り、カイの袖をつかんだまま、窓口の奥から続く紙をめくるような音へ慎重に近づく。霧の流れと床の状態を観察し、いつでも引き返せる距離を保つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0148",
    "turn": 17,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、音の正体だけ確かめよう。何か動いたら、すぐに一緒に戻るから」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0150",
    "turn": 17,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、濃霧と窓口の奥を交互に警戒しながら、足音を立てずに左側の通路を進む。逃げ道を塞がない位置を保ち、何かが現れればすぐにリナを後退させられるよう身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0151",
    "turn": 17,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「音の正体は後で確かめる。今はここを抜ける。俺から離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0153",
    "turn": 17,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "地上から遠雷のような街のざわめきが届き、すぐに霧へ吸われて消える",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0157",
    "turn": 17,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "追跡者の真実を確かめ、封印の行方を決める",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0158",
    "turn": 17,
    "type": "action_outcome",
    "cause": "action:char_001:affordance_002",
    "text": "追跡者の真実を確かめ、封印の行方を決める",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action_outcome": {
        "affordance_id": "affordance_002",
        "character_id": "char_001",
        "outcomes": [
          {
            "target": "threads",
            "op": "set",
            "path": "status",
            "id": "thread_001",
            "value": "resolved",
            "visibility": "reader"
          },
          {
            "target": "threads",
            "op": "add",
            "path": "",
            "id": null,
            "value": {
              "id": "thread_002",
              "description": "追跡者は誰の命令で封印施設を探しているのか",
              "status": "open",
              "related_event_ids": [],
              "notes": [],
              "opened_turn": 0
            },
            "visibility": "reader"
          },
          {
            "target": "quests",
            "op": "set",
            "path": "status",
            "id": "quest_001",
            "value": "advanced",
            "visibility": "reader"
          }
        ],
        "consumption": {
          "recurrence": "once",
          "exclusive": true,
          "fallback": true
        }
      },
      "accepted": true,
      "advancement": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0159",
    "turn": 17,
    "type": "thread_update",
    "cause": "authored:affordance_002",
    "text": "地下ホームに響く足音の正体",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "resolve",
      "thread_id": "thread_001",
      "authored": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0160",
    "turn": 17,
    "type": "thread_update",
    "cause": "authored:affordance_002",
    "text": "追跡者は誰の命令で封印施設を探しているのか",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "open",
      "thread_id": "thread_002",
      "authored": true
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "threads",
    "op": "set",
    "path": "status",
    "value": "resolved",
    "id": "thread_001",
    "visibility": "reader",
    "source_event": "event_0158"
  },
  {
    "target": "threads",
    "op": "add",
    "path": "",
    "value": {
      "id": "thread_002",
      "description": "追跡者は誰の命令で封印施設を探しているのか",
      "status": "open",
      "related_event_ids": [],
      "notes": [],
      "opened_turn": 17
    },
    "id": null,
    "visibility": "reader",
    "source_event": "event_0158"
  },
  {
    "target": "quests",
    "op": "set",
    "path": "status",
    "value": "advanced",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0147",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0148",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0150",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0151",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0153",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0157",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0158",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 18

### Status

applied

### Narration

リナは懐中電灯を低く構え、カイの袖をつかんだまま、追跡者の影と背後の濃霧を交互に見た。霧は退路を塞ぎ、行き止まりの通路に逃げ場はない。改札跡の鉄柵では、誰かが結んだ色褪せたお守りの紐だけが、かすかに揺れていた。

「カイ、まだ動かないで。あの影が動いたら、今度は私が合図する」

カイはお守りの揺れに気づくと、リナを背にかばい、鉄柵の前で足を止めた。濃霧の奥と周囲を警戒しながら、紐の結び目にも逃げ道にも触れず、慎重に見極めようとする。追跡者は足音を止めたまま、じっと二人を見据えていた。

「リナ、止まれ。あのお守りは誰かが結んだものだ。近づくなら俺が先に見る。何かあれば、すぐ戻るぞ」

### Reader-visible events

```json
[
  {
    "id": "event_0161",
    "turn": 18,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を低く構え、カイの袖をつかんだまま、追跡者の影と濃霧の動きを交互に観察する。退路を塞ぐ霧の濃さと、改札跡の鉄柵に揺れるお守りの位置を確かめ、カイと離れないよう身を寄せる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0162",
    "turn": 18,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。あの影が動いたら、今度は私が合図する」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0164",
    "turn": 18,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは揺れるお守りの紐に気づき、リナを背にかばったまま鉄柵の前で足を止める。濃霧の奥と周囲を警戒し、触れずに紐の結び目と逃げ道を見極める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0165",
    "turn": 18,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、止まれ。あのお守りは誰かが結んだものだ。近づくなら俺が先に見る。何かあれば、すぐ戻るぞ」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0167",
    "turn": 18,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "改札跡の鉄柵で、誰かが結んだ色褪せたお守りの紐が揺れる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 19

### Status

applied

### Narration

リナはカイの袖を離さず、懐中電灯の光を錆びた案内板と鉄柵のお守りへ交互に向けた。身を低くして追跡者を刺激しないようにしながら、結び目や案内板に隠された手掛かりを目だけで慎重に探る。「カイ、案内板とお守りを見て。何か出口につながる印があるかもしれない。でも、追跡者が動いたらすぐに下がろう」

### Reader-visible events

```json
[
  {
    "id": "event_0171",
    "turn": 19,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖を離さず、懐中電灯の光を錆びた案内板と鉄柵のお守りへ交互に向ける。追跡者を刺激しないよう身を低くし、結び目や案内板に隠された手掛かりを目だけで慎重に探る。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0172",
    "turn": 19,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、案内板とお守りを見て。何か出口につながる印があるかもしれない。でも、追跡者が動いたらすぐに下がろう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0174",
    "turn": 19,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、錆びた案内板と追跡者の影を交互に見据える。鉄柵から離れず、霧の動きに合わせてリナを守れる位置を保つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0175",
    "turn": 19,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺が合図するまで動くな。あの影が近づいたら、俺の後ろを離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0177",
    "turn": 19,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "錆びた案内板が軋み、読めない駅名が霧の中に揺れる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 20

### Status

applied

### Narration

リナは懐中電灯を消し、カイの袖をつかんだまま柱の影へ身を寄せた。通路の先は行き止まり、背後には濃い霧が満ちている。天井の亀裂から落ちる水滴が、闇の奥で規則正しい音を刻んでいた。リナは水音と追跡者の影が消えた方角を交互に確かめ、霧のわずかな動きさえ見逃すまいと息を潜める。

### Reader-visible events

```json
[
  {
    "id": "event_0180",
    "turn": 20,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を消し、カイの袖をつかんだまま柱の影に身を寄せる。水滴の規則正しい音と、追跡者の影が消えた方向を交互に確かめ、霧の動きを見逃さないよう息を潜める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0181",
    "turn": 20,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今の影が消えた場所を見て。音が水滴に紛れているかもしれない。動くなら、私たちは一緒に動こう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0183",
    "turn": 20,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、今だ。俺から離れるな。影が消えた先を確かめるが、危なくなったらすぐ戻る」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0056"
    ]
  },
  {
    "id": "event_0185",
    "turn": 20,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "天井の亀裂から水滴が落ち、闇の奥で規則正しい音を刻む",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "memory",
    "op": "add",
    "path": "",
    "value": {
      "id": "memory_0020",
      "up_to_turn": 20,
      "text": "リナとカイは霧に覆われた地下ホームで、古い切符を握る子どもや改札跡の鉄柵に結ばれた色褪せたお守りを目にしてきた。二人は足音と霧の正体、追跡者の動きを確かめながら、案内板や水滴の音を手掛かりに互いに離れず進んでいる。追跡者は霧の奥に現れてから足を止め、二人を見据えている。現在、行き止まりと濃霧に退路を塞がれた二人は、柱の影に身を寄せ、水滴の音に紛れた気配と追跡者の影が消えた場所を探っている。"
    },
    "id": null,
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 21

### Status

applied

### Narration

リナはカイの袖を握ったまま、柱の影から窓口の奥へ懐中電灯を向けた。紙をめくるような気配が、水滴の音に紛れて一定の間隔で続いている。濃い霧も、行き止まりの先でこちらを見据える追跡者の影も、変化を見せなかった。

「カイ、窓口の奥から音がする。追跡者の動きがないか確かめながら、少しだけ近づいてみよう。危なくなったらすぐ戻るから」

カイはリナを背にかばい、足音を殺して柱の影を進んだ。「リナ、窓口の奥で音がした。俺が先に見る。合図するまで、ここを動くな」そう言って気配の方へ視線を凝らし、霧の向こうの追跡者へ声を投げた。「お前は誰の命令で、封印施設を探している？」返事はなく、窓口の奥ではなお紙をめくるような音だけが続いた。

### Reader-visible events

```json
[
  {
    "id": "event_0189",
    "turn": 21,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖を握ったまま、柱の影から窓口の奥へ懐中電灯を向ける。紙をめくる気配の間隔と、追跡者の影や霧の動きに変化がないかを慎重に聞き分ける。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0190",
    "turn": 21,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、窓口の奥から音がする。追跡者の動きがないか確かめながら、少しだけ近づいてみよう。危なくなったらすぐ戻るから」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0192",
    "turn": 21,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、窓口の奥から聞こえる紙をめくるような気配へ視線を向ける。足音を殺して柱の影を保ちながら、霧と追跡者の動きを警戒する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0193",
    "turn": 21,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、窓口の奥で音がした。俺が先に見る。合図するまで、ここを動くな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0195",
    "turn": 21,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "誰もいないはずの窓口の奥で、紙をめくるような気配がする",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0198",
    "turn": 21,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "追跡者の命令系統を問いただす",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0199",
    "turn": 21,
    "type": "action_outcome",
    "cause": "action:char_001:affordance_003",
    "text": "追跡者の命令系統を問いただす",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action_outcome": {
        "affordance_id": "affordance_003",
        "character_id": "char_001",
        "outcomes": [
          {
            "target": "threads",
            "op": "set",
            "path": "status",
            "id": "thread_002",
            "value": "resolved",
            "visibility": "reader"
          },
          {
            "target": "threads",
            "op": "add",
            "path": "",
            "id": null,
            "value": {
              "id": "thread_003",
              "description": "封印施設の鍵を握る人物は誰なのか",
              "status": "open",
              "related_event_ids": [],
              "notes": [],
              "opened_turn": 0
            },
            "visibility": "reader"
          },
          {
            "target": "quests",
            "op": "set",
            "path": "status",
            "id": "quest_001",
            "value": "advanced",
            "visibility": "reader"
          }
        ],
        "consumption": {
          "recurrence": "once",
          "exclusive": true,
          "fallback": true
        }
      },
      "accepted": true,
      "advancement": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0200",
    "turn": 21,
    "type": "thread_update",
    "cause": "authored:affordance_003",
    "text": "追跡者は誰の命令で封印施設を探しているのか",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "resolve",
      "thread_id": "thread_002",
      "authored": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0201",
    "turn": 21,
    "type": "thread_update",
    "cause": "authored:affordance_003",
    "text": "封印施設の鍵を握る人物は誰なのか",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "open",
      "thread_id": "thread_003",
      "authored": true
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "threads",
    "op": "set",
    "path": "status",
    "value": "resolved",
    "id": "thread_002",
    "visibility": "reader",
    "source_event": "event_0199"
  },
  {
    "target": "threads",
    "op": "add",
    "path": "",
    "value": {
      "id": "thread_003",
      "description": "封印施設の鍵を握る人物は誰なのか",
      "status": "open",
      "related_event_ids": [],
      "notes": [],
      "opened_turn": 21
    },
    "id": null,
    "visibility": "reader",
    "source_event": "event_0199"
  }
]
```

### Failure

none

## Turn 22

### Status

applied

### Narration

リナはカイの袖を握ったまま柱の影に身を寄せ、窓口の奥から続く紙をめくるような音と、霧の向こうの気配を交互に確かめた。濃い霧は背後の通路を塞ぎ、行き止まりの先では、足音を止めた追跡者がじっと二人を見据えている。リナはカイの合図を待ちながら、霧の流れにわずかな変化もないか目を凝らした。「わかった。合図があるまで動かない。でも、音の間隔と霧の流れは見ておくね。何か変わったらすぐ伝える」

カイはリナを背にかばったまま、窓口の奥へ半歩だけ進んだ。紙をめくる音の間隔と、霧の向こうに追跡者の影が戻っていないかを同時に確かめ、危険を感じればすぐ引き返せる姿勢を崩さない。「リナ、俺の後ろにいろ。音の正体だけ確かめる。何か見えたら、すぐに戻るぞ」そのとき、地上から遠雷のような街のざわめきが届いたが、音はたちまち霧に吸われて消えた。

### Reader-visible events

```json
[
  {
    "id": "event_0202",
    "turn": 22,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖を握ったまま柱の影に身を寄せ、窓口の奥から続く紙をめくるような音と、霧の向こうの気配を交互に確かめる。カイの合図を待ちながら、退路を塞ぐ濃霧にも注意を向ける。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0203",
    "turn": 22,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「わかった。合図があるまで動かない。でも、音の間隔と霧の流れは見ておくね。何か変わったらすぐ伝える」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0205",
    "turn": 22,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばったまま、窓口の奥へ半歩だけ進む。紙をめくる音の間隔と、霧の向こうに追跡者の影が戻っていないかを同時に確かめ、危険を感じた瞬間に引き返せる姿勢を保つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0206",
    "turn": 22,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろにいろ。音の正体だけ確かめる。何か見えたら、すぐに戻るぞ」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0208",
    "turn": 22,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "地上から遠雷のような街のざわめきが届き、すぐに霧へ吸われて消える",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 23

### Status

applied

### Narration

リナはカイの背後から離れず、懐中電灯の細い光を窓口の奥へ差し向けた。紙をめくる音は止んでいる。彼女は霧の渦の変化を見逃さぬよう目を凝らし、身に迫る異変があればすぐ伝えられるよう身構えた。「カイ、まだ動かないで。霧の流れが少し変わった気がする。音の正体を確かめるなら、私もすぐ後ろについていく」

### Reader-visible events

```json
[
  {
    "id": "event_0211",
    "turn": 23,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後から離れず、懐中電灯の光を窓口の奥へ細く差し向ける。紙をめくる音と霧の渦の変化を注意深く観察し、異変があればすぐにカイへ伝えられるよう身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0212",
    "turn": 23,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。霧の流れが少し変わった気がする。音の正体を確かめるなら、私もすぐ後ろについていく」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0214",
    "turn": 23,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、柱の影から窓口の奥を慎重に見据える。紙をめくる音が止まっている隙に、霧と追跡者の気配を探りながら、すぐ引き返せる位置を保つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0215",
    "turn": 23,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、まだ動くな。音が止まった。追跡者の位置を確かめてから、俺が合図する」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0217",
    "turn": 23,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 24

### Status

applied

### Narration

リナはカイの袖を離さぬまま、柱の影から追跡者の影が消えた方角と、線路の奥を交互に見つめた。懐中電灯の光を足元だけに絞り、霧の薄くなる場所を冷たい風の流れから探る。行き止まりの通路の先に逃げ場はなく、背後では濃い霧が満ちたままだった。「カイ、追跡者はまだ近くにいる。風の流れが変わった場所を探して、そこから抜け道を見つけよう」

カイはリナを背にかばい、追跡者の影が消えた柱へ視線を固定した。いつでも彼女を連れて窓口の奥から離れられるよう身構えながら、風の流れを確かめる。「リナ、風が線路の奥から来ている。追跡者が近づく前に、あの流れを確かめる。俺から離れるな」そのとき、線路の奥から冷たい風が吹き、油と土の匂いを運んできた。

### Reader-visible events

```json
[
  {
    "id": "event_0220",
    "turn": 24,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖を離さず、柱の影から追跡者の影が消えた方向と線路の奥を交互に見つめる。懐中電灯の光を足元だけに絞り、冷たい風の流れが霧のどこを薄くしているか探る。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0221",
    "turn": 24,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、追跡者はまだ近くにいる。風の流れが変わった場所を探して、そこから抜け道を見つけよう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0223",
    "turn": 24,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、追跡者の影が消えた柱の方へ視線を固定する。冷たい風の流れを確かめながら、いつでもリナを連れて窓口の奥から離れられるよう身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0224",
    "turn": 24,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、風が線路の奥から来ている。追跡者が近づく前に、あの流れを確かめる。俺から離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0226",
    "turn": 24,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "冷たい風が線路の奥から吹き、油と土の匂いを運んでくる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 25

### Status

applied

### Narration

リナは懐中電灯の光を窓口の奥へ細く伸ばしたまま、カイの袖を握り直した。紙をめくるような気配の間隔と霧の流れを見比べ、追跡者に気づかれぬよう身を低くする。行き止まりの先は暗く、背後では濃い霧が退路を塞いでいた。追跡者は足音を止め、ただ二人を見据えている。

「カイ、音がまた聞こえた。窓口の奥からだと思う。でも、追跡者が近くにいるなら、無理に進まず風の流れを使える場所を探そう」リナが囁くと、カイは彼女を背にかばい、窓口の奥へ耳を澄ました。紙をめくるような気配は、誰もいないはずの奥からなお続いている。追跡者の影と濃霧の動きを警戒しながら、カイは風の流れが続く線路の奥を慎重に見極めた。「リナ、俺の後ろから離れるな。音の正体を確かめる。危なくなったら、すぐに戻るぞ」二人は封印施設の鍵の手がかりを求め、逃げ場のない通路の奥へ意識を集中させた。

### Reader-visible events

```json
[
  {
    "id": "event_0230",
    "turn": 25,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯の光を窓口の奥へ細く向けたまま、カイの袖を握り直す。紙をめくる気配の間隔と霧の流れを見比べ、追跡者に気づかれないよう身を低く保つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0231",
    "turn": 25,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、音がまた聞こえた。窓口の奥からだと思う。でも、追跡者が近くにいるなら、無理に進まず風の流れを使える場所を探そう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0233",
    "turn": 25,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばいながら、窓口の奥から聞こえる紙をめくるような気配に耳を澄ます。追跡者の影と濃霧の動きを警戒し、風の流れが続く線路の奥へ進めるか慎重に見極める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0234",
    "turn": 25,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろから離れるな。音の正体を確かめる。危なくなったら、すぐに戻るぞ」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0236",
    "turn": 25,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "誰もいないはずの窓口の奥で、紙をめくるような気配がする",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0240",
    "turn": 25,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "封印施設の鍵の手がかりを探る",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0241",
    "turn": 25,
    "type": "action_outcome",
    "cause": "action:char_001:affordance_004",
    "text": "封印施設の鍵の手がかりを探る",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action_outcome": {
        "affordance_id": "affordance_004",
        "character_id": "char_001",
        "outcomes": [
          {
            "target": "threads",
            "op": "set",
            "path": "status",
            "id": "thread_003",
            "value": "resolved",
            "visibility": "reader"
          },
          {
            "target": "threads",
            "op": "add",
            "path": "",
            "id": null,
            "value": {
              "id": "thread_004",
              "description": "駅の最深部に残された封印の意味",
              "status": "open",
              "related_event_ids": [],
              "notes": [],
              "opened_turn": 0
            },
            "visibility": "reader"
          },
          {
            "target": "quests",
            "op": "set",
            "path": "status",
            "id": "quest_001",
            "value": "advanced",
            "visibility": "reader"
          }
        ],
        "consumption": {
          "recurrence": "once",
          "exclusive": true,
          "fallback": true
        }
      },
      "accepted": true,
      "advancement": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0242",
    "turn": 25,
    "type": "thread_update",
    "cause": "authored:affordance_004",
    "text": "封印施設の鍵を握る人物は誰なのか",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "resolve",
      "thread_id": "thread_003",
      "authored": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0243",
    "turn": 25,
    "type": "thread_update",
    "cause": "authored:affordance_004",
    "text": "駅の最深部に残された封印の意味",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "open",
      "thread_id": "thread_004",
      "authored": true
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "threads",
    "op": "set",
    "path": "status",
    "value": "resolved",
    "id": "thread_003",
    "visibility": "reader",
    "source_event": "event_0241"
  },
  {
    "target": "threads",
    "op": "add",
    "path": "",
    "value": {
      "id": "thread_004",
      "description": "駅の最深部に残された封印の意味",
      "status": "open",
      "related_event_ids": [],
      "notes": [],
      "opened_turn": 25
    },
    "id": null,
    "visibility": "reader",
    "source_event": "event_0241"
  },
  {
    "target": "quests",
    "op": "set",
    "path": "status",
    "value": "advanced",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0230",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0231",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0233",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0234",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0236",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0240",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0241",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 26

### Status

applied

### Narration

リナは息を殺し、カイの袖を握ったまま柱の影から動かなかった。足音の止まった霧の奥を、懐中電灯で照らさずに見つめる。「カイ、今の足音は近い。まだ動かずに、風の流れが変わるまで待とう」

カイはリナを背にかばい、足音の消えた霧の奥ではなく、冷たい風が流れ込む線路脇の隙間へ慎重に身を寄せた。水滴の音に紛れる窓口の奥の気配を探りながら、退路になりそうな場所を確かめる。「リナ、追跡者は動いていない。今のうちに風の通り道を探す。俺のそばを離れるな」その直後、霧の奥で足音が一度だけ響いた。二人が耳を澄ますと、それもまた途絶えた。

### Reader-visible events

```json
[
  {
    "id": "event_0244",
    "turn": 26,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは息を殺し、カイの袖を握ったまま柱の影から動かず、足音が止まった霧の奥を懐中電灯で照らさずに見つめる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0245",
    "turn": 26,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今の足音は近い。まだ動かずに、風の流れが変わるまで待とう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0247",
    "turn": 26,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、足音が消えた霧の奥ではなく、冷たい風が流れ込む線路脇の隙間へ慎重に身を寄せる。水滴の音に紛れるよう、窓口の奥の気配を探りながら退路になりそうな場所を確認する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0248",
    "turn": 26,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、追跡者は動いていない。今のうちに風の通り道を探す。俺のそばを離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0250",
    "turn": 26,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "霧の奥で足音が一度だけ響き、耳を澄ますと止む",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "quests",
    "op": "set",
    "path": "status",
    "value": "advanced",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0244",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0245",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0247",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0248",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0250",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 27

### Status

applied

### Narration

リナはカイの袖を離さず、柱の影から錆びた案内板と線路脇を流れる風を注意深く見比べた。懐中電灯は消したまま、二人は身を低くしている。通路の先は行き止まり、背後には濃い霧が満ちていた。やがて錆びた案内板が軋み、読めない駅名が霧の中で揺れる。その向きと風の流れは、どうしても噛み合わなかった。

「案内板の揺れ方と風の向きが違う。線路の奥に、別の通路か空間があるのかもしれない。カイ、音を立てずに少しだけ確かめよう」

カイはリナを背にかばい、案内板の揺れと霧の流れを慎重に見比べながら、風の通り道へ少しずつ身を移した。「リナ、まだ動くな。案内板の向きと風の流れを見て、抜け道を探す。追跡者には気づかれるな」追跡者は足音を止めたまま、じっとこちらを見据えている。二人はその視線を刺激せず、駅の最深部へ続く気配を探った。

### Reader-visible events

```json
[
  {
    "id": "event_0253",
    "turn": 27,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖を離さず、柱の影から錆びた案内板と線路脇の風の流れを注意深く見比べる。追跡者を刺激しないよう、懐中電灯は消したまま身を低く保つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0254",
    "turn": 27,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「案内板の揺れ方と風の向きが違う。線路の奥に、別の通路か空間があるのかもしれない。カイ、音を立てずに少しだけ確かめよう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0256",
    "turn": 27,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばったまま、錆びた案内板の揺れと霧の流れを慎重に見比べる。追跡者を刺激しないよう、風の通り道へ少しずつ身を移し、最深部へ続く気配を探る。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0257",
    "turn": 27,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、まだ動くな。案内板の向きと風の流れを見て、抜け道を探す。追跡者には気づかれるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0259",
    "turn": 27,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "錆びた案内板が軋み、読めない駅名が霧の中に揺れる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "quests",
    "op": "set",
    "path": "status",
    "value": "advanced",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0253",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0254",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0256",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0257",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0259",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## Turn 28

### Status

applied

### Narration

リナはカイの袖を握り直し、追跡者の影が消えた柱の方角を目で追った。懐中電灯は消えたまま、風の通り道と最深部へ続く階段の位置を慎重に確かめる。背後では濃い霧が行き止まりの通路を埋め、逃げ道の輪郭さえ曖昧にしていた。

カイはリナを背にかばい、柱の影から動かずに追跡者の影が消えた方向を見張った。片手で線路脇の風の通り道を示し、霧が濃くなった隙に進めるよう身構える。その先で、最深部へ続く階段の闇が、今夜はいつもより深く見えていた。

### Reader-visible events

```json
[
  {
    "id": "event_0263",
    "turn": 28,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖を握り直し、追跡者の影が消えた柱の方角を目で追う。懐中電灯は消したまま、風の通り道と最深部へ続く階段の位置を慎重に確かめる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0075"
    ]
  },
  {
    "id": "event_0265",
    "turn": 28,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、柱の影から動かずに追跡者の影が消えた方向を見張る。片手で線路脇の風の通り道を示し、霧が濃くなった隙に進めるよう身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0076"
    ]
  },
  {
    "id": "event_0267",
    "turn": 28,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "最深部へ続く階段の闇が、今夜はいつもより深く見える",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

none

## Turn 29

### Status

applied

### Narration

リナはカイの袖を握ったまま、冷たい風に混じる油と土の匂いを確かめた。通路の先は行き止まりで、背後には濃い霧が満ちている。足音を止めた追跡者は、逃げ場を塞ぐようにじっと二人を見据えていた。それでもリナは線路脇の風の通り道へ身を寄せ、最深部へ続く階段の位置を見失わないよう、霧の深まりに紛れて慎重に進んだ。「カイ、風が線路の奥から来ている。あの階段の先に空間があるかもしれない。霧が深くなる今なら、音を立てずに少しだけ進めそう」

### Reader-visible events

```json
[
  {
    "id": "event_0271",
    "turn": 29,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖を握ったまま、冷たい風に混じる油と土の匂いを確かめる。追跡者の気配を警戒しつつ、霧が濃くなった隙に線路脇の風の通り道へ身を寄せ、最深部へ続く階段の位置を見失わないよう進む。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0272",
    "turn": 29,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、風が線路の奥から来ている。あの階段の先に空間があるかもしれない。霧が深くなる今なら、音を立てずに少しだけ進めそう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": []
  },
  {
    "id": "event_0274",
    "turn": 29,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、冷たい風が吹き込む線路脇の隙間へ身を寄せる。油と土の匂いの流れを確かめ、追跡者に気づかれないよう最深部へ続く階段の方角を探る。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0275",
    "turn": 29,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、風は線路の奥から来ている。俺の後ろを離れるな。霧が濃くなったら、階段の方へ進む」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": []
  },
  {
    "id": "event_0277",
    "turn": 29,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "冷たい風が線路の奥から吹き、油と土の匂いを運んでくる",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0280",
    "turn": 29,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "封印の意味を追跡者に問い返す",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": null
    },
    "roll_ids": []
  },
  {
    "id": "event_0281",
    "turn": 29,
    "type": "action_outcome",
    "cause": "action:char_001:affordance_005",
    "text": "封印の意味を追跡者に問い返す",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action_outcome": {
        "affordance_id": "affordance_005",
        "character_id": "char_001",
        "outcomes": [
          {
            "target": "threads",
            "op": "set",
            "path": "status",
            "id": "thread_004",
            "value": "resolved",
            "visibility": "reader"
          },
          {
            "target": "threads",
            "op": "add",
            "path": "",
            "id": null,
            "value": {
              "id": "thread_005",
              "description": "霧の夜に足音が響く理由",
              "status": "open",
              "related_event_ids": [],
              "notes": [],
              "opened_turn": 0
            },
            "visibility": "reader"
          },
          {
            "target": "quests",
            "op": "set",
            "path": "status",
            "id": "quest_001",
            "value": "advanced",
            "visibility": "reader"
          }
        ],
        "consumption": {
          "recurrence": "once",
          "exclusive": true,
          "fallback": true
        }
      },
      "accepted": true,
      "advancement": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0282",
    "turn": 29,
    "type": "thread_update",
    "cause": "authored:affordance_005",
    "text": "駅の最深部に残された封印の意味",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "resolve",
      "thread_id": "thread_004",
      "authored": true
    },
    "roll_ids": []
  },
  {
    "id": "event_0283",
    "turn": 29,
    "type": "thread_update",
    "cause": "authored:affordance_005",
    "text": "霧の夜に足音が響く理由",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "action": "open",
      "thread_id": "thread_005",
      "authored": true
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "threads",
    "op": "set",
    "path": "status",
    "value": "resolved",
    "id": "thread_004",
    "visibility": "reader",
    "source_event": "event_0281"
  },
  {
    "target": "threads",
    "op": "add",
    "path": "",
    "value": {
      "id": "thread_005",
      "description": "霧の夜に足音が響く理由",
      "status": "open",
      "related_event_ids": [],
      "notes": [],
      "opened_turn": 29
    },
    "id": null,
    "visibility": "reader",
    "source_event": "event_0281"
  }
]
```

### Failure

none

## Turn 30

### Status

applied

### Narration

古い電球がどこかで明滅し、そのたびにホームの影が伸び縮みした。カイは一瞬だけそちらへ目を向けると、すぐにリナを背にかばい直す。水滴の規則正しい音に耳を澄ませ、階段の方角から別の気配がないか探った。だが、追跡者は足音を止めたまま、濃霧の向こうから二人をじっと見据えている。

### Reader-visible events

```json
[
  {
    "id": "event_0286",
    "turn": 30,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは明滅する電球に一瞬だけ目を向け、すぐにリナを背にかばい直す。水滴の規則正しい音に紛れて、階段の方角から別の気配がないか耳を澄ます。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0082"
    ]
  },
  {
    "id": "event_0288",
    "turn": 30,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "どこかで古い電球が明滅し、ホームの影が伸び縮みする",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "target_id": null
    },
    "roll_ids": []
  }
]
```

### Reader-visible state/delta

```json
[
  {
    "target": "memory",
    "op": "add",
    "path": "",
    "value": {
      "id": "memory_0030",
      "up_to_turn": 30,
      "text": "リナとカイは霧に覆われた地下ホームで、古い切符を握る子どもや改札跡の鉄柵に結ばれた色褪せたお守りを目にしてきた。二人は足音と霧の正体、追跡者の動きを確かめながら、案内板や水滴の音、線路の奥から吹く風を手掛かりに互いに離れず進んでいる。追跡者は霧の奥で足を止め、行き止まりと濃霧に挟まれた二人を見据えている。明滅する古い電球がホームの影を揺らす中、カイはリナを背にかばい、階段の方角から別の気配がないか耳を澄ませている。"
    },
    "id": null,
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

none

## 機械証跡

- metrics_json: sandbox/20260727-issue086-r4-hardening/metrics.json
- leak_scan: PASS — critical/high findings 0
- resume: PASS — checkpoint turn 15, resumed turn 16
- provider_failures: none
- narrator: binding `narrator`, 30 LLM turns, 31 requests, fallback none
- elapsed: 868.476s / 1200s
- LLM calls: 90 / 100（retry込みrequest数 91）
- total tokens: 487284 / 700000
- cost_usd: 未価格モデルのため参考値のみ

## 結論

- failed_items: none
- rerun_required: NO
- notes: 機械SLOは全項目PASS。人手rubric R1–R8は別途判定する。
