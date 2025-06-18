use crate::cli::{Arch, Args, OutputFormat};
use crate::model::AppImageRelease;
use std::collections::HashMap;
use std::fs::File;
use std::io::Write;

pub fn write_results(results: &[AppImageRelease], args: &Args) -> anyhow::Result<()> {
    match args.arch {
        Arch::All => {
            let mut arch_groups: HashMap<String, Vec<&AppImageRelease>> = HashMap::new();
            for item in results {
                let arch = item
                    .architecture
                    .clone()
                    .unwrap_or_else(|| "unknown".to_string());
                arch_groups.entry(arch).or_default().push(item);
            }
            for (arch, group) in arch_groups {
                match args.format {
                    OutputFormat::Json => {
                        let fname = format!("{}-{}.json", &args.output, arch);
                        let mut f = File::create(&fname)?;
                        writeln!(f, "{}", serde_json::to_string_pretty(&group)?)?;
                    }
                    OutputFormat::Csv => {
                        let fname = format!("{}-{}.csv", &args.output, arch);
                        let mut wtr = csv::Writer::from_path(&fname)?;
                        for item in group {
                            wtr.serialize(item)?;
                        }
                        wtr.flush()?;
                    }
                }
            }
            println!(
                "共发现 {} 个有效 AppImage 发布项，结果已按架构分别保存为 {}-<arch>.{:?}",
                results.len(),
                args.output,
                args.format
            );
        }
        _ => {
            match args.format {
                OutputFormat::Json => {
                    let fname = format!("{}-{:?}.json", &args.output, args.arch);
                    let mut f = File::create(&fname)?;
                    writeln!(f, "{}", serde_json::to_string_pretty(&results)?)?;
                }
                OutputFormat::Csv => {
                    let fname = format!("{}-{:?}.csv", &args.output, args.arch);
                    let mut wtr = csv::Writer::from_path(&fname)?;
                    for item in results {
                        wtr.serialize(item)?;
                    }
                    wtr.flush()?;
                }
            }
            println!(
                "共发现 {} 个有效 AppImage 发布项，结果已保存为 {}-{:?}.{:?}",
                results.len(),
                args.output,
                args.arch,
                args.format
            );
        }
    }
    Ok(())
}
