#!/usr/bin/env python3
"""
查找GitHub指定topic下包含AppImage的最新release，支持持续发布模式
使用多种排序方式搜索并去重，以突破GitHub API 1000条结果的限制

用法:
  python3 find_appimage_releases.py <topic1> [topic2...] [--output=文件名] [--latest-only]

示例:
  python3 find_appimage_releases.py gui --latest-only
"""

import argparse
import csv
import json
import os
import sys
import re
import time
from datetime import datetime
import requests
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

def parse_args():
    parser = argparse.ArgumentParser(description='查找GitHub指定topic下包含AppImage的最新release')
    parser.add_argument('topics', nargs='+', help='GitHub topic标签 (可提供多个)')
    parser.add_argument('--output', default=None, help='输出文件名前缀 (不含扩展名)')
    parser.add_argument('--include-checksums', action='store_true', 
                       help='包含校验和文件 (.sha256sum, .md5, 等)')
    parser.add_argument('--latest-only', action='store_true', 
                       help='对于多版本AppImage，只保留最新版本')
    parser.add_argument('--keep-all', action='store_false', dest='latest_only',
                       help='保留所有版本的AppImage (默认)')
    return parser.parse_args()

def is_appimage_file(filename):
    """判断文件是否为真正的AppImage文件"""
    # AppImage通常以.AppImage或appimage结尾
    filename_lower = filename.lower()
    
    # 检查文件是否为校验和或签名文件
    checksum_patterns = ['.sha256', '.sha256sum', '.md5', '.sha1', '.asc', '.sig', '.sum']
    for pattern in checksum_patterns:
        if filename_lower.endswith(pattern):
            return False
    
    # 使用更严格的模式匹配AppImage文件
    # 必须以.AppImage或appimage结尾（不区分大小写）
    if (filename_lower.endswith('.appimage') or 
        re.search(r'\.appimage$', filename_lower, re.IGNORECASE)):
        return True
    
    return False

def extract_version_from_filename(filename):
    """从文件名中提取版本号"""
    # 常见模式: AppName-1.2.3-x86_64.AppImage
    version_pattern = r'[-_](\d+(?:\.\d+)+)[-_]'
    match = re.search(version_pattern, filename)
    if match:
        return match.group(1)
    
    # 尝试其他模式: AppName-v1.2.3.AppImage
    version_pattern = r'[-_]v?(\d+(?:\.\d+)+)'
    match = re.search(version_pattern, filename)
    if match:
        return match.group(1)
    
    # 尝试直接匹配数字序列: 1.2.3
    version_pattern = r'(\d+(?:\.\d+)+)'
    match = re.search(version_pattern, filename)
    if match:
        return match.group(1)
    
    return None

def parse_version(version_str):
    """解析版本号为可比较的元组"""
    if not version_str:
        return (0, 0, 0)
    
    # 将版本号分解为组件
    components = version_str.split('.')
    # 确保至少有三个组件 (major.minor.patch)
    while len(components) < 3:
        components.append('0')
    
    # 尝试转换为整数
    version_components = []
    for comp in components:
        try:
            version_components.append(int(comp))
        except ValueError:
            version_components.append(0)
    
    # 返回前三个组件
    return tuple(version_components[:3])

def is_continuous_release(release_name, appimages):
    """判断是否为持续发布模式"""
    # 检查release名称是否含有持续发布相关词汇
    continuous_keywords = ['continuous', 'continous', 'latest', 'nightly', 'daily', 'current']
    if any(keyword in release_name.lower() for keyword in continuous_keywords):
        return True
    
    # 检查是否有超过3个不同版本的AppImage
    versions = set()
    for app in appimages:
        version = extract_version_from_filename(app['name'])
        if version:
            versions.add(version)
    
    return len(versions) >= 3

