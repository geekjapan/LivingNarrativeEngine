# Changelog

このプロジェクトの変更履歴は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)
形式で管理し、バージョン番号は [Semantic Versioning](https://semver.org/lang/ja/)
に従う。リリース前の変更は`Unreleased`へ記録し、リリース時にタグと日付を付けた
版へ移す。

## [Unreleased]

### Added

- release engineering baseline、release checklist、SemVer保証面、upgrade policyを文書化。
- `schema_version: 1`をβschemaの保証起点として固定する宣言形式を追加。

### Changed

- turn commit artifactにstate hash、`diff_id`、`rng_start_offset`を記録し、replayと
  recoveryの検証可能性を高めた。
