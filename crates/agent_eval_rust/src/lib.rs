// Rustによる高速YAMLパースとストリーミング層。

use serde::{Deserialize, Serialize};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

// ベンチマーク軽量メタデータを保持する
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BenchmarkSummary {
    pub id: String,
    pub title: String,
    pub family: String,
    pub fixture: String,
    pub schema_version: String,
}

// YAML文字列を解析して要約を返す
pub fn parse_benchmark_yaml(content: &str) -> Result<BenchmarkSummary, String> {
    serde_yaml::from_str::<BenchmarkSummary>(content).map_err(|e| e.to_string())
}

// 複数ファイルをストリーム走査する
pub fn stream_benchmarks<'a, I>(contents: I) -> Vec<Result<BenchmarkSummary, String>>
where
    I: IntoIterator<Item = &'a str>,
{
    contents.into_iter().map(parse_benchmark_yaml).collect()
}

// C言語互換インターフェースでパースする
#[no_mangle]
pub extern "C" fn agent_eval_parse_yaml(yaml_ptr: *const c_char) -> *mut c_char {
    if yaml_ptr.is_null() {
        return std::ptr::null_mut();
    }
    let c_str = unsafe { CStr::from_ptr(yaml_ptr) };
    let content = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    match parse_benchmark_yaml(content) {
        Ok(summary) => match serde_json::to_string(&summary) {
            Ok(json) => CString::new(json).map(|c| c.into_raw()).unwrap_or(std::ptr::null_mut()),
            Err(_) => std::ptr::null_mut(),
        },
        Err(err) => {
            let err_json = format!("{{\"error\": \"{}\"}}", err);
            CString::new(err_json).map(|c| c.into_raw()).unwrap_or(std::ptr::null_mut())
        }
    }
}

// Cインターフェースのメモリを解放する
#[no_mangle]
pub extern "C" fn agent_eval_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            let _ = CString::from_raw(ptr);
        }
    }
}
