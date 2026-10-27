# Codex Pets · 桌宠合集

为 Codex 桌面端制作的 V2 动画宠物。每只宠物独立安装、预览与维护：选择你喜欢的伙伴，让它陪你工作。

| 小澄 · 薄荷助手 | 大肥鱼 · 蓝色鲸鱼娘 |
| --- | --- |
| ![小澄待机](pets/xiaocheng/previews/idle.gif) | ![大肥鱼待机](pets/dafeiyu/previews/idle.gif) |
| 柔和 3D 手办，安静温柔的薄荷助手 | 二次元 Q 版，聪明贪吃的蓝色鲸鱼娘 |
| `xiaocheng` · [详情与预览](pets/xiaocheng/README.md) | `dafeiyu` · [详情与预览](pets/dafeiyu/README.md) |
| 美术 CC BY 4.0 | 美术 CC BY-NC-SA 4.0，保留上游许可 |
| [下载小澄 ZIP](https://github.com/fichil/codex-pets/releases/download/v2.0.0/xiaocheng-v2.0.0.zip) | [下载大肥鱼 ZIP](https://github.com/fichil/codex-pets/releases/download/v2.0.0/dafeiyu-v2.0.0.zip) |
| 安装参数：`-PetId xiaocheng`（默认） | 安装参数：`-PetId dafeiyu` |

## 安装

```powershell
git clone https://github.com/fichil/codex-pets.git
Set-Location .\codex-pets
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -List
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -PetId dafeiyu
```

不传 `-PetId` 仍安装小澄，兼容旧命令。覆盖同 ID 宠物加 `-Force`，安装前预览加 `-WhatIf`。脚本只写入所选宠物目录，不更改当前启用的桌宠。安装后在 Codex 的宠物选择界面刷新并手动选择。

[独立安装包与 SHA256](https://github.com/fichil/codex-pets/releases/tag/v2.0.0) · [安装、手动安装与卸载](docs/安装与使用.md)

## 项目组织

`pets/<id>/` 各自包含 `pet/` 安装包、`assets/` 检查图、`previews/` 动画、`source/` 基准图/提示词/QA 和独立许可说明。`scripts/` 提供通用安装、卸载、校验、预览和打包工具。

两只宠物采用相同 V2 格式：透明 WebP 1536×2288，8列×11行，单格192×208；九种标准状态、额外中性姿态、十六个顺时针观察方向。制作流程及验收边界见[制作与验证](docs/制作与验证.md)。

## 维护与验证

普通用户安装不需要 Python。维护工具需要 Python 3.12+：

```powershell
python -m pip install -r requirements-dev.txt
python scripts/validate.py
powershell -ExecutionPolicy Bypass -File scripts/test-install.ps1
python scripts/package.py --version v2.0.0
python scripts/verify-release.py output/releases
```

小澄素材原样迁移；大肥鱼使用内置 imagegen 重新制作，提示词与采用的原图均保留。生成过程不保证逐像素复现，打包和校验可重复执行。[贡献指南](CONTRIBUTING.md)

## 许可

工程代码使用 [MIT](LICENSE)。小澄美术沿用 [CC BY 4.0](pets/xiaocheng/LICENSE)；大肥鱼美术使用 [CC BY-NC-SA 4.0](pets/dafeiyu/LICENSE)，含署名、非商业和相同方式共享要求。请按角色查阅 [NOTICE](NOTICE.md)，不要把代码许可理解为全部角色素材的许可。

这是社区项目，与 OpenAI、Codex、ChatGPT 或 DeepSeek 无隶属、赞助或背书关系。
