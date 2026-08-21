---
id: 126
title: accepted manuscriptからDOCX・EPUB・PDFを生成する
status: done
created: 2026-08-21
type: feature
priority: P1
parent: 123
blocked_by: [122]
labels: [long-form, export, publication]
---

# 126: accepted manuscriptからDOCX・EPUB・PDFを生成する

## 背景

制作済みのMarkdown正本だけでは、著者が配布・組版・電子書籍化する出荷物として十分ではない。chapter順序とreader textを保ったまま、accepted pointerのみからDOCX・EPUB・PDFを再現可能に生成する必要がある。

## 公開seam

`export_publication(workspace, output_dir) -> PublicationExportResult`を唯一のexport seamとする。内部で既存`export_accepted_manuscript`を先に呼び、accepted chapterの検証とcanonical Markdown作成を再利用してから3形式のadapterを実行する。

## 完了条件

- [x] DOCX・EPUB・PDFをaccepted Markdownだけから生成する。
- [x] 3形式ともchapter順序とreader textを維持する。
- [x] PDFはJapanese CID fontで本文を置換文字にせず組版する。
- [x] unaccepted chapter、accepted pointer欠落、candidate hash不整合時に出荷を拒否する。
- [x] format生成失敗時、completeなpublication manifestを公開しない。
- [x] `book export-publication`で著者がaccepted manuscript exportを実行できる。

## 非対象

cover artworkの自動生成、ISBN取得、DRM、外部ストア投稿、印刷会社固有の入稿テンプレートは対象外とする。
