// スタンドアロン高速パーサーコマンド。

use agent_eval_rust::parse_benchmark_yaml;
use std::env;
use std::fs;
use std::process;

// コマンドを実行してJSONを出力する
fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: agent-eval-parser <yaml_path>");
        process::exit(1);
    }

    let file_path = &args[1];
    let content = match fs::read_to_string(file_path) {
        Ok(c) => c,
        Err(err) => {
            eprintln!("Error reading file: {}", err);
            process::exit(1);
        }
    };

    match parse_benchmark_yaml(&content) {
        Ok(summary) => {
            println!("{}", serde_json::to_string(&summary).unwrap());
        }
        Err(err) => {
            eprintln!("Parse error: {}", err);
            process::exit(1);
        }
    }
}
