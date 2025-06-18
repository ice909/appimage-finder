use crate::cli::Arch;
use crate::model::AppImageRelease;
use serde_json::Value;

pub fn extract_architecture(filename: &str) -> Option<String> {
    let re_x86 = regex::Regex::new(r"(x86_64|x86-64|amd64|64bit|x64|x86)").unwrap();
    let re_arm = regex::Regex::new(r"(aarch64|arm64|ARM64)").unwrap();
    if re_x86.is_match(filename) {
        Some("x86_64".to_string())
    } else if re_arm.is_match(filename) {
        Some("aarch64".to_string())
    } else {
        None
    }
}

pub fn extract_version_4digit(tag: Option<&str>, filename: Option<&str>) -> String {
    for s in [tag, filename] {
        if let Some(s) = s {
            let re = regex::Regex::new(r"(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?").unwrap();
            if let Some(m) = re.captures(s) {
                let mut parts = vec![];
                for i in 1..=4 {
                    let part = m.get(i).map(|v| v.as_str()).unwrap_or("0");
                    parts.push(part);
                }
                return parts.join(".");
            }
        }
    }
    "1.0.0.0".to_string()
}

pub fn get_package_name(repo: &str) -> String {
    let repo_lower = repo.to_lowercase();
    let mut parts = repo_lower.splitn(2, '/');
    let owner = parts.next().unwrap_or("");
    let repo_name = parts.next().unwrap_or("");
    format!("io.github.{}.{}", owner, repo_name)
}

pub fn is_continuous_release(release_name: &str, appimages: &[Value]) -> bool {
    let keywords = [
        "continuous",
        "continous",
        "latest",
        "nightly",
        "daily",
        "current",
    ];
    if keywords
        .iter()
        .any(|kw| release_name.to_lowercase().contains(kw))
    {
        return true;
    }
    let mut versions = std::collections::HashSet::new();
    for asset in appimages {
        if let Some(name) = asset.get("name").and_then(|v| v.as_str()) {
            let v = extract_version_from_filename(name);
            if let Some(ver) = v {
                versions.insert(ver);
            }
        }
    }
    versions.len() >= 3
}

fn extract_version_from_filename(filename: &str) -> Option<String> {
    let re = regex::Regex::new(r"[-_]?v?(\d+\.\d+(?:\.\d+)*)").unwrap();
    re.captures(filename)
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().to_string())
}

pub fn filter_appimages(
    assets: &[Value],
    include_checksums: bool,
    target_arch: &Arch,
) -> Vec<Value> {
    let checksum_suffixes = [".sha256sum", ".md5", ".sha256", ".sha512", ".md5sum"];
    let mut filtered = vec![];
    for asset in assets {
        let name = asset.get("name").and_then(|v| v.as_str()).unwrap_or("");
        if name.ends_with(".AppImage") {
            let arch = extract_architecture(name);
            match target_arch {
                Arch::All => filtered.push(asset.clone()),
                Arch::X86_64 => {
                    if arch.as_deref() == Some("x86_64") || arch.is_none() {
                        filtered.push(asset.clone());
                    }
                }
                Arch::Aarch64 => {
                    if arch.as_deref() == Some("aarch64") {
                        filtered.push(asset.clone());
                    }
                }
            }
        } else if include_checksums && checksum_suffixes.iter().any(|suf| name.ends_with(suf)) {
            let base_name = name.split('.').next().unwrap_or("");
            if assets.iter().any(|a| {
                let n = a.get("name").and_then(|v| v.as_str()).unwrap_or("");
                n.starts_with(base_name) && n.ends_with(".AppImage")
            }) {
                filtered.push(asset.clone());
            }
        }
    }
    filtered
}

pub fn keep_latest_versions(results: &[AppImageRelease]) -> Vec<AppImageRelease> {
    use chrono::NaiveDateTime;
    use std::collections::HashMap;
    let mut latest: HashMap<(String, Option<String>), &AppImageRelease> = HashMap::new();
    for item in results {
        let key = (item.repo.clone(), item.architecture.clone());
        let item_dt = NaiveDateTime::parse_from_str(&item.published_at, "%Y-%m-%dT%H:%M:%SZ")
            .unwrap_or(chrono::NaiveDate::from_ymd_opt(2015, 1, 1).unwrap().and_hms_opt(0, 0, 0).unwrap());
        let update = match latest.get(&key) {
            None => true,
            Some(old) => {
                let old_dt = NaiveDateTime::parse_from_str(&old.published_at, "%Y-%m-%dT%H:%M:%SZ")
                    .unwrap_or(chrono::NaiveDate::from_ymd_opt(2015, 1, 1).unwrap().and_hms_opt(0, 0, 0).unwrap());
                item_dt > old_dt
            }
        };
        if update {
            latest.insert(key, item);
        }
    }
    latest.values().map(|v| (*v).clone()).collect()
}
