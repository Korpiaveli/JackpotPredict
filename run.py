#!/usr/bin/env python3
"""
JackpotPredict Run Script
=========================
Unified script to start both backend and frontend servers.

Usage:
    python run.py              # Start both servers
    python run.py --backend    # Start backend only
    python run.py --frontend   # Start frontend only
    python run.py --build      # Build frontend for production

The application will be available at:
    - Frontend: http://localhost:5173
    - Backend API: http://localhost:8000
    - API Docs: http://localhost:8000/docs
"""

import os
import sys
import subprocess
import signal
import time
import threading
from pathlib import Path
from typing import Optional, List

# Constants
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Global process handles
processes: List[subprocess.Popen] = []


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

    @classmethod
    def disable(cls):
        """Disable colors for non-supporting terminals."""
        cls.GREEN = cls.YELLOW = cls.RED = cls.BLUE = cls.CYAN = cls.BOLD = cls.END = ''


# Enable ANSI colors on Windows
if os.name == 'nt':
    try:
        os.system('')
    except:
        Colors.disable()


def print_banner():
    """Print application banner."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
     ██╗ █████╗  ██████╗██╗  ██╗██████╗  ██████╗ ████████╗
     ██║██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗╚══██╔══╝
     ██║███████║██║     █████╔╝ ██████╔╝██║   ██║   ██║
██   ██║██╔══██║██║     ██╔═██╗ ██╔═══╝ ██║   ██║   ██║
╚█████╔╝██║  ██║╚██████╗██║  ██╗██║     ╚██████╔╝   ██║
 ╚════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝      ╚═════╝    ╚═╝

          ██████╗ ██████╗ ███████╗██████╗ ██╗ ██████╗████████╗
          ██╔══██╗██╔══██╗██╔════╝██╔══██╗██║██╔════╝╚══██╔══╝
          ██████╔╝██████╔╝█████╗  ██║  ██║██║██║        ██║
          ██╔═══╝ ██╔══██╗██╔══╝  ██║  ██║██║██║        ██║
          ██║     ██║  ██║███████╗██████╔╝██║╚██████╗   ██║
          ╚═╝     ╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝ ╚═════╝   ╚═╝
{Colors.END}
    {Colors.GREEN}AI-Powered Trivia Prediction for Netflix Best Guess Live{Colors.END}
""")


def print_status(component: str, message: str, color: str = Colors.BLUE):
    """Print a status message with component prefix."""
    print(f"{color}[{component}]{Colors.END} {message}")


def check_prerequisites() -> bool:
    """Check if setup has been completed."""
    # Check backend venv
    if os.name == 'nt':
        python_path = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    else:
        python_path = BACKEND_DIR / "venv" / "bin" / "python"

    if not python_path.exists():
        print(f"{Colors.RED}[ERROR]{Colors.END} Backend not set up. Run 'python setup.py' first.")
        return False

    # Check frontend node_modules
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print(f"{Colors.RED}[ERROR]{Colors.END} Frontend not set up. Run 'python setup.py' first.")
        return False

    # Check .env
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        print(f"{Colors.YELLOW}[WARNING]{Colors.END} No .env file found. Creating from template...")
        env_example = BACKEND_DIR / ".env.example"
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print(f"{Colors.GREEN}[OK]{Colors.END} .env created. Please configure your GEMINI_API_KEY.")
        else:
            print(f"{Colors.RED}[ERROR]{Colors.END} No .env.example found.")
            return False

    return True


def get_python_executable() -> str:
    """Get path to Python executable in venv."""
    if os.name == 'nt':
        return str(BACKEND_DIR / "venv" / "Scripts" / "python.exe")
    else:
        return str(BACKEND_DIR / "venv" / "bin" / "python")


