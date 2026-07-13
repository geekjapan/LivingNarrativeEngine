# Living Narrative Engine 企画書
## リアルタイム物語生成・介入型ナラティブエンジン構築計画

作成日: 2026-07-03
文書種別: 企画書 / システム構想書 / 完成ロードマップ
想定リポジトリ名: `LivingNarrativeEngine` / `NarrativeWorldPlayer` / `StoryWorldEngine`
想定読者: プロジェクトオーナー、設計者、AIコーディングエージェント、将来の協力者

---

# 0. エグゼクティブサマリ

本企画は、ユーザーがリアルタイムまたはターン単位で生成される物語を楽しみ、その物語世界に多様な形で介入できるシステムを構築するものである。

従来の「AI小説生成」は、完成した文章を出力することを中心に置きがちである。しかし本システムの核は、文章生成ではない。核は、**物語世界そのものを状態として保持し、キャラクター・世界パラメータ・乱数・因果関係・ユーザー介入により自律的に進行させること**である。

ユーザーは、物語世界を眺めることもできるし、毎ターン指示を出すこともできる。さらに、GM、作者、神視点の観測者、特定キャラクターのプレイヤー、演出家、世界法則の編集者として、複数のレベルで介入できる。

このシステムは、初期段階ではテキストベースのリアルタイム物語プレイヤーとして構築する。将来的には、物語ログを小説原案へ変換したり、TRPG支援、RPG、ビジュアルノベル、画像生成AIを統合したゲームへ派生させたりできる。

本プロジェクトの最重要原則は次の通りである。

- **物語を「書く」のではなく、物語世界を「動かす」。**
- **本文は成果物であり、正本は世界状態・キャラクター状態・イベントログ・介入履歴・状態差分である。**
- **ユーザー介入は単なるプロンプトではなく、監査可能な世界イベントとして記録する。**
- **乱数と自律性により予測不能性を持たせるが、状態管理と検査により物語破綻を抑制する。**
- **小説化・TRPG化・RPG化・画像ゲーム化は、コアエンジンの上に載る派生レイヤとして設計する。**

---

# 1. 企画名

## 1.1 仮称

**Living Narrative Engine**

## 1.2 代替名称

- Narrative World Player
- Autonomous Story Player
- StoryWorld Engine
- Multi-Agent Narrative Player
- Interactive Narrative Simulator
- Living Story World
- AI物語世界シミュレーター
- 介入型ナラティブエンジン
- 自律物語世界プレイヤー

## 1.3 推奨名称

初期プロダクト名としては、**Living Narrative Engine** または **Narrative World Player** が適切である。

理由は、単なる「Novel Writer」ではなく、ユーザーが物語世界を観測し、介入し、遊ぶシステムであることを明確に示せるためである。

---

# 2. 企画の核

## 2.1 基本コンセプト

本システムは、ユーザーがリアルタイムで生成される物語を楽しむためのシステムである。

物語は、固定された一本道のシナリオではない。世界には様々なパラメータがあり、個々のキャラクターは性格・目的・感情・知識・秘密・関係性を持つ。さらに、世界イベントや乱数が加わり、物語は自律的に進行する。

ユーザーは、以下のような形で物語世界に介入できる。

- ターンごとに自由文で指示する。
- キャラクターに行動方針を与える。
- 世界イベントを挿入する。
- 天候、緊張度、危険度、勢力状況などの世界パラメータを変更する。
- 成功・失敗・遭遇などを乱数で判定させる。
- 神視点でCanonや秘密を編集する。
- GMとして状態差分を承認・却下・修正する。
- 何もせず、自律的なストーリーを眺める。

この体験は、AI小説生成、TRPG、RPG、ビジュアルノベル、箱庭シミュレーション、ローグライク的な乱数展開、AIキャラクター会話の中間に位置する。

## 2.2 一文での定義

> Living Narrative Engine は、AIエージェント群・世界状態・乱数・ユーザー介入によって、物語世界をリアルタイムに進行させ、ユーザーが観測・介入・再利用できる介入型ナラティブシミュレーション基盤である。

## 2.3 本質

本システムの本質は、次の一文に集約できる。

> 物語を「完成文章」として生成するのではなく、物語世界を「状態遷移」として進行させ、その結果をユーザーがリアルタイムに体験する。

---

# 3. 背景と課題認識

## 3.1 既存のAI小説生成の限界

現在のAI小説生成では、短い文章や単発の章は生成できても、長期的・自律的・対話的な物語体験には弱い。

典型的な課題は次の通りである。

- 長く続けるとCanonが矛盾する。
- キャラクターが設定と違う行動をする。
- キャラクターが知ってはいけない情報を知っているように振る舞う。
- 伏線や秘密が雑に処理される。
- ユーザーが介入すると前後関係が崩れる。
- 物語が一方的な文章生成に留まり、「遊ぶ」体験になりにくい。
- 生成ログを後から小説・TRPG・ゲームに再利用しにくい。
- ランダム性や世界シミュレーションが弱く、展開が平板になりやすい。
- 何がなぜ起きたのか、後から検証しにくい。

## 3.2 既存ジャンルの強み

本企画は、複数の既存ジャンルの強みを取り込む。

| 領域 | 強み |
|---|---|
| AI小説生成 | 文章表現、情景描写、台詞生成 |
| TRPG | GM裁定、プレイヤー介入、予測不能な共同創作 |
| RPG | キャラクター成長、探索、戦闘、クエスト |
| 箱庭シミュレーション | 世界状態の自律変化 |
| ローグライク | 乱数による毎回異なる体験 |
| ビジュアルノベル | 物語体験としての見せ方 |
| AIチャット | 自由入力と自然言語介入 |
| 生成AI画像 | シーン・キャラクター・背景の視覚化 |

ただし、これらを無秩序に混ぜると破綻する。
したがって、コアはあくまで **物語世界状態の自律進行エンジン** とし、各ジャンル要素は派生レイヤとして載せる。

## 3.3 解くべき中心課題

本システムが解くべき中心課題は、次の通りである。

1. ユーザーがリアルタイムに生成される物語を楽しめること。
2. 物語が世界状態とキャラクター状態に基づいて自律進行すること。
3. ユーザー介入が自然に世界へ反映されること。
4. 乱数による予測不能性と、物語としての整合性を両立すること。
5. 状態、ログ、介入、判定、生成文章を後から再利用できること。
6. 将来的な小説化・TRPG化・RPG化・画像ゲーム化へ拡張できること。

---

# 4. プロダクトビジョン

## 4.1 長期ビジョン

Living Narrative Engine は、ユーザーごとに異なる「生きた物語世界」を作り出す。

ユーザーは、そこに存在するキャラクターの行動を眺め、必要に応じて世界へ介入し、時にはキャラクターとして参加し、時にはGMとして裁定し、時には作者として演出する。

最終的には、次のような体験を実現する。

- 自律進行する群像劇を眺める。
- 物語が想定外の方向へ転がるのを楽しむ。
- キャラクター同士の関係変化を追う。
- 世界の危機や事件の進展を観測する。
- 自分の介入によって物語が変化するのを見る。
- 面白いログを小説原案にする。
- TRPGセッションのように遊ぶ。
- 画像生成AIと組み合わせてビジュアル付き物語ゲームとして楽しむ。

## 4.2 プロダクトの最終形

最終形では、以下を備える。

- 作品・キャンペーン単位のワークスペース管理。
- 世界状態・キャラクター状態・勢力状態・場所・時間・イベントの構造化管理。
- 複数AIエージェントによる自律ターン進行。
- ユーザーの自由文介入と構造化介入。
- 乱数・判定・イベントテーブル。
- GM/作者/観測者/プレイヤーモード。
- 状態差分レビューと承認。
- リアルタイムまたは準リアルタイムUI。
- ターンログ、リプレイ、分岐、巻き戻し。
- 小説原案化、シナリオ化、TRPGリプレイ化。
- 画像生成AI・音声生成・ゲームUIへの拡張。
- セキュリティ・権利・再現性を考慮したローカルファースト運用。

---

# 5. プロダクトの基本思想

## 5.1 本文生成ファーストではなく状態ファースト

本システムの正本は、生成された本文ではない。
正本は、世界状態・キャラクター状態・イベントログ・ユーザー介入ログ・乱数ログ・状態差分である。

本文は、それらをユーザーが楽しめるようにレンダリングした出力である。

この設計により、以下が可能になる。

- 同じ状態から別文体で再レンダリングする。
- ログから小説原案を作る。
- TRPGリプレイ風に出力する。
- ゲームイベントログに変換する。
- 途中から分岐再実行する。
- 破綻時に状態差分を巻き戻す。
- キャラクターごとの知識範囲を制御する。
- 未公開情報の漏洩を検査する。

## 5.2 ユーザー介入を第一級オブジェクトにする

ユーザーの指示は、単なるプロンプトとして消費して消すのではなく、**Intervention Event** として保存する。

例:

```yaml
intervention:
  id: int_0042
  turn: 18
  user_role: gm
  type: world_directive
  target: scene
  content: "このタイミングで停電を起こす。ただし原因はまだ明かさない"
  visibility: reader_visible_result_only
  constraints:
    reveal_cause: false
    preserve_mystery: true
```

