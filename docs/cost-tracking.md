# LLM利用量・概算費用

`living-narrative status` とwebのGMビューは、各プロジェクトの正規ターンディレクトリ
`workspace/runs/turn_NNNN/meta.yaml` に既に記録された `llm_calls` と
`llm_tokens_total` を集計します。discarded / rolledback ディレクトリと、欠落または
不正な `meta.yaml` は集計しません。

モデル価格は `project.yaml` と同じディレクトリに `pricing.yaml` を置いて設定します。
モデル名は完全一致のみで、prefixやaliasの推測は行いません。設定例:

```yaml
auto/best-coding:
  input_usd_per_1m: 1.25   # 入力100万tokenあたりのUSD価格
  output_usd_per_1m: 10.00 # 出力100万tokenあたりのUSD価格
vendor/model-exact-name:
  input_usd_per_1m: 0.50
  output_usd_per_1m: 2.00
```

`pricing.yaml` がない、書式が不正、または利用モデルの完全一致エントリがない場合も、
呼出回数とtoken数は集計を続けます。その集計単位の概算費用は `null`（画面では
「価格未設定」）になります。組み込み価格snapshotは意図的に空であり、実際に利用する
モデルと契約時点の価格をプロジェクト側で明示してください。
