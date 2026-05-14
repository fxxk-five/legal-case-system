from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MINI_PROGRAM_DIR = ROOT / "mini-program"
PAGES_JSON = MINI_PROGRAM_DIR / "pages.json"
COMPILED_DIR = MINI_PROGRAM_DIR / "unpackage" / "dist" / "dev" / "mp-weixin"
RUNTIME_DIR = ROOT / ".runtime" / f"mini-program-static-audit-{date.today().isoformat()}"
RESULTS_JSON = RUNTIME_DIR / "results.json"

SUSPICIOUS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("replacement-char", re.compile("\ufffd")),
    ("broken-zh-char", re.compile("锟")),
    ("double-hot", re.compile("烫烫烫")),
    ("multi-question", re.compile(r"(?<!\?)\?{4,}(?!\?)")),
)

PAGE_EXPECTATIONS: dict[str, list[str]] = {
    "pages/login/index": ["安全登录", "选择登录方式"],
    "pages/common/my": ["账号与工作空间", "快捷操作"],
    "pages/common/force-reset-password": ["首次登录请先修改密码", "设置新密码"],
    "pages/lawyer/home": ["案件概览", "新建案件"],
    "pages/lawyer/cases": ["筛选与排序", "搜索标题或案号"],
    "pages/lawyer/create-case": ["案件基础信息", "当事人信息"],
    "pages/lawyer/case-detail": ["案件时间线", "案件文件"],
    "pages/lawyer/clients": ["当事人管理", "列表概览"],
    "pages/lawyer/lawyers": ["律师管理", "邀请入口"],
    "pages/lawyer/analytics": ["分析管理", "任务列表"],
    "pages/client/entry": ["案件邀请", "继续进入"],
    "pages/client/case-list": ["我的案件", "概览"],
    "pages/client/case-detail": ["案件进度", "证据材料"],
    "pages/client/upload-material": ["把材料传给律师", "上传入口"],
    "pages/ai/document-parsing": ["文档智能解析", "点击上传案件文档"],
    "pages/ai/legal-analysis": ["法律分析", "行动建议"],
    "pages/ai/falsification": ["证伪校验", "总校验项"],
}


@dataclass
class PageAuditResult:
    page_id: str
    page_path: str
    source_file: str
    compiled_js: str
    exists: bool
    compiled_exists: bool
    missing_markers: list[str] = field(default_factory=list)
    suspicious_hits: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.exists and self.compiled_exists and not self.missing_markers and not self.suspicious_hits


def json_escape(text: str) -> str:
    return json.dumps(text, ensure_ascii=True)[1:-1]


def contains_marker(blob: str, marker: str) -> bool:
    if marker in blob:
        return True
    return json_escape(marker) in blob


def collect_suspicious_hits(blob: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in SUSPICIOUS_PATTERNS:
        for match in pattern.finditer(blob):
            snippet = blob[max(0, match.start() - 20): min(len(blob), match.end() + 20)]
            snippet = snippet.replace("\n", "\\n")
            hits.append(f"{name}:{snippet}")
            break
    return hits


def audit_page(page_path: str, page_index: int) -> PageAuditResult:
    source_file = MINI_PROGRAM_DIR / f"{page_path}.vue"
    compiled_js = COMPILED_DIR / f"{page_path}.js"

    exists = source_file.exists()
    compiled_exists = compiled_js.exists()
    source_text = source_file.read_text(encoding="utf-8") if exists else ""
    compiled_text = compiled_js.read_text(encoding="utf-8", errors="ignore") if compiled_exists else ""
    blob = "\n".join([source_text, compiled_text])

    missing_markers = [
        marker for marker in PAGE_EXPECTATIONS.get(page_path, []) if not contains_marker(blob, marker)
    ]
    suspicious_hits = collect_suspicious_hits(blob)

    return PageAuditResult(
        page_id=f"MP-{page_index:02d}",
        page_path=page_path,
        source_file=str(source_file.relative_to(ROOT)).replace("\\", "/"),
        compiled_js=str(compiled_js.relative_to(ROOT)).replace("\\", "/"),
        exists=exists,
        compiled_exists=compiled_exists,
        missing_markers=missing_markers,
        suspicious_hits=suspicious_hits,
    )


def main() -> int:
    if not PAGES_JSON.exists():
        print(f"[error] missing pages.json: {PAGES_JSON}")
        return 1

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    pages_doc = json.loads(PAGES_JSON.read_text(encoding="utf-8"))
    pages = pages_doc.get("pages", [])

    results = [
        audit_page(str(page.get("path", "")).strip(), index)
        for index, page in enumerate(pages, start=1)
        if str(page.get("path", "")).strip()
    ]

    payload = {
        "date": date.today().isoformat(),
        "repo_root": str(ROOT),
        "compiled_dir": str(COMPILED_DIR),
        "summary": {
            "total": len(results),
            "passed": sum(1 for item in results if item.passed),
            "failed": sum(1 for item in results if not item.passed),
        },
        "results": [asdict(item) | {"passed": item.passed} for item in results],
    }
    RESULTS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Mini-program static audit summary:")
    print(f"- total:  {payload['summary']['total']}")
    print(f"- passed: {payload['summary']['passed']}")
    print(f"- failed: {payload['summary']['failed']}")
    print(f"- report: {RESULTS_JSON}")

    failed_items = [item for item in results if not item.passed]
    if failed_items:
        print("\nFailed pages:")
        for item in failed_items:
            print(f"- {item.page_id} {item.page_path}")
            if not item.exists:
                print("  - missing source file")
            if not item.compiled_exists:
                print("  - missing compiled js")
            if item.missing_markers:
                print(f"  - missing markers: {', '.join(item.missing_markers)}")
            if item.suspicious_hits:
                print(f"  - suspicious hits: {', '.join(item.suspicious_hits)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