これにより、後から「なぜその展開になったのか」を追跡できる。

## 5.3 乱数を制御された不確実性として扱う

物語には予測不能性が必要である。
しかし、完全ランダムでは物語が壊れる。

したがって、乱数は次のように扱う。

- 状態パラメータによって重みづけする。
- キャラクター能力や関係性を修正値にする。
- 重大結果はユーザー確認で止める。
- 乱数seedと結果を保存する。
- 重要な判定は再実行・巻き戻し可能にする。

例:

```yaml
roll:
  id: roll_0018
  type: stealth_check
  base_chance: 55
  modifiers:
    weather: +10
    character_fatigue: -15
    enemy_alertness: -20
  final_chance: 30
  roll: 41
  result: failure
```

## 5.4 情報スコープを分離する

物語の面白さには、秘密、誤解、読者への非開示、キャラクターごとの知識差が重要である。
そのため、情報スコープを明確に分ける。

- GM Vault: GMまたはシステムだけが知っている真実。
- Canon State: 世界の真実として確定した事実。
- Reader State: ユーザー・読者に見えている情報。
- Scene State: 現在シーンに限定される情報。
- Character State: 各キャラクターが知っている情報。
- Private Mind: 各キャラクターの内面、秘密、誤解、意図。
- Narrator Context: ナレーターが描写してよい情報。

## 5.5 AIエージェントに全知を与えない

すべてのエージェントに全情報を渡してはいけない。

キャラクターエージェントには、そのキャラクターが知っている情報だけを渡す。
ナレーターには、読者に公開してよい情報だけを渡す。
State Managerには、状態更新候補を作るために必要な情報を渡す。
Checkerには、検査に必要な情報を渡す。

これにより、以下を防ぐ。

- キャラクターが未公開情報を知っているように振る舞う。
- ナレーションが読者に秘密を漏らす。
- GMだけが知る真実が本文に出る。
- 他キャラクターの秘密を勝手に使う。
- 物語の緊張感が失われる。

---

# 6. 対象ユーザー

## 6.1 一次ターゲット

初期ターゲットは次の通りである。

- AI生成物語を読むだけでなく、介入して楽しみたいユーザー。
- TRPGのGM的な遊び方が好きなユーザー。
- AIキャラクター同士の自律的な掛け合いを眺めたいユーザー。
- 箱庭型・群像劇型のストーリー生成に興味があるユーザー。
- 小説やシナリオの原案を作りたい創作者。
- 自分専用の物語世界を育てたいユーザー。
- ローカルLLMや自律AIエージェントを試したい技術ユーザー。

## 6.2 二次ターゲット

派生段階では次の層にも広がる。

- TRPGシナリオ制作者。
- RPG制作者。
- ビジュアルノベル制作者。
- AIキャラクターゲーム制作者。
- 小説投稿者。
- ゲーム実況・配信用の物語生成をしたいユーザー。
- 教育・訓練・ロールプレイ演習に使いたいユーザー。
- シミュレーション型教材を作りたいユーザー。

## 6.3 初期段階で主対象にしないユーザー

MVPでは次の期待には応えない。

- 完成商用ゲームを即座に作りたいユーザー。
- 完全自動で出版品質の長編小説を得たいユーザー。
- 複雑な3DゲームやMMOのような体験を期待するユーザー。
- マルチユーザーオンラインTRPGを期待するユーザー。
- 既存著作物の二次創作を公開前提で量産したいユーザー。

---

# 7. コア体験

## 7.1 観測する体験

ユーザーは、自律的に進む物語を眺める。

体験例:

```text
ユーザー:
  「5ターン進める」

システム:
  霧の旧市街で、リナとカイは無人駅へ入る。
  遠くで金属音が響く。
  カイはその音に過剰に反応し、リナは彼が何かを隠していると感じる。
  世界パラメータ danger_level が上昇する。
  未解決スレッド「カイの秘密」が強化される。
```

このモードでは、ユーザーは「観客」として世界の進行を楽しむ。

## 7.2 ターンごとに介入する体験

ユーザーは、各ターンで指示を出せる。

例:

```text
ユーザー:
  「リナにはカイの様子がおかしいことに気づかせたい。ただし、カイの秘密はまだ明かさない」

システム:
  指示を character_directive と reveal_control に分解。
  リナの観察行動を強化。
  カイの秘密は Reader State に出さない。
  次ターンで緊張した会話を生成。
```

## 7.3 GMとして裁定する体験

ユーザーは、GMとして物語を制御する。

例:

```text
システム:
  追跡者が接近しています。
  リナが気づけるか判定しますか？

ユーザー:
  「2d6で7以上なら気づく。失敗したらカイだけが先に気づく」

システム:
  roll = 6
  失敗。
  カイだけが追跡者に気づき、リナには隠す。
```

## 7.4 作者として演出する体験

ユーザーは、作者として物語の見せ方に介入する。

例:

```text
ユーザー:
  「このシーンは会話を少なめにして、音と気配で不穏さを出す。章末フックになるように」

システム:
  tone_control、pacing_control、scene_goal として反映。
  ナレーターが描写重視で出力。
  最後に未解決の気配を残す。
```

## 7.5 キャラクターとして参加する体験

ユーザーは、特定キャラクターを担当できる。

例:

```text
ユーザー:
  char_001 リナとして発言:
  「カイ、さっきから何を隠してるの？」

システム:
  リナの発言を入力として扱う。
  カイ、ミラ、世界イベントをAIが応答。
  GM判断が必要な場合は停止。
```

## 7.6 ログを小説原案にする体験

ユーザーは、セッションログを後から小説原案にできる。

出力例:

- シーン一覧。
- 章構成。
- 主要イベント。
- キャラクター変化。
- 伏線一覧。
- 小説草稿。
- TRPGリプレイ。
- ゲームシナリオJSON。

---

# 8. ユーザーモード

## 8.1 Watcher Mode

観測者モード。
ユーザーは物語を見るだけで、介入しない。

主な用途:

- 自律生成ストーリーを眺める。
- キャラクター同士の自然な関係変化を見る。
- 乱数による展開を楽しむ。
- 作業中のBGM的に物語を流す。

## 8.2 Assistant GM Mode

補助GMモード。
システムが基本進行し、重要な判断点でユーザーに確認する。

停止条件例:

- キャラクター死亡。
- 重大な秘密の開示。
- Canonに大きな変更が入る。
- 情報リークの可能性。
- ユーザーの方針確認が必要。
- 物語分岐が大きい。

## 8.3 Full GM Mode

ユーザーがGMとして積極的に介入する。

できること:

- イベント投入。
- 判定条件指定。
- NPC行動の方向づけ。
- 伏線・秘密管理。
- 状態差分承認。
- シーン切り替え。
- 失敗結果の調整。

## 8.4 Author Mode

作者モード。
物語としての完成度を重視する。

できること:

- シーン目的指定。
- テーマ指定。
- 文体指定。
- 章末フック指定。
- 視点人物指定。
- 伏線配置。
- 感情線の調整。
- 小説化のためのリライト。

## 8.5 Player Character Mode

ユーザーが特定キャラクターを演じる。

できること:

- 自分のキャラクターとして発言。
- 行動入力。
- 判定要求。
- 所持品使用。
- 他キャラクターへの対話。
- 物語世界内での探索。

## 8.6 God Mode

神視点モード。
世界そのものを編集できる。

できること:

- Canon編集。
- 世界法則編集。
- キャラクター秘密の変更。
- パラメータ直接変更。
- 乱数結果の上書き。
- 分岐作成。
- 巻き戻し。
- 削除・改変。

God Modeは強力だが、物語の緊張感を壊しやすいため、明示的に区別する。

---

# 9. 自律性レベル

## 9.1 manual

毎ターン、ユーザー確認を必要とする。

用途:

- GMが細かく制御したい。
- 重要なシーン。
- 小説化を前提に丁寧に進めたい。
- デバッグ。

## 9.2 assist

通常は自律進行するが、重要判断で止まる。

用途:

- 標準モード。
- ユーザーが眺めつつ適度に介入する。
- 破綻しやすい分岐だけ確認する。

## 9.3 auto

指定ターン数またはシーン終了まで自律進行する。

用途:

- 眺める体験。
- ログ大量生成。
- 物語の自然な展開を見る。
- サンプル生成。

## 9.4 watch

完全観測。
介入はしないが、介入候補は提示される。

用途:

- 物語鑑賞。
- AI箱庭観察。
- 自律ストーリー生成。

## 9.5 god

すべての状態に介入できる。

用途:

- デバッグ。
- シナリオ編集。
- 世界設定構築。
- 破綻修正。
- 分岐実験。

---

# 10. 機能要件

## 10.1 プロジェクト作成

ユーザーは新しい物語プロジェクトを作成できる。

入力項目:

- タイトル。
- ジャンル。
- トーン。
- 世界観の種。
- 初期状況。
- キャラクター人数。
- 自律性レベル。
- 乱数seed。
- LLM provider。
- 表示形式。

