// Prevent console window on Windows
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_http::init())
        .setup(|app| {
            let handle = app.handle();

            // Start Python backend sidecar
            let sidecar_command = handle
                .shell()
                .sidecar("humitron-backend")
                .expect("Failed to create sidecar command");

            let (mut rx, _child) = sidecar_command
                .spawn()
                .expect("Failed to spawn sidecar");

            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    if let tauri::shell::SidecarEvent::Stdout(line) = event {
                        println!("[backend] {}", String::from_utf8_lossy(&line));
                    } else if let tauri::shell::SidecarEvent::Stderr(line) = event {
                        eprintln!("[backend] {}", String::from_utf8_lossy(&line));
                    }
                }
            });

            // Ensure backend is killed on app exit
            let handle_clone = handle.clone();
            app.on_window_event(move |_window, event| {
                if let tauri::WindowEvent::CloseRequested { .. } = event {
                    // Sidecar will be killed automatically when app exits
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::pick_folder,
            commands::start_sidecar,
            commands::update_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

mod commands {
    use tauri::{command, State, AppHandle, Manager};
    use std::sync::Mutex;
    use std::path::PathBuf;

    #[command]
    async fn pick_folder(app: AppHandle) -> Result<Option<String>, String> {
        use tauri_plugin_dialog::DialogExt;

        let folder = app.dialog()
            .file()
            .pick_folder(None)
            .await
            .map_err(|e| e.to_string())?;

        Ok(folder.map(|p| p.to_string()))
    }

    #[command]
    async fn start_sidecar(app: AppHandle, workspace: String) -> Result<(), String> {
        // Set workspace env var for sidecar
        std::env::set_var("HUMITRON_WORKSPACE", workspace);

        let sidecar_command = app
            .shell()
            .sidecar("humitron-backend")
            .map_err(|e| e.to_string())?;

        let (mut _rx, _child) = sidecar_command
            .spawn()
            .map_err(|e| e.to_string())?;

        Ok(())
    }

    #[command]
    async fn update_config(config: serde_json::Value) -> Result<(), String> {
        // Write config to file
        let config_path = std::env::current_dir()
            .map_err(|e| e.to_string())?
            .join("config.yaml");

        let yaml = serde_yaml::to_string(&config)
            .map_err(|e| e.to_string())?;

        std::fs::write(config_path, yaml)
            .map_err(|e| e.to_string())?;

        Ok(())
    }
}