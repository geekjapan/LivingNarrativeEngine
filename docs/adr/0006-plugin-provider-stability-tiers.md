# ADR-0006: plugin/provider面のstability tier(stable契約とexperimental)

## Context

ADR-0004のplugin allowlist runtime(Issue 049)とprovider protocol/registryは実装済み
だが、1.0の公開契約(SemVer保証対象)にどこまで含めるかが未確定だった。plugin SDK
Python APIはIssue 049直後で未成熟であり、1.0で凍結すると将来の改善を majorに縛る
高リスクな不可逆決定になる。Issue 053の決定台帳D5として決定した。

## Decision

- **1.0公開契約(stable、ADR-0005 D2/SemVer保証対象)**:
  1. allowlist設定形式とtransactional登録の挙動(ADR-0004)。
  2. provider設定面(OpenAI-compatible `base_url`/`model`/key環境変数、mock provider指定)。
- **1.0に含むがexperimental(互換保証外、minor releaseで破壊的変更可)**:
  3. plugin SDK Python API。
  4. provider protocol(自作provider実装面)。
- experimentalであることをdocsと利用時表示で明示する。
- must(ADR-0005 D3(ii)): 「allowlist外pluginを絶対にloadしない」
  「登録はtransactionalを維持する」の回帰testを1.0 gateに含める。
- 1.0前に①②の正確な設定key・環境変数名・失敗時挙動を列挙し、contract testで固定する。
- security floorの具体的検査項目(web面のdisclosure検査、plugin導入時の確認UX、
  secrets非漏洩チェック)はIssue 054で決定する。本ADRは契約範囲のみを定める。

## Consequences

- docsに「stability: stable / experimental」区分が生まれ、README/plugin guideへの
  明記が必要になる。
- allowlist回帰testとprovider設定面smoke(mock+OpenAI-compatible)がmust入りする。
  plugin SDK APIの互換testは1.0非必須。
- ①②は公開後SemVer互換義務を負い、名称・挙動変更には互換層かmajor releaseが必要。
- ③④の利用者にはminor更新での追随を求め得る。SDK凍結の判断は1.1以降の独立issueへ
  予約される。
- trust boundary(security性質)は保証しつつAPI形状(利便性)は動かせる。
