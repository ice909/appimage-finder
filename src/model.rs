use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AppImageRelease {
    pub repo: String,
    pub release_name: Option<String>,
    pub tag_name: Option<String>,
    pub published_at: String,
    pub appimage_name: String,
    pub download_url: String,
    pub architecture: Option<String>,
    pub package_name: String,
    pub version: String,
}
