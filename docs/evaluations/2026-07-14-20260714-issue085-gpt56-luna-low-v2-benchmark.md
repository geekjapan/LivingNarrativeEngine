# 実LLM benchmark転記 — 20260714-issue085-gpt56-luna-low-v2

- gate: `1.0`
- result: `FAIL`
- started_at: 2026-07-14T01:59:09+09:00
- finished_at: 2026-07-14T02:08:00+09:00
- git_revision: `c5c0fcde79f5ff65a48b1609149db0734e9242d3`
- sample: `mist_station`
- seed: `issue-085-mist-station-v1`
- provider: `openai-compatible`
- model: `cx/gpt-5.6-luna-low`
- completed_turns: 30 / 30
- benchmark_json: `sandbox/20260714-issue085-gpt56-luna-low-v2/benchmark.json`
- provider_failure: none
- resume: `PASS`（turn 15 → turn 16、別プロセス）

## 事前確認

- [ ] `run.status`が`PASS`（機械SLO不合格）
- [x] 30ターンが`applied`
- [x] JSONとMarkdownのturn番号・narrationが一致
- [x] provider failureなし
- [x] reader-visible出力に非公開情報なし
- [x] `mechanical.metrics`、leak scan、resumeを確認

## 機械SLO

| 項目 | 判定 | 実測 | 閾値 |
|---|---|---:|---:|
| completed turns | PASS | 30 | 30 |
| replay match rate | PASS | 1.0 | 1.0 |
| max consecutive stall turns | **FAIL** | 15 | ≤3 |
| thread opened / resolved ratio | **FAIL** | 0 / null | ≥1 / ≥0.5 |
| critical/high leak | PASS | 0 | 0 |
| emotion ceiling consecutive | PASS | 0 | ≤5 |
| game feature count | PASS | 30 | >0 |
| scene transitions | OBSERVED | 1 | 未定義 |

resource observation: elapsed `531.034s`、LLM calls `60`、tokens `465052`、cost `unpriced`。

## Turns

