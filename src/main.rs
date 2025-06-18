mod cli;
mod downloader;
mod extractor;
mod filter;
mod model;
mod output;
mod utils;

use anyhow::Result;

fn main() -> Result<()> {
    let args = cli::parse_args();

    let (start_dt, _start_prec) = utils::parse_time_str(&args.start_time)?;
    let (end_dt, end_prec) = utils::parse_time_str(&args.end_time)?;
    let end_dt = utils::adjust_end_time(end_dt, &end_prec);

    let urls = downloader::generate_hourly_urls(start_dt, end_dt);

    std::fs::create_dir_all("gharchive_tmp")?;

    let mut results = Vec::new();

    for (url, filename) in urls {
        let local_path = format!("gharchive_tmp/{}", filename);
        downloader::download_file(&url, &local_path)?;
        if std::path::Path::new(&local_path).exists() {
            extractor::process_file(
                &local_path,
                start_dt,
                end_dt,
                args.include_checksums,
                &args.arch,
                &mut results,
            )?;
        }
        std::thread::sleep(std::time::Duration::from_millis(200));
    }

    if results.is_empty() {
        println!("未发现任何有效的 AppImage 发布项。");
        return Ok(());
    }

    output::write_results(&results, &args)?;

    Ok(())
}
