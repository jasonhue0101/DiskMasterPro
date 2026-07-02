from pathlib import Path
from rich.console import Console
from diskmaster.core.scanner import Scanner

console = Console()

def main():
    console.print("[bold green]DiskMaster Pro v0.1[/bold green]")
    path = input("Scan Path (Enter=current folder): ").strip()
    if path == "":
        scan_path = Path.cwd()
    else:
        scan_path = Path(path)
    if not scan_path.exists():
        console.print("[red]Path not found.[/red]")
        return

    scanner = Scanner(workers=8)
    scanner.scan(scan_path)
    console.print()
    console.print(f"Folders : {scanner.folder_count:,}")
    console.print(f"Files : {scanner.file_count:,}")
    console.print(f"Size : {scanner.total_size/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()