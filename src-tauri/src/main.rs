#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;
use tauri::{Manager, State, AppHandle};
use tauri_plugin_shell::ShellExt;
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

#[derive(Serialize, Deserialize)]
struct SidecarConfig {
    port: u16,
    workspace: String,
}

struct SidecarState {
    process: Mutex<Option<std::process::Child>>,
    config: Mutex<SidecarConfig>,
}

#[tauri::command]
async fn start_sidecar(app: AppHandle, state: State<'_, SidecarState>, workspace: String) -> Result<String, String> {
    let config = SidecarConfig {
        port: 8000,
        workspace: workspace.clone(),
    };
    
    *state.config.lock().unwrap() = config.clone();
    
    let sidecar_command = app.shell().sidecar("humitron-backend")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?;
    
    let mut child = sidecar_command
        .args(["--workspace", &workspace, "--port", &config.port.to_string()])
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;
    
    *state.process.lock().unwrap() = Some(child);
    
    // Wait a bit for server to start
    tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;
    
    // Verify server is running
    let client = reqwest::Client::new();
    match client.get(format!("http://localhost:{}/health", config.port)).send().await {
        Ok(resp) if resp.status().is_success() => Ok("Backend started successfully".to_string()),
        Ok(_) => Err("Backend health check failed".to_string()),
        Err(e) => Err(format!("Failed to connect to backend: {}", e)),
    }
}

#[tauri::command]
async fn stop_sidecar(state: State<'_, SidecarState>) -> Result<String, String> {
    if let Some(mut child) = state.process.lock().unwrap().take() {
        child.kill().map_err(|e| format!("Failed to kill sidecar: {}", e))?;
        Ok("Backend stopped".to_string())
    } else {
        Ok("No backend running".to_string())
    }
}

#[tauri::command]
async fn check_ollama() -> Result<OllamaStatus, String> {
    let client = reqwest::Client::new();
    match client.get("http://localhost:11434/api/tags").send().await {
        Ok(resp) => {
            if resp.status().is_success() {
                let data: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
                let models: Vec<String> = data["models"].as_array()
                    .unwrap_or(&vec![])
                    .iter()
                    .map(|m| m["name"].as_str().unwrap_or("").to_string())
                    .collect();
                Ok(OllamaStatus {
                    running: true,
                    models,
                    error: None,
                })
            } else {
                Ok(OllamaStatus {
                    running: false,
                    models: vec![],
                    error: Some("Ollama not responding".to_string()),
                })
            }
        }
        Err(e) => Ok(OllamaStatus {
            running: false,
            models: vec![],
            error: Some(e.to_string()),
        }),
    }
}

#[derive(Serialize, Deserialize)]
struct OllamaStatus {
    running: bool,
    models: Vec<String>,
    error: Option<String>,
}

#[tauri::command]
async fn pull_model(model: String) -> Result<String, String {
    let client = reqwest::Client::new();
    let payload = serde_json::json!({"name": model, "stream": false});
    match client.post("http://localhost:11434/api/pull").json(&payload).send().await {
        Ok(resp) => {
            if resp.status().is_success() {
                format!("Model {} pulled successfully", model)
            } else {
                format!("Failed to pull model: {}", resp.status())
            }
        }
        Err(e) => format!("Error pulling model: {}", e),
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_http::init())
        .manage(SidecarState {
            process: Mutex::new(None),
            config: Mutex::new(SidecarConfig { port: 8000, workspace: ".".to_string() }),
        })
        .invoke_handler(tauri::generate_handler![
            start_sidecar,
            stop_sidecar,
            check_ollama,
            pull_model,
        ])
        .setup(|app| {
            // Auto-start backend on launch
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let workspace = dirs::home_dir()
                    .unwrap_or_else(|| std::path::PathBuf::from("."))
                    .join("humitron-workspace")
                    .to_string_lossy()
                    .to_string();
                
                let _ = start_sidecar(handle, State::new(SidecarState {
                    process: Mutex::new(None),
                    config: Mutex::new(SidecarConfig { port: 8000, workspace: workspace.clone() }),
                }), workspace).await;
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // Stop sidecar on close
                let state: State<SidecarState> = window.state();
                let _ = tauri::async_runtime::block_on(stop_sidecar(state));
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}