出力:

- `project.yaml`
- `workspace/`
- 初期 `world.yaml`
- 初期 `characters/*.yaml`
- 初期 `canon.yaml`
- 初期 `reader_state.yaml`
- 初期 `scene.yaml`

## 10.2 世界生成

世界は、以下を持つ。

- 地理。
- 時代。
- 技術水準。
- 魔法・超能力・SF設定。
- 社会制度。
- 勢力。
- 世界法則。
- 危機。
- 未解決問題。
- ランダムイベントテーブル。
- パラメータ。

例:

```yaml
world:
  id: world_mist_city
  name: 霧の都市国家エルメリア
  genre: dark_fantasy
  tone: quiet_ominous
  laws:
    - 霧の夜には失踪事件が増える
    - 旧王家の血筋は公には断絶したことになっている
  parameters:
    public_order: 45
    magic_instability: 70
    faction_tension: 62
    mystery_pressure: 55
    danger_level: 40
```

## 10.3 キャラクター生成・管理

キャラクターは、以下を持つ。

- 名前。
- 役割。
- 性格。
- 目標。
- 短期行動方針。
- 長期行動方針。
- 感情。
- 知識。
- 誤解。
- 秘密。
- 関係性。
- 所持品。
- 能力。
- 制約。
- 過去ログ要約。

例:

```yaml
character:
  id: char_001
  name: リナ
  public_role: 主人公
  personality:
    - 慎重
    - 責任感が強い
    - 過去に囚われている
  goals:
    short_term:
      - 失踪した兄の手掛かりを探す
    long_term:
      - 都市崩壊を止める
  emotions:
    fear: 35
    anger: 20
    trust: 40
    curiosity: 75
  knowledge:
    knows:
      - 旧市街に地下通路がある
    believes:
      - 兄は誘拐された
    does_not_know:
      - 兄が敵勢力に協力している
  secrets:
    - 本人も知らない血筋の秘密
```

## 10.4 シーン管理

シーンは、現在の場所・時間・登場人物・状況・緊張・目的を持つ。

例:

```yaml
scene:
  id: scene_012
  location: 旧市街の地下駅
  time: day3 22:10
  active_characters:
    - char_001
    - char_002
  mood: ominous
  stakes:
    - 追手に発見される可能性
    - 封印施設への入口が見つかる可能性
  reader_visible_facts:
    - 駅は停電している
  hidden_facts:
    - 封印施設の入口は壁の向こうにある
```

## 10.5 ターン進行

1ターンは以下で構成する。

1. 状態読み込み。
2. ユーザー介入取得。
3. 介入の構造化。
4. 世界状態更新候補。
5. キャラクター行動候補。
6. 衝突解決。
7. 乱数判定。
8. ナレーション生成。
9. 整合性チェック。
10. 情報リークチェック。
11. 状態差分生成。
12. 適用またはレビュー待ち。
13. ログ保存。
14. UI更新。

## 10.6 自律進行

ユーザーは以下を選べる。

- 次の1ターン。
- 3ターン進行。
- 5ターン進行。
- シーン終了まで進行。
- GM判断点まで進行。
- 重要イベントまで進行。
- 危険状態まで進行。

自律進行の停止条件:

- 重大なCanon更新。
- キャラクター死亡。
- キャラクター関係の重大変化。
- 重大な秘密の公開。
- ユーザー確認が必要な分岐。
- 情報リーク疑い。
- 整合性エラー。
- ランダム判定の重大失敗。
- シーン終了。
- 指定ターン到達。

## 10.7 ユーザー介入

介入タイプ:

- `scene_directive`
- `character_directive`
- `world_directive`
- `event_injection`
- `probability_bias`
- `tone_control`
- `pacing_control`
- `reveal_control`
- `hidden_truth_edit`
- `canon_edit`
- `dice_roll_request`
- `stop_condition`
- `scene_pivot`
- `relationship_edit`
- `memory_edit`

## 10.8 乱数・判定

必要機能:

- seed管理。
- ダイス表記対応。
- 成功確率判定。
- 修正値。
- イベントテーブル。
- 結果ログ。
- reroll。
- accept/reject。
- GM override。

## 10.9 ナレーション

出力形式:

- 小説風。
- TRPGリプレイ風。
- ログ風。
- 脚本風。
- ビジュアルノベル台本風。
- ゲームイベント風。
- 要約風。

## 10.10 状態差分レビュー

State Managerは、ターン結果を直接Canonへ反映せず、まず候補として出す。

例:

```yaml
state_update_candidate:
  turn: 18
  changes:
    reader_state:
      add:
        - 停電が発生した
    character_state:
      char_001:
        emotions:
          fear: +15
        knowledge:
          add:
            - 誰かが意図的に電力を落とした可能性
    world_parameters:
      danger_level: +8
```

ユーザーは以下を選ぶ。

- accept all
- reject all
- edit
- apply partially
- rerun turn
- branch from here

## 10.11 ログ・リプレイ

保存対象:

- ユーザー入力。
- 構造化介入。
- 各エージェント入力。
- 各エージェント出力。
- 乱数結果。
- 競合解決結果。
- ナレーション。
- チェック結果。
- 状態差分候補。
- 適用結果。
- UI表示履歴。

## 10.12 小説原案化

ログから以下を出力する。

- シーンリスト。
- 章構成。
- 主要イベント一覧。
- キャラクター変化。
- 感情線。
- 伏線一覧。
- 章草稿。
- 小説原案Markdown。
- 改稿指示。
- 読者向け要約。

---

# 11. 非機能要件

## 11.1 応答性

初期MVPは、完全なリアルタイムではなく、準リアルタイムのターン制でよい。

目標:

| 処理 | 目標時間 |
|---|---:|
| mock turn | 1秒未満 |
| 軽量LLM 1ターン | 5〜15秒 |
| 通常LLM 1ターン | 15〜45秒 |
| 複数Agent + Check | 30〜90秒 |
| 5ターン自律進行 | 2〜5分以内 |

## 11.2 再現性

保存するもの:

- random seed。
- input state。
- user intervention。
- model provider。
- model name。
- promptsまたはprompt hash。
- random rolls。
- state diff。
- output artifacts。

## 11.3 拡張性

プラグイン化する対象:

- LLM provider。
- Renderer。
- Exporter。
- Random rule。
- Game rule。
- Image generation。
- Voice generation。
- UI。
- Storage。
- Checker。

## 11.4 可観測性

必要なログ:

- ターン処理時間。
- LLM呼び出し回数。
- token使用量。
- 失敗率。
- checker結果。
- rerun回数。
- 状態差分数。
- ユーザー介入数。

## 11.5 セキュリティ

最低要件:

- APIキーをログに出さない。
- `.env` をコミットしない。
- ローカルWeb UIはデフォルトで `127.0.0.1` bind。
- 外部通信先を明示。
- plugin実行はsandbox化。
- ユーザーデータとシステム設定を分離。
- Web投稿や外部公開は初期MVPに含めない。
- 生成ログに秘匿情報が混ざる前提でprivate運用を推奨。

## 11.6 権利・倫理

方針:

- 初期はユーザーが権利を持つ素材または完全オリジナル世界を前提にする。
- 既存作品の本文取り込みは初期MVPに含めない。
- fanfiction modeはprivate/local useを前提とする。
- raw text非保持モードを将来用意する。
- 公開・投稿・商用利用は明示的に別機能として扱う。
- 画像生成連携時は、モデル・プロンプト・生成物の権利リスクをUI上で明示する。

---

# 12. システム全体構想

## 12.1 論理アーキテクチャ

```text
[User Interface]
    |
    v
[Session Controller]
    |
    v
[Turn Orchestrator]
    |
    +--> [Intervention Interpreter]
    +--> [Context Builder]
    +--> [World Simulator]
    +--> [Character Agents]
    +--> [Conflict Resolver]
    +--> [Random Engine]
    +--> [Narrator / Renderer]
    +--> [Continuity Checker]
    +--> [Information Leak Checker]
    +--> [State Manager]
    +--> [Logger / Replay Store]
    +--> [Exporter]
```

## 12.2 レイヤ構成

```text
Presentation Layer
  Web UI / CLI / TUI / API

Application Layer
  Session Controller
  Turn Orchestrator
  User Mode Manager
  Autonomy Controller

Narrative Runtime Layer
  World Simulator
  Character Agents
  Conflict Resolver
  Narrator
  Director / GM Assistant

State Layer
  Project State
  World State
  Character State
  Scene State
  Canon State
  Reader State
  GM Vault
  Event Log

LLM Layer
  Provider Abstraction
  Prompt Builder
  Structured Output Parser
  Mock Provider

Persistence Layer
  SQLite
  YAML/JSON artifacts
  Markdown logs
  Optional object storage

Extension Layer
  Novel Exporter
  TRPG Module
  RPG Rule Module
  Image Renderer
  Voice Renderer
  Visual Novel Renderer
```

## 12.3 物理構成 MVP

初期MVPではローカル実行を基本にする。

