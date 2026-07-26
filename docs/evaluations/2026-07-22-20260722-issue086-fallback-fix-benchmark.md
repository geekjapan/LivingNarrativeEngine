# 実LLM benchmark転記 — 20260722-issue086-fallback-fix

- gate: `1.0`
- result: `FAIL`
- started_at: 2026-07-22T00:41:14+09:00
- finished_at: 2026-07-22T00:58:45+09:00
- git_revision: `7f62ecce83e3cc7ee5d85fb1ed1c469719f085a2`
- implementation_diff_sha256: `fc6f460d318599d8e4b725017c2355ff2a3aacda33b3d43f5a98d86165c2803f`
- sample: `mist_station`
- seed: `issue-085-mist-station-v1`
- provider: `openai-compatible`
- model: `cx/gpt-5.6-luna-low`
- completed_turns: 30 / 30
- benchmark_json: `sandbox/20260722-issue086-fallback-fix/benchmark.json`
- provider_failure: none
- narrator: 30 calls | LLM turns: 29 | fallback: turn 21 StructuredOutputError
- resume: turn 15 → turn 16 `PASS`

## Turns

## Turn 01

### Status

`applied`

### Narration

「あなた、そこで何をしているの？　足音の主を知ってるなら、教えて」リナの声が、濃い霧の中へ静かに沈んだ。

カイはリナの前に立ち、霧の向こうから規則正しく近づく足音へ身を向けた。子どもから目を離さず、いつでもリナを連れて退けるよう足場を確かめる。「リナ、俺の後ろにいろ。あの足音……近づいてくるまで動くな」静かな時間が流れ、ホームの縁では霧がゆっくりと渦を巻いていた。やがてその向こうに、古い切符を握った子どもの姿が現れ、こちらを見つめた。

### Reader-visible events

