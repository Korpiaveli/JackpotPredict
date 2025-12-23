#!/usr/bin/env python3
"""
JackpotPredict Setup Script
===========================
Cross-platform setup for installing and configuring JackpotPredict.

Usage:
    python setup.py           # Full setup
    python setup.py --check   # Check installation status
    python setup.py --update  # Update dependencies only

Requirements:
    - Python 3.10+
    - Node.js 18+
    - npm
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path
from typing import Tuple, Optional

# Constants
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = BACKEND_DIR / "app" / "data"

# Minimum versions
MIN_PYTHON_VERSION = (3, 10)
MIN_NODE_VERSION = 18

# Required data files (will be created if missing)
REQUIRED_DATA_FILES = {
    "history.json": [],
    "error_patterns.json": {"patterns": [], "last_updated": ""},
}


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

    @classmethod
    def disable(cls):
        """Disable colors for non-supporting terminals."""
        cls.GREEN = cls.YELLOW = cls.RED = cls.BLUE = cls.BOLD = cls.END = ''


# Disable colors on Windows cmd.exe (not PowerShell)
if os.name == 'nt' and 'ANSICON' not in os.environ and 'WT_SESSION' not in os.environ:
    try:
        os.system('')  # Enable ANSI on Windows 10+
    except:
        Colors.disable()


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_step(text: str):
    """Print a step indicator."""
    print(f"{Colors.BLUE}[*]{Colors.END} {text}")


def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.GREEN}[+]{Colors.END} {text}")


def print_warning(text: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}[!]{Colors.END} {text}")


def print_error(text: str):
    """Print an error message."""
    print(f"{Colors.RED}[X]{Colors.END} {text}")


def run_command(cmd: list, cwd: Optional[Path] = None, capture: bool = False) -> Tuple[bool, str]:
    """
    Run a shell command.

    Args:
        cmd: Command and arguments as a list
        cwd: Working directory
        capture: Whether to capture output

    Returns:
        Tuple of (success, output)
    """
    try:
        if capture:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                shell=(os.name == 'nt')
            )
            return result.returncode == 0, result.stdout.strip()
        else:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                shell=(os.name == 'nt')
            )
            return result.returncode == 0, ""
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except Exception as e:
        return False, str(e)


def check_python_version() -> bool:
    """Check if Python version meets requirements."""
    version = sys.version_info[:2]
    if version >= MIN_PYTHON_VERSION:
        print_success(f"Python {version[0]}.{version[1]} detected (>= {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} required)")
        return True
    else:
        print_error(f"Python {version[0]}.{version[1]} detected, but >= {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} required")
        return False


def check_node_version() -> bool:
    """Check if Node.js version meets requirements."""
    success, output = run_command(["node", "--version"], capture=True)
    if not success:
        print_error("Node.js not found. Please install Node.js 18+")
        return False

    try:
        version = int(output.lstrip('v').split('.')[0])
        if version >= MIN_NODE_VERSION:
            print_success(f"Node.js v{version} detected (>= {MIN_NODE_VERSION} required)")
            return True
        else:
            print_error(f"Node.js v{version} detected, but >= {MIN_NODE_VERSION} required")
            return False
    except:
        print_warning(f"Could not parse Node.js version: {output}")
        return True  # Assume it's okay


def check_npm() -> bool:
    """Check if npm is available."""
    success, output = run_command(["npm", "--version"], capture=True)
    if success:
        print_success(f"npm v{output} detected")
        return True
    else:
        print_error("npm not found. Please install Node.js with npm")
        return False


def setup_backend_venv() -> bool:
    """Create and setup Python virtual environment for backend."""
    print_step("Setting up Python virtual environment...")

    venv_path = BACKEND_DIR / "venv"

    # Create venv if it doesn't exist
    if not venv_path.exists():
        success, output = run_command([sys.executable, "-m", "venv", str(venv_path)])
        if not success:
            print_error(f"Failed to create virtual environment: {output}")
            return False
        print_success("Virtual environment created")
    else:
        print_success("Virtual environment already exists")

    # Determine pip path
    if os.name == 'nt':
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"

    # Upgrade pip
    print_step("Upgrading pip...")
    run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], capture=True)

    # Install requirements
    print_step("Installing Python dependencies...")
    requirements_path = BACKEND_DIR / "requirements.txt"
    success, output = run_command([str(pip_path), "install", "-r", str(requirements_path)])
    if not success:
        print_error(f"Failed to install requirements: {output}")
        return False
    print_success("Python dependencies installed")

    # Download spaCy model
    print_step("Downloading spaCy language model...")
    success, _ = run_command([str(python_path), "-m", "spacy", "download", "en_core_web_sm"], capture=True)
    if success:
        print_success("spaCy model downloaded")
    else:
        print_warning("spaCy model download may have failed - will try at runtime")

    return True


def setup_frontend() -> bool:
    """Install frontend dependencies."""
    print_step("Installing frontend dependencies...")

    success, output = run_command(["npm", "install"], cwd=FRONTEND_DIR)
    if not success:
        print_error(f"Failed to install npm dependencies: {output}")
        return False

    print_success("Frontend dependencies installed")
    return True


def setup_env_file() -> bool:
    """Create .env file from template if it doesn't exist."""
    env_example = BACKEND_DIR / ".env.example"
    env_file = BACKEND_DIR / ".env"

    if env_file.exists():
        print_success(".env file already exists")
        return True

    if env_example.exists():
        shutil.copy(env_example, env_file)
        print_success(".env file created from template")
        print_warning("Please edit backend/.env and add your GEMINI_API_KEY")
        return True
    else:
        print_error(".env.example template not found")
        return False