```text
Local Machine
  ├─ FastAPI backend
  ├─ SQLite DB
  ├─ workspace files
  ├─ Web UI at 127.0.0.1
  ├─ LLM provider
  │    ├─ OpenAI-compatible API
  │    ├─ Ollama
  │    ├─ LM Studio
  │    └─ mock
  └─ Markdown / JSON / YAML artifacts
```

## 12.4 将来構成

```text
Local / Private Server
  ├─ Web frontend
  ├─ API backend
  ├─ Worker queue
  ├─ SQLite or PostgreSQL
  ├─ Artifact storage
  ├─ Model gateway
  ├─ Image generation worker
  ├─ Game renderer
  └─ Optional multi-user session service
```

---

# 13. 主要コンポーネント

## 13.1 Session Controller

責務:

- project読み込み。
- campaign/session開始。
- 現在ターン管理。
- 自律性レベル管理。
- ユーザーモード管理。
- save/resume。
- branch管理。
- rollback管理。

## 13.2 Turn Orchestrator

責務:

- 1ターンの実行順序管理。
- agent呼び出し。
- checker呼び出し。
- state diff生成。
- artifact保存。
- 例外処理。
- stop condition判定。

## 13.3 Intervention Interpreter

責務:

- ユーザー自由文の解釈。
- 介入タイプ分類。
- 対象特定。
- 可視性分類。
- 制約抽出。
- 構造化intervention生成。

## 13.4 Context Builder

責務:

- 各agentに渡す最小コンテキストを構築。
- GM Vaultの漏洩防止。
- Characterごとの知識制限。
- Narratorの可視範囲制御。
- token節約のための要約・抽出。

## 13.5 World Simulator

責務:

- 時間経過。
- 天候変化。
- 勢力行動。
- 背景イベント。
- 世界パラメータ更新。
- ランダムイベント発生。
- 期限付きイベント処理。

## 13.6 Character Agent

責務:

- キャラクターの行動候補生成。
- 発言候補生成。
- 内面反応生成。
- 感情変化候補。
- 目標更新候補。
- 秘密保持判断。
- 他者への反応。

## 13.7 Conflict Resolver

責務:

- 複数キャラクターの行動衝突を解決。
- 世界イベントとの整合。
- 乱数判定の適用。
- 行動結果の決定。
- イベント列への変換。

## 13.8 Random Engine

責務:

- seed管理。
- dice parser。
- success/failure判定。
- weighted table。
- modifiers。
- random event selection。
- roll log保存。

## 13.9 Narrator / Renderer

責務:

- 読者可視情報だけで本文生成。
- 文体・トーン制御。
- 出力形式切替。
- 物語として読みやすく整形。
- 未公開情報を漏らさない。

## 13.10 Checker

責務:

- continuity check。
- leak check。
- character consistency check。
- pacing check。
- user constraint check。
- repeated phrase check。
- stale plot check。

## 13.11 State Manager

責務:

- resolved eventsからstate diff生成。
- diff validation。
- apply/reject。
- partial apply。
- rollback。
- branch作成。

## 13.12 Logger / Replay Store

責務:

- turn artifact保存。
- agent input/output保存。
- narration保存。
- random log保存。
- checks保存。
- replay生成。
- audit trail生成。

## 13.13 Exporter

責務:

- Markdown replay。
- novel outline。
- chapter draft。
- TRPG replay。
- game scenario JSON。
- visual novel script。
- dataset for regression。

---

# 14. データモデル

## 14.1 Project

```yaml
project:
  id: mist_city_001
  title: 霧の駅
  genre: mystery_fantasy
  tone: quiet_ominous
  autonomy_level: assist
  user_mode: assistant_gm
  random_seed: 20260703-mist-city
  default_renderer: novel
  llm:
    provider: mock
    model: mock-v1
  paths:
    workspace: workspace
    runs: runs
```

## 14.2 World

```yaml
world:
  id: world_001
  name: 霧の都市国家エルメリア
  summary: 魔法文明崩壊後の都市国家
  laws:
    - 霧の夜には失踪事件が増える
    - 旧王家の血筋は断絶したことになっている
  parameters:
    public_order: 45
    magic_instability: 70
    faction_tension: 62
    mystery_pressure: 55
    danger_level: 40
```

## 14.3 Faction

```yaml
faction:
  id: faction_001
  name: 旧王党派
  public_face: 存在しないとされる地下組織
  goals:
    - 旧王家の血筋を探す
    - 封印施設を再起動する
  resources:
    influence: 40
    military: 20
    secrecy: 80
  relations:
    faction_002:
      hostility: 70
```

## 14.4 Character

```yaml
character:
  id: char_001
  name: リナ
  role: 主人公
  traits:
    - 慎重
    - 責任感が強い
  goals:
    short_term:
      - 兄の手掛かりを探す
    long_term:
      - 都市崩壊を止める
  emotions:
    fear: 35
    anger: 20
    trust: 40
    curiosity: 75
  knowledge:
    knows:
      - 旧市街に地下通路がある
    believes:
      - 兄は誘拐された
    does_not_know:
      - 兄が敵勢力に協力している
  secrets:
    - 本人も知らない血筋の秘密
```

## 14.5 Relationship

```yaml
relationship:
  from: char_001
  to: char_002
  trust: 62
  affection: 40
  tension: 25
  suspicion: 35
  notes:
    - 幼なじみ
    - 最近カイが何かを隠している
```

## 14.6 Scene

```yaml
scene:
  id: scene_001
  title: 霧の地下駅
  location: 旧市街の地下駅
  time: day3 22:10
  active_characters:
    - char_001
    - char_002
  mood: ominous
  stakes:
    - 追跡者に発見される
    - 封印施設の入口に気づく
  reader_visible_facts:
    - 駅は停電している
  hidden_facts:
    - 壁の奥に封印施設がある
```

## 14.7 Event

```yaml
event:
  id: event_0081
  turn: 18
  type: blackout
  cause: enemy_action
  visibility: reader_visible_result_only
  known_by:
    - char_003
  hidden_from:
    - char_001
    - char_002
  effects:
    world_parameters:
      danger_level: +8
    scene:
      visibility: -30
```

## 14.8 Intervention

```yaml
intervention:
  id: int_0021
  turn: 18
  user_role: gm
  type: world_directive
  target: scene
  content: 停電を起こす。ただし原因はまだ明かさない
  constraints:
    do_not_reveal_cause: true
    keep_scene_tense: true
```

## 14.9 Roll

```yaml
roll:
  id: roll_0018
  turn: 18
  type: detection_check
  dice: 2d6
  target: 7
  result_value: 6
  outcome: failure
  consequences:
    - リナは追跡者に気づかない
    - カイだけが気づく
```

## 14.10 State Diff

```yaml
state_diff:
  id: diff_0018
  turn: 18
  changes:
    reader_state:
      add:
        - 停電が発生した
    character_state:
      char_002:
        knowledge:
          add:
            - 追跡者が近づいている
        emotions:
          fear: +10
    world:
      parameters:
        danger_level: +8
```

---

# 15. ターンパイプライン

## 15.1 標準ターン

```text
1. Load Project
2. Load Current State
3. Load Recent Memory
4. Receive User Input
5. Interpret Intervention
6. Build Agent Contexts
7. Advance World
8. Run Character Agents
9. Resolve Conflicts
10. Execute Random Rolls
11. Generate Narration
12. Run Checks
13. Generate State Diff
14. Apply or Review
15. Persist Artifacts
16. Render UI
```

## 15.2 自律ターン

```text
1. 自動進行条件を確認
2. GM判断点がないか確認
3. 軽量World Simulator実行
4. 関連キャラクターのみagent実行
5. event resolution
6. narration
7. check
8. state diff auto-applyまたは停止
```

## 15.3 GMレビュー付きターン

```text
1. ターン実行
2. state_update_candidate生成
3. UIでdiff表示
4. ユーザーがaccept/reject/edit
5. apply後に次ターンへ
```

## 15.4 失敗時処理

失敗パターン:

- LLM出力がschema不一致。
- 情報リーク疑い。
- continuity error。
- 乱数結果が重大。
- ユーザー制約違反。
- agent timeout。
- token過多。

対応:

- retry。
- fallback renderer。
- stop for review。
- partial artifact保存。
- rollback。
- safe summary only output。

---

# 16. UI構想

## 16.1 MVP UI

MVPでは、ローカルWeb UIを推奨する。

画面構成:

```text
+------------------------------------------------------------+
| Story Pane                                                 |
| 生成された物語本文                                         |
+--------------------------+---------------------------------+
| Characters               | World Status                    |
| 感情・関係・状態          | 時間・天候・危険度・勢力状況    |
+--------------------------+---------------------------------+
| User Intervention                                          |
| 自由文入力、介入種別、対象指定                             |
+------------------------------------------------------------+
| Controls                                                   |
| [Next Turn] [Auto 3] [Auto 5] [Stop] [Review Diff] [Log]   |
+------------------------------------------------------------+
```

## 16.2 GM Cockpit

GM向け画面:

