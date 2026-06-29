#!/usr/bin/env python3
"""Deployment script for Humitron."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, cwd: Path = None) -> tuple:
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def build_docker(image_name: str = "humitron", tag: str = "latest") -> bool:
    """Build Docker image."""
    print(f"Building Docker image: {image_name}:{tag}")
    success, output = run_command(["docker", "build", "-t", f"{image_name}:{tag}", "."])
    if success:
        print("Docker image built successfully")
    else:
        print(f"Docker build failed: {output}")
    return success


def run_tests() -> bool:
    """Run test suite."""
    print("Running tests...")
    success, output = run_command(["python", "-m", "pytest", "tests/", "-v"])
    if success:
        print("All tests passed")
    else:
        print(f"Tests failed: {output}")
    return success


def lint_code() -> bool:
    """Run linter."""
    print("Running linter...")
    success, output = run_command(["ruff", "check", "src/", "tests/"])
    if success:
        print("Linting passed")
    else:
        print(f"Linting failed: {output}")
    return success


def format_code() -> bool:
    """Format code with black."""
    print("Formatting code...")
    success, output = run_command(["black", "src/", "tests/"])
    if success:
        print("Formatting complete")
    else:
        print(f"Formatting failed: {output}")
    return success


def main():
    parser = argparse.ArgumentParser(description="Deploy Humitron")
    parser.add_argument("--build", action="store_true", help="Build Docker image")
    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument("--lint", action="store_true", help="Run linter")
    parser.add_argument("--format", action="store_true", help="Format code")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--image", default="humitron", help="Docker image name")
    parser.add_argument("--tag", default="latest", help="Docker image tag")

    args = parser.parse_args()

    if args.all:
        args.test = True
        args.lint = True
        args.format = True
        args.build = True

    all_passed = True

    if args.format:
        all_passed &= format_code()

    if args.lint:
        all_passed &= lint_code()

    if args.test:
        all_passed &= run_tests()

    if args.build:
        all_passed &= build_docker(args.image, args.tag)

    if all_passed:
        print("\n✅ All deployment steps passed!")
        sys.exit(0)
    else:
        print("\n❌ Some deployment steps failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()