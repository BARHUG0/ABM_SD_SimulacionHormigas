import json
import sys
from pathlib import Path

from hormiguero.main import app

DEFAULT_TARGET = Path(__file__).resolve().parents[3] / "contract" / "openapi.json"


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Contrato exportado en {target}")


if __name__ == "__main__":
    main()