- GM Vault。
- Canon。
- Reader State。
- Character Knowledge Matrix。
- State Diff。
- Random Rolls。
- Check Results。
- Pending Threads。
- Foreshadowing Ledger。
- Accept / Reject / Edit。

## 16.3 Timeline

表示項目:

- ターン。
- シーン。
- イベント。
- 介入。
- 乱数。
- 状態差分。
- 伏線発生。
- 伏線回収。
- キャラクター関係変化。

## 16.4 Character View

表示項目:

- 感情。
- 目的。
- 知識。
- 秘密。
- 関係性。
- 所持品。
- 直近行動。
- 内面要約。
- ユーザーからの指示履歴。

## 16.5 World View

表示項目:

- 現在時刻。
- 天候。
- 場所。
- 勢力状況。
- 危険度。
- 社会不安。
- イベントテーブル。
- 未解決危機。
- 世界法則。

---

# 17. 小説化・派生構想

## 17.1 小説原案化

物語ログを小説原案に変換する。

処理:

1. ターンログを選択。
2. 重要イベントを抽出。
3. シーン単位に統合。
4. 視点人物を決定。
5. メタ情報を削除。
6. 台詞と描写を整理。
7. 章構成へ変換。
8. 整合性チェック。
9. 改稿パス。
10. Markdown出力。

## 17.2 TRPG化

追加機能:

- PC/NPC区分。
- キャラクターシート。
- ダイスルール。
- 判定難易度。
- GM screen。
- NPC行動生成。
- セッションログ。
- リプレイ出力。
- シナリオフック生成。

## 17.3 RPG化

追加機能:

- ステータス。
- スキル。
- 装備。
- インベントリ。
- 戦闘。
- 探索。
- マップ。
- クエスト。
- 成長。
- 報酬。
- 敵AI。

## 17.4 ビジュアルノベル化

追加機能:

- シーンスクリプト。
- 台詞ウィンドウ。
- 立ち絵。
- 背景。
- 選択肢。
- 分岐。
- BGM/SFX。
- CGイベント。

## 17.5 画像生成AI連携

追加機能:

- シーン画像プロンプト生成。
- キャラクター外見プロファイル。
- 背景プロファイル。
- 画像生成履歴。
- 採用/破棄。
- 画風固定。
- キャラクター一貫性チェック。
- visual scene cache。

## 17.6 音声生成連携

追加機能:

- ナレーション音声。
- キャラクターボイス。
- 台詞読み上げ。
- 効果音。
- BGM提案。

---

# 18. 技術スタック案

## 18.1 推奨スタック MVP

```text
Language:
  Python 3.12+

Backend:
  FastAPI
  Pydantic
  SQLite
  SQLAlchemy or SQLModel

Frontend:
  Jinja2 + HTMX
  もしくは React / Next.js

LLM:
  OpenAI-compatible API
  LiteLLM
  Ollama
  LM Studio
  mock provider

Storage:
  SQLite
  YAML / JSON artifacts
  Markdown logs

Package:
  uv
  Docker Compose

Testing:
  pytest
  ruff
  mypy optional
```

## 18.2 なぜPythonか

理由:

- LLM連携が容易。
- YAML/JSON/SQLite操作が容易。
- FastAPIでローカルWeb UIを作りやすい。
- 既存のAI/LLMエコシステムが豊富。
- 画像生成やローカルLLM連携へ拡張しやすい。
- PoCからMVPまでの速度が速い。

## 18.3 ディレクトリ構成

> **Stale / historical (2026-07-13)**: 以下は初期設計時のディレクトリ構成案であり、現行の
> ファイル配置を規定しない。現行の実体はリポジトリの`src/living_narrative/`、`tests/`、
> `docs/`を参照する。

```text
living-narrative-engine/
  README.md
  pyproject.toml
  docs/
    00_project_charter.md
    01_product_thesis.md
    02_user_experience.md
    03_system_architecture.md
    04_state_model.md
    05_agent_model.md
    06_intervention_model.md
    07_turn_pipeline.md
    08_mvp_scope.md
    09_roadmap.md
    10_security_and_rights.md
    11_completion_plan.md
  src/
    living_narrative/
      app/
        web/
        api/
      core/
        session.py
        turn.py
        orchestrator.py
      state/
        models.py
        store.py
        diff.py
        validation.py
      agents/
        world_simulator.py
        character.py
        conflict_resolver.py
        narrator.py
        checker.py
        state_manager.py
        director.py
      llm/
        client.py
        providers.py
        mock.py
        schemas.py
      random/
        engine.py
        dice.py
        tables.py
      renderers/
        novel.py
        replay.py
        game_log.py
        visual_novel.py
      exporters/
        markdown.py
        novel_outline.py
        trpg_replay.py
        game_json.py
      safety/
        leak_check.py
        continuity_check.py
        rights.py
      web/
        templates/
        static/
  examples/
    mist_station/
      project.yaml
      workspace/
  tests/
```

---

# 19. GitHub運用方針

> **Stale / historical (2026-07-13)**: 以下は初期計画時のGitHub運用・文書名・優先順位の
> 記録である。現行の作業単位は`docs/issues/`、永続的な判断は`docs/adr/`、ユーザー向け
> CLI導線は`README.md`を参照する。

## 19.1 正本

GitHubリポジトリを正本とする。

優先順位:

1. `PROJECT_RULES.md`
2. `docs/`
3. Milestones
4. Issues
5. Decision Log
6. README
7. 会話ログ・ローカルメモ

## 19.2 必須ドキュメント

```text
README.md
PROJECT_RULES.md
docs/00_project_charter.md
docs/01_product_thesis.md
docs/02_user_experience.md
docs/03_system_architecture.md
docs/04_state_model.md
docs/05_agent_model.md
docs/06_intervention_model.md
docs/07_turn_pipeline.md
docs/08_mvp_scope.md
docs/09_roadmap.md
docs/10_security_and_rights.md
docs/11_completion_plan.md
docs/12_decision_log.md
```

## 19.3 Issue運用

Issueは、1回の実装・テスト・docs更新で閉じられる粒度にする。

Issueテンプレート:

```markdown
## Purpose

## Scope

## Non-Goals

## Acceptance Criteria

## Files to Touch

## Tests

## Docs Update

## Risks
```

## 19.4 Milestone運用

MilestoneはPhase単位で切る。

- M0: Specification
- M1: Text MVP
- M2: State and Agent Runtime
- M3: Web UI / GM Cockpit
- M4: Long Session Stability
- M5: Novel Export
- M6: TRPG/RPG Extension
- M7: Visual and Media Extension
- M8: Product Hardening

---

# 20. 完成までの全ロードマップ

> **Historical (2026-07-13)**: 以下は初期企画のPhaseロードマップであり、現在の完成判定や
> 実装状態を示す正本ではない。現行のリリース契約は`docs/adr/0005-v1-release-contract.md`、
> 実装計画と判定表はIssue 052/062を参照する。

## 20.1 全体方針

完成までを次の9段階に分ける。

| Phase | 名称 | 目的 |
|---:|---|---|
| 0 | Concept & Specification | 企画・仕様・MVP確定 |
| 1 | Text MVP | テキストで1シーンを進める |
| 2 | Core Runtime | 状態・agent・turn実行を安定化 |
| 3 | User Intervention & Autonomy | 介入と自律進行を完成させる |
| 4 | Web UI / GM Cockpit | 体験として遊べるUIを作る |
| 5 | Long-running Story Stability | 長期セッションを破綻しにくくする |
| 6 | Export / Novelization | ログから小説・リプレイを生成 |
| 7 | Game Extension | TRPG/RPG/ゲーム要素を拡張 |
| 8 | Visual / Media Extension | 画像・音声・ビジュアル化 |
| 9 | Productization | 配布・運用・品質・安全性を固める |

---

## Phase 0: Concept & Specification

### 目的

プロジェクトの核、非ゴール、MVP範囲、状態モデル、ターン処理、介入モデルを固める。

### 成果物

- Project Charter
- Product Thesis
- MVP Scope
- State Model
- Turn Pipeline
- Intervention Model
- Architecture
- Roadmap
- Decision Log
- GitHub Issues

### 完了条件

- 何を作るか説明できる。
- 何を作らないか説明できる。
- MVPの成功条件が明確。
- 初期サンプルシナリオがある。
- 実装Issueが切れる。

### 推奨Issue

1. Project Charterを作成する。
2. Product Thesisを作成する。
3. MVP Scopeを確定する。
4. State Modelを定義する。
5. Turn Pipelineを定義する。
6. User Intervention Modelを定義する。
7. 初期サンプルシナリオを定義する。
8. repositoryルールを作成する。

---

## Phase 1: Text MVP

### 目的

テキストだけで、物語が1ターンずつ進み、ユーザーが介入できる最小プロトタイプを作る。

### 機能

- CLIまたは簡易Web UI。
- project.yaml。
- workspace layout。
- world state。
- character state。
- scene state。
- mock LLM provider。
- turn runner。
- user intervention入力。
- random roll。
- narrator出力。
- markdown log。

### 完了条件

