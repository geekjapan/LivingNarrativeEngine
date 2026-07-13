# 実LLM 30ターン benchmark 手順

Issue 072の実LLM定点観測手順である。実行はCIでは行わず、β gate、1.0 gate、または
リリース前の定点観測で実施する。機械SLOは[ADR-0010](adr/0010-quality-gate-narrative-slo.md)、
人手判定は[β/1.0 rubric](beta-quality-gate-rubric.md)を正本とする。

## 実行契約

- 対象は**30ターン**。`applied`で完了したターンが30未満ならrunは`FAIL`とする。
- `random_seed`、provider、model、git revision、実行日時を必ず記録する。再実行は新しい
  `run_id`を発行する。
- `turn_NNNN/meta.yaml`が正本であり、`status: failed`、途中停止、ターン欠落はrunを
  `FAIL`とする。provider failureは発生ターン、phase、例外型、秘密を含まない短い理由を
  記録する。
- JSONはsandbox内のcanonical artifact、Markdownはそのreader-visible部分の転記とする。
  Markdownを編集してJSONの内容を変更してはならない。
- API key、prompt本文、credential付きURL、`gm_vault`、`hidden_facts`、character secrets、
  `private_mind`はJSONにもMarkdownにも記録しない。`prompt_recording: hash_only`を使う。

## 1. 実行環境を固定する

実行前に、使用するgatewayが疎通可能であることを確認する。以下は既存のOpenAI-compatible
gatewayを使う例であり、provider/modelは実際のrunの値に置き換える。

```bash
RUN_ID=20260713-issue072-mist-station
RUN_DIR="sandbox/${RUN_ID}"
BENCH_SEED=issue-072-mist-station-v1
BENCH_BASE_URL=http://127.0.0.1:20128/v1
BENCH_MODEL=auto/best-coding

# API keyは.envまたはshell環境からだけ渡す。値を表示・保存・commitしない。
export OPENAI_API_KEY='<set-in-your-untracked-environment>'

uv run living-narrative init \
  --title 'Issue 072 実LLM 30ターン' \
  --template mist_station \
  --output "$RUN_DIR"

uv run python - "$RUN_DIR/project.yaml" "$BENCH_SEED" "$BENCH_BASE_URL" "$BENCH_MODEL" <<'PY'
import sys
from pathlib import Path

import yaml

project_path = Path(sys.argv[1])
data = yaml.safe_load(project_path.read_text(encoding="utf-8"))
data["random_seed"] = sys.argv[2]
data["llm"] = {
    "provider": "openai-compatible",
    "model": sys.argv[4],
    "base_url": sys.argv[3],
    "timeout_seconds": 60,
    "prompt_recording": "hash_only",
}
project_path.write_text(
    yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
    encoding="utf-8",
)
PY
```

`OPENAI_API_KEY`のplaceholderは実値に置き換えるが、shell historyやログへ残さない。
`base_url`にcredentialやquery parameterを含めず、artifactには`redacted`または
credentialを除いたendpointだけを記録する。別の実providerを使う場合も、実際のprovider、
model、endpoint種別をartifactへ記録する。

## 2. 30ターンを2プロセスで走らせる

各ターンをCLIの別プロセスで実行し、15ターン後に一度プロセスを終了する。これにより
後半はresume経路になる。以下のloopを、最初は`seq 1 15`、新しいshellでは`seq 16 30`
に置き換えて実行する。

```bash
for i in $(seq 1 15); do
  turn_dir="$RUN_DIR/workspace/runs/turn_$(printf '%04d' "$i")"
  status=0
  NO_COLOR=1 uv run living-narrative auto \
    --project "$RUN_DIR/project.yaml" \
    --turns 1 || status=$?

  if [ "$status" -ne 0 ] || [ ! -f "$turn_dir/meta.yaml" ]; then
    echo "benchmark failed at turn $i"
    break
  fi

  turn_status=$(uv run python -c \
    'import sys, yaml; print(yaml.safe_load(open(sys.argv[1], encoding="utf-8"))["status"])' \
    "$turn_dir/meta.yaml")
  case "$turn_status" in
    applied) ;;
    pending_review|stopped_for_review)
      NO_COLOR=1 uv run living-narrative review \
        --project "$RUN_DIR/project.yaml" \
        --decision accept_all
      ;;
    failed)
      echo "benchmark failed at provider/runtime turn $i"
      break
      ;;
    *)
      echo "unknown turn status at turn $i: $turn_status"
      break
      ;;
  esac
done
```

15ターン終了後にshell/processを終了し、`RUN_ID`と`RUN_DIR`を同じ値で新しいshellへ
設定して、上のloopの`seq 1 15`を`seq 16 30`に変えて実行する。レビュー停止を
`accept_all`する操作もturn artifactに残る。provider failureで`status=failed`になった
場合はacceptや再試行で同じrunを修復せず、失敗turnを記録してrunを`FAIL`にする。

## 3. 機械証跡を保存する

30ターン完了後、metricsのJSONを改変せず保存する。

```bash
NO_COLOR=1 uv run living-narrative metrics \
  --project "$RUN_DIR/project.yaml" \
  --json > "$RUN_DIR/metrics.json"

git rev-parse HEAD > "$RUN_DIR/git_revision.txt"
```

`docs/evaluations/real-llm-benchmark-template.json`を`$RUN_DIR/benchmark.json`へコピーし、
run metadata、30個のturn entry、`metrics.json`の内容、resume結果を埋める。JSONの必須形は
次のとおりである。

| JSON path | 内容 |
|---|---|
| `schema_version` / `artifact_type` | `1` / `real_llm_benchmark` |
| `run.*` | run ID、gate、日時、revision、sample、seed、provider、model、30ターンの結果 |
| `run.provider_failures[]` | `turn`、`phase`、`exception_type`、秘密を含まない`reason`。なければ空配列 |
| `turns[]` | `turn`、`status`、narration、reader-visible event/state。失敗turnも含める |
| `mechanical.metrics` | `metrics --json`のオブジェクトをそのまま格納 |
| `mechanical.resume` | checkpoint turn、再開turn、成功/失敗。今回の手順は15→16 |
| `sources` | sandbox run、metrics、転記Markdownの相対パス |

`completed_turns`は`status: applied`の数であり、review後に`applied`となったturnだけを
数える。provider failureが1件でもある、`completed_turns != 30`、またはturn番号が
`1..30`でない場合、`run.status`は`FAIL`である。

## 4. Markdownへ転記する

Markdownは`docs/evaluations/YYYY-MM-DD-<run-id>-benchmark.md`として保存し、
`docs/evaluations/real-llm-benchmark-template.md`を使う。全30ターンをJSONの順番どおりに
転記し、narrationとreader-visible event/stateだけを含める。JSONとMarkdownのturn番号・
narrationが一致しない場合は評価入力として無効である。

転記後、[β/1.0 rubricの実施手順](beta-quality-gate-rubric.md)を実行する。

- β: この30ターンrunを1回、人手rubric R1–R8で判定する。
- 1.0: gate時とリリース前定点観測で同じartifact契約を使い、判定ごとに新しい`run_id`
  と評価IDを発行する。
- provider failure、途中停止、ターン欠落はrubricを読む前に`FAIL`とし、発生turnを
  `run.provider_failures`とMarkdown headerへ記録する。
- rubric記録は`docs/evaluations/YYYY-MM-DD-<run-id>-human-rubric.md`に保存する。

転記半自動CLIは057で`should`としたため、このIssueでは追加しない。必要になった時点で
この固定形式を入力にする。