def setup_data_files() -> bool:
    """Ensure required data files exist."""
    print_step("Checking data files...")

    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for filename, default_content in REQUIRED_DATA_FILES.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(default_content, f, indent=2)
            print_success(f"Created {filename}")
        else:
            print_success(f"{filename} already exists")

    return True


def check_gemini_api_key() -> bool:
    """Check if Gemini API key is configured."""
    env_file = BACKEND_DIR / ".env"

    if not env_file.exists():
        print_warning("No .env file found")
        return False

    with open(env_file, 'r') as f:
        content = f.read()

    if "GEMINI_API_KEY=" in content:
        # Check if it has a value (not empty)
        for line in content.split('\n'):
            if line.startswith('GEMINI_API_KEY='):
                value = line.split('=', 1)[1].strip()
                if value and not value.startswith('#'):
                    print_success("Gemini API key is configured")
                    return True

    print_warning("Gemini API key not configured in backend/.env")
    print_warning("Get your free key at: https://aistudio.google.com/app/apikey")
    return False


def check_installation() -> bool:
    """Check current installation status."""
    print_header("JackpotPredict Installation Check")

    checks = []

    # Python version
    checks.append(("Python version", check_python_version()))

    # Node.js
    checks.append(("Node.js", check_node_version()))
    checks.append(("npm", check_npm()))

    # Virtual environment
    venv_path = BACKEND_DIR / "venv"
    venv_exists = venv_path.exists()
    if venv_exists:
        print_success("Backend virtual environment exists")
    else:
        print_warning("Backend virtual environment not found")
    checks.append(("Backend venv", venv_exists))

    # Frontend node_modules
    node_modules = FRONTEND_DIR / "node_modules"
    node_exists = node_modules.exists()
    if node_exists:
        print_success("Frontend node_modules exists")
    else:
        print_warning("Frontend node_modules not found")
    checks.append(("Frontend dependencies", node_exists))

    # .env file
    env_file = BACKEND_DIR / ".env"
    env_exists = env_file.exists()
    if env_exists:
        print_success(".env file exists")
    else:
        print_warning(".env file not found")
    checks.append((".env file", env_exists))

    # Gemini API key
    checks.append(("Gemini API key", check_gemini_api_key()))

    # Data files
    for filename in REQUIRED_DATA_FILES.keys():
        filepath = DATA_DIR / filename
        exists = filepath.exists()
        if exists:
            print_success(f"Data file: {filename}")
        else:
            print_warning(f"Data file missing: {filename}")
        checks.append((f"Data: {filename}", exists))

    # Summary
    print_header("Summary")
    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    if passed == total:
        print_success(f"All checks passed ({passed}/{total})")
        return True
    else:
        print_warning(f"Some checks failed ({passed}/{total})")
        return False


def full_setup():
    """Run full setup process."""
    print_header("JackpotPredict Full Setup")
    print(f"Project root: {PROJECT_ROOT}\n")

    # Check prerequisites
    print_header("Checking Prerequisites")

    if not check_python_version():
        print_error("Setup cannot continue without Python 3.10+")
        return False

    if not check_node_version():
        print_error("Setup cannot continue without Node.js 18+")
        return False

    if not check_npm():
        print_error("Setup cannot continue without npm")
        return False

    # Setup backend
    print_header("Setting Up Backend")
    if not setup_backend_venv():
        return False

    # Setup frontend
    print_header("Setting Up Frontend")
    if not setup_frontend():
        return False

    # Setup configuration
    print_header("Setting Up Configuration")
    if not setup_env_file():
        return False

    if not setup_data_files():
        return False

    # Check API key
    print_header("API Configuration")
    check_gemini_api_key()

    # Final summary
    print_header("Setup Complete!")
    print(f"""
{Colors.GREEN}JackpotPredict is now installed!{Colors.END}

{Colors.BOLD}Next steps:{Colors.END}
1. Edit {Colors.YELLOW}backend/.env{Colors.END} and add your Gemini API key:
   GEMINI_API_KEY=your_key_here

2. Get a free API key at: {Colors.BLUE}https://aistudio.google.com/app/apikey{Colors.END}

3. Start the application:
   {Colors.YELLOW}python run.py{Colors.END}

   Or manually:
   - Backend:  cd backend && venv/Scripts/activate && uvicorn app.main:app --reload
   - Frontend: cd frontend && npm run dev

{Colors.BOLD}Data files are stored in:{Colors.END}
   {DATA_DIR}

   - history.json: Past game results for few-shot learning
   - error_patterns.json: Tracked prediction errors
   - entities.db: Entity database (auto-generated)
""")

    return True


def update_dependencies():
    """Update only dependencies without full setup."""
    print_header("Updating Dependencies")

    print_header("Updating Backend")
    if os.name == 'nt':
        pip_path = BACKEND_DIR / "venv" / "Scripts" / "pip.exe"
    else:
        pip_path = BACKEND_DIR / "venv" / "bin" / "pip"

    if pip_path.exists():
        requirements_path = BACKEND_DIR / "requirements.txt"
        success, _ = run_command([str(pip_path), "install", "-r", str(requirements_path), "--upgrade"])
        if success:
            print_success("Backend dependencies updated")
        else:
            print_error("Failed to update backend dependencies")
    else:
        print_error("Backend venv not found. Run full setup first.")
        return False

    print_header("Updating Frontend")
    success, _ = run_command(["npm", "update"], cwd=FRONTEND_DIR)
    if success:
        print_success("Frontend dependencies updated")
    else:
        print_error("Failed to update frontend dependencies")
        return False

    print_success("All dependencies updated!")
    return True


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if "--check" in args:
        success = check_installation()
        sys.exit(0 if success else 1)
    elif "--update" in args:
        success = update_dependencies()
        sys.exit(0 if success else 1)
    elif "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)
    else:
        success = full_setup()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