def start_backend() -> Optional[subprocess.Popen]:
    """Start the backend server."""
    print_status("BACKEND", "Starting FastAPI server...", Colors.GREEN)

    python_exe = get_python_executable()

    # Use uvicorn module directly
    cmd = [
        python_exe, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]

    try:
        process = subprocess.Popen(
            cmd,
            cwd=BACKEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(process)

        # Wait a moment for startup
        time.sleep(2)

        if process.poll() is None:
            print_status("BACKEND", f"Running at {Colors.CYAN}http://localhost:8000{Colors.END}", Colors.GREEN)
            print_status("BACKEND", f"API Docs at {Colors.CYAN}http://localhost:8000/docs{Colors.END}", Colors.GREEN)
            return process
        else:
            print_status("BACKEND", "Failed to start!", Colors.RED)
            return None

    except Exception as e:
        print_status("BACKEND", f"Error: {e}", Colors.RED)
        return None


def start_frontend() -> Optional[subprocess.Popen]:
    """Start the frontend dev server."""
    print_status("FRONTEND", "Starting Vite dev server...", Colors.BLUE)

    cmd = ["npm", "run", "dev"]

    try:
        process = subprocess.Popen(
            cmd,
            cwd=FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=(os.name == 'nt')
        )
        processes.append(process)

        # Wait a moment for startup
        time.sleep(3)

        if process.poll() is None:
            print_status("FRONTEND", f"Running at {Colors.CYAN}http://localhost:5173{Colors.END}", Colors.BLUE)
            return process
        else:
            print_status("FRONTEND", "Failed to start!", Colors.RED)
            return None

    except Exception as e:
        print_status("FRONTEND", f"Error: {e}", Colors.RED)
        return None


def build_frontend() -> bool:
    """Build frontend for production."""
    print_status("BUILD", "Building frontend for production...", Colors.YELLOW)

    cmd = ["npm", "run", "build"]

    try:
        result = subprocess.run(
            cmd,
            cwd=FRONTEND_DIR,
            shell=(os.name == 'nt')
        )
        if result.returncode == 0:
            print_status("BUILD", "Frontend built successfully!", Colors.GREEN)
            print_status("BUILD", f"Output in {FRONTEND_DIR / 'dist'}", Colors.GREEN)
            return True
        else:
            print_status("BUILD", "Build failed!", Colors.RED)
            return False

    except Exception as e:
        print_status("BUILD", f"Error: {e}", Colors.RED)
        return False


def stream_output(process: subprocess.Popen, prefix: str, color: str):
    """Stream process output to console."""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                # Filter out some noisy lines
                line = line.strip()
                if line and not line.startswith('  '):  # Skip deep indentation
                    print(f"{color}[{prefix}]{Colors.END} {line}")
            if process.poll() is not None:
                break
    except:
        pass


def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    print(f"\n{Colors.YELLOW}[SHUTDOWN]{Colors.END} Stopping servers...")

    for proc in processes:
        try:
            if os.name == 'nt':
                proc.terminate()
            else:
                proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=5)
        except:
            proc.kill()

    print(f"{Colors.GREEN}[SHUTDOWN]{Colors.END} All servers stopped.")
    sys.exit(0)


def main():
    """Main entry point."""
    args = sys.argv[1:]

    # Show help
    if "--help" in args or "-h" in args:
        print(__doc__)
        return

    # Build mode
    if "--build" in args:
        if check_prerequisites():
            success = build_frontend()
            sys.exit(0 if success else 1)
        else:
            sys.exit(1)

    # Print banner
    print_banner()

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Register cleanup handler
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    backend_only = "--backend" in args
    frontend_only = "--frontend" in args

    backend_proc = None
    frontend_proc = None

    try:
        # Start backend
        if not frontend_only:
            backend_proc = start_backend()
            if not backend_proc:
                print(f"\n{Colors.RED}[ERROR]{Colors.END} Backend failed to start. Check logs above.")
                sys.exit(1)

        # Start frontend
        if not backend_only:
            frontend_proc = start_frontend()
            if not frontend_proc:
                print(f"\n{Colors.RED}[ERROR]{Colors.END} Frontend failed to start. Check logs above.")
                cleanup()

        # Print final status
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}{Colors.BOLD}  JackpotPredict is running!{Colors.END}")
        print(f"{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.END}")

        if not frontend_only:
            print(f"\n  {Colors.BOLD}Backend API:{Colors.END}  http://localhost:8000")
            print(f"  {Colors.BOLD}API Docs:{Colors.END}     http://localhost:8000/docs")

        if not backend_only:
            print(f"\n  {Colors.BOLD}Frontend:{Colors.END}     http://localhost:5173")

        print(f"\n  Press {Colors.YELLOW}Ctrl+C{Colors.END} to stop all servers.\n")

        # Stream output
        threads = []

        if backend_proc:
            t = threading.Thread(target=stream_output, args=(backend_proc, "BACKEND", Colors.GREEN))
            t.daemon = True
            t.start()
            threads.append(t)

        if frontend_proc:
            t = threading.Thread(target=stream_output, args=(frontend_proc, "FRONTEND", Colors.BLUE))
            t.daemon = True
            t.start()
            threads.append(t)

        # Wait for processes
        while True:
            if backend_proc and backend_proc.poll() is not None:
                print_status("BACKEND", "Process exited unexpectedly!", Colors.RED)
                cleanup()

            if frontend_proc and frontend_proc.poll() is not None:
                print_status("FRONTEND", "Process exited unexpectedly!", Colors.RED)
                cleanup()

            time.sleep(1)

    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
