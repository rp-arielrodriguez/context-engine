from __future__ import annotations

import re


def normalize_range(values: list[int]) -> tuple[int, int, int, int] | None:
    if len(values) == 4:
        return values[0], values[1], values[2], values[3]
    if len(values) == 3:
        return values[0], values[1], values[0], values[2]
    return None


def scope_size(scope: tuple[int, int, int, int]) -> int:
    sl, sc, el, ec = scope
    return (el - sl) * 100000 + (ec - sc)


def contains_scope(scope: tuple[int, int, int, int], line: int, col: int) -> bool:
    sl, sc, el, ec = scope
    if line < sl or line > el:
        return False
    if line == sl and col < sc:
        return False
    if line == el and col > ec:
        return False
    return True


def is_spring_component_annotation(symbol: str) -> bool:
    return any(
        token in symbol
        for token in (
            "org/springframework/stereotype/Service",
            "org/springframework/stereotype/Component",
            "org/springframework/stereotype/Controller",
            "org/springframework/web/bind/annotation/RestController",
        )
    )


def is_spring_mapping_annotation(symbol: str) -> bool:
    return any(
        token in symbol
        for token in (
            "org/springframework/web/bind/annotation/RequestMapping",
            "org/springframework/web/bind/annotation/GetMapping",
            "org/springframework/web/bind/annotation/PostMapping",
            "org/springframework/web/bind/annotation/PutMapping",
            "org/springframework/web/bind/annotation/DeleteMapping",
            "org/springframework/web/bind/annotation/PatchMapping",
        )
    )


def is_injection_annotation(symbol: str) -> bool:
    return any(
        token in symbol
        for token in (
            "org/springframework/beans/factory/annotation/Autowired",
            "javax/inject/Inject",
            "jakarta/inject/Inject",
        )
    )


def fqcn_from_symbol(symbol: str) -> str | None:
    prefix = "semanticdb maven . . "
    if not symbol.startswith(prefix):
        return None
    body = symbol[len(prefix):]
    hash_idx = body.find("#")
    if hash_idx == -1:
        slash_idx = body.rfind("/")
        if slash_idx == -1:
            return None
        body = body[:slash_idx]
    else:
        body = body[:hash_idx]
    body = body.rstrip("/")
    if not body:
        return None
    return body.replace("/", ".")


def simple_name_from_fqcn(fqcn: str) -> str:
    return fqcn.rsplit(".", 1)[-1]


def bean_name_for_class(fqcn: str) -> str:
    simple = simple_name_from_fqcn(fqcn)
    if not simple:
        return fqcn
    return simple[:1].lower() + simple[1:]


def extract_import_map(source: str) -> dict[str, str]:
    imports: dict[str, str] = {}
    for match in re.finditer(r"^import\s+([\w\.]+);", source, flags=re.MULTILINE):
        fqcn = match.group(1)
        imports[simple_name_from_fqcn(fqcn)] = fqcn
    return imports


def extract_constructor_params(source: str, class_name: str) -> list[tuple[str, str]]:
    pattern = re.compile(rf"public\s+{re.escape(class_name)}\s*\((.*?)\)", re.DOTALL)
    match = pattern.search(source)
    if not match:
        return []
    params_blob = match.group(1).strip()
    if not params_blob:
        return []
    params: list[tuple[str, str]] = []
    for raw in params_blob.split(","):
        part = raw.strip()
        if not part:
            continue
        tokens = part.split()
        if len(tokens) < 2:
            continue
        param_name = tokens[-1]
        type_name = tokens[-2]
        params.append((param_name, type_name))
    return params


