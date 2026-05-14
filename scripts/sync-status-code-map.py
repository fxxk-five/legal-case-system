from __future__ import annotations

import json
from pathlib import Path


def _render_js(mapping: dict[str, str]) -> str:
    lines = ["export const STATUS_CODE_MAP = Object.freeze({"]
    for status in sorted(mapping, key=int):
        code = mapping[status]
        lines.append(f"  {int(status)}: '{code}',")
    lines.append("})")
    lines.append("")
    lines.append("export default STATUS_CODE_MAP")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    source_file = project_root / "contracts" / "status-code-map.json"

    mapping = json.loads(source_file.read_text(encoding="utf-8"))

    targets = [
        project_root / "web-frontend" / "src" / "shared" / "api" / "statusCodeMap.js",
        project_root / "mini-program" / "shared" / "api" / "statusCodeMap.js",
    ]

    js_content = _render_js(mapping)
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(js_content, encoding="utf-8")
        print(f"updated {target.relative_to(project_root)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
