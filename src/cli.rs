use clap::{Parser, ValueEnum};

#[derive(Parser, Debug)]
#[command(
    name = "AppImage Finder",
    version = "0.1.0",
    about = "从GH Archive数据中查找包含AppImage的GitHub Release，支持按时间筛选（年/月/日/小时），自动下载，输出JSON或CSV。"
)]
pub struct Args {
    #[arg(
        long,
        help = "开始时间，格式支持 yyyy 或 yyyy-mm 或 yyyy-mm-dd 或 yyyy-mm-dd-hh"
    )]
    pub start_time: String,
    #[arg(
        long,
        help = "结束时间，格式支持 yyyy 或 yyyy-mm 或 yyyy-mm-dd 或 yyyy-mm-dd-hh"
    )]
    pub end_time: String,
    #[arg(long, value_enum, default_value_t = OutputFormat::Json, help = "输出格式 (json 或 csv)，默认json")]
    pub format: OutputFormat,
    #[arg(
        long,
        default_value = "appimages",
        help = "输出文件名前缀，默认appimages"
    )]
    pub output: String,
    #[arg(long, help = "包含校验和文件 (.sha256sum, .md5 等) 的AppImage")]
    pub include_checksums: bool,
    #[arg(long, value_enum, default_value_t = Arch::All, help = "指定AppImage架构 (x86_64, aarch64, all)，默认all")]
    pub arch: Arch,
}

#[derive(Clone, Debug, ValueEnum)]
pub enum OutputFormat {
    Json,
    Csv,
}

#[derive(Clone, Debug, ValueEnum)]
pub enum Arch {
    X86_64,
    Aarch64,
    All,
}

pub fn parse_args() -> Args {
    Args::parse()
}
