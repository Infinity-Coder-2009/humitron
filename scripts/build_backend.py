#!/usr/bin/env python3
"""Build script for Python backend using PyInstaller."""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def build_backend():
    """Build the Python backend executable."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    dist_dir = project_root / "src-tauri" / "sidecars"
    
    # Ensure sidecars directory exists
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Run PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        f"--distpath={dist_dir}",
        f"--workpath={project_root / 'build' / 'pyinstaller'}",
        f"--specpath={project_root}",
        "pyinstaller.spec",
    ]
    
    print(f"Building backend...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        print("Backend built successfully!")
        
        # Copy to platform-specific name
        if sys.platform == "win32":
            exe_name = "humitron-backend.exe"
        else:
            exe_name = "humitron-backend"
        
        src_exe = dist_dir / exe_name
        if src_exe.exists():
            # Also copy to root for Tauri bundling
            shutil.copy2(src_exe, project_root / exe_name)
            print(f"Copied {exe_name} to project root")
    else:
        print("Backend build failed!")
        sys.exit(1)


if __name__ == "__main__":
    build_backend()