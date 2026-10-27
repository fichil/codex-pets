# 历史 QA 与目录迁移

现有图集仍为 2026-09-14 的 3D 版。原验收结论、原图和动画不因目录迁移而重新生成。

`migration-v2.json` 记录旧提交到 `pets/xiaocheng/` 的文件映射及 SHA256：18 个图像文件和安装清单字节均未改变。所有现行 QA 相对路径以 `pets/xiaocheng/` 为基准。

`visual-qa.json` 的 `historicalReviewedSources` 是当时制作运行的临时文件名，并非本仓库的文件链接；现有公开对应资料列于 `reviewedSources`。`chroma-despill.json` 中 `<run>/` 同样表示历史运行目录。历史用户确认与代理直接观察仍分别记录，本次没有重新验证 Codex 实时播放。