def find_latest_version(appimages):
    """在多个AppImage中找出最新版本"""
    if not appimages:
        return None
    
    # 解析每个AppImage的版本
    versioned_apps = []
    for app in appimages:
        version_str = extract_version_from_filename(app['name'])
        if version_str:
            versioned_apps.append((app, parse_version(version_str), version_str))
    
    if not versioned_apps:
        # 如果没有可解析的版本，按创建时间排序
        sorted_by_date = sorted(appimages, 
                               key=lambda x: x.get('created_at', ''), 
                               reverse=True)
        return sorted_by_date[0] if sorted_by_date else None
    
    # 按版本号排序
    sorted_by_version = sorted(versioned_apps, 
                              key=lambda x: x[1], 
                              reverse=True)
    return sorted_by_version[0][0]  # 返回版本号最高的AppImage

def get_repos_for_topic_with_sort(topic, sort_by, headers):
    """使用指定排序方式获取指定topic的所有仓库列表，支持分页，遵循GitHub API限制"""
    # GitHub API每页最多返回100条结果
    PAGE_SIZE = 100
    # GitHub API搜索结果限制为前1000个结果
    MAX_GITHUB_SEARCH_RESULTS = 1000
    
    print(f"🔍 正在搜索topic为\"{topic}\"的仓库 (排序方式: {sort_by})...")
    
    # 首先获取满足条件的仓库总数
    initial_url = f"https://api.github.com/search/repositories?q=topic:{topic}&sort={sort_by}&order=desc&per_page=1"
    initial_response = requests.get(initial_url, headers=headers)
    
    if initial_response.status_code != 200:
        print(f"错误: 无法获取仓库列表 (状态码: {initial_response.status_code})")
        print(initial_response.json().get('message', ''))
        return []
    
    initial_data = initial_response.json()
    total_count = initial_data.get('total_count', 0)
    
    if total_count == 0:
        print(f"未找到topic为\"{topic}\"的仓库")
        return []
    
    print(f"找到topic为\"{topic}\"的仓库总数: {total_count}")
    
    # 如果仓库数量超过GitHub搜索限制，则提醒用户
    if total_count > MAX_GITHUB_SEARCH_RESULTS:
        print(f"⚠️ 注意: GitHub API限制只能返回前{MAX_GITHUB_SEARCH_RESULTS}个搜索结果（按{sort_by}排序）")
        repos_to_fetch = MAX_GITHUB_SEARCH_RESULTS
    else:
        repos_to_fetch = total_count
        
    print(f"将获取{repos_to_fetch}个仓库")
    
    # 计算需要的页数
    total_pages = (repos_to_fetch + PAGE_SIZE - 1) // PAGE_SIZE  # 向上取整
    
    # 开始分页获取所有仓库
    all_repos = []
    for page in range(1, total_pages + 1):
        # 计算当前页要获取多少条记录
        current_page_size = min(PAGE_SIZE, repos_to_fetch - len(all_repos))
        
        print(f"  获取第{page}/{total_pages}页，每页{current_page_size}条记录...")
        
        page_url = f"https://api.github.com/search/repositories?q=topic:{topic}&sort={sort_by}&order=desc&per_page={current_page_size}&page={page}"
        page_response = requests.get(page_url, headers=headers)
        
        # 检查是否达到了GitHub搜索限制
        if page_response.status_code == 422 and "Only the first 1000 search results are available" in page_response.text:
            print(f"  已达到GitHub搜索API限制（最多返回1000条结果）")
            break
        elif page_response.status_code != 200:
            print(f"错误: 获取第{page}页失败 (状态码: {page_response.status_code})")
            print(page_response.json().get('message', ''))
            break
        
        page_data = page_response.json()
        page_repos = page_data.get('items', [])
        all_repos.extend(page_repos)
        
        # 检查是否已经获取了足够的仓库
        if len(all_repos) >= repos_to_fetch:
            break
        
        # 添加延迟以避免触发GitHub API速率限制
        if page < total_pages:
            time.sleep(1)
    
    print(f"成功获取了{len(all_repos)}个仓库（排序方式: {sort_by}）")
    return all_repos