- サンプル世界を作成できる。
- 3〜5キャラクターで1シーンを開始できる。
- 10ターン以上進行できる。
- ユーザー介入が次ターンに反映される。
- 乱数結果がログに残る。
- Markdownリプレイを出力できる。

### 推奨Issue

1. project.yaml schemaを作る。
2. workspace layoutを作る。
3. world.yaml schemaを作る。
4. character.yaml schemaを作る。
5. scene.yaml schemaを作る。
6. mock LLM providerを作る。
7. random engineを作る。
8. turn runnerを作る。
9. narrator mockを作る。
10. markdown log exporterを作る。
11. sample worldを作る。
12. 10ターンsmoke testを作る。

---

## Phase 2: Core Runtime

### 目的

Turn Orchestrator、Context Builder、Agent群、State Managerを分離し、拡張可能な中核実行系を作る。

### 機能

- Turn Orchestrator。
- Context Builder。
- World Simulator。
- Character Agent。
- Conflict Resolver。
- Narrator。
- Checker。
- State Manager。
- State Diff。
- Artifact Store。
- LLM provider abstraction。

### 完了条件

- 各agentの入出力schemaが定義されている。
- 各agentをmockでテストできる。
- state diffを生成・適用できる。
- agentごとのcontextが分離されている。
- turn artifactが保存される。

### 推奨Issue

1. Agent I/O schemaを定義する。
2. LLMClient interfaceを実装する。
3. Context Builderを実装する。
4. Character Agentを実装する。
5. World Simulatorを実装する。
6. Conflict Resolverを実装する。
7. Narratorを実装する。
8. State Managerを実装する。
9. State Diff apply/rejectを実装する。
10. Artifact Storeを実装する。

---

## Phase 3: User Intervention & Autonomy

### 目的

ユーザー介入と自律進行をプロダクト体験として成立させる。

### 機能

- free-text intervention。
- structured intervention。
- intervention visibility。
- intervention history。
- autonomy level。
- stop conditions。
- GM review gate。
- auto N turns。
- scene-end auto進行。
- intervention suggestions。

### 完了条件

- 自由文介入を構造化できる。
- manual/assist/auto/watch/godを切り替えられる。
- stop conditionで適切に停止する。
- 介入履歴がログに残る。
- 自動進行中でも重大イベントで停止する。

### 推奨Issue

1. Intervention schemaを実装する。
2. Intervention Interpreterを実装する。
3. Intervention visibilityを実装する。
4. autonomy_levelを実装する。
5. stop conditionを実装する。
6. auto N turnsを実装する。
7. GM review gateを実装する。
8. intervention suggestionを実装する。
9. God mode編集を制限付きで実装する。

---

## Phase 4: Web UI / GM Cockpit

### 目的

システムを「使える」から「楽しめる」に引き上げる。

### 機能

- ローカルWeb UI。
- Story Pane。
- Intervention Input。
- Character Pane。
- World Status Pane。
- Timeline。
- Turn Controls。
- GM Cockpit。
- State Diff Review。
- Logs view。
- Session resume。

### 完了条件

- ユーザーがブラウザで物語を読める。
- 次ターン・自動進行・停止が操作できる。
- キャラクター状態が見える。
- 世界状態が見える。
- 状態差分を確認できる。
- 介入を入力できる。
- ログを見返せる。

### 推奨Issue

1. FastAPI appを作る。
2. Story Paneを作る。
3. Intervention Inputを作る。
4. Turn Controlsを作る。
5. Character Paneを作る。
6. World Status Paneを作る。
7. Timeline Paneを作る。
8. State Diff Reviewを作る。
9. Session Pickerを作る。
10. Local-only bindingを確認する。

---

## Phase 5: Long-running Story Stability

### 目的

長く遊んでも物語が壊れにくいようにする。

### 機能

- memory summary。
- relationship graph。
- faction state。
- foreshadowing ledger。
- unresolved threads。
- continuity checker。
- leak checker。
- pacing checker。
- character consistency checker。
- regression scenarios。
- branch/rollback。

### 完了条件

- 50ターン以上のセッションを維持できる。
- キャラクターの知識範囲が保たれる。
- 未公開情報の漏洩を検知できる。
- 伏線・未解決threadが追跡される。
- 分岐と巻き戻しが可能。
- regression fixtureで品質低下を検知できる。

### 推奨Issue

1. Memory Summaryを実装する。
2. Relationship Graphを実装する。
3. Faction Stateを実装する。
4. Foreshadowing Ledgerを実装する。
5. Unresolved Threadsを実装する。
6. Continuity Checkerを実装する。
7. Leak Checkerを実装する。
8. Character Consistency Checkerを実装する。
9. Branch/Rollbackを実装する。
10. 50ターンregression testを作る。

---

## Phase 6: Export / Novelization

### 目的

物語ログを小説原案・TRPGリプレイ・シナリオ素材として再利用できるようにする。

### 機能

- scene reconstruction。
- event extraction。
- chapter outline。
- novel draft exporter。
- replay exporter。
- character arc summary。
- foreshadowing report。
- revision pass。
- publish bundle draft。
- Obsidian export optional。

### 完了条件

- セッションログからシーン一覧を作れる。
- ログから章原案を作れる。
- 小説風Markdownを出力できる。
- TRPGリプレイ風出力ができる。
- 伏線・キャラクター変化の一覧が出せる。

### 推奨Issue

1. Scene Reconstructionを実装する。
2. Important Event Extractorを実装する。
3. Chapter Outline Exporterを実装する。
4. Novel Draft Exporterを実装する。
5. TRPG Replay Exporterを実装する。
6. Character Arc Summaryを実装する。
7. Foreshadowing Reportを実装する。
8. Revision Passを実装する。

---

## Phase 7: Game Extension

### 目的

TRPG/RPG的に遊べる拡張を作る。

### 機能

- character sheet。
- stats。
- skills。
- dice rules。
- inventory。
- quest。
- map。
- combat。
- NPC AI。
- encounter table。
- reward system。

### 完了条件

- ユーザーがPCとして参加できる。
- スキル判定ができる。
- アイテム管理ができる。
- クエスト状態が管理できる。
- 簡易戦闘ができる。
- TRPGセッションログとして出力できる。

### 推奨Issue

1. PC/NPC modelを追加する。
2. Stats/Skills schemaを追加する。
3. Dice Rule moduleを作る。
4. Inventoryを作る。
5. Quest modelを作る。
6. Map/Location graphを作る。
7. Encounter tableを作る。
8. Simple combatを作る。
9. TRPG session modeを作る。

---

## Phase 8: Visual / Media Extension

### 目的

画像・音声・ビジュアルノベル的な表示へ拡張する。

### 機能

- image prompt generator。
- character visual profile。
- background profile。
- scene image generation。
- image gallery。
- visual novel renderer。
- voice prompt。
- TTS integration。
- BGM/SFX suggestion。
- asset cache。

### 完了条件

- シーンごとに画像プロンプトを作れる。
- キャラクター外見を維持できる。
- 背景画像を生成・保存できる。
- 物語本文と画像を並べて表示できる。
- ビジュアルノベル風のscriptを出力できる。

### 推奨Issue

1. Visual Profile schemaを作る。
2. Image Prompt Generatorを作る。
3. Image Provider Interfaceを作る。
4. Scene Image Cacheを作る。
5. Visual Novel Rendererを作る。
6. Voice Prompt Exporterを作る。
7. Asset rights noteを追加する。

---

## Phase 9: Productization

### 目的

長期利用できる配布・運用品質に仕上げる。

### 機能

- installer。
- Docker Compose。
- user data directory。
- backup/restore。
- migration。
- settings UI。
- model profile。
- cost tracking。
- telemetry optional/local only。
- documentation。
- sample worlds。
- plugin SDK。
- security review。
- rights guidance。

### 完了条件

- 新規ユーザーがREADMEだけで起動できる。
- サンプル世界で遊べる。
- データをバックアップ・復元できる。
- バージョンアップ時にstate migrationできる。
- plugin追加方法がある。
- 権利・セキュリティ注意が明記されている。
- 長期ロードマップに基づく安定運用ができる。

### 推奨Issue

1. Docker Composeを整備する。
2. Installer/Quick Startを整備する。
3. Settings UIを作る。
4. Model Profileを作る。
5. Cost Trackingを作る。
6. Backup/Restoreを作る。
7. Migration frameworkを作る。
8. Plugin SDKを設計する。
9. Sample Worldsを増やす。
10. Security/rights docsを仕上げる。

---

# 21. MVP詳細計画

> **Historical (2026-07-13)**: 以下は初期MVPの範囲・成功条件・サンプル世界を保存した記録で
> あり、現行実装の全提供範囲ではない。現在の起動・CLI利用方法は`README.md`を参照する。

## 21.1 MVP名

**Text-based Living Story Player**

## 21.2 MVP目的

ユーザーが、テキストベースで自律進行する物語をターンごとに眺め、必要に応じて介入できることを実証する。

## 21.3 MVP範囲

含めるもの:

- project.yaml。
- workspace。
- world state。
- scene state。
- character state。
- turn runner。
- mock provider。
- OpenAI-compatible provider optional。
- random roll。
- user intervention。
- narrator。
- state diff。
- markdown logs。
- simple UI or CLI。

