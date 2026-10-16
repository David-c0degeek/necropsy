#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::Mutex;
use tauri::{Emitter, Manager, State};

struct EngineProcess {
    child: Child,
    input: ChildStdin,
}

#[derive(Default)]
struct Engine(Mutex<Option<EngineProcess>>);

#[tauri::command]
fn start_engine(app: tauri::AppHandle, engine: State<Engine>) -> Result<(), String> {
    let mut state = engine
        .0
        .lock()
        .map_err(|_| "Could not access the analysis engine.")?;
    if state.is_some() {
        return Ok(());
    }
    let mut command = engine_command()?;
    // A frozen engine has its own bootloader parent; pass the actual window PID.
    command.env("NECROPSY_GUI_PID", std::process::id().to_string());
    if let Some(directory) = std::env::var_os("NECROPSY_DESKTOP_DATA_DIR") {
        command.arg("--data-dir").arg(directory);
    }
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW; piped stdin remains available.
    }
    let mut child = command.spawn().map_err(|_| {
        "Could not start the analysis engine. Reinstall Necropsy, or run uv sync in a source checkout."
    })?;
    let input = child
        .stdin
        .take()
        .ok_or("The analysis engine has no input pipe.")?;
    let output = child
        .stdout
        .take()
        .ok_or("The analysis engine has no output pipe.")?;
    *state = Some(EngineProcess { child, input });
    std::thread::spawn(move || {
        for line in BufReader::new(output).lines() {
            let Ok(line) = line else { break };
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(&line) {
                let _ = app.emit_to("main", "engine-message", value);
            }
        }
        let _ = app.emit_to("main", "engine-exit", ());
    });
    Ok(())
}

fn engine_command() -> Result<Command, String> {
    #[cfg(debug_assertions)]
    {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(|p| p.parent())
            .ok_or("Source checkout not found.")?;
        let python = if cfg!(windows) {
            ".venv/Scripts/python.exe"
        } else {
            ".venv/bin/python"
        };
        let mut command = Command::new(root.join(python));
        command
            .args(["-m", "necropsy.desktop.engine"])
            .current_dir(root);
        Ok(command)
    }
    #[cfg(not(debug_assertions))]
    {
        let exe = std::env::current_exe().map_err(|_| "Could not locate Necropsy.")?;
        let folder = exe
            .parent()
            .ok_or("Could not locate the application folder.")?;
        let name = if cfg!(windows) {
            "necropsy-engine.exe"
        } else {
            "necropsy-engine"
        };
        Ok(Command::new(folder.join(name)))
    }
}

#[tauri::command]
fn engine_request(message: serde_json::Value, engine: State<Engine>) -> Result<(), String> {
    let mut state = engine
        .0
        .lock()
        .map_err(|_| "Could not access the analysis engine.")?;
    let process = state
        .as_mut()
        .ok_or("The analysis engine has not started.")?;
    let mut line = serde_json::to_vec(&message).map_err(|_| "Could not encode the request.")?;
    line.push(b'\n');
    process
        .input
        .write_all(&line)
        .and_then(|_| process.input.flush())
        .map_err(|_| {
            "The analysis engine stopped. Restart Necropsy; your saved progress is retained.".into()
        })
}

#[tauri::command]
async fn quit_app(app: tauri::AppHandle) -> Result<(), String> {
    let owned = app.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let process = owned
            .state::<Engine>()
            .0
            .lock()
            .ok()
            .and_then(|mut state| state.take());
        if let Some(EngineProcess { mut child, input }) = process {
            // EOF requests a cooperative stop, including when the UI did not finish loading.
            drop(input);
            let _ = child.wait();
        }
        owned.exit(0);
    })
    .await
    .map_err(|_| "Could not finish saving. Please try closing again.".to_string())?;
    Ok(())
}

fn main() {
    let version = format!("necropsy {}", env!("CARGO_PKG_VERSION"));
    if std::env::args().any(|arg| arg == "--version") {
        println!("{version}");
        return;
    }
    if std::env::args().any(|arg| arg == "--check-install") {
        let result = engine_command().and_then(|mut command| {
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000);
            }
            command
                .arg("--version")
                .output()
                .map_err(|error| error.to_string())
        });
        match result {
            Ok(output)
                if output.status.success()
                    && String::from_utf8_lossy(&output.stdout).trim() == version =>
            {
                println!("{version}");
                return;
            }
            _ => {
                eprintln!("Necropsy's desktop engine is missing or has a different version.");
                std::process::exit(1);
            }
        }
    }
    tauri::Builder::default()
        .manage(Engine::default())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            start_engine,
            engine_request,
            quit_app
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let running = window
                    .state::<Engine>()
                    .0
                    .lock()
                    .map(|state| state.is_some())
                    .unwrap_or(false);
                if running {
                    api.prevent_close();
                    let _ = window.emit("desktop-close", ());
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("Necropsy could not start its desktop window")
        .run(|app, event| {
            if let tauri::RunEvent::ExitRequested {
                code: None, api, ..
            } = event
            {
                let running = app
                    .state::<Engine>()
                    .0
                    .lock()
                    .map(|state| state.is_some())
                    .unwrap_or(false);
                if running {
                    api.prevent_exit();
                    let _ = app.emit_to("main", "desktop-close", ());
                }
            }
        });
}