def get_repos_for_topic(topic, headers):
    """使用多种排序方式获取指定topic的仓库，并合并结果"""
    # 支持的排序方式列表
    sort_methods = ['stars', 'forks', 'help-wanted-issues', 'updated']
    
    print(f"\n🔍 开始使用多种排序方式搜索topic为\"{topic}\"的仓库...")
    
    # 用于存储不同排序方式获取的所有仓库，按仓库名称索引以避免重复
    all_repos_by_id = {}
    
    # 统计数据
    total_fetched = 0
    
    # 对每种排序方式进行搜索
    for sort_by in sort_methods:
        repos = get_repos_for_topic_with_sort(topic, sort_by, headers)
        total_fetched += len(repos)
        
        # 合并到总仓库列表中，去除重复项
        for repo in repos:
            repo_id = repo['id']  # 使用ID而不是名称作为唯一标识
            if repo_id not in all_repos_by_id:
                all_repos_by_id[repo_id] = repo
        
        print(f"当前已获取{len(all_repos_by_id)}个不重复仓库（处理了{total_fetched}个结果）")
        
        # 添加延迟以避免触发GitHub API速率限制
        if sort_by != sort_methods[-1]:
            print("等待5秒后继续下一种排序方式...")
            time.sleep(5)
    
    all_repos = list(all_repos_by_id.values())
    print(f"最终获取了{len(all_repos)}个不重复仓库（总共处理了{total_fetched}个结果）")
    
    return all_repos

def process_repo_for_appimages(repo_name, repo_data, headers, include_checksums=False, latest_only=False):
    """处理单个仓库，检查AppImage"""
    # 获取最新release
    releases_url = f"https://api.github.com/repos/{repo_name}/releases/latest"
    releases_response = requests.get(releases_url, headers=headers)
    
    # 如果找不到release或发生错误，返回None
    if releases_response.status_code != 200:
        print(f"    ✗ 未找到release或API错误 ({releases_response.status_code})")
        return None
    
    release = releases_response.json()
    release_tag = release.get('tag_name', '')
    release_name = release.get('name', '') or release_tag
    release_url = release.get('html_url', '')
    
    # 检查assets中是否有AppImage
    appimage_assets = []
    checksum_assets = []
    
    for asset in release.get('assets', []):
        asset_name = asset.get('name', '')
        
        if is_appimage_file(asset_name):
            appimage_assets.append({
                'name': asset['name'],
                'download_url': asset['browser_download_url'],
                'size': asset['size'],
                'download_count': asset['download_count'],
                'created_at': asset.get('created_at', ''),
                'updated_at': asset.get('updated_at', '')
            })
        # 可选地收集校验和文件
        elif include_checksums and any(ext in asset_name.lower() for ext in ['.sha256', '.md5', '.asc']):
            checksum_assets.append({
                'name': asset['name'],
                'download_url': asset['browser_download_url'],
                'size': asset['size'],
                'type': 'checksum'
            })
    
    if appimage_assets:
        # 检查是否为持续发布模式
        continuous = is_continuous_release(release_name, appimage_assets)
        
        # 如果是持续发布模式且用户选择了只保留最新版本
        if continuous and latest_only:
            latest_app = find_latest_version(appimage_assets)
            if latest_app:
                total_versions = len(appimage_assets)
                appimage_assets = [latest_app]
                print(f"    ✓ 持续发布: 在release {release_name} 中找到 {total_versions} 个版本，保留最新版本 {latest_app['name']}")
            else:
                print(f"    ✓ 持续发布: 在release {release_name} 中找到 {len(appimage_assets)} 个AppImage")
        else:
            print(f"    ✓ 在release {release_name} 中找到 {len(appimage_assets)} 个AppImage" + 
                  (" (持续发布)" if continuous else ""))
        
        # 创建一个包含所有AppImage的仓库记录
        repo_result = {
            'repository_name': repo_name,
            'repository_url': repo_data['html_url'],
            'repository_stars': repo_data['stargazers_count'],
            'repository_description': repo_data['description'],
            'release_tag': release_tag,
            'release_name': release_name,
            'release_url': release_url,
            'release_date': release.get('published_at', ''),
            'release_body': release.get('body', ''),
            'is_continuous_release': continuous,
            'appimages_count': len(appimage_assets),
            'total_versions': len(appimage_assets) if not continuous else len(appimage_assets),
            'appimages': appimage_assets
        }
        
        # 如果包含校验和文件，则添加
        if include_checksums and checksum_assets:
            repo_result['checksums'] = checksum_assets
        
        return repo_result
    else:
        print(f"    ✗ 在release {release_name} 中未找到AppImage")
        return None

