---
id: 127
title: publication manifestとartifact verificationを実装する
status: done
created: 2026-08-21
type: feature
priority: P1
parent: 123
blocked_by: [126]
labels: [long-form, export, manifest, integrity]
---

# 127: publication manifestとartifact verificationを実装する

## 背景

複数形式の出荷物は、どのaccepted manuscript・quality gate・format artifactを根拠に生成されたかを後から説明できなければならない。1ファイルでも差し替わった場合は、配布前に検出する必要がある。

## 公開seam

`verify_publication(manifest_path) -> PublicationVerificationResult`を検証seamとする。manifestはcanonical manuscript hash、source manuscript manifest hash、DOCX・EPUB・PDFのfilename/hash、quality gate、licenseを持ち、検証はhashとbasename-safe pathをfail-closedで確認する。

## 完了条件

- [x] single publication manifestがcanonical manuscriptと3形式artifactをhashで結ぶ。
- [x] manifestは`accepted_chapters_only` quality gateとlicense stateを明示する。
- [x] manuscript/source manifest/format fileのhash不一致、format不足、path traversalをすべて検出する。
- [x] verificationはreader-safeなresultだけを返し、本文・prompt・credential・private dataを返さない。
- [x] manifestはformat生成成功後に最後に公開する。
- [x] `book verify-publication`で著者がartifact integrityをfail-closedに確認できる。

## 非対象

電子署名、外部notary、公開鍵管理、ライセンスの法的妥当性評価は対象外とする。