含めないもの:

- 本格GUI。
- 画像生成。
- 音声。
- Web投稿。
- PDF/ePub。
- マルチユーザー。
- 本格RPG戦闘。
- 複雑な既存作品DB。
- 完全自律長編生成。

## 21.4 MVP成功条件

- 3〜5キャラクターのサンプル世界を開始できる。
- 10〜20ターン進行できる。
- ユーザー介入が反映される。
- 乱数により展開が変化する。
- 状態差分が保存される。
- ログからリプレイを読める。
- 重大な情報リークを簡易チェックできる。
- session resumeできる。

## 21.5 MVPサンプル世界

```text
タイトル:
  霧の駅

ジャンル:
  ミステリ・ファンタジー

舞台:
  霧に包まれた旧市街の地下駅

キャラクター:
  リナ:
    兄を探す主人公

  カイ:
    幼なじみ。何かを隠している

  ミラ:
    駅に現れた謎の少女

  追跡者:
    正体不明の敵

初期状況:
  リナとカイは、失踪した兄の手掛かりを追って旧市街の地下駅に来た。
  駅は無人のはずだが、奥から足音が聞こえる。

隠し真実:
  地下駅は封印施設の入口である。
  カイはそのことを一部知っている。
  ミラは施設から逃げてきた存在である。

初期目標:
  10ターン以内に、地下駅の異常に気づく。
```

---

# 22. 初期GitHub Issue一覧

> **Historical (2026-07-13)**: 以下は初期計画時点のIssue番号スナップショットであり、現在の
> Issue状態や担当範囲を示さない。現行の作業単位は`docs/issues/`とIssue 052/062を参照する。

## 22.1 Phase 0 Issues

```text
#1 Create Project Charter
#2 Define Product Thesis
#3 Define MVP Scope
#4 Define Narrative State Model
#5 Define Turn Pipeline
#6 Define User Intervention Model
#7 Define Architecture Overview
#8 Define Repository Rules
#9 Create Initial Sample Scenario
#10 Create Completion Roadmap
```

## 22.2 Phase 1 Issues

```text
#11 Create project.yaml schema
#12 Create workspace layout
#13 Implement YAML/JSON state loader
#14 Implement world state model
#15 Implement character state model
#16 Implement scene state model
#17 Implement mock LLM provider
#18 Implement random engine
#19 Implement turn runner skeleton
#20 Implement basic narrator
#21 Implement markdown log writer
#22 Add sample world: Mist Station
#23 Add 10-turn smoke test
```

## 22.3 Phase 2 Issues

```text
#24 Implement Context Builder
#25 Implement Character Agent interface
#26 Implement World Simulator interface
#27 Implement Conflict Resolver interface
#28 Implement State Manager
#29 Implement State Diff schema
#30 Implement Artifact Store
#31 Implement structured output validation
#32 Implement OpenAI-compatible provider
#33 Add agent-level tests
```

## 22.4 Phase 3 Issues

```text
#34 Implement Intervention schema
#35 Implement free-text Intervention Interpreter
#36 Implement autonomy levels
#37 Implement stop conditions
#38 Implement auto N turns
#39 Implement GM review gate
#40 Implement intervention history
#41 Implement intervention suggestions
#42 Add intervention regression tests
```

## 22.5 Phase 4 Issues

```text
#43 Create local Web UI
#44 Add Story Pane
#45 Add Intervention Input
#46 Add Turn Controls
#47 Add Character Pane
#48 Add World Status Pane
#49 Add Timeline Pane
#50 Add State Diff Review
#51 Add Session Picker
#52 Add Logs View
```

## 22.6 Later Phase Issues

```text
#53 Add Memory Summary
#54 Add Relationship Graph
#55 Add Faction State
#56 Add Foreshadowing Ledger
#57 Add Continuity Checker
#58 Add Information Leak Checker
#59 Add Branch/Rollback
#60 Add Novel Draft Exporter
#61 Add TRPG Replay Exporter
#62 Add Game Rule Plugin
#63 Add Image Prompt Generator
#64 Add Visual Novel Renderer
#65 Add Backup/Restore
#66 Add Migration Framework
```

---

# 23. 品質評価

## 23.1 体験評価

評価観点:

- 次ターンを見たいと思えるか。
- 介入が反映されたと感じるか。
- キャラクターが生きているように感じるか。
- 世界が動いているように感じるか。
- 乱数結果が面白い展開を生んでいるか。
- ユーザーの想定外だが納得できる展開があるか。

## 23.2 整合性評価

評価観点:

- Canon矛盾数。
- 情報リーク数。
- キャラクター不一致数。
- 伏線消失数。
- 未解決threadの追跡率。
- relation変化の説明可能性。
- state diffの妥当性。

## 23.3 技術評価

評価観点:

- 1ターンあたり処理時間。
- 1ターンあたりLLM呼び出し回数。
- token使用量。
- APIコスト。
- retry率。
- schema validation失敗率。
- checkpoint/rollback成功率。
- smoke test成功率。

## 23.4 小説化評価

評価観点:

- ログから自然なシーンに変換できるか。
- 章原案として使えるか。
- 伏線・感情線が維持されるか。
- 余計なシステムログを除去できるか。
- 読み物として成立するか。

---

# 24. リスクと対策

## 24.1 物語破綻

リスク:

- Canon矛盾。
- キャラクター崩壊。
- 伏線消失。
- 目的喪失。
- 展開の停滞。

対策:

- 状態を正本にする。
- State Diffを導入する。
- Continuity Checkerを入れる。
- Unresolved Threadsを管理する。
- Memory Summaryを導入する。
- 長期セッションの回帰テストを作る。

## 24.2 情報リーク

リスク:

- GM Vaultが本文に出る。
- キャラクターが知らない秘密を使う。
- 読者に未公開情報が漏れる。

対策:

- 情報スコープ分離。
- Context Builderで最小情報化。
- Leak Checker。
- Visibility付きEvent/Fact。
- GM review gate。

## 24.3 介入の過剰自由度

リスク:

- 何でもできすぎて緊張感がなくなる。
- ユーザー指示でキャラクターが操り人形になる。
- 物語世界の因果関係が壊れる。

対策:

- user modeを分ける。
- intervention levelを明示。
- interventionの影響範囲を記録。
- God Modeを通常モードと分離。
- 介入結果をstate diffとしてレビューする。

## 24.4 コストと遅延

リスク:

- 複数agentでLLM呼び出しが増える。
- ターンが遅い。
- APIコストが高い。

対策:

- mock provider。
- local LLM対応。
- small modelとlarge modelの役割分担。
- agent実行の省略。
- context圧縮。
- summary cache。
- parallel execution。
- token/cost tracking。

## 24.5 権利問題

リスク:

- 既存作品風の生成。
- fanfictionの公開。
- 画像生成物の権利。
- 既存小説本文の取り込み。

対策:

- 初期はオリジナル世界前提。
- public exportをMVPに入れない。
- raw text非保持。
- private/local use明記。
- rights warning。
- source material metadata。

## 24.6 プロジェクト肥大化

リスク:

- 小説生成、TRPG、RPG、画像、音声、GUIを同時に作ろうとして破綻する。
- また中途半端なrepoになる。

対策:

- コアをNarrative Runtimeに限定。
- 派生機能はplugin/moduleに分離。
- MVPの非ゴールを明記。
- Milestone単位で完了条件を決める。
- docs/decision_log.mdを維持する。

---

# 25. セキュリティ・プライバシー設計

## 25.1 初期方針

- ローカルファースト。
- APIキーは環境変数またはローカル設定に保存。
- ログにsecretを出さない。
- Web UIは127.0.0.1で起動。
- 外部公開機能は初期MVPに入れない。
- Pluginは明示許可。
- ユーザーデータはworkspaceに分離。

## 25.2 ログの扱い

物語ログには、ユーザーの創作内容、入力、設定、場合によっては個人的嗜好が含まれる。

方針:

- デフォルトprivate。
- export時に確認。
- cloud送信内容を明示。
- LLM providerごとの送信対象を表示。
- delete/export機能を用意する。
- secret scannerを将来導入。

## 25.3 Plugin安全性

将来的なpluginにはリスクがある。

対策:

- plugin manifest。
- 権限宣言。
- network access制御。
- file access制御。
- sandbox実行。
- signed plugin optional。
- audit log。

---

# 26. 完成定義

## 26.1 MVP完成

MVP完成とは、次を満たす状態である。

- サンプル世界で10〜20ターン遊べる。
- ユーザー介入ができる。
- 乱数が反映される。
- ログが保存される。
- 状態差分が保存される。
- リプレイが読める。
- READMEで起動できる。

α/β/1.0の定義はADR-0005のgate構造を正本とする(2026-07-12、Issue 053)。
primary personaと代表ジャーニー、判定原則(must/should/post-1.0)もADR-0005に従う。

## 26.2 α版完成

α gate(遡及認定)。自動検証のみ。

- 全test green。
- mock providerで代表ジャーニーのE2E自動走行(init→serve→介入込み複数turn→export)が
  CIでpass。

