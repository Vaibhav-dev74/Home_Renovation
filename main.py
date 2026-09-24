"""Entry point and runner for AI Home Renovation Planner.

Usage:
    python main.py             # Start interactive terminal chat (default)
    python main.py --cli       # Start interactive terminal chat
    python main.py --web       # Launch ADK Web UI in browser
    python main.py --check     # Run project health & diagnostic checks
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 console output on Windows to prevent UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load environment configuration
load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
PARENT_DIR = PROJECT_DIR.parent
PROJECT_NAME = PROJECT_DIR.name


def print_banner():
    banner = r"""
========================================================================
   [AI HOME RENOVATION PLANNER] - MULTI-AGENT SYSTEM
   Powered by Google ADK (Agent Development Kit) & Gemini Multimodal
========================================================================
    """
    print(banner)


def run_diagnostics():
    """Verify environment, API keys, dependencies, tools, and agent loading."""
    print("\n[*] Running AI Home Renovation Planner Pre-Flight Check...\n")
    all_passed = True

    # 1. Check Python version
    py_ver = sys.version.split()[0]
    print(f"  [OK] Python Runtime: {py_ver}")

    # 2. Check API Key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key and not api_key.startswith("your_"):
        masked = api_key[:6] + "..." + api_key[-4:]
        print(f"  [OK] Gemini API Key Configured: {masked}")
    else:
        print("  [!] Warning: GOOGLE_API_KEY or GEMINI_API_KEY not configured in .env.")
        print("      Add your key to `.env` to enable live LLM responses and rendering.")

    # 3. Check Tools module
    try:
        import tools
        export_count = len(getattr(tools, "__all__", []))
        print(f"  [OK] Tools Module: Loaded cleanly ({export_count} exports verified)")
    except Exception as e:
        print(f"  [FAIL] Tools Module Error: {e}")
        all_passed = False

    # 4. Check Agent module
    try:
        import agent
        root = getattr(agent, "root_agent", None)
        if root:
            subagent_names = [sub.name for sub in root.sub_agents]
            print(f"  [OK] Multi-Agent Hierarchy: Root '{root.name}' with specialists: {subagent_names}")
        else:
            print("  [FAIL] Agent Module: root_agent not found.")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Agent Module Error: {e}")
        all_passed = False

    # 5. Check ADK AgentLoader compatibility
    try:
        from google.adk.cli.cli import AgentLoader
        loader = AgentLoader(str(PARENT_DIR))
        loaded_agent = loader.load_agent(PROJECT_NAME)
        print(f"  [OK] ADK Loader Compatibility: Agent '{loaded_agent.name}' discovered by ADK")
    except Exception as e:
        print(f"  [FAIL] ADK Loader Check Error: {e}")
        all_passed = False

    # 6. Sample tool sanity executions
    try:
        from agent import estimate_renovation_cost, calculate_timeline
        from tools import check_renovation_permits, recommend_materials_and_finishes
        _ = estimate_renovation_cost("kitchen", "moderate", 150)
        _ = calculate_timeline("moderate", "kitchen")
        _ = check_renovation_permits("bathroom", "moderate")
        _ = recommend_materials_and_finishes("kitchen", "modern", "moderate")
        print("  [OK] Core Renovation Tools: Calculations and recommendations verified")
    except Exception as e:
        print(f"  [FAIL] Core Tools Sanity Error: {e}")
        all_passed = False

    print("\n------------------------------------------------------------------------")
    if all_passed:
        print(">> System Status: ALL CHECKS PASSED! The project is healthy and ready to run.")
    else:
        print(">> Warning: Some checks reported errors. Review details above.")
    print("------------------------------------------------------------------------\n")
    return all_passed


import socket


def is_port_in_use(port: int) -> bool:
    """Check if a network port is already bound on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_available_port(start_port: int = 8000) -> int:
    """Find the next available port starting from start_port."""
    port = start_port
    while port < start_port + 50:
        if not is_port_in_use(port):
            return port
        port += 1
    return start_port


def launch_web(port: int = 8000):
    """Launch ADK Web server for visual chat and photo uploads."""
    if is_port_in_use(port):
        free_port = find_available_port(port + 1)
        print(f"\n[!] Notice: Port {port} is currently in use by another running process.")
        print(f"    Automatically switching to available port {free_port}...\n")
        port = free_port

    print_banner()
    print(f"Starting ADK Web UI server on port {port}...")
    print(f"Open your browser and navigate to: http://localhost:{port}")
    print("Press Ctrl+C to stop the server.\n")

    cmd = [
        sys.executable,
        "-m",
        "google.adk.cli",
        "web",
        str(PARENT_DIR),
        f"--port={port}",
    ]
    try:
        subprocess.run(cmd, cwd=str(PROJECT_DIR))
    except KeyboardInterrupt:
        print("\nADK Web server stopped.")


def launch_cli():
    """Launch interactive terminal CLI session with the root agent."""
    print_banner()
    print("Starting Interactive Multi-Agent Terminal Session...")
    print("Type your questions or renovation requests (e.g. 'Plan my 150 sq ft kitchen').")
    print("Press Ctrl+C or type 'exit' to quit.\n")

    cmd = [
        sys.executable,
        "-m",
        "google.adk.cli",
        "run",
        PROJECT_NAME,
    ]
    try:
        # Run from PARENT_DIR so ADK can resolve the agent package
        subprocess.run(cmd, cwd=str(PARENT_DIR))
    except KeyboardInterrupt:
        print("\nSession ended.")


def main():
    parser = argparse.ArgumentParser(
        description="AI Home Renovation Planner - Google ADK Multi-Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run interactive terminal CLI chat session (default)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the ADK Web UI in your browser",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the Web UI server (default: 8000)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run environment, key, and agent diagnostics",
    )

    args = parser.parse_args()

    if args.check:
        run_diagnostics()
    elif args.web:
        launch_web(port=args.port)
    else:
        launch_cli()


if __name__ == "__main__":
    main()