```json
[
  {
    "id": "event_0001",
    "turn": 1,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「あなた、そこで何をしているの？　足音の主を知ってるなら、教えて」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0004"
    ]
  },
  {
    "id": "event_0003",
    "turn": 1,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ち、霧の向こうから近づく足音へ身を向ける。子どもから目を離さず、いつでもリナを連れて退けるよう足場を確かめる。",
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
    "id": "event_0004",
    "turn": 1,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろにいろ。あの足音……近づいてくるまで動くな」",
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

`none`

## Turn 02

### Status

`applied`

### Narration

リナはカイの背後から半歩だけ身を乗り出し、懐中電灯の光を改札跡の鉄柵へ向けた。濃い霧の中で、誰かが結んだ色褪せたお守りの紐がかすかに揺れている。彼女は足音への警戒を解かないまま、紐と子どもが握る古い切符のあいだに共通する印がないか、目を凝らした。

「カイ、あのお守りを見て。あなたは何か知ってる？　それから……その切符、どこで手に入れたの？」

カイはなおもリナを背後にかばい、霧と子どもの様子を警戒しながら、お守りの紐へ視線を移した。「リナ、ここを動くな。あのお守りを確認してくる。足音が近づいたら、すぐ俺を呼べ」規則正しい足音は、静かなホームの向こうから変わらず近づいていた。

### Reader-visible events

```json
[
  {
    "id": "event_0011",
    "turn": 2,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後から半歩だけ身を乗り出し、改札跡の鉄柵で揺れる色褪せたお守りの紐を懐中電灯で照らす。子どもと近づく足音への警戒は解かず、紐と古い切符の間に共通する印がないか観察する。",
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
    "id": "event_0012",
    "turn": 2,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、あのお守りを見て。あなたは何か知ってる？　それから……その切符、どこで手に入れたの？」",
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
    "id": "event_0014",
    "turn": 2,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背後にかばったまま、霧と子どもの様子を警戒し、改札跡の鉄柵で揺れる色褪せたお守りの紐へ視線を移す。",
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
    "id": "event_0015",
    "turn": 2,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、ここを動くな。あのお守りを確認してくる。足音が近づいたら、すぐ俺を呼べ」",
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
    "id": "event_0017",
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

`none`

## Turn 03

### Status

`applied`

### Narration

「カイ、霧が濃すぎる。お守りを調べたら、すぐ戻ってきて。足音が近づいてる」リナの声が、白く閉ざされていくホームに落ちた。改札跡の鉄柵では、色褪せたお守りがかすかに揺れ、古い切符との共通点を探る手がかりを残していた。どこからともなく響く規則正しい足音は、ひとつ、またひとつと近づいてくる。

カイは霧の向こうへ向かいかけたが、すぐにリナへ視線を戻した。「お守りのことは、まだはっきりしない。だが、この足音には覚えがある気がする。リナ、俺から離れるな」その直後、霧が一段と濃くなり、数歩先の視界さえ白く閉ざされた。足音だけが、二人のいる場所へ確実に迫っていた。

### Reader-visible events

```json
[
  {
    "id": "event_0020",
    "turn": 3,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、霧が濃すぎる。お守りを調べたら、すぐ戻ってきて。足音が近づいてる」",
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
    "text": "「お守りのことは、まだはっきりしない。だが、この足音には覚えがある気がする。リナ、俺から離れるな」",
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

`none`

## Turn 04

### Status

`applied`

### Narration

「わかった、離れない。あの案内板、駅名は読めないけど……足音が来る前に、出口の手がかりを探そう」リナはそう答え、カイのそばを離れなかった。

カイはリナの前に立ったまま、錆びた案内板と霧の奥へ交互に視線を向けた。規則正しく近づく足音の間隔を測りながら、二人は改札跡の鉄柵のそばへと下がる。そのとき、錆びた案内板が軋み、読めない駅名が濃い霧の中で揺れた。

### Reader-visible events

```json
[
  {
    "id": "event_0029",
    "turn": 4,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「わかった、離れない。あの案内板、駅名は読めないけど……足音が来る前に、出口の手がかりを探そう」",
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
    "id": "event_0031",
    "turn": 4,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ったまま、錆びた案内板と霧の奥へ交互に視線を向ける。足音の間隔を測りながら、リナを連れて改札跡の鉄柵のそばへ下がる。",
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
    "id": "event_0033",
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
    "value": "event_0029",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0031",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0033",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

`none`

## Turn 05

### Status

`applied`

### Narration

リナは懐中電灯の光を天井の亀裂へ向けた。そこから落ちる水滴は、一定の間隔で静寂を打ち、霧の奥から近づく足音もまた、乱れのない律動を刻んでいる。彼女はカイのそばを離れず、二つの音を慎重に聞き比べながら、霧の向こうへ意識を凝らした。「カイ、水滴の音……足音と何か関係があるかもしれない。少しだけ聞かせて。危なくなったら、すぐ戻ろう」

カイはリナを背後にかばい、片手を伸ばしていつでも彼女を連れて退けるよう身構えた。二人は水滴の間隔と闇の奥の足音を重ねて聞き分ける。濃い霧に包まれたホームでは、規則正しい音だけが、近づく気配の輪郭をわずかに浮かび上がらせていた。

### Reader-visible events

```json
[
  {
    "id": "event_0036",
    "turn": 5,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を天井の亀裂へ向け、水滴の落ちる間隔と闇の奥から響く足音のリズムを慎重に聞き比べる。カイのそばを離れず、霧の向こうの気配にも意識を向けた。",
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
    "id": "event_0037",
    "turn": 5,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、水滴の音……足音と何か関係があるかもしれない。少しだけ聞かせて。危なくなったら、すぐ戻ろう」",
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
    "id": "event_0039",
    "turn": 5,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背後にかばい、天井から落ちる水滴の間隔と霧の奥の足音を重ねて聞き分ける。片手を伸ばし、いつでもリナを連れて退けるよう身構える。",
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
    "id": "event_0041",
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

`none`

## Turn 06

### Status

`applied`

### Narration

リナは懐中電灯を足元へ落とし、カイの袖をつかんだまま、天井の亀裂から落ちる水滴と霧の奥から響く足音の間隔を、もう一度慎重に聞き比べた。濃い霧の向こう、規則正しい音が近づいてくる方向から目を離さず、足元と鉄柵の周囲に退路を探る。暗がりでは、水滴が一定の間隔で音を刻み続けていた。

### Reader-visible events

```json
[
  {
    "id": "event_0044",
    "turn": 6,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を足元に落とし、カイの袖をつかんだまま、水滴と足音の間隔をもう一度慎重に聞き比べる。足音の主が近づいている方向からは目を離さず、退路を確かめる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0020"
    ]
  },
  {
    "id": "event_0046",
    "turn": 6,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背後にかばい、鉄柵のそばから動かずに霧の奥の足音と水滴の間隔を聞き分ける。足音が近づけば、すぐにリナを連れて退けるよう身構えた。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0021"
    ]
  },
  {
    "id": "event_0048",
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

`none`

## Turn 07

### Status

`applied`

### Narration

リナは足音の方向から目を離さず、足元に落ちていた懐中電灯を拾い上げた。光を向けても、濃い霧の向こうにあるものは捉えられない。彼女はカイの袖を強くつかみ、鉄柵を背にしたまま、規則正しく近づいてくる足音から距離を取れる退路へ、慎重に下がった。

「リナ、俺の後ろから離れるな。足音が近い。見えなくても、近づかれたらすぐ走る」

その直後、霧が一段と濃くなった。数歩先の視界さえ白く閉ざされ、足音だけが、変わらぬ間隔で近づき続けていた。

### Reader-visible events

```json
[
  {
    "id": "event_0051",
    "turn": 7,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは足音の方向から目を離さず、落とした懐中電灯を拾い上げる。カイの袖を強くつかみ、鉄柵を背にしたまま、足音から距離を取れる退路へ慎重に下がる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0024"
    ]
  },
  {
    "id": "event_0053",
    "turn": 7,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろから離れるな。足音が近い。見えなくても、近づかれたらすぐ走る」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0025"
    ]
  },
  {
    "id": "event_0055",
    "turn": 7,
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
  }
]
```

### Failure

`none`

## Turn 08

### Status

`applied`

### Narration

リナは懐中電灯の光を追跡者の影へ向けたまま、カイの袖をつかんでいた。背後に満ちる濃霧へ慎重に視線を走らせても、退路は見えない。追跡者は足音を止め、行き止まりの通路でじっと二人を見据えている。「カイ、動かないで。……あなたは、私たちを追ってきたの？」

「リナ、俺から離れるな。動くなら俺が合図する。あれが近づいたら、隙を見て走る」その直後、遠くで金属を引きずるような低い響きが起こり、霧に閉ざされた駅の奥へ不穏に広がった。二人の前には追跡者、背後には濃霧があり、逃げ場のない緊張だけが通路を満たしていた。

### Reader-visible events

```json
[
  {
    "id": "event_0063",
    "turn": 8,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を追跡者の影へ向け、カイの袖をつかんだまま、背後の濃霧に退路がないか慎重に確かめる。",
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
    "id": "event_0064",
    "turn": 8,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、動かないで。……あなたは、私たちを追ってきたの？」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_004"
    },
    "roll_ids": []
  },
  {
    "id": "event_0066",
    "turn": 8,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺から離れるな。動くなら俺が合図する。あれが近づいたら、隙を見て走る」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0029"
    ]
  },
  {
    "id": "event_0068",
    "turn": 8,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "遠くで不穏な物音がする。金属を引きずるような、低い響き",
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

`none`

## Turn 09

### Status

`applied`

### Narration

「カイ、まだ動かないで。霧の流れが変わったら、私が先に知らせるから」リナの声が、行き止まりの通路に低く落ちた。カイは彼女を背後にかばったまま、霧の渦と線路の奥を交互に見据える。止まった足音の隙に、彼女を逃がせる位置を探しながら、身を固くして構えていた。対峙する追跡者は動かず、ただ二人をじっと見つめている。

静かな時間が、逃げ場のない空間に引き延ばされていく。ホームの縁では濃い霧がゆっくりと渦を巻き、背後の退路を塞いだまま、かすかな流れだけを変えていた。

### Reader-visible events

```json
[
  {
    "id": "event_0073",
    "turn": 9,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。霧の流れが変わったら、私が先に知らせるから」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0032"
    ]
  },
  {
    "id": "event_0075",
    "turn": 9,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背後にかばったまま、霧の渦と線路の奥を交互に見据える。足音が止まっている隙に、彼女を逃がせる位置を探して身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0033"
    ]
  },
  {
    "id": "event_0077",
    "turn": 9,
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

`none`

## Turn 10

### Status

`applied`

### Narration

リナは懐中電灯の光を低く保ったまま、カイの袖をつかみ、霧の中で揺れる人影から目を離さずに身を固めた。カイは彼女を背後にかばい、線路側へ半歩踏み出す。触れずにその体で進路を隠しながら、霧の奥の追跡者を見据えた。どこかで古い電球が明滅し、ホームの影が伸び縮みする。そのたび、霧の奥の人影が揺れ、規則正しく響いていた足音が、唐突に途切れた。

通路の先は行き止まりだった。背後には濃い霧が満ち、逃げ場を塞いでいる。追跡者は足音を止めたまま、じっとこちらを見据えていた。ホームの縁で霧が静かに渦巻き、明滅する光がその姿を白く切り取っては、また影の中へ沈めていった。

### Reader-visible events

```json
[
  {
    "id": "event_0080",
    "turn": 10,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯の光を低く保ち、カイの袖をつかんだまま、霧の中の人影から目を離さずに身を固める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0036"
    ]
  },
  {
    "id": "event_0082",
    "turn": 10,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背後にかばい、線路側へ半歩踏み出して霧の奥の人影を見据える。逃げ道を塞がれないよう、彼女には触れずに自分の体で進路を隠す。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0037"
    ]
  },
  {
    "id": "event_0084",
    "turn": 10,
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
  },
  {
    "id": "event_0086",
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
      "roll_id": "roll_0035",
      "target_id": null
    },
    "roll_ids": [
      "roll_0035"
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
      "text": "カイとリナは、霧に覆われた地下駅で足音の主を追い、霧の向こうから現れた古い切符を握る子どもや、改札跡の色褪せたお守りを手がかりに進んできた。霧は濃くなり、錆びた案内板や天井から落ちる水滴を調べても、出口や足音の正体は明らかになっていない。二人は足音と水滴の規則性を警戒しながら退路を探していたが、霧の奥の人影が近づき、足音が止まった。現在、通路の先は行き止まりで背後は濃霧に塞がれ、カイがリナをかばいながら追跡者と対峙している。"
    },
    "id": null,
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

`none`

## Turn 11

### Status

`applied`

### Narration

「カイ、離れないで。見えなくても、何か動いたらすぐ教えて。私たちはここで無理に進まず、霧が薄くなる隙を待とう」リナは袖をつかんだまま、濃霧の向こうを見つめた。

「リナ、俺の後ろにいろ。足音が聞こえたら、俺の合図で走る」カイは彼女を背後にかばい、線路側へ身構えた。だが、追跡者は動かない。次の瞬間、霧が一段と濃くなり、数歩先の視界さえ白く閉ざされた。行き止まりと霧の壁の間で、二人は息を潜め、足音の再開を待った。

### Reader-visible events

```json
[
  {
    "id": "event_0089",
    "turn": 11,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、離れないで。見えなくても、何か動いたらすぐ教えて。私たちはここで無理に進まず、霧が薄くなる隙を待とう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0040"
    ]
  },
  {
    "id": "event_0091",
    "turn": 11,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろにいろ。足音が聞こえたら、俺の合図で走る」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0041"
    ]
  },
  {
    "id": "event_0093",
    "turn": 11,
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

`none`

## Turn 12

### Status

`applied`

### Narration

リナは懐中電灯を消さず、光を足元へ落としたまま、カイの背中から離れなかった。線路の奥へ吹く冷たい風が、油と土の匂いを運んでくる。彼女は風と霧の流れを慎重に見極めようとし、カイもまた彼女を背後にかばいながら、追跡者の気配に備えて身構えた。濃霧の向こうでは、止まった足音の主がじっとこちらを見据えている。

### Reader-visible events

```json
[
  {
    "id": "event_0097",
    "turn": 12,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を消さずに光を足元へ落とし、カイの背中から離れないまま、線路の奥へ吹く風と霧の動きを慎重に見極めようとする。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0045"
    ]
  },
  {
    "id": "event_0099",
    "turn": 12,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背後にかばい、線路の奥から吹く冷たい風と霧の流れを確かめながら、追跡者の気配に備えて身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0046"
    ]
  },
  {
    "id": "event_0101",
    "turn": 12,
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

`none`

## Turn 13

### Status

`applied`

### Narration

リナは懐中電灯を追跡者へ向けず、足元を照らしたまま、カイの背中に触れて霧の奥の姿を見据えた。「そこで止まって。あなたは誰？　私たちを追ってきた理由を話して」声が行き止まりの通路に張りつめる。カイは彼女をかばうように立ち、「リナ、俺から離れるな。合図を出すまで動くな」と低く告げた。

そのとき、誰もいないはずの窓口の奥で、紙をめくるような気配がした。背後を満たす濃い霧が揺れ、線路の奥から冷たい風が吹き抜ける。やがて霧が裂け、その向こうにいた追跡者が、二人の前へ姿を現した。

### Reader-visible events

```json
[
  {
    "id": "event_0105",
    "turn": 13,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を追跡者へ向けるのではなく足元に保ち、カイの背中に触れたまま、霧の奥の姿を見据える。",
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
    "id": "event_0106",
    "turn": 13,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「そこで止まって。あなたは誰？　私たちを追ってきた理由を話して」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_004"
    },
    "roll_ids": []
  },
  {
    "id": "event_0108",
    "turn": 13,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺から離れるな。合図を出すまで動くな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0049"
    ]
  },
  {
    "id": "event_0110",
    "turn": 13,
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
    "id": "event_0112",
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
      "roll_id": "roll_0048",
      "target_id": null
    },
    "roll_ids": [
      "roll_0048"
    ]
  }
]
```

### Reader-visible state/delta

```json
[]
```

### Failure

`none`

## Turn 14

### Status

`applied`

### Narration

リナはカイの背中に身を寄せたまま、懐中電灯の光を追跡者の足元へ向けた。濃霧に遮られた背後の通路へ慎重に視線を走らせ、逃げ道を確かめる。追跡者は足音を止め、行き止まりの先で二人をじっと見据えていた。

「カイ、合図を待つ。でも、あなたも動かないで。あなたは誰なの？　私たちを追う理由を答えて」リナが問いかけると、カイは背中越しに低く告げた。「リナ、俺の背中から離れるな。お前が動くなら、俺が合図する」そのとき、地上から遠雷のような街のざわめきが届いたが、音はすぐに霧へ吸い込まれ、行き止まりの静けさだけが残った。

### Reader-visible events

```json
[
  {
    "id": "event_0115",
    "turn": 14,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背中に身を寄せ、懐中電灯を追跡者の足元へ向けたまま、濃霧に遮られた退路を慎重に確かめる。",
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
    "id": "event_0116",
    "turn": 14,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、合図を待つ。でも、あなたも動かないで。あなたは誰なの？　私たちを追う理由を答えて」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_004"
    },
    "roll_ids": []
  },
  {
    "id": "event_0118",
    "turn": 14,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の背中から離れるな。お前が動くなら、俺が合図する」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0052"
    ]
  },
  {
    "id": "event_0120",
    "turn": 14,
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

`none`

## Turn 15

### Status

`applied`

### Narration

「……答えろ。近づくなら、俺が止める。リナには指一本触れさせない」カイは低く言い放ち、リナを背中で覆うように立った。霧に塞がれた背後を一度だけ確かめると、追跡者との距離を保ったまま身構える。行き止まりの通路に、逃げ場はなかった。

地上から遠雷のような街のざわめきが届いた。だがその音は、二人と追跡者のあいだに張りつめた沈黙へ触れることなく、すぐに濃霧へ吸われて消えた。追跡者は足音を止めたまま、じっとこちらを見据えている。

### Reader-visible events

```json
[
  {
    "id": "event_0123",
    "turn": 15,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「……答えろ。近づくなら、俺が止める。リナには指一本触れさせない」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_004"
    },
    "roll_ids": [
      "roll_0055",
      "roll_0056"
    ]
  },
  {
    "id": "event_0125",
    "turn": 15,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背中で覆うように立ち、霧に塞がれた背後を一度だけ確認してから、追跡者との距離を保ったまま身構える。",
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
    "id": "event_0127",
    "turn": 15,
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

`none`

## Turn 16

### Status

`applied`

### Narration

「カイ、まだ動かないで。水滴の音……何かの合図みたい。追跡者にも聞こえているのか、確かめたい」リナの声が、霧に閉ざされた行き止まりへ押し戻された。カイは視線を追跡者から外さず、リナを背にかばったまま低く答える。「リナ、俺の合図まで動くな。あの影が近づくなら、俺が前に出る」

そのとき、天井の亀裂から水滴が落ちた。ひとつ、またひとつ。闇の奥で、規則正しい音が刻まれていく。足音を止めた追跡者は身じろぎもせず、濃霧の向こうから二人をじっと見据えていた。前は行き止まり、後ろは霧。水滴の音だけが、逃げ場のない通路に残った。

### Reader-visible events

```json
[
  {
    "id": "event_0130",
    "turn": 16,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。水滴の音……何かの合図みたい。追跡者にも聞こえているのか、確かめたい」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0060"
    ]
  },
  {
    "id": "event_0132",
    "turn": 16,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の合図まで動くな。あの影が近づくなら、俺が前に出る」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0061"
    ]
  },
  {
    "id": "event_0134",
    "turn": 16,
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

`none`

## Turn 17

### Status

`applied`

### Narration

リナはカイの背後から慎重に身を乗り出し、懐中電灯の光を錆びた案内板へ向けた。読めない駅名が水滴の規則正しい音に合わせるように揺れ、彼女は追跡者から目を離さないまま、低く告げる。「カイ、あの案内板……音に合わせて揺れているように見える。追跡者を刺激しないように、まず音の正体を確かめよう」

カイはリナを背中でかばい、案内板と追跡者を交互に見据えた。水滴の音を数えるように耳を澄ましながら、足元だけを慎重に確かめ、霧に塞がれた退路を探る。やがて錆びた案内板が軋み、読めない駅名が濃霧の中で不気味に揺れ続けた。

### Reader-visible events

```json
[
  {
    "id": "event_0139",
    "turn": 17,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後から慎重に身を乗り出し、懐中電灯の光を錆びた案内板へ向ける。読めない駅名の揺れと、水滴の規則正しい音を照らし合わせながら、追跡者から目を離さない。",
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
    "id": "event_0140",
    "turn": 17,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、あの案内板……音に合わせて揺れているように見える。追跡者を刺激しないように、まず音の正体を確かめよう」",
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
    "id": "event_0142",
    "turn": 17,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背中でかばったまま、錆びた案内板と追跡者を交互に見据える。水滴の規則正しい音に合わせ、退路を探るため足元だけを慎重に確かめる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0064"
    ]
  },
  {
    "id": "event_0144",
    "turn": 17,
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
  },
  {
    "id": "event_0149",
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
    "id": "event_0150",
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
    "source_event": "event_0148"
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
    "source_event": "event_0148"
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
    "value": "event_0139",
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
    "value": "event_0142",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  },
  {
    "target": "quests",
    "op": "add",
    "path": "related_event_ids",
    "value": "event_0144",
    "id": "quest_001",
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

`none`

## Turn 18

### Status

`applied`

### Narration

リナは階段の先へ向けられた視線を戻さず、霧に沈む通路の奥で追跡者がこちらを見据えているのを感じ取っていた。「カイ、階段の先が気になる。でも、追跡者を刺激するのは危険だよ。私が合図したら、音を立てずに少しだけ後ろへ下がろう」

カイは彼女のそばを離れず、行き止まりと濃い霧に挟まれた空間で、低く言い聞かせた。「リナ、俺から離れるな。追跡者が動くまで、階段にも近づかない」その言葉の先で、最深部へ続く階段の闇が、今夜はいつもより深く見えた。

### Reader-visible events

```json
[
  {
    "id": "event_0151",
    "turn": 18,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、階段の先が気になる。でも、追跡者を刺激するのは危険だよ。私が合図したら、音を立てずに少しだけ後ろへ下がろう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0067"
    ]
  },
  {
    "id": "event_0152",
    "turn": 18,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺から離れるな。追跡者が動くまで、階段にも近づかない」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0068"
    ]
  },
  {
    "id": "event_0154",
    "turn": 18,
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

`none`

## Turn 19

### Status

`applied`

### Narration

リナはカイの背中に身を寄せたまま、懐中電灯の光を足元へ絞った。階段の先に広がる闇と、じっとこちらを見据える追跡者の影を交互に見つめ、水滴の間隔を数えながら、その動く兆しを慎重にうかがう。最深部へ続く階段の闇は、今夜はいっそう深く沈んで見えた。

「カイ、まだ動かないで。水滴の音が変わるまで、ここで様子を見る。もし影が近づいたら、私が知らせるから」

「リナ、俺の後ろにいろ。追跡者が動くまで、階段にも霧にも手を出すな」

行き止まりの先にも、濃霧に塞がれた背後にも、逃げ場はなかった。二人は身じろぎせず、追跡者の視線と水滴の音だけを待ち続けた。

### Reader-visible events

```json
[
  {
    "id": "event_0157",
    "turn": 19,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背中に身を寄せたまま、懐中電灯の光を足元へ絞り、階段の闇と追跡者の影を交互に見つめる。水滴の間隔を数えながら、追跡者が動く兆しを慎重にうかがう。",
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
    "turn": 19,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。水滴の音が変わるまで、ここで様子を見る。もし影が近づいたら、私が知らせるから」",
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
    "id": "event_0160",
    "turn": 19,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろにいろ。追跡者が動くまで、階段にも霧にも手を出すな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0071"
    ]
  },
  {
    "id": "event_0162",
    "turn": 19,
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

`none`

## Turn 20

### Status

`applied`

### Narration

リナは懐中電灯の光を足元へ絞り、カイの背中に身を寄せたまま息を殺した。金属を引きずる低い響きの方向と、濃霧の中で動きを止めた追跡者の影を、交互に見張る。「カイ、まだ動かないで。音が近づくまで、私たちの位置を悟らせないようにしよう」

カイは身を翻して金属音の方を向き、リナを背中に隠したまま、霧の中の影を見失わないよう身構えた。行き止まりの通路に、遠くから不穏な物音が低く這い寄り、濃霧に塞がれた背後と、じっとこちらを見据える追跡者との間で、二人の逃げ場はさらに狭まっていった。

### Reader-visible events

```json
[
  {
    "id": "event_0165",
    "turn": 20,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯の光を足元に絞り、カイの背中に身を寄せたまま息を殺す。金属を引きずる低い音の方向と、霧の中で止まった追跡者の影を交互に見張る。",
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
    "id": "event_0166",
    "turn": 20,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。音が近づくまで、私たちの位置を悟らせないようにしよう」",
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
    "id": "event_0168",
    "turn": 20,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは金属を引きずる音の方向へ体を向け、リナを背中に隠したまま、霧の中の影を見失わないよう身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0075"
    ]
  },
  {
    "id": "event_0170",
    "turn": 20,
    "type": "background_event",
    "cause": "world_simulator",
    "text": "遠くで不穏な物音がする。金属を引きずるような、低い響き",
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
      "text": "カイとリナは、霧に覆われた地下駅で足音の主を追い、霧の向こうから現れた古い切符を握る子どもや、改札跡の色褪せたお守りを手がかりに進んできた。霧は濃くなり、錆びた案内板や天井から落ちる水滴を調べても、出口や足音の正体は明らかになっていない。二人は行き止まりと濃霧に挟まれ、追跡者がこちらを見据えるなか、リナは光を足元に絞って息を殺し、カイは彼女をかばいながら金属を引きずる低い音の方向へ身構えている。地下には不穏な物音が響き続け、追跡者の正体や足音との関係、封印施設を探す命令の出どころはなお明らかになっていない。"
    },
    "id": null,
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

`none`

## Turn 21

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは懐中電灯の光をさらに足元へ絞り、カイの背中越しに追跡者の影と濃霧の揺らぎを慎重に見張る。行き止まりを背にしたまま、金属を引きずる音の間隔に耳を澄ます。「カイ、まだ動かないで。追跡者の視線が外れるまで、音の間隔だけを確かめよう。何か変わったら、私が合図する」カイは錆びた案内板の軋む音に反応し、リナを背中にかばったまま、追跡者から目を離さず周囲の退路を探る。「リナ、動くなら俺が先だ。合図するまで、絶対に離れるな」錆びた案内板が軋み、読めない駅名が霧の中に揺れる。

### Reader-visible events

```json
[
  {
    "id": "event_0174",
    "turn": 21,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯の光をさらに足元へ絞り、カイの背中越しに追跡者の影と濃霧の揺らぎを慎重に見張る。行き止まりを背にしたまま、金属を引きずる音の間隔に耳を澄ます。",
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
    "id": "event_0175",
    "turn": 21,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないで。追跡者の視線が外れるまで、音の間隔だけを確かめよう。何か変わったら、私が合図する」",
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
    "id": "event_0177",
    "turn": 21,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは錆びた案内板の軋む音に反応し、リナを背中にかばったまま、追跡者から目を離さず周囲の退路を探る。",
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
    "id": "event_0178",
    "turn": 21,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、動くなら俺が先だ。合図するまで、絶対に離れるな」",
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
    "id": "event_0180",
    "turn": 21,
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
  },
  {
    "id": "event_0186",
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
    "id": "event_0187",
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
    "source_event": "event_0185"
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
    "source_event": "event_0185"
  }
]
```

### Failure

`none`

## Turn 22

### Status

`applied`

### Narration

リナは懐中電灯を足元に向けたまま、カイの背後からわずかに身を乗り出した。追跡者の影と濃霧の揺れを交互に見つめ、息を潜めたまま低く告げる。「カイ、合図を待つ。でも、あの階段の水滴の音は確かめたい。追跡者の視線が外れたら、静かに動こう」

カイは彼女を背中にかばい、片手で不用意に動かないよう制しながら、最深部へ続く階段の闇と霧の向こうの追跡者を交互に見据えた。退路を探る視線の先で、階段の闇は今夜に限っていつもより深く沈んでいる。足音を止めた追跡者はなおこちらを見据え、行き止まりと濃霧に挟まれた空間から、逃げ場だけが静かに失われていった。

### Reader-visible events

```json
[
  {
    "id": "event_0188",
    "turn": 22,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を足元に向けたまま、カイの背後からわずかに身を乗り出し、追跡者の影と濃霧の揺れを交互に観察する。",
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
    "id": "event_0189",
    "turn": 22,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、合図を待つ。でも、あの階段の水滴の音は確かめたい。追跡者の視線が外れたら、静かに動こう」",
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
    "id": "event_0191",
    "turn": 22,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背中にかばい、最深部へ続く階段の闇と霧の向こうの追跡者を交互に見据える。退路を探りながら、リナが不用意に動かないよう片手で制した。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0080"
    ]
  },
  {
    "id": "event_0193",
    "turn": 22,
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

`none`

## Turn 23

### Status

`applied`

### Narration

リナはカイの制止に従い、懐中電灯の光を足元へ絞ったまま身を低くした。天井の亀裂から落ちる水滴が、闇の奥で規則正しい音を刻んでいる。彼女はその間隔と、行き止まりの先でじっとこちらを見据える追跡者の気配とを慎重に聞き分け、動く機会を待った。

「まだだ。音を数える。追跡者の視線が外れたら、俺が先に階段を確かめる。リナは離れるな」カイの声は低く、濃霧に閉ざされた背後の気配を警戒していた。水滴の音だけが変わらぬ間隔で響き、二人は息を潜めたまま、その次の瞬間を待ち続けた。

### Reader-visible events

```json
[
  {
    "id": "event_0196",
    "turn": 23,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの制止に従い、懐中電灯の光を足元へ絞ったまま身を低くする。水滴の間隔と追跡者の気配を慎重に聞き分け、動く機会を待つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0083"
    ]
  },
  {
    "id": "event_0198",
    "turn": 23,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「まだだ。音を数える。追跡者の視線が外れたら、俺が先に階段を確かめる。リナは離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0084"
    ]
  },
  {
    "id": "event_0200",
    "turn": 23,
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

`none`

## Turn 24

### Status

`applied`

### Narration

リナは懐中電灯の光をさらに絞り、足元にわずかに落ちる明かりのなかで、明滅する電球に合わせて伸び縮みする影の位置を目で追った。カイの背中から離れず、行き止まりの先と濃い霧に閉ざされた背後を意識しながら、追跡者の視線が外れる瞬間を待つ。どこかで古い電球が明滅し、そのたびにホームの影が不規則に伸び縮みした。

やがて、見据えていた追跡者の足音が止まった。カイは身を固くしたまま、低く告げる。「今だ。俺が先に見る。足音を立てるな、離れるな」リナは答えず、なおも彼の背に寄り添った。光と影が揺れる狭い通路で、二人は動く機会を逃さないよう息を潜めた。

### Reader-visible events

```json
[
  {
    "id": "event_0203",
    "turn": 24,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯の光をさらに絞り、明滅する電球に合わせて伸び縮みする影の位置を目で追う。カイの背中から離れず、追跡者の視線が外れる瞬間を待つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0088"
    ]
  },
  {
    "id": "event_0205",
    "turn": 24,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「今だ。俺が先に見る。足音を立てるな、離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0089"
    ]
  },
  {
    "id": "event_0207",
    "turn": 24,
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

`none`

## Turn 25

### Status

`applied`

### Narration

リナはカイの背中に触れない距離を保って身を低くし、水滴の間隔と、行き止まりの先で足音を止めた追跡者の気配を、もう一度慎重に聞き分けた。懐中電灯の光は足元から動かない。天井の亀裂から落ちる水滴が、闇の奥で規則正しい音を刻み続けている。

濃い霧は背後を塞ぎ、逃げ道はない。追跡者はただこちらを見据えていた。カイは先を確かめるように身構え、低い声で告げた。「俺が先に行く。足音が変わったら、すぐ戻れ」

### Reader-visible events

```json
[
  {
    "id": "event_0211",
    "turn": 25,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背中に触れない距離を保ちながら身を低くし、水滴の間隔と追跡者の気配をもう一度慎重に聞き分ける。懐中電灯の光は足元から動かさない。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0092"
    ]
  },
  {
    "id": "event_0213",
    "turn": 25,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「俺が先に行く。足音が変わったら、すぐ戻れ」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0093"
    ]
  },
  {
    "id": "event_0215",
    "turn": 25,
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
  },
  {
    "id": "event_0221",
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
    "id": "event_0222",
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
    "source_event": "event_0220"
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
    "source_event": "event_0220"
  }
]
```

### Failure

`none`

## Turn 26

### Status

`applied`

### Narration

「分かった。私も離れない。水滴の音が変わったら、すぐに知らせるね」リナの声が、濃い霧に閉ざされた通路へ沈んだ。行き止まりの先には進めず、背後からは霧が逃げ道を塞いでいる。追跡者は足音を止めたまま、二人をじっと見据えていた。

「リナ、俺の後ろから離れるな。動くなら、俺が合図してからだ」カイが前へ身構えた、そのときだった。どこかで古い電球が明滅し、ホームの影が伸びては縮む。揺れる光のなかで、追跡者の視線だけが動かなかった。

### Reader-visible events

```json
[
  {
    "id": "event_0223",
    "turn": 26,
    "type": "character_dialogue",
    "cause": "character:char_001:0",
    "text": "「分かった。私も離れない。水滴の音が変わったら、すぐに知らせるね」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0096"
    ]
  },
  {
    "id": "event_0225",
    "turn": 26,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろから離れるな。動くなら、俺が合図してからだ」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0097"
    ]
  },
  {
    "id": "event_0227",
    "turn": 26,
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

`none`

## Turn 27

### Status

`applied`

### Narration

リナは身を低くしたまま、錆びた案内板の揺れを目で追った。懐中電灯の光を足元から文字の輪郭へ慎重に滑らせると、読めない駅名が霧の中でかすかに浮かび上がった。案内板は軋み、古い電球の明滅に合わせて、ホームの影が不規則に揺れた。

追跡者がじっとこちらを見据えるなか、カイの声だけが張り詰めた空気を切った。「リナ、まだ動くな。俺が合図するまで、絶対に離れるな」濃霧は背後を塞ぎ、前には行き止まりがある。二人はその場に身を寄せたまま、次の合図を待ち続けた。

### Reader-visible events

```json
[
  {
    "id": "event_0230",
    "turn": 27,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは錆びた案内板の揺れを追い、懐中電灯の光を足元から文字の輪郭へ慎重に滑らせる。カイの合図を待ちながら、追跡者を刺激しないよう身を低く保つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0100"
    ]
  },
  {
    "id": "event_0232",
    "turn": 27,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、まだ動くな。俺が合図するまで、絶対に離れるな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0101"
    ]
  },
  {
    "id": "event_0234",
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
[]
```

### Failure

`none`

## Turn 28

### Status

`applied`

### Narration

「カイ、まだ動かないほうがいいよね。何か見えたら、すぐ教えて」リナは声を潜めたまま、光を案内板から逸らさなかった。

「リナ、光を動かすな。俺が合図するまで、絶対に動くな」カイの制止が、霧の満ちた行き止まりに低く落ちる。錆びた案内板が軋み、読めない駅名が濃い霧の中で揺れた。足音を止めた追跡者は、なおも二人をじっと見据えていた。

### Reader-visible events

```json
[
  {
    "id": "event_0237",
    "turn": 28,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かないほうがいいよね。何か見えたら、すぐ教えて」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0105"
    ]
  },
  {
    "id": "event_0239",
    "turn": 28,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、光を動かすな。俺が合図するまで、絶対に動くな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0106"
    ]
  },
  {
    "id": "event_0241",
    "turn": 28,
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

`none`

## Turn 29

### Status

`applied`

### Narration

「カイ、動かない。水滴の間隔を数えてみる。何か変わったら、すぐ知らせて」リナの声が、行き止まりの通路に低く落ちた。

カイは彼女の前に立ち、背後を満たす濃霧と逃げ道のない壁を素早く確かめた。それから追跡者から視線を外さぬまま、わずかな動きさえ見逃さないよう身構える。天井の亀裂から水滴が落ち、闇の奥で規則正しい音を刻んでいた。追跡者は足音を止めたまま、二人をじっと見据えている。

### Reader-visible events

```json
[
  {
    "id": "event_0245",
    "turn": 29,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、動かない。水滴の間隔を数えてみる。何か変わったら、すぐ知らせて」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0109"
    ]
  },
  {
    "id": "event_0247",
    "turn": 29,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ち、背後の濃霧と行き止まりを素早く確かめる。水滴の規則正しい音に耳を澄まし、追跡者から視線を外さず、わずかな動きも見逃さない。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0110"
    ]
  },
  {
    "id": "event_0249",
    "turn": 29,
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
  },
  {
    "id": "event_0255",
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
    "id": "event_0256",
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
    "source_event": "event_0254"
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
    "source_event": "event_0254"
  }
]
```

### Failure

`none`

## Turn 30

### Status

`applied`

### Narration

「カイ、まだ動かない。水滴の音が途切れたら、私が合図するまで絶対に振り向かないで」リナはそう告げ、懐中電灯の光を足元に固定した。息を殺し、水滴の間隔と霧の向こうの気配を注意深く聞き分ける。カイは彼女をかばったまま、追跡者から目を離さなかった。「まだだ。音が変わるまで動くな。俺が守る」

そのとき、錆びた案内板が軋み、読めない駅名が濃霧の中で揺れた。行き止まりの先にも、背後の霧の中にも逃げ場はない。止まった足音の主は、ただじっと二人を見据えていた。

### Reader-visible events

```json
[
  {
    "id": "event_0257",
    "turn": 30,
    "type": "character_dialogue",
    "cause": "character:char_001:0",
    "text": "「カイ、まだ動かない。水滴の音が途切れたら、私が合図するまで絶対に振り向かないで」",
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
    "id": "event_0258",
    "turn": 30,
    "type": "character_action",
    "cause": "character:char_001:1",
    "text": "リナは懐中電灯の光を足元に固定し、息を殺したまま水滴の間隔と霧の向こうの気配を注意深く聞き分ける。",
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
    "id": "event_0260",
    "turn": 30,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「まだだ。音が変わるまで動くな。俺が守る」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0113"
    ]
  },
  {
    "id": "event_0262",
    "turn": 30,
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
    "target": "memory",
    "op": "add",
    "path": "",
    "value": {
      "id": "memory_0030",
      "up_to_turn": 30,
      "text": "カイとリナは、霧に覆われた地下駅で足音の主を追い、霧の向こうから現れた古い切符を握る子どもや、改札跡の色褪せたお守りを手がかりに進んできた。霧は濃くなり、錆びた案内板や天井から落ちる水滴を調べても、出口や足音の正体は明らかになっていない。二人は行き止まりと濃霧に挟まれ、追跡者がこちらを見据えるなか、リナは懐中電灯を足元に固定して水滴の間隔と霧の向こうの気配を聞き分け、カイは彼女をかばいながら追跡者を監視している。錆びた案内板が霧の中で揺れたが、追跡者の正体や足音との関係、封印施設を探す命令の出どころはなお明らかになっていない。"
    },
    "id": null,
    "visibility": "reader",
    "source_event": null
  }
]
```

### Failure

`none`

## 機械証跡

- metrics_json: `sandbox/20260722-issue086-fallback-fix/metrics.json`
- leak_scan: `PASS` — critical/high findingなし
- resume: `PASS` — checkpoint turn 15, resumed turn 16
- provider_failures: none
- narrator: binding `narrator`, 30 calls, fallback turn 21 StructuredOutputError
- action_outcomes: turn 7 affordance_001, turn 17 affordance_002, turn 21 affordance_003, turn 25 affordance_004, turn 29 affordance_005
- SLO: `FAIL` — failed_items: threads, narrator_fallback

## 結論

- failed_items: threads, narrator_fallback
- rerun_required: `YES`（修正後）
- notes: fallback開始とpacingは改善。長期open thread、narrator fallback、反復が残る。
