use anyhow::Result;
use chrono::NaiveDateTime;
use chrono::{Datelike, Timelike};
use indicatif::{ProgressBar, ProgressStyle};
use std::fs::File;
use std::io::copy;

pub fn generate_hourly_urls(
    start_dt: NaiveDateTime,
    end_dt: NaiveDateTime,
) -> Vec<(String, String)> {
    let mut urls = Vec::new();
    let mut cur = start_dt;
    while cur <= end_dt {
        let url = format!(
            "https://data.gharchive.org/{:04}-{:02}-{:02}-{}.json.gz",
            cur.year(),
            cur.month(),
            cur.day(),
            cur.hour()
        );
        let fname = format!(
            "{:04}-{:02}-{:02}-{}.json.gz",
            cur.year(),
            cur.month(),
            cur.day(),
            cur.hour()
        );
        urls.push((url, fname));
        cur += chrono::Duration::hours(1);
    }
    urls
}

pub fn download_file(url: &str, filename: &str) -> Result<()> {
    if std::path::Path::new(filename).exists() {
        println!("文件已存在，跳过下载: {filename}");
        return Ok(());
    }
    println!("开始下载: {filename}");
    let resp = reqwest::blocking::get(url)?;
    let pb = ProgressBar::new(resp.content_length().unwrap_or(0));
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{bar:40.cyan/blue} {bytes}/{total_bytes} {msg}")
            .unwrap(),
    );
    let mut out = File::create(filename)?;
    let mut reader = pb.wrap_read(resp);
    copy(&mut reader, &mut out)?;
    pb.finish_and_clear();
    println!("下载完成: {filename}");
    Ok(())
}
