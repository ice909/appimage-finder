use anyhow::{bail, Result};
use chrono::{Datelike, Duration, NaiveDate, NaiveDateTime};

pub enum Precision {
    Year,
    Month,
    Day,
    Hour,
}

pub fn parse_time_str(tstr: &str) -> Result<(NaiveDateTime, Precision)> {
    let parts: Vec<_> = tstr.split('-').collect();
    let year: i32 = parts[0].parse()?;
    let month = if parts.len() > 1 {
        parts[1].parse()?
    } else {
        1
    };
    let day = if parts.len() > 2 {
        parts[2].parse()?
    } else {
        1
    };
    let hour = if parts.len() > 3 {
        parts[3].parse()?
    } else {
        0
    };

    let precision = match parts.len() {
        1 => Precision::Year,
        2 => Precision::Month,
        3 => Precision::Day,
        4 => Precision::Hour,
        _ => bail!("时间格式不正确"),
    };
    let dt = NaiveDate::from_ymd_opt(year, month, day)
        .and_then(|d| d.and_hms_opt(hour, 0, 0))
        .ok_or_else(|| anyhow::anyhow!("时间解析失败"))?;
    Ok((dt, precision))
}

pub fn adjust_end_time(dt: NaiveDateTime, precision: &Precision) -> NaiveDateTime {
    match precision {
        Precision::Year => NaiveDate::from_ymd_opt(dt.year(), 12, 31)
            .unwrap()
            .and_hms_opt(23, 0, 0)
            .unwrap(),
        Precision::Month => {
            let (y, m) = (dt.year(), dt.month());
            let next_month = if m == 12 { (y + 1, 1) } else { (y, m + 1) };
            let last_day = (NaiveDate::from_ymd_opt(next_month.0, next_month.1, 1).unwrap()
                - Duration::days(1))
            .day();
            NaiveDate::from_ymd_opt(y, m, last_day)
                .unwrap()
                .and_hms_opt(23, 0, 0)
                .unwrap()
        }
        Precision::Day => dt.date().and_hms_opt(23, 0, 0).unwrap(),
        Precision::Hour => dt,
    }
}