## Turn 01

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナは懐中電灯を足音の方向へ向け、カイのそばから離れずに霧の向こうを凝視する。「カイ、あの子……どうしてこんな場所にいるの？　足音の主が来る前に、声をかけてみる？」カイはリナを背にかばうように一歩前へ出て、霧の向こうから近づく足音へ身構える。「リナ、俺の後ろにいろ。……そこの子ども、動くな。切符を見せろ」静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0001",
    "turn": 1,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を足音の方向へ向け、カイのそばから離れずに霧の向こうを凝視する。",
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
    "text": "「カイ、あの子……どうしてこんな場所にいるの？　足音の主が来る前に、声をかけてみる？」",
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
    "id": "event_0004",
    "turn": 1,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばうように一歩前へ出て、霧の向こうから近づく足音へ身構える。",
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
    "id": "event_0005",
    "turn": 1,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろにいろ。……そこの子ども、動くな。切符を見せろ」",
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
    "id": "event_0007",
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
    "id": "event_0010",
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

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。「その切符、少しだけ見せてくれる？　私たちはあなたを傷つけない。名前と、ここで何をしているのか教えて」カイはリナを背後にかばったまま、霧の向こうの子どもとの距離を保ち、深く見える階段の闇へ視線を走らせる。「リナ、近づくな。……お前、その切符をどこで手に入れた。階段の先から来たのか」最深部へ続く階段の闇が、今夜はいつもより深く見える。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0011",
    "turn": 2,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「その切符、少しだけ見せてくれる？　私たちはあなたを傷つけない。名前と、ここで何をしているのか教えて」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": [
      "roll_0007"
    ]
  },
  {
    "id": "event_0013",
    "turn": 2,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背後にかばったまま、霧の向こうの子どもとの距離を保ち、深く見える階段の闇へ視線を走らせる。",
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
    "id": "event_0014",
    "turn": 2,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、近づくな。……お前、その切符をどこで手に入れた。階段の先から来たのか」",
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
    "id": "event_0016",
    "turn": 2,
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
  },
  {
    "id": "event_0019",
    "turn": 2,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0006",
      "target_id": null
    },
    "roll_ids": [
      "roll_0006"
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

## Turn 03

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナはカイの袖をそっとつかみ、彼の背後に隠れるのではなく隣に並ぶ。懐中電灯を子どもと足音の間へ向け、霧の動きと影の変化を慎重に見極める。「ねえ、足音が近づいている。あなたはこの駅から出る方法を知っているの？」カイはリナの前に立ったまま、明滅する電球と階段の闇を交互に見据え、子どもとの距離を崩さない。「リナ、俺から離れるな。……お前も、切符を見せたままそこにいろ。階段には近づくな」どこかで古い電球が明滅し、ホームの影が伸び縮みする。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0020",
    "turn": 3,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖をそっとつかみ、彼の背後に隠れるのではなく隣に並ぶ。懐中電灯を子どもと足音の間へ向け、霧の動きと影の変化を慎重に見極める。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0011"
    ]
  },
  {
    "id": "event_0021",
    "turn": 3,
    "type": "character_dialogue",
    "cause": "character:char_001:2",
    "text": "「ねえ、足音が近づいている。あなたはこの駅から出る方法を知っているの？」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0022",
    "turn": 3,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ったまま、明滅する電球と階段の闇を交互に見据え、子どもとの距離を崩さない。",
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
    "id": "event_0023",
    "turn": 3,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺から離れるな。……お前も、切符を見せたままそこにいろ。階段には近づくな」",
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
    "id": "event_0025",
    "turn": 3,
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
    "id": "event_0029",
    "turn": 3,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0010",
      "target_id": null
    },
    "roll_ids": [
      "roll_0010"
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

## Turn 04

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナは懐中電灯を低く構え、霧の渦とホームの縁を照らしながら、カイの隣で足音の間隔を数える。階段からは距離を保ったまま、子どもの様子も視界に入れ続ける。カイはリナの前に立ち、霧と階段の間を遮るように身を固める。足音の間隔を測りながら、子どもからも目を離さない。「リナ、俺のそばを離れるな。……お前、足音の主を知っているのか」静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0030",
    "turn": 4,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を低く構え、霧の渦とホームの縁を照らしながら、カイの隣で足音の間隔を数える。階段からは距離を保ったまま、子どもの様子も視界に入れ続ける。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0015"
    ]
  },
  {
    "id": "event_0032",
    "turn": 4,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ち、霧と階段の間を遮るように身を固める。足音の間隔を測りながら、子どもからも目を離さない。",
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
    "id": "event_0033",
    "turn": 4,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺のそばを離れるな。……お前、足音の主を知っているのか」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0035",
    "turn": 4,
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
    "id": "event_0038",
    "turn": 4,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0014",
      "target_id": null
    },
    "roll_ids": [
      "roll_0014"
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

## Turn 05

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナはカイの隣から離れず、懐中電灯の光を階段の闇と霧の境目へ向ける。足音の間隔を数えながら、子どもの手元にある古い切符も見失わないよう注意深く見つめる。「カイ、階段の先を知っているなら教えて。足音が来る前に、ここを離れる方法を見つけたいの」「あなたも聞こえているよね？　その切符を見せてくれたら、私たちもここから出る方法を探す」「リナ、俺の後ろにいろ。足音が止まるまで、誰にも近づくな」最深部へ続く階段の闇が、今夜はいつもより深く見える。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0039",
    "turn": 5,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの隣から離れず、懐中電灯の光を階段の闇と霧の境目へ向ける。足音の間隔を数えながら、子どもの手元にある古い切符も見失わないよう注意深く見つめる。",
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
    "id": "event_0040",
    "turn": 5,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、階段の先を知っているなら教えて。足音が来る前に、ここを離れる方法を見つけたいの」",
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
    "id": "event_0041",
    "turn": 5,
    "type": "character_dialogue",
    "cause": "character:char_001:2",
    "text": "「あなたも聞こえているよね？　その切符を見せてくれたら、私たちもここから出る方法を探す」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0042",
    "turn": 5,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろにいろ。足音が止まるまで、誰にも近づくな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0019"
    ]
  },
  {
    "id": "event_0044",
    "turn": 5,
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
  },
  {
    "id": "event_0047",
    "turn": 5,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0018",
      "target_id": null
    },
    "roll_ids": [
      "roll_0018"
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

## Turn 06

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナはカイの隣で足音の間隔を数え続け、懐中電灯の光を霧の渦と階段の手前へ静かに滑らせる。子どもの姿を視界から外さず、逃げ道になりそうなホームの端も慎重に確かめる。「リナ、まだ動くな。足音の主が来るまで、俺がここにいる」静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0048",
    "turn": 6,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの隣で足音の間隔を数え続け、懐中電灯の光を霧の渦と階段の手前へ静かに滑らせる。子どもの姿を視界から外さず、逃げ道になりそうなホームの端も慎重に確かめる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0023"
    ]
  },
  {
    "id": "event_0050",
    "turn": 6,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、まだ動くな。足音の主が来るまで、俺がここにいる」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0024"
    ]
  },
  {
    "id": "event_0052",
    "turn": 6,
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
    "id": "event_0055",
    "turn": 6,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0022",
      "target_id": null
    },
    "roll_ids": [
      "roll_0022"
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

## Turn 07

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。「わかった、離れない。でも、足音がもう近い。カイ、知っていることを今すぐ教えて。私たちはどこへ逃げればいいの？」カイはリナを背にかばい、階段と霧の境目へ向けて身を低くする。近づく足音の間隔を測りながら、退路を塞がれない位置へゆっくり後退する。天井の亀裂から水滴が落ち、闇の奥で規則正しい音を刻む。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0056",
    "turn": 7,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「わかった、離れない。でも、足音がもう近い。カイ、知っていることを今すぐ教えて。私たちはどこへ逃げればいいの？」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0028"
    ]
  },
  {
    "id": "event_0058",
    "turn": 7,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばい、階段と霧の境目へ向けて身を低くする。近づく足音の間隔を測りながら、退路を塞がれない位置へゆっくり後退する。",
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
    "id": "event_0060",
    "turn": 7,
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
    "id": "event_0065",
    "turn": 7,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0027",
      "target_id": null
    },
    "roll_ids": [
      "roll_0027"
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

## Turn 08

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナはカイの背後に身を寄せたまま、懐中電灯の光を金属音のする霧の奥へ向ける。足音と引きずる音の位置を聞き分けながら、子どもとホームの端を同時に視界へ収める。「カイ、あの音は足音とは違う。今のうちに、子どもを連れて逃げられる場所を探そう」「リナ、俺から離れるな。音の正体はまだ分からない。近づいてきたら、階段ではなくホームの端へ走る」遠くで不穏な物音がする。金属を引きずるような、低い響き。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0066",
    "turn": 8,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後に身を寄せたまま、懐中電灯の光を金属音のする霧の奥へ向ける。足音と引きずる音の位置を聞き分けながら、子どもとホームの端を同時に視界へ収める。",
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
    "id": "event_0067",
    "turn": 8,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、あの音は足音とは違う。今のうちに、子どもを連れて逃げられる場所を探そう」",
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
    "id": "event_0069",
    "turn": 8,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺から離れるな。音の正体はまだ分からない。近づいてきたら、階段ではなくホームの端へ走る」",
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
    "id": "event_0071",
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
  },
  {
    "id": "event_0074",
    "turn": 8,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
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
[]
```

### Failure

`none`

## Turn 09

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナはカイの背後から半歩だけ身を乗り出し、懐中電灯の光を錆びた案内板から古い切符を握る子どもへゆっくり移す。足音の方向とホームの端を意識しながら、子どもが逃げ道を示していないか観察する。「カイ、案内板は読めないけど、あの子は何か知っているかもしれない。足音が来る前に、声をかけてもいい？」カイはリナを背にかばったまま、錆びた案内板の陰へ移動する。霧の奥とホームの端を交互に見張り、足音の間隔を測りながら、子どもへ近づける退路を探す。錆びた案内板が軋み、読めない駅名が霧の中に揺れる。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0075",
    "turn": 9,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの背後から半歩だけ身を乗り出し、懐中電灯の光を錆びた案内板から古い切符を握る子どもへゆっくり移す。足音の方向とホームの端を意識しながら、子どもが逃げ道を示していないか観察する。",
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
    "id": "event_0076",
    "turn": 9,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、案内板は読めないけど、あの子は何か知っているかもしれない。足音が来る前に、声をかけてもいい？」",
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
    "id": "event_0078",
    "turn": 9,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナを背にかばったまま、錆びた案内板の陰へ移動する。霧の奥とホームの端を交互に見張り、足音の間隔を測りながら、子どもへ近づける退路を探す。",
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
    "id": "event_0080",
    "turn": 9,
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
    "id": "event_0083",
    "turn": 9,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0036",
      "target_id": null
    },
    "roll_ids": [
      "roll_0036"
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

## Turn 10

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナはカイの袖をつかみ、案内板の陰から動かずに子どもへ懐中電灯を弱く向ける。霧の奥の人影を警戒しながら、子どもの足元とホームの端に逃げ道がないか見定める。「あなた、聞こえる？　その切符を見せて。音が来る前に、逃げ道を教えて」「リナ、今だ。子どもに声をかけろ。何か動いたら、俺の合図でホームの端へ走る」錆びた案内板が軋み、読めない駅名が霧の中に揺れる。霧の奥に人影が揺れ、規則正しい足音が急に止まる。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0084",
    "turn": 10,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖をつかみ、案内板の陰から動かずに子どもへ懐中電灯を弱く向ける。霧の奥の人影を警戒しながら、子どもの足元とホームの端に逃げ道がないか見定める。",
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
    "id": "event_0085",
    "turn": 10,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「あなた、聞こえる？　その切符を見せて。音が来る前に、逃げ道を教えて」",
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
    "id": "event_0087",
    "turn": 10,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、今だ。子どもに声をかけろ。何か動いたら、俺の合図でホームの端へ走る」",
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
    "id": "event_0089",
    "turn": 10,
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
    "id": "event_0091",
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
      "roll_id": "roll_0039",
      "target_id": null
    },
    "roll_ids": [
      "roll_0039"
    ]
  },
  {
    "id": "event_0093",
    "turn": 10,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0040",
      "target_id": null
    },
    "roll_ids": [
      "roll_0040"
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

## Turn 11

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。リナはカイの袖を強く引き、追跡者の影が消えた柱の反対側へ身を寄せる。懐中電灯を子どもの足元へ向け、ホームの端へ続く道を確かめながら、いつでも走れる姿勢を取る。カイはリナの前に立ち、柱の影を横切った追跡者の気配から彼女をかばう。霧の向こうを見失わないまま、子どもへ近づく退路を探す。地上から遠雷のような街のざわめきが届き、すぐに霧へ吸われて消える。

### Reader-visible events

```json
[
  {
    "id": "event_0094",
    "turn": 11,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナはカイの袖を強く引き、追跡者の影が消えた柱の反対側へ身を寄せる。懐中電灯を子どもの足元へ向け、ホームの端へ続く道を確かめながら、いつでも走れる姿勢を取る。",
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
    "id": "event_0096",
    "turn": 11,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前に立ち、柱の影を横切った追跡者の気配から彼女をかばう。霧の向こうを見失わないまま、子どもへ近づく退路を探す。",
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
    "id": "event_0098",
    "turn": 11,
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

## Turn 12

### Status

`applied`

### Narration

静かな緊張感の空気が漂っている。ホームには濃い霧が立ち込めている。どこからか、規則正しい足音が近づいてくる。「カイ、今すぐ走るよ！　あなたも、こっちへ来て！」「リナ、俺の後ろから離れるな。子どもは見捨てない。動くなら、俺が合図するまで待て」錆びた案内板が軋み、読めない駅名が霧の中に揺れる。霧を裂いて、追跡者が二人の前に姿を現す。霧の向こうから、古い切符を握った子どもがこちらを見つめている。

### Reader-visible events

```json
[
  {
    "id": "event_0102",
    "turn": 12,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今すぐ走るよ！　あなたも、こっちへ来て！」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0050"
    ]
  },
  {
    "id": "event_0104",
    "turn": 12,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、俺の後ろから離れるな。子どもは見捨てない。動くなら、俺が合図するまで待て」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0051"
    ]
  },
  {
    "id": "event_0106",
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
  },
  {
    "id": "event_0108",
    "turn": 12,
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
  },
  {
    "id": "event_0110",
    "turn": 12,
    "type": "encounter",
    "cause": "world_simulator",
    "text": "霧の向こうから、古い切符を握った子どもがこちらを見つめている。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "encounter_id": "encounter_001",
      "roll_id": "roll_0049",
      "target_id": null
    },
    "roll_ids": [
      "roll_0049"
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

## Turn 13

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。「カイ、合図を待つ。でも、隙ができたら子どもを真ん中にして走ろう」カイは行き止まりの通路でリナの前に立ち、背後の濃霧と追跡者を同時に警戒する。片手をわずかに上げ、子どもには近づかず、リナが動く準備を整えるよう合図する。どこかで古い電球が明滅し、ホームの影が伸び縮みする。

### Reader-visible events

```json
[
  {
    "id": "event_0111",
    "turn": 13,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、合図を待つ。でも、隙ができたら子どもを真ん中にして走ろう」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0055"
    ]
  },
  {
    "id": "event_0113",
    "turn": 13,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは行き止まりの通路でリナの前に立ち、背後の濃霧と追跡者を同時に警戒する。片手をわずかに上げ、子どもには近づかず、リナが動く準備を整えるよう合図する。",
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
    "id": "event_0115",
    "turn": 13,
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

## Turn 14

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。「カイ、今なら行けるかもしれない。私が子どもを連れて走るから、後ろをお願い！」「まだ動くな。俺が隙を作る。合図したら、子どもを連れて走れ」冷たい風が線路の奥から吹き、油と土の匂いを運んでくる。

### Reader-visible events

```json
[
  {
    "id": "event_0119",
    "turn": 14,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今なら行けるかもしれない。私が子どもを連れて走るから、後ろをお願い！」",
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
    "id": "event_0121",
    "turn": 14,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「まだ動くな。俺が隙を作る。合図したら、子どもを連れて走れ」",
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
    "id": "event_0123",
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

`none`

## Turn 15

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。「わかった。合図があったら、私があの子の手を取って走る。絶対に置いていかない」カイはリナの前から退かず、追跡者との間合いを測りながら、改札跡の鉄柵へ視線を走らせる。片手を低く伸ばし、リナには子どものそばを離れないよう静かに合図する。改札跡の鉄柵で、誰かが結んだ色褪せたお守りの紐が揺れる。

### Reader-visible events

```json
[
  {
    "id": "event_0127",
    "turn": 15,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「わかった。合図があったら、私があの子の手を取って走る。絶対に置いていかない」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_002"
    },
    "roll_ids": [
      "roll_0065"
    ]
  },
  {
    "id": "event_0129",
    "turn": 15,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前から退かず、追跡者との間合いを測りながら、改札跡の鉄柵へ視線を走らせる。片手を低く伸ばし、リナには子どものそばを離れないよう静かに合図する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0066"
    ]
  },
  {
    "id": "event_0131",
    "turn": 15,
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

## Turn 16

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは懐中電灯を低く構え、子どもの手が届く距離まで慎重に身を寄せる。カイの合図を見逃さないよう、追跡者の影と彼の手元を交互に見つめた。「わかった。合図があったら、すぐに走る。あの子の手は私が離さない」「リナ、子どもから離れるな。合図を出すまで、絶対に動くな」最深部へ続く階段の闇が、今夜はいつもより深く見える。

### Reader-visible events

```json
[
  {
    "id": "event_0135",
    "turn": 16,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を低く構え、子どもの手が届く距離まで慎重に身を寄せる。カイの合図を見逃さないよう、追跡者の影と彼の手元を交互に見つめた。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0136",
    "turn": 16,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「わかった。合図があったら、すぐに走る。あの子の手は私が離さない」",
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
    "id": "event_0138",
    "turn": 16,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、子どもから離れるな。合図を出すまで、絶対に動くな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0070"
    ]
  },
  {
    "id": "event_0140",
    "turn": 16,
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

## Turn 17

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手をしっかり握り、懐中電灯の光を足元だけに落としたまま、カイの合図を待つ。追跡者を刺激しないよう息を潜め、逃げ道になりそうな階段の位置を慎重に確かめる。「カイ、合図を見たらすぐ走る。あなたも絶対に戻ってきて」「……まだだ。俺が合図するまで、絶対に動くな」最深部へ続く階段の闇が、今夜はいつもより深く見える。

### Reader-visible events

```json
[
  {
    "id": "event_0145",
    "turn": 17,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手をしっかり握り、懐中電灯の光を足元だけに落としたまま、カイの合図を待つ。追跡者を刺激しないよう息を潜め、逃げ道になりそうな階段の位置を慎重に確かめる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0146",
    "turn": 17,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、合図を見たらすぐ走る。あなたも絶対に戻ってきて」",
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
    "id": "event_0148",
    "turn": 17,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「……まだだ。俺が合図するまで、絶対に動くな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0074"
    ]
  },
  {
    "id": "event_0150",
    "turn": 17,
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

## Turn 18

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手を握ったまま身を低くし、懐中電灯の光を足元に絞る。水滴の規則的な音に耳を澄ませながら、追跡者の影と階段の位置を慎重に見比べる。「カイ、まだ動かない。合図があったら、子どもを連れて階段へ走るよ」カイはリナの前から一歩も退かず、鉄柵と階段の位置を背にしたまま、霧の奥に潜む追跡者の動きを見極める。片手を低く上げ、リナにはまだ動かないよう合図する。天井の亀裂から水滴が落ち、闇の奥で規則正しい音を刻む。

### Reader-visible events

```json
[
  {
    "id": "event_0155",
    "turn": 18,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手を握ったまま身を低くし、懐中電灯の光を足元に絞る。水滴の規則的な音に耳を澄ませながら、追跡者の影と階段の位置を慎重に見比べる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0156",
    "turn": 18,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かない。合図があったら、子どもを連れて階段へ走るよ」",
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
    "id": "event_0158",
    "turn": 18,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナの前から一歩も退かず、鉄柵と階段の位置を背にしたまま、霧の奥に潜む追跡者の動きを見極める。片手を低く上げ、リナにはまだ動かないよう合図する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0078"
    ]
  },
  {
    "id": "event_0160",
    "turn": 18,
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

## Turn 19

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手を握ったまま、懐中電灯の光を錆びた案内板と濃い霧の境目へ静かに向ける。追跡者を刺激しないよう身を低くし、カイの合図を待ちながら、霧の薄い方角を探る。「カイ、まだ動かない。霧が薄くなったら、子どもを連れて一気に抜けよう」「リナ、子どもを連れて俺の後ろへ。追跡者が動いたら、階段まで一気に走る」錆びた案内板が軋み、読めない駅名が霧の中に揺れる。

### Reader-visible events

```json
[
  {
    "id": "event_0165",
    "turn": 19,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手を握ったまま、懐中電灯の光を錆びた案内板と濃い霧の境目へ静かに向ける。追跡者を刺激しないよう身を低くし、カイの合図を待ちながら、霧の薄い方角を探る。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0166",
    "turn": 19,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、まだ動かない。霧が薄くなったら、子どもを連れて一気に抜けよう」",
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
    "turn": 19,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、子どもを連れて俺の後ろへ。追跡者が動いたら、階段まで一気に走る」",
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
    "id": "event_0170",
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

`none`

## Turn 20

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは懐中電灯を消し、子どもの手を握ったまま壁際に身を寄せる。追跡者の視線から子どもを隠すように立ち、カイの動きを慎重に待つ。「カイ、今は動かない。隙ができたら、私が子どもを連れて走る」カイはリナと子どもの前に立ちはだかり、背後の行き止まりと階段の位置を確かめながら、追跡者から目を離さない。どこかで古い電球が明滅し、ホームの影が伸び縮みする。

### Reader-visible events

```json
[
  {
    "id": "event_0175",
    "turn": 20,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは懐中電灯を消し、子どもの手を握ったまま壁際に身を寄せる。追跡者の視線から子どもを隠すように立ち、カイの動きを慎重に待つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0176",
    "turn": 20,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今は動かない。隙ができたら、私が子どもを連れて走る」",
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
    "id": "event_0178",
    "turn": 20,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナと子どもの前に立ちはだかり、背後の行き止まりと階段の位置を確かめながら、追跡者から目を離さない。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0086"
    ]
  },
  {
    "id": "event_0180",
    "turn": 20,
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

## Turn 21

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手を強く握り、壁際から動かずに身を低くする。懐中電灯は消したまま、霧の流れと追跡者の気配を慎重に探り、カイの合図に備える。「カイ、霧が濃すぎる。合図があったら、私が子どもを連れて階段へ走るね」カイは濃い霧の中でもリナと子どもの位置を背にかばい、階段の方向へ手探りで一歩ずつ後退する。追跡者の動きがあれば、すぐに自分が引きつけられるよう身構える。霧が一段と濃くなり、数歩先の視界が白く閉ざされる。

### Reader-visible events

```json
[
  {
    "id": "event_0185",
    "turn": 21,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手を強く握り、壁際から動かずに身を低くする。懐中電灯は消したまま、霧の流れと追跡者の気配を慎重に探り、カイの合図に備える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0186",
    "turn": 21,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、霧が濃すぎる。合図があったら、私が子どもを連れて階段へ走るね」",
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
    "id": "event_0188",
    "turn": 21,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは濃い霧の中でもリナと子どもの位置を背にかばい、階段の方向へ手探りで一歩ずつ後退する。追跡者の動きがあれば、すぐに自分が引きつけられるよう身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0090"
    ]
  },
  {
    "id": "event_0190",
    "turn": 21,
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

## Turn 22

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手を握ったまま、霧の渦がわずかに薄くなる瞬間を見逃さないよう目を凝らす。カイの背後から階段の位置を確かめ、走り出せる姿勢を整える。「カイ、霧が動いたら合図して。子どもを連れて、あなたの後ろを離れないから」「まだだ。追跡者が離れた瞬間に、リナは子どもを連れて階段へ。俺が最後に続く」静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている。

### Reader-visible events

```json
[
  {
    "id": "event_0195",
    "turn": 22,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手を握ったまま、霧の渦がわずかに薄くなる瞬間を見逃さないよう目を凝らす。カイの背後から階段の位置を確かめ、走り出せる姿勢を整える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0196",
    "turn": 22,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、霧が動いたら合図して。子どもを連れて、あなたの後ろを離れないから」",
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
    "id": "event_0198",
    "turn": 22,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「まだだ。追跡者が離れた瞬間に、リナは子どもを連れて階段へ。俺が最後に続く」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0094"
    ]
  },
  {
    "id": "event_0200",
    "turn": 22,
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

## Turn 23

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手を握ったまま、明滅する電球の間隔と霧の流れを見比べる。追跡者の影が消えた方向を避け、階段へ通じる足場を慎重に探す。「カイ、今。影が消えた方は避けて、階段まで一気に行こう」「今だ。リナ、子どもを連れて階段へ。俺が最後に行く」どこかで古い電球が明滅し、ホームの影が伸び縮みする。

### Reader-visible events

```json
[
  {
    "id": "event_0205",
    "turn": 23,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手を握ったまま、明滅する電球の間隔と霧の流れを見比べる。追跡者の影が消えた方向を避け、階段へ通じる足場を慎重に探す。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0206",
    "turn": 23,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今。影が消えた方は避けて、階段まで一気に行こう」",
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
    "id": "event_0208",
    "turn": 23,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「今だ。リナ、子どもを連れて階段へ。俺が最後に行く」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0098"
    ]
  },
  {
    "id": "event_0210",
    "turn": 23,
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

## Turn 24

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手を離さず、霧の向こうに追跡者の影が戻らないか確かめながら、階段へ向かって慎重に進む。カイの背中から離れないよう足音を抑え、いつでも身を伏せられる姿勢を保つ。「今のうちに進もう。カイ、後ろをお願い。何か見えたらすぐ知らせて」カイはリナと子どもの前に立ち、霧の向こうに消えた追跡者の影を見据えながら、階段へ続く道を塞がない位置で身構える。静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている。

### Reader-visible events

```json
[
  {
    "id": "event_0215",
    "turn": 24,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手を離さず、霧の向こうに追跡者の影が戻らないか確かめながら、階段へ向かって慎重に進む。カイの背中から離れないよう足音を抑え、いつでも身を伏せられる姿勢を保つ。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0216",
    "turn": 24,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「今のうちに進もう。カイ、後ろをお願い。何か見えたらすぐ知らせて」",
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
    "id": "event_0218",
    "turn": 24,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナと子どもの前に立ち、霧の向こうに消えた追跡者の影を見据えながら、階段へ続く道を塞がない位置で身構える。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0102"
    ]
  },
  {
    "id": "event_0220",
    "turn": 24,
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

## Turn 25

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手を強く握り、カイの背後を守るように階段へ進む。霧の中で追跡者の影が戻らないか、足を止めずに周囲を見回す。「カイ、階段を上がる前に一度だけ周囲を確認して。追跡者が戻る前に、子どもを先に進ませよう」カイはリナと子どもの前に立ち、濃い霧の向こうの追跡者から二人を隠すように身を低く構える。階段への退路を塞がないまま、追跡者の動きを見極める。静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている。

### Reader-visible events

```json
[
  {
    "id": "event_0225",
    "turn": 25,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手を強く握り、カイの背後を守るように階段へ進む。霧の中で追跡者の影が戻らないか、足を止めずに周囲を見回す。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0226",
    "turn": 25,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、階段を上がる前に一度だけ周囲を確認して。追跡者が戻る前に、子どもを先に進ませよう」",
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
    "id": "event_0228",
    "turn": 25,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナと子どもの前に立ち、濃い霧の向こうの追跡者から二人を隠すように身を低く構える。階段への退路を塞がないまま、追跡者の動きを見極める。",
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
    "id": "event_0230",
    "turn": 25,
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

## Turn 26

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもの手を握ったまま、懐中電灯を階段の先へ向ける。追跡者の影が霧に溶けている隙に、身を低くして子どもを先に階段へ進ませる。「カイ、今のうちに上がろう。私が子どものそばにいるから、あなたは後ろを見ていて」カイはリナと子どもの前に立ちはだかり、濃い霧の奥を睨みながら、二人が退ける道を背中で確保する。静かな時間が流れる。ホームの縁で霧がゆっくりと渦を巻いている。

### Reader-visible events

```json
[
  {
    "id": "event_0235",
    "turn": 26,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもの手を握ったまま、懐中電灯を階段の先へ向ける。追跡者の影が霧に溶けている隙に、身を低くして子どもを先に階段へ進ませる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0236",
    "turn": 26,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、今のうちに上がろう。私が子どものそばにいるから、あなたは後ろを見ていて」",
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
    "id": "event_0238",
    "turn": 26,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイはリナと子どもの前に立ちはだかり、濃い霧の奥を睨みながら、二人が退ける道を背中で確保する。",
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
    "id": "event_0240",
    "turn": 26,
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

## Turn 27

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは地上から届いた街のざわめきに耳を澄ませ、懐中電灯の光を階段の上へ伸ばす。追跡者の影が再び現れないか確かめながら、子どもをかばうように一段ずつ上がる。「街の音が聞こえた……出口が近いのかもしれない。でも急がないで。カイ、後ろを見ながらついてきて」カイは階段の入口に身を寄せ、リナと子どもを先に通すため、霧の奥へ背を向けずに道を確保する。地上から遠雷のような街のざわめきが届き、すぐに霧へ吸われて消える。

### Reader-visible events

```json
[
  {
    "id": "event_0245",
    "turn": 27,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは地上から届いた街のざわめきに耳を澄ませ、懐中電灯の光を階段の上へ伸ばす。追跡者の影が再び現れないか確かめながら、子どもをかばうように一段ずつ上がる。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0246",
    "turn": 27,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「街の音が聞こえた……出口が近いのかもしれない。でも急がないで。カイ、後ろを見ながらついてきて」",
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
    "id": "event_0248",
    "turn": 27,
    "type": "character_action",
    "cause": "character:char_002:0",
    "text": "カイは階段の入口に身を寄せ、リナと子どもを先に通すため、霧の奥へ背を向けずに道を確保する。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0114"
    ]
  },
  {
    "id": "event_0250",
    "turn": 27,
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

## Turn 28

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは階段を上りきる前に足を止め、懐中電灯を左右へゆっくり振る。街のざわめきが本当に地上から届いたものか確かめながら、子どもを自分の背後へかばう。「カイ、先に周囲を見て。人の気配がなければ、子どもを連れて一気に地上へ出よう」「俺が最後に上がる。リナ、子どもを連れて先へ行け」地上から遠雷のような街のざわめきが届き、すぐに霧へ吸われて消える。

### Reader-visible events

```json
[
  {
    "id": "event_0255",
    "turn": 28,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは階段を上りきる前に足を止め、懐中電灯を左右へゆっくり振る。街のざわめきが本当に地上から届いたものか確かめながら、子どもを自分の背後へかばう。",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_001",
      "target_id": "char_003"
    },
    "roll_ids": []
  },
  {
    "id": "event_0256",
    "turn": 28,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、先に周囲を見て。人の気配がなければ、子どもを連れて一気に地上へ出よう」",
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
    "turn": 28,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「俺が最後に上がる。リナ、子どもを連れて先へ行け」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0118"
    ]
  },
  {
    "id": "event_0260",
    "turn": 28,
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

## Turn 29

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもを背後にかばい、懐中電灯を低く構えて霧の向こうを照らす。追跡者の位置を見失わないよう、カイのいる方へゆっくり後退する。「カイ、離れないで。子どもを連れて、壁沿いに出口を探そう。あの影が近づいたら、すぐに知らせて」「リナ、子どもを連れて上へ。俺がここで足を止める。霧が晴れるまで、振り返るな」霧が一段と濃くなり、数歩先の視界が白く閉ざされる。

### Reader-visible events

```json
[
  {
    "id": "event_0265",
    "turn": 29,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもを背後にかばい、懐中電灯を低く構えて霧の向こうを照らす。追跡者の位置を見失わないよう、カイのいる方へゆっくり後退する。",
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
    "id": "event_0266",
    "turn": 29,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、離れないで。子どもを連れて、壁沿いに出口を探そう。あの影が近づいたら、すぐに知らせて」",
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
    "id": "event_0268",
    "turn": 29,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、子どもを連れて上へ。俺がここで足を止める。霧が晴れるまで、振り返るな」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0122"
    ]
  },
  {
    "id": "event_0270",
    "turn": 29,
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

## Turn 30

### Status

`applied`

### Narration

逃げ場のない緊迫の空気が漂っている。通路の先は行き止まりで、後ろには濃い霧が満ちている。追跡者は足音を止め、じっとこちらを見据えている。リナは子どもを背後にかばい、懐中電灯を追跡者の影へ向けたまま、カイのいる方へ慎重に身を寄せる。「カイ、子どもを連れて壁際へ。私が光で足元を照らすから、影が動いたらすぐに知らせて」「リナ、先に行け。俺がここを見ている。影が動いたら、迷わず走れ」地上から遠雷のような街のざわめきが届き、すぐに霧へ吸われて消える。

### Reader-visible events

```json
[
  {
    "id": "event_0275",
    "turn": 30,
    "type": "character_action",
    "cause": "character:char_001:0",
    "text": "リナは子どもを背後にかばい、懐中電灯を追跡者の影へ向けたまま、カイのいる方へ慎重に身を寄せる。",
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
    "id": "event_0276",
    "turn": 30,
    "type": "character_dialogue",
    "cause": "character:char_001:1",
    "text": "「カイ、子どもを連れて壁際へ。私が光で足元を照らすから、影が動いたらすぐに知らせて」",
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
    "id": "event_0278",
    "turn": 30,
    "type": "character_dialogue",
    "cause": "character:char_002:1",
    "text": "「リナ、先に行け。俺がここを見ている。影が動いたら、迷わず走れ」",
    "visibility": "reader",
    "known_by": [],
    "hidden_from": [],
    "effects": {
      "character_id": "char_002",
      "target_id": "char_001"
    },
    "roll_ids": [
      "roll_0126"
    ]
  },
  {
    "id": "event_0280",
    "turn": 30,
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

## 機械証跡

- metrics_json: `sandbox/20260714-issue085-gpt56-luna-low-v2/metrics.json`
- leak_scan: `PASS` — critical/high findingなし
- resume: `PASS` — checkpoint turn 15、resumed turn 16
- provider_failures: none

## 結論

- failed_items: pacing SLO、thread SLO、human rubric R1/R3/R5
- rerun_required: `YES`（修正後）
- notes: モデル呼び出しは安定完走したが、物語進行と反復品質がgate閾値を満たさない。