## 26.3 β版完成

β gate = α +

- 正式2経路(uv / docker compose)のclean install smokeがCIでpass。
- βschema凍結宣言(migration互換保証の起点、宣言形式はIssue 059)。
- 実LLMでの代表ジャーニー人手smoke 1回合格(合否基準はIssue 057 rubricの簡易版)。

## 26.4 1.0完成

1.0 gate = β + must全充足 ∧ 全gate green。

- ADR-0005 D3のmust項目全充足。
- βschema→1.0のmigration regression test pass。
- 実LLM品質gate pass(Issue 057)。
- UX受入pass(Issue 058)。
- release checklist完了(Issue 059)。
- version 1.0.0。

---

# 27. 初期実装優先順位

> **Historical (2026-07-13)**: 以下は初期実装時の優先順位を保存した記録であり、現在の
> 実装順序・リリース判断を規定しない。現行の判断は`docs/adr/0005-v1-release-contract.md`
> とIssue 052/062を参照する。

最初に作るべき順番は次の通りである。

1. docs整備。
2. sample world作成。
3. schema定義。
4. mock turn runner。
5. random engine。
6. markdown log。
7. user intervention。
8. state diff。
9. simple narrator。
10. 10-turn smoke test。
11. OpenAI-compatible provider。
12. minimal Web UI。
13. GM review。
14. memory summary。
15. checker。

最初から画像生成、RPG戦闘、本格GUI、小説投稿は作らない。

---

# 28. 企画上の非ゴール

初期段階では以下を目指さない。

- 完全自動で出版品質の長編小説を完成させる。
- 商用ゲームエンジンを作る。
- MMO型の永続オンラインワールドを作る。
- マルチユーザーTRPGをいきなり実装する。
- 画像生成AI込みの完成ゲームを作る。
- 既存作品の二次創作を公開前提で量産する。
- すべての旧repoのコードを移植する。
- すべての派生方向を同時に実装する。

---

# 29. 最小実装のユーザーフロー

## 29.1 新規作成

```bash
living-narrative init \
  --title "霧の駅" \
  --genre "mystery_fantasy" \
  --tone "quiet_ominous" \
  --template mist_station
```

## 29.2 1ターン進行

```bash
living-narrative turn --project projects/mist_station/project.yaml
```

## 29.3 介入付き進行

```bash
living-narrative turn \
  --project projects/mist_station/project.yaml \
  --intervention "ここで停電を起こす。ただし原因はまだ明かさない"
```

## 29.4 自動進行

```bash
living-narrative auto \
  --project projects/mist_station/project.yaml \
  --turns 5
```

## 29.5 ログ出力

```bash
living-narrative export replay \
  --project projects/mist_station/project.yaml \
  --output out/replay.md
```

## 29.6 Web UI

```bash
living-narrative serve \
  --project-root projects \
  --port 8765
```

---

# 30. 完成後の姿

最終的なLiving Narrative Engineは、以下のような体験を提供する。

ユーザーは、ブラウザで自分の物語世界を開く。
画面には、現在のシーン、登場人物、世界状態、タイムライン、介入欄が表示される。
ユーザーが「次へ」を押すと、キャラクターが自律的に考え、会話し、行動する。
世界は時間と乱数により変化し、勢力は裏で動き、未解決の伏線は少しずつ圧力を増す。
ユーザーは、ただ眺めてもよい。
気になる時だけ、「この人物に疑念を持たせる」「ここで雨を強くする」「この秘密はまだ明かさない」と介入できる。
システムはその介入を構造化し、状態に反映し、結果を物語として表示する。
後からログを開けば、その物語は小説原案にも、TRPGリプレイにも、ゲームシナリオにもなる。

このプロジェクトは、AIに文章を書かせるだけのものではない。
AI、乱数、状態管理、ユーザー介入により、物語世界を動かし、その世界で遊ぶための基盤である。

---

# 31. まとめ

Living Narrative Engine の価値は、次の3点にある。

1. **リアルタイムに生成される物語を楽しむ体験**
   ユーザーは完成済み文章を読むのではなく、生きた物語世界の進行を眺め、介入し、楽しむ。

2. **状態管理された自律物語世界**
   世界、キャラクター、勢力、関係、秘密、伏線、乱数、イベントを構造化し、物語を壊さず進行させる。

3. **派生可能なナラティブ基盤**
   小説原案、TRPG、RPG、ビジュアルノベル、画像付きAIゲームへ拡張できる。

最初に作るべきものは、完成ゲームでも自動小説投稿ツールでもない。
まず作るべきものは、**テキストベースで、ユーザーが介入でき、状態が保存され、10〜20ターン破綻せず進む、最小の物語世界プレイヤー**である。

ここから始めれば、プロジェクトは無理なく拡張できる。

---

# Appendix A. 旧アイディアrepoから取り込む概念

> **Historical (2026-07-13)**: Appendix A〜Fは初期企画・サンプル・判断案の保存記録であり、
> 現行仕様を上書きしない。現行の契約は`README.md`、`docs/spec-foundation.md` §3〜§8、
> `docs/adr/0005-v1-release-contract.md`を参照する。

コード移植は不要。取り込むのは概念である。

| 元アイディア | 取り込む概念 |
|---|---|
| MultiAgentNarrativeEngine | hidden information、GM Vault、turn artifact、review/apply |
| MultiAgentNarrativeEngineNeo | GitHub正本、Spec/Milestone/Issue駆動 |
| auto-novel-writer | 長編production pipeline、resume/rerun、autonomy level、publish bundle |
| autonovel | seedから世界・キャラ・プロット・本文へ進む多層生成 |
| NovelGenOrchestrator | project.yaml + workspace、runner抽象、GUI、quality report |
| RolePlayStoryMaker | TRPG風multi-character loop、感情値、自律ループ、transcript |
| NovelStructureDBBuilder | story structure DB、raw text非保持、構造分析 |
| FanfictionWorldPlayer | 既存世界内で遊ぶという方向性 |
| NovelHub | 複数物語/世界のHub構想 |
| NovelGenSuite | suite化・統合管理の方向性 |

---

# Appendix B. 初期サンプル `project.yaml`

```yaml
schema_version: 1
id: mist_station
title: 霧の駅
genre: mystery_fantasy
tone: quiet_ominous
autonomy_level: assist
user_mode: assistant_gm
random_seed: 20260703-mist-station
renderer: novel
llm:
  provider: mock
  model: mock-v1
workspace:
  root: workspace
  state: workspace/state
  runs: workspace/runs
  exports: workspace/exports
```

---

# Appendix C. 初期ワークスペース構成

```text
projects/mist_station/
  project.yaml
  workspace/
    state/
      world.yaml
      canon.yaml
      reader_state.yaml
      gm_vault.yaml
      scenes/
        scene_001.yaml
      characters/
        char_001_lina.yaml
        char_002_kai.yaml
        char_003_mira.yaml
      relationships.yaml
      timeline.yaml
      unresolved_threads.yaml
    runs/
      turn_0001/
      turn_0002/
    exports/
      replay.md
```

---

# Appendix D. 最初の開発コマンド案

```bash
uv sync

uv run living-narrative init \
  --template mist_station \
  --output projects/mist_station

uv run living-narrative turn \
  --project projects/mist_station/project.yaml

uv run living-narrative auto \
  --project projects/mist_station/project.yaml \
  --turns 5

uv run living-narrative export replay \
  --project projects/mist_station/project.yaml \
  --output projects/mist_station/workspace/exports/replay.md

uv run pytest -q
```

---

# Appendix E. 判断基準

新機能を追加する時は、以下を確認する。

1. その機能は「リアルタイム生成物語を楽しむ体験」に直接寄与するか。
2. 状態管理、介入、自律進行、再利用のどれを強化するか。
3. MVPに必要か、派生機能か。
4. コアエンジンに入れるべきか、pluginにするべきか。
5. 情報リーク、権利、コスト、遅延のリスクは何か。
6. ログ・状態差分・テストで検証可能か。
7. 既存の中途半端repo再生産にならないか。

---

# Appendix F. 最初のDecision Log案

```markdown
# Decision Log

## D001: コアは小説生成ではなく物語世界進行エンジンとする

理由:
本文生成を中心にすると、TRPG/RPG/ゲーム派生やユーザー介入を統合しにくい。
状態遷移を中心にすると、小説化・TRPG化・ゲーム化へ展開できる。

## D002: 本文ではなく状態を正本にする

理由:
長期整合性、分岐、巻き戻し、小説化、ゲーム化に必要。

## D003: MVPでは画像生成を含めない

理由:
コア体験は物語世界の自律進行とユーザー介入である。
画像生成はコスト・一貫性・権利リスクが高く、後続pluginにすべき。

## D004: 初期はローカルファーストとする

理由:
創作ログ、ユーザー入力、APIキー、二次創作的素材が含まれる可能性があり、private運用が安全。

## D005: ユーザー介入は構造化して保存する

理由:
後からなぜ展開が変わったか説明可能にし、小説化・リプレイ・デバッグに使うため。
```
