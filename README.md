# AppImage Finder

![AppImage](https://img.shields.io/badge/AppImage-Finder-blue)
![Python](https://img.shields.io/badge/Python-3.6+-green)
![License](https://img.shields.io/badge/License-MIT-orange)

一个强大的命令行脚本，用于查找GitHub上基于特定topic标签的AppImage应用程序。

## 📝 功能特点

- 🔍 按topic标签搜索GitHub仓库中的AppImage
- 🔄 支持多个topic同时搜索，自动去重
- 🚀 识别并处理持续发布模式（continuous release）仓库
- 📊 提供详细的统计信息和摘要
- 📦 提取AppImage的版本信息并支持版本比较
- 💾 以JSON和CSV格式保存结果

## 🛠️ 安装要求

### 依赖项

- Python 3.6+
- 以下Python包:
  - requests
  - pandas (可选，用于更好的CSV输出)

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/ice909/appimage-finder.git
cd appimage-finder

# 安装依赖
pip install requests pandas
```

## 🚀 使用方法

### 设置GitHub Token

该工具需要GitHub API令牌来获取仓库信息。请设置`GITHUB_TOKEN`环境变量：

```bash
export GITHUB_TOKEN=your_github_token_here
```

> 注意：您可以在GitHub设置中创建个人访问令牌: https://github.com/settings/tokens

### 基本用法

```bash
python find_appimage_releases.py <topic1> [topic2...] [--repos=数量] [--output=文件名] [--latest-only]
```

## 📋 命令行参数

| 参数 | 描述 |
|------|------|
| `topics` | 要搜索的GitHub topic标签（必需，可提供多个） |
| `--repos` | 每个topic要检查的仓库数量 (默认: 10) |
| `--output` | 输出文件名前缀 (不含扩展名) |
| `--include-checksums` | 包含校验和文件(.sha256sum, .md5等) |
| `--latest-only` | 对于多版本AppImage，只保留最新版本 |
| `--keep-all` | 保留所有版本的AppImage (默认) |

## 💡 使用示例

### 搜索单个topic

```bash
# 搜索gui标签下的AppImage，检查前20个仓库
python find_appimage_releases.py gui --repos=20
```

### 搜索多个topic

```bash
# 同时搜索多个相关topic
python find_appimage_releases.py gui electron qt --repos=15
```

### 处理持续发布模式

```bash
# 对于持续发布模式的仓库，只保留最新版本
python find_appimage_releases.py electron --latest-only
```

### 自定义输出

```bash
# 指定输出文件名
python find_appimage_releases.py gui --output=gui-apps
```

## 🔍 持续发布模式处理

该工具能够识别"持续发布"模式的仓库（例如单个release中包含多个版本的AppImage）。这类仓库通常有以下特点：

- release名称包含"continuous"、"latest"、"nightly"等关键词
- 单个release中包含3个或更多不同版本的AppImage

使用`--latest-only`参数，工具将自动检测这类仓库，并只保留最新版本的AppImage，避免结果中出现大量重复信息。

## 📤 输出文件

该工具会生成3种格式的输出文件：

1. **完整JSON** (`<output>.json`): 包含所有详细信息
2. **简洁摘要** (`<output>-summary.json`): 精简版本，包含重要信息
3. **CSV表格** (`<output>.csv`): 适合在电子表格软件中查看

## 🔄 版本识别

工具会自动从AppImage文件名中提取版本号，支持以下格式：

- `AppName-1.2.3-x86_64.AppImage`
- `AppName-v1.2.3.AppImage`
- `AppName_1.2.3_amd64.AppImage`

## 📊 统计信息

执行后，工具会显示详细的统计信息：

- 检查的仓库总数
- 找到的AppImage数量
- 持续发布模式的仓库数量
- 各文件保存位置

## 🤝 贡献

欢迎提交问题报告和改进建议！请随时提交 Pull Request 或创建 Issue。

## 📜 许可

MIT License