import subprocess
import sys
from importlib.metadata import version

from rich.console import Console
from rich.table import Table

console = Console()

# ========================================
# SECTION 1: Python package checks
#=========================================

REQUIRED_PACKAGES = [
    # (import_name, display_name)
    ("agentic_sentinel", "agentic-sentinel"),
    ("rich",        "rich"),
    ("streamlit",   "streamlit"),
    ("typer",       "typer"),
    ("fastapi",     "fastapi"),
    ("uvicorn",     "uvicorn"),
    ("sqlmodel",    "sqlmodel"),
    ("chromadb",    "chromadb"),
    ("httpx",       "httpx"),
    ("pytest",      "pytest"),
    ("langchain",   "langchain"),
    ("langgraph",   "langgraph"),
    ("ruff",        "ruff"),
    ("mypy",        "mypy")
]

def check_python_packages() -> list[tuple[str, bool, str]]:
    """
    Check if all required python packages are installed.

    Returns a list of tuples containing the package name, a boolean indicating if
    the package is installed, and an error message if the package is not installed.
    """
    results = []
    for import_name, display_name in REQUIRED_PACKAGES:
        try:
            __import__(import_name)
            results.append((display_name, True, version(display_name)))
        except ImportError as e:
            results.append((display_name, False, str(e)))
    return results

# ==========================================
# SECTION 2: System tool checks
# ==========================================

REQUIRED_TOOLS = [
    # (shell_command, display_name)
    # Check these with `which` to confirm they're on PATH
    ("git",              "git"),
    ("podman",           "podman"),
    ("podman-compose",   "podman_compose"),
    ("python3",          "python3"),
    ("sqlite3",          "sqlite3")
]

def check_system_tools() -> list[tuple[str, bool, str]]:
    """
    Check if all required system tools are installed and on PATH.

    Returns a list of tuples containing the tool name, a boolean indicating if
    the tool is installed, and an error message if the tool is not installed.
    """
    results = []
    for command, display_name in REQUIRED_TOOLS:
        result = subprocess.run(["which", command], capture_output=True, text=True) # noqa: S603,S607
        if result.returncode == 0:
            results.append((display_name, True, result.stdout.strip()))
        else:
            results.append((display_name, False, "NOT FOUND - install with dnf"))
    return results

# =========================================
# SECTION 3: Python version check
# =========================================

def check_python_version() -> tuple[bool, str]:
    """
    Check if the current Python version is 3.11 or higher.

    Returns a tuple containing a boolean indicating if the version is ok,
    and a string representing the current version.
    """
    major = sys.version_info.major
    minor = sys.version_info.minor
    ok = major == 3 and minor >=3.11
    version_str = f"{major}.{minor}.{sys.version_info.micro}"
    return ok, version_str


# ======================================
# SECTION 4: Report rendering
# ======================================

def render_report(
    python_ok: bool,
    python_version: str,
    package_results: list[tuple[str, bool, str]],
    tool_results: list[tuple[str, bool, str]]
    ) -> bool:
    """
    Render a report summarizing the results of environment checks.

    Prints a table containing the results of package checks,
    system tool checks and python version check.
    Returns True if all checks pass, False otherwise.
    """
    console.print("\n[bold cyan]=== Agentic Sentinel - Environment Check ===[/bold cyan]\n")

    # Python version row
    py_status = "[green]✅ OK[/green]" if python_ok else "[red]x FAIL[/red]"
    console.print(f"Python version : {python_version} {py_status}")
    console.print()

    # Packages table
    pkg_table = Table(title="Python Packages", show_lines=True)
    pkg_table.add_column("Package", style="cyan", min_width=30)
    pkg_table.add_column("Status", min_width=10)
    pkg_table.add_column("Version", style="dim")


    all_pkg_ok = True
    for name, ok, ver in package_results:
        status = "[green]✅ OK[/green]" if ok else "[red]x FAIL[/red]"
        if not ok:
            all_pkg_ok = False
        pkg_table.add_row(name, status, ver)
    console.print(pkg_table)
    console.print()

    # Tools table
    tool_table = Table(title="System Tools", show_lines=True)
    tool_table.add_column("Tool", style="cyan", min_width=20)
    tool_table.add_column("Status", min_width=10)
    tool_table.add_column("Path", style="dim")

    all_tools_ok = True
    for name, ok, path in tool_results:
        status = "[green]✅ OK[/green]" if ok else "[red]x FAIL[/red]"
        if not ok:
            all_tools_ok = False
        tool_table.add_row(name, status, path)
    console.print(tool_table)
    console.print()

    overall = python_ok and all_pkg_ok and all_tools_ok
    if overall:
        console.print("[bold green]✅ All checks passed. Environment is ready.[/bold green]\n")
    else:
        console.print("[bold red]x Some checks failed.\
        Fix the items above before proceeding.[/bold red]\n"
        )
    return overall

# ==============================
# SECTION 5: Main entrypoint
# ===============================

def main() -> None:
    python_ok, python_version = check_python_version()
    package_results = check_python_packages()
    tool_results = check_system_tools()

    all_ok = render_report(python_ok, python_version, package_results, tool_results)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