def extract_field_types(source: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    pattern = re.compile(
        r"(?:@Autowired\s+)?(?:private|protected|public)\s+(?:final\s+)?([\w<>\.]+)\s+(\w+)\s*;",
        re.MULTILINE,
    )
    for match in pattern.finditer(source):
        type_name = match.group(1)
        field_name = match.group(2)
        fields[field_name] = type_name
    return fields


def extract_final_fields(source: str) -> set[str]:
    finals: set[str] = set()
    pattern = re.compile(
        r"(?:private|protected|public)\s+final\s+[\w<>\.]+\s+(\w+)\s*;",
        re.MULTILINE,
    )
    for match in pattern.finditer(source):
        finals.add(match.group(1))
    return finals


def field_has_nearby_inject_annotation(source: str, field_name: str) -> bool:
    lines = source.splitlines()
    for idx, line in enumerate(lines):
        if field_name not in line or ";" not in line:
            continue
        window = "\n".join(lines[max(0, idx - 2) : idx + 1])
        if "@Autowired" in window or "@Inject" in window:
            return True
    return False


def extract_qualifier_hint(source: str, field_name: str) -> str | None:
    """Extract @Qualifier("name") or @Resource(name="name") for a field.

    Searches a small window above the field declaration for:
    - @Qualifier("beanName")
    - @Resource(name = "beanName")
    """
    lines = source.splitlines()
    for idx, line in enumerate(lines):
        if field_name not in line or ";" not in line:
            continue
        window = "\n".join(lines[max(0, idx - 3) : idx + 1])
        q_match = re.search(r'@Qualifier\(\s*"([^"]+)"\s*\)', window)
        if q_match:
            return q_match.group(1)
        r_match = re.search(r'@Resource\(\s*name\s*=\s*"([^"]+)"\s*\)', window)
        if r_match:
            return r_match.group(1)
    return None


def extract_constructor_qualifier_hints(source: str, class_name: str) -> dict[str, str]:
    """Extract @Qualifier hints from constructor parameters.

    Returns {param_name: qualifier_value} for parameters annotated with @Qualifier.
    """
    pattern = re.compile(rf"public\s+{re.escape(class_name)}\s*\((.*?)\)\s*\{{", re.DOTALL)
    match = pattern.search(source)
    if not match:
        return {}
    params_blob = match.group(1).strip()
    if not params_blob:
        return {}
    hints: dict[str, str] = {}
    for raw in params_blob.split(","):
        part = raw.strip()
        if not part:
            continue
        q_match = re.search(r'@Qualifier\(\s*"([^"]+)"\s*\)', part)
        if q_match:
            tokens = part.split()
            if len(tokens) >= 2:
                param_name = tokens[-1]
                hints[param_name] = q_match.group(1)
    return hints


def is_test_document(document: str) -> bool:
    return "/src/test/" in document or document.startswith("src/test/") or "/test/" in document


def extract_implemented_interfaces(source: str, class_name: str) -> list[str]:
    pattern = re.compile(
        rf"class\s+{re.escape(class_name)}(?:\s+extends\s+[\w\.<>]+)?\s+implements\s+([^{{]+)\{{",
        re.MULTILINE,
    )
    match = pattern.search(source)
    if not match:
        return []
    raw = match.group(1)
    return [part.strip().split("<", 1)[0] for part in raw.split(",") if part.strip()]


def extract_bean_methods(source: str) -> list[tuple[str, str]]:
    lines = source.splitlines()
    out: list[tuple[str, str]] = []
    for idx, line in enumerate(lines):
        if "@Bean" not in line:
            continue
        for follow in lines[idx + 1 : idx + 6]:
            candidate = follow.strip()
            if not candidate or candidate.startswith("@"):
                continue
            match = re.search(r"public\s+([\w\.<>]+)\s+(\w+)\s*\(", candidate)
            if match:
                return_type = match.group(1).split("<", 1)[0]
                method_name = match.group(2)
                out.append((method_name, return_type))
                break
    return out


def is_reactor_publisher_symbol(symbol: str) -> bool:
    return any(token in symbol for token in ("reactor/core/publisher/Mono#", "reactor/core/publisher/Flux#"))


def reactor_operator_name(symbol: str) -> str | None:
    operators = {
        "#fromFuture().": "fromFuture",
        "#fromCallable().": "fromCallable",
        "#map().": "map",
        "#flatMap().": "flatMap",
        "#filter().": "filter",
        "#zip().": "zip",
        "#defaultIfEmpty().": "defaultIfEmpty",
        "#doOnError().": "doOnError",
        "#onErrorResume().": "onErrorResume",
        "#just().": "just",
        "#justOrEmpty().": "justOrEmpty",
        "#block().": "block",
    }
    for token, name in operators.items():
        if token in symbol:
            return name
    if "#onErrorMap" in symbol:
        return "onErrorMap"
    return None
