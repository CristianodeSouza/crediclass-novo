from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pdf_bridge import ensure_react_pdf_runtime


def main() -> None:
    status = ensure_react_pdf_runtime(install_if_missing=True)
    print(
        "React-pdf runtime pronto:",
        {
            "available": status.get("available"),
            "node": status.get("node"),
            "npm": status.get("npm"),
            "dependencies_installed": status.get("dependencies_installed"),
        },
    )


if __name__ == "__main__":
    main()
