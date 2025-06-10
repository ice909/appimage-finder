# AppImage Finder

AppImage Finder 是一个从 GitHub Archive 数据中查找包含 AppImage 文件的 GitHub Release 的工具。它支持按时间范围筛选，并能输出 JSON 或 CSV 格式的结果。

## 功能特性

从 GH Archive 数据中查找包含 AppImage 的 GitHub Release
支持多种时间粒度：年、月、日、小时
自动下载所需的 GH Archive 数据文件
可过滤掉持续集成/夜间构建版本
可选择保留所有版本或仅保留最新版本
支持包含校验和文件（如 .sha256sum, .md5 等）
输出格式支持 JSON 或 CSV

## 安装

确保已安装 Python 3.6+，然后直接运行脚本：

```bash
git clone https://github.com/ice909/appimage-finder.git
cd appimage-finder
chmod +x appimage-finder
```

## 使用方法

```text
AppImage Finder
---------------------------
从GH Archive数据中查找包含AppImage的GitHub Release，
支持按时间筛选（支持年、月、日、小时），自动下载数据，输出JSON或CSV。

示例用法:
  ./appimage-finder --start-time=2025-06-09 --end-time=2025-06-09
  ./appimage-finder --start-time=2025-06 --end-time=2025-07 --format=csv --output=result

选项:
  --start-time      开始时间，格式支持 yyyy 或 yyyy-mm 或 yyyy-mm-dd 或 yyyy-mm-dd-hh
  --end-time        结束时间，格式支持 yyyy 或 yyyy-mm 或 yyyy-mm-dd 或 yyyy-mm-dd-hh
  --format          输出格式 (json 或 csv)，默认json
  --output          输出文件名前缀，默认appimages
  --include-checksums  包含校验和文件 (.sha256sum, .md5 等) 的AppImage
  --keep-all        保留所有版本的AppImage，不仅是最新版本（默认只保留最新）
```
  
## 示例

查找2025年6月9日全天的AppImage发布：

```bash
./appimage-finder --start-time=2025-06-09 --end-time=2025-06-09
```

查找2025年6月全月的AppImage发布，输出为CSV格式：

```bash
./appimage-finder --start-time=2025-06 --end-time=2025-06 --format=csv
```

查找2025年6月到7月的AppImage发布，包含校验和文件，保留所有版本：

```bash
./appimage-finder --start-time=2025-06 --end-time=2025-07 --include-checksums --keep-all
```

## 输出格式

输出文件包含以下字段：
repo: GitHub仓库名称（格式：owner/repo）
release_name: Release名称
tag_name: Release标签名
published_at: 发布时间
appimage_name: AppImage文件名
download_url: 下载URL

## 注意事项

脚本会自动下载GH Archive数据文件到gharchive_tmp目录，请确保有足够的磁盘空间。
首次运行时可能需要下载大量数据文件，请耐心等待。
为避免被GitHub限流，脚本在请求之间设置了200ms的延迟。

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件。

## 贡献

欢迎提交问题和拉取请求！
