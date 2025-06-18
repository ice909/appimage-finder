use crate::filter::{
    extract_architecture, extract_version_4digit, filter_appimages, get_package_name,
    is_continuous_release,
};
use crate::model::AppImageRelease;
use anyhow::Result;
use chrono::NaiveDateTime;
use flate2::read::GzDecoder;
use std::fs::File;
use std::io::{BufRead, BufReader};

pub fn process_file(
    filepath: &str,
    start_dt: NaiveDateTime,
    end_dt: NaiveDateTime,
    include_checksums: bool,
    target_arch: &crate::cli::Arch,
    results: &mut Vec<AppImageRelease>,
) -> Result<()> {
    let f = File::open(filepath)?;
    let gz = GzDecoder::new(f);
    let reader = BufReader::new(gz);

    for line in reader.lines() {
        let line = line?;
        let event: serde_json::Value = serde_json::from_str(&line)?;
        if event.get("type").and_then(|v| v.as_str()) != Some("ReleaseEvent") {
            continue;
        }
        let created_at = event
            .get("created_at")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let dt =
            NaiveDateTime::parse_from_str(created_at, "%Y-%m-%dT%H:%M:%SZ").unwrap_or(start_dt);
        if dt < start_dt || dt > end_dt {
            continue;
        }
        let release = event.get("payload").and_then(|p| p.get("release"));
        if release.is_none()
            || !release
                .unwrap()
                .get("assets")
                .unwrap_or(&serde_json::Value::Null)
                .is_array()
        {
            continue;
        }
        let assets = release.unwrap().get("assets").unwrap().as_array().unwrap();
        let appimages = filter_appimages(assets, include_checksums, target_arch);
        if appimages.is_empty() {
            continue;
        }
        let release_name = release
            .unwrap()
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        if is_continuous_release(release_name, &appimages) {
            continue;
        }
        for asset in appimages {
            let arch = extract_architecture(&asset["name"].as_str().unwrap_or(""));
            let arch = if (matches!(
                target_arch,
                crate::cli::Arch::All | crate::cli::Arch::X86_64
            )) && arch.is_none()
            {
                Some("x86_64".to_string())
            } else {
                arch
            };
            let version = extract_version_4digit(
                release.unwrap().get("tag_name").and_then(|v| v.as_str()),
                asset["name"].as_str(),
            );
            let package_name = get_package_name(
                event
                    .get("repo")
                    .unwrap()
                    .get("name")
                    .unwrap()
                    .as_str()
                    .unwrap(),
            );
            results.push(AppImageRelease {
                repo: event
                    .get("repo")
                    .unwrap()
                    .get("name")
                    .unwrap()
                    .as_str()
                    .unwrap()
                    .to_string(),
                release_name: release
                    .unwrap()
                    .get("name")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string()),
                tag_name: release
                    .unwrap()
                    .get("tag_name")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string()),
                published_at: release
                    .unwrap()
                    .get("published_at")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string(),
                appimage_name: asset["name"].as_str().unwrap_or("").to_string(),
                download_url: asset["browser_download_url"]
                    .as_str()
                    .unwrap_or("")
                    .to_string(),
                architecture: arch,
                package_name,
                version,
            });
        }
    }
    *results = crate::filter::keep_latest_versions(results);
    Ok(())
}