def find_appimage_releases(topics, include_checksums=False, latest_only=False):
    """查找指定多个topic下含AppImage的仓库release，去除重复仓库"""
    
    # 从环境变量获取GitHub令牌
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("错误: 环境变量GITHUB_TOKEN未设置")
        print("请设置: export GITHUB_TOKEN=你的个人访问令牌")
        sys.exit(1)
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'AppImageFinder/1.0'
    }
    
    # 用于存储所有找到的仓库，按仓库ID索引以避免重复
    all_repos_by_id = {}
    
    # 对每个topic获取仓库
    for topic in topics:
        repos = get_repos_for_topic(topic, headers)
        
        for repo in repos:
            repo_id = repo['id']
            # 如果这个仓库还没处理过，加入列表
            if repo_id not in all_repos_by_id:
                all_repos_by_id[repo_id] = repo
    
    # 转换为列表
    all_repos = list(all_repos_by_id.values())
    
    if not all_repos:
        print("未找到任何仓库")
        return [], 0, 0, 0, 0
    
    print(f"\n找到{len(all_repos)}个不重复的仓库，正在检查最新release...")
    
    # 存储找到的AppImage包
    results = []
    processed_repos = 0
    repos_with_appimages = 0
    continuous_repos = 0
    total_appimages = 0
    total_checksums = 0
    
    # 处理所有不重复的仓库
    for repo in all_repos:
        processed_repos += 1
        repo_name = repo['full_name']
        print(f"  • 正在处理 {repo_name} [{processed_repos}/{len(all_repos)}]")
        
        # 处理这个仓库的AppImage
        repo_result = process_repo_for_appimages(
            repo_name, repo, headers, include_checksums, latest_only
        )
        
        if repo_result:
            repos_with_appimages += 1
            total_appimages += repo_result['appimages_count']
            
            # 统计持续发布仓库
            if repo_result.get('is_continuous_release', False):
                continuous_repos += 1
                
            # 计算校验和文件数量
            if include_checksums and 'checksums' in repo_result:
                total_checksums += len(repo_result['checksums'])
                
            results.append(repo_result)
        
        # 避免触发GitHub API速率限制
        time.sleep(0.5)
    
    return results, repos_with_appimages, continuous_repos, total_appimages, total_checksums

