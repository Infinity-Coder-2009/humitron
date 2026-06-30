@echo off
echo Checking Rust installation...
rustc --version
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Rust is not installed.
    echo To install Rust, run: winget install Rustlang.Rustup
    echo Or visit: https://rustup.rs
    exit /b 1
)
echo Rust is installed.