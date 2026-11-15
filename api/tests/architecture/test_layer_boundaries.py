import ast
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]


def _imported_modules(package: str) -> set[str]:
    package_root = API_ROOT / package
    imported: set[str] = set()

    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module)

    return imported


def test_domain_does_not_depend_on_framework_or_infrastructure_code():
    forbidden_prefixes = (
        "adapters",
        "fastapi",
        "infrastructure",
        "sqlalchemy",
    )

    forbidden = sorted(
        module
        for module in _imported_modules("domain")
        if module.startswith(forbidden_prefixes)
    )

    assert forbidden == []


def test_application_does_not_depend_on_http_adapters():
    forbidden_prefixes = ("adapters.inbound.http",)

    forbidden = sorted(
        module
        for module in _imported_modules("application")
        if module.startswith(forbidden_prefixes)
    )

    assert forbidden == []


def test_auth_application_does_not_depend_on_web_frameworks():
    forbidden_prefixes = ("fastapi", "sqlalchemy")

    forbidden = sorted(
        module
        for module in _imported_modules("application/auth")
        if module.startswith(forbidden_prefixes)
    )

    assert forbidden == []