def save_results(results, output_prefix):
    """将结果保存为CSV和JSON格式"""
    
    if not output_prefix:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_prefix = f"appimage-results-{timestamp}"
    
    # 保存为JSON格式
    json_file = f"{output_prefix}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 保存为CSV格式 - 需要展开appimages数组
    csv_file = f"{output_prefix}.csv"
    if results:
        # 创建适合CSV的展平结构
        flattened_data = []
        for repo in results:
            base_info = {k: v for k, v in repo.items() if k not in ['appimages', 'checksums']}
            
            # 每个仓库至少有一个条目，即使没有AppImage
            if not repo.get('appimages'):
                flattened_data.append(base_info)
            
            # 为每个AppImage创建一行，但保持仓库信息一致
            for appimage in repo.get('appimages', []):
                row = base_info.copy()
                # 尝试从文件名提取版本
                version = extract_version_from_filename(appimage['name'])
                row.update({
                    'appimage_name': appimage['name'],
                    'appimage_version': version,
                    'appimage_url': appimage['download_url'],
                    'appimage_size': appimage['size'],
                    'download_count': appimage['download_count']
                })
                flattened_data.append(row)
        
        # 使用pandas输出更好的CSV格式（如果可用）
        if PANDAS_AVAILABLE:
            df = pd.DataFrame(flattened_data)
            df.to_csv(csv_file, index=False, encoding='utf-8')
        else:
            # 如果没有pandas，回退到标准csv模块
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                if flattened_data:
                    writer = csv.DictWriter(f, fieldnames=flattened_data[0].keys())
                    writer.writeheader()
                    writer.writerows(flattened_data)
                else:
                    writer = csv.writer(f)
                    writer.writerow(["未找到AppImage发布包"])
    else:
        # 如果没有结果，创建一个空CSV文件
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["未找到AppImage发布包"])
    
    # 创建一个简化版本的JSON，更易于阅读
    summary_file = f"{output_prefix}-summary.json"
    summary_list = []
    
    for repo in results:
        is_continuous = repo.get('is_continuous_release', False)
        summary_item = {
            'repository': repo['repository_name'],
            'stars': repo['repository_stars'],
            'release': repo['release_tag'],
            'release_date': repo['release_date'],
            'is_continuous_release': is_continuous,
        }
        
        # 如果是持续发布，找出最新版本
        if is_continuous:
            latest = find_latest_version(repo.get('appimages', []))
            if latest:
                version = extract_version_from_filename(latest['name'])
                summary_item['latest_version'] = version
                summary_item['latest_appimage'] = latest['name']
                summary_item['download_url'] = latest['download_url']
                summary_item['total_versions'] = repo.get('total_versions', len(repo.get('appimages', [])))
        
        # 添加所有AppImage信息
        summary_item['appimages'] = []
        for appimage in repo.get('appimages', []):
            version = extract_version_from_filename(appimage['name'])
            summary_item['appimages'].append({
                'name': appimage['name'],
                'version': version,
                'url': appimage['download_url'],
                'downloads': appimage['download_count']
            })
        
        summary_list.append(summary_item)
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_list, f, indent=2, ensure_ascii=False)
    
    return json_file, csv_file, summary_file

def main():
    args = parse_args()
    
    print(f"🚀 开始查找topics '{', '.join(args.topics)}' 下包含AppImage的最新发布版本")
    print(f"📝 注意: 只搜索真正的AppImage文件，{'包括' if args.include_checksums else '不包括'}校验和文件")
    print(f"📦 持续发布模式: {'只保留最新版本' if args.latest_only else '保留所有版本'}")
    print(f"🔄 搜索策略: 使用多种排序方式 (stars, forks, help-wanted-issues, updated) 并合并去重")
    
    # 处理所有topic并去除重复仓库
    results, repos_with_appimages, continuous_repos, total_appimages, total_checksums = find_appimage_releases(
        args.topics, args.include_checksums, args.latest_only
    )
    
    if not results:
        print("❌ 未找到任何包含AppImage的release")
        sys.exit(0)
    
    # 生成默认输出文件名
    if not args.output:
        output_prefix = "appimages"
    else:
        output_prefix = args.output
    
    # 保存结果
    json_file, csv_file, summary_file = save_results(results, output_prefix)
    
    print(f"\n✅ 查找完成！")
    print(f"📊 统计:")
    print(f"  • 查找的topics: {', '.join(args.topics)} (共{len(args.topics)}个)")
    print(f"  • 有AppImage的仓库数: {repos_with_appimages}")
    print(f"  • 持续发布模式的仓库数: {continuous_repos}")
    print(f"  • 找到的AppImage总数: {total_appimages}")
    if args.include_checksums:
        print(f"  • 找到的校验和文件数: {total_checksums}")
    print(f"  • 结果保存为:")
    print(f"    - 完整JSON: {json_file}")
    print(f"    - 简洁摘要: {summary_file}")
    print(f"    - CSV表格: {csv_file}")
    
    # 输出执行时间和用户信息
    current_time = "2025-05-16 06:48:26"
    print(f"\n执行时间: {current_time} (UTC)")
    print(f"执行用户: ice909")

if __name__ == "__main__":
    main()