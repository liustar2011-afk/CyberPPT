"""Page script content-composition contract helpers.

Authority: config/rules.yaml → page_composition.
Used by quality-check to validate onscreen zones, module walls,
backend↔onscreen count alignment, intra-page repeats, and adjacent overlap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .rules import ContentRules

_CIRCLED = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]")
_ZONE_LABELS = r"(?:①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|主判断[：:]|辅助区[：:]|副标题[：:]|标题[：:])"
@dataclass(frozen=True, slots=True)
class CompositionIssue:
    category: str
    page: str
    message: str
    text: str = ""
    level: str = "WARN"


@dataclass(frozen=True, slots=True)
class OnscreenZones:
    title: str
    subtitle: str
    main_judgment: str
    modules: tuple[str, ...]
    auxiliary: str

    @property
    def module_count(self) -> int:
        return len(self.modules)


def _field(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}[：:]\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _labeled_block(onscreen: str, label: str) -> str:
    match = re.search(
        rf"(?:^|\n){re.escape(label)}[：:]\s*(.*?)(?=\n{_ZONE_LABELS}|\Z)",
        onscreen,
        re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _normalize(text: str) -> str:
    return re.sub(r"[\s，。；：、,.!?！？（）()《》〈〉\[\]【】\|｜\-—]+", "", text).lower()


def _shingles(text: str, size: int = 2) -> set[str]:
    normalized = _normalize(text)
    if len(normalized) < size:
        return {normalized} if normalized else set()
    return {normalized[i : i + size] for i in range(len(normalized) - size + 1)}


def _dice(left: str, right: str) -> float:
    left_set = _shingles(left)
    right_set = _shingles(right)
    if not left_set or not right_set:
        return 0.0
    return 2 * len(left_set & right_set) / (len(left_set) + len(right_set))


def parse_onscreen_zones(onscreen: str) -> OnscreenZones:
    title_match = re.search(r"(?:^|\n)标题[：:]\s*\n?\s*([^\n]+)", onscreen)
    title = title_match.group(1).strip() if title_match else ""
    subtitle = _labeled_block(onscreen, "副标题")
    main_judgment = _labeled_block(onscreen, "主判断")
    auxiliary = _labeled_block(onscreen, "辅助区")

    modules: list[str] = []
    circled = list(re.finditer(r"[①②③④⑤⑥⑦⑧⑨⑩]\s*", onscreen))
    if circled:
        for index, match in enumerate(circled):
            start = match.start()
            end = circled[index + 1].start() if index + 1 < len(circled) else len(onscreen)
            chunk = onscreen[start:end].strip()
            # Stop at 辅助区 if it appears inside the last circled block.
            aux_cut = re.search(r"\n辅助区[：:]", chunk)
            if aux_cut:
                chunk = chunk[: aux_cut.start()].strip()
            if chunk:
                modules.append(chunk)
    else:
        # Fallback: blank-line blocks that are not structural labels.
        skip = {"标题", "副标题", "主判断", "辅助区", "注释文字"}
        for raw in re.split(r"\n\s*\n", onscreen):
            block = raw.strip()
            if not block:
                continue
            line = block.splitlines()[0].strip()
            label = line.split("：", 1)[0].split(":", 1)[0].strip()
            if label in skip or line.startswith("标题") or line.startswith("副标题"):
                continue
            if line.startswith("辅助区") or line.startswith("主判断"):
                continue
            modules.append(block)
    return OnscreenZones(title, subtitle, main_judgment, tuple(modules), auxiliary)


def _has_hierarchy(text: str, signals: tuple[str, ...]) -> bool:
    return any(signal and signal in text for signal in signals)


def _backend_blob(text: str, field_names: list[str]) -> str:
    parts = [_field(text, name) for name in field_names]
    # Also capture multi-line-ish single-line fields already covered by _field.
    return "\n".join(part for part in parts if part)


def _claimed_counts(blob: str, patterns: list[dict]) -> list[int]:
    found: list[int] = []
    for item in patterns:
        match = str(item.get("match") or "")
        count = int(item.get("count") or 0)
        if match and count and re.search(match, blob):
            found.append(count)
    return found


def _enumerated_label_count(text: str) -> int:
    """Count short labels listed in subtitle (①… or 口径·留痕·授权)."""
    if not text:
        return 0
    head = re.split(r"[→⇢⇒]|决定|汇聚|环绕|待补齐", text, maxsplit=1)[0]
    circled = len(_CIRCLED.findall(head))
    if circled:
        return circled
    for sep in ("·", "/", "／", "、"):
        if sep in head:
            parts = [part.strip() for part in head.split(sep) if part.strip()]
            # Keep concise labels only; drop long clauses.
            labels = [part for part in parts if 1 <= len(re.sub(r"\s+", "", part)) <= 12]
            if len(labels) >= 2:
                return len(labels)
    return 0


def _module_title(module: str) -> str:
    line = module.splitlines()[0].strip() if module else ""
    return re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*", "", line)


def _shared_ngrams(left: str, right: str, n: int) -> list[str]:
    a = _normalize(left)
    b = _normalize(right)
    if len(a) < n or len(b) < n:
        return []
    left_grams = {a[i : i + n] for i in range(len(a) - n + 1)}
    hits = []
    for i in range(len(b) - n + 1):
        gram = b[i : i + n]
        if gram in left_grams:
            hits.append(gram)
            if len(hits) >= 3:
                break
    return hits


def audit_page_composition(
    *,
    page: str,
    text: str,
    onscreen: str,
    nature: str,
    rules: ContentRules,
    module_count_hint: int | None = None,
) -> list[CompositionIssue]:
    cfg = rules.page_composition or {}
    if nature != "内容页" or not cfg:
        return []

    zones = parse_onscreen_zones(onscreen)
    module_count = module_count_hint if module_count_hint is not None else zones.module_count
    issues: list[CompositionIssue] = []
    hierarchy = tuple(cfg.get("hierarchy_signals") or ())

    # --- required title ---
    if "标题" in (cfg.get("onscreen_zones") or {}).get("required", []) and not zones.title:
        issues.append(
            CompositionIssue(
                "composition-title-missing",
                page,
                "上屏组成缺少标题区",
                level="ERROR",
            )
        )

    # --- module band ---
    modules_cfg = (cfg.get("onscreen_zones") or {}).get("modules") or {}
    min_modules = int(modules_cfg.get("min") or 0)
    max_modules = int(modules_cfg.get("max") or 0)
    preferred_max = int(modules_cfg.get("preferred_max") or 0)
    wall_at = int(modules_cfg.get("wall_warn_at") or 0)
    strategy = _field(text, "落图策略建议")

    if min_modules and module_count and module_count < min_modules and strategy in {"高密度专项", "超高密度专项", "标准"}:
        # Floor for high density already enforced elsewhere; here only warn for thin content pages.
        if strategy == "标准" and module_count < min_modules:
            issues.append(
                CompositionIssue(
                    "composition-modules-thin",
                    page,
                    f"内容页上屏业务模块偏少（建议≥{min_modules}）",
                    f"实际约 {module_count} 个",
                    level="WARN",
                )
            )

    if max_modules and strategy != "超高密度专项" and module_count > max_modules:
        issues.append(
            CompositionIssue(
                "composition-modules-ceiling",
                page,
                f"内容页业务模块超过组成上限 {max_modules}（超高密度专项除外）",
                f"实际约 {module_count} 个",
                level="ERROR",
            )
        )
    elif preferred_max and module_count > preferred_max and not _has_hierarchy(onscreen, hierarchy):
        issues.append(
            CompositionIssue(
                "composition-modules-preferred",
                page,
                f"业务模块超过建议上限 {preferred_max} 且缺少层级/顺序信号，易成等权卡片墙",
                f"实际约 {module_count} 个",
                level="WARN",
            )
        )
    if wall_at and module_count >= wall_at and not _has_hierarchy(onscreen, hierarchy):
        issues.append(
            CompositionIssue(
                "composition-module-wall",
                page,
                f"上屏出现≥{wall_at}个等权模块迹象，应重组关系或拆页",
                f"实际约 {module_count} 个",
                level="WARN",
            )
        )

    # --- subtitle / main judgment dual ---
    dual_cfg = cfg.get("subtitle_main_judgment") or {}
    if zones.subtitle and zones.main_judgment:
        issues.append(
            CompositionIssue(
                "composition-subtitle-main-dual",
                page,
                "副标题与主判断同时填写；Stage-2 副标题位仅一行，须二选一并在视觉转译重点注明",
                level=str(dual_cfg.get("both_filled_level") or "WARN"),
            )
        )

    # --- density strategy max_modules ceiling ---
    # Use the highest max_modules among bound bands (标准 → medium=3, not low=1).
    ceiling_cfg = cfg.get("density_ceiling") or {}
    if ceiling_cfg.get("enforce_max_modules") and strategy in rules.render_strategies:
        render = rules.render_strategies.get(strategy) or {}
        levels = render.get("density_levels") or []
        dens_maxes = []
        for level_name in levels:
            level = rules.density_levels.get(str(level_name)) or {}
            if level.get("max_modules") is not None:
                dens_maxes.append(int(level["max_modules"]))
        dens_max = max(dens_maxes) if dens_maxes else None
        if dens_max is not None and module_count > dens_max:
            issues.append(
                CompositionIssue(
                    "composition-density-max-modules",
                    page,
                    f"落图策略“{strategy}”模块数不得超过 {dens_max}",
                    f"实际约 {module_count} 个",
                    level="ERROR",
                )
            )

    # --- render strategy enum / placeholder ---
    strategy_cfg = cfg.get("render_strategy") or {}
    allowed = tuple(strategy_cfg.get("allowed") or ())
    if strategy and allowed and strategy not in allowed:
        if strategy_cfg.get("reject_placeholder") or True:
            issues.append(
                CompositionIssue(
                    "composition-strategy-invalid",
                    page,
                    "落图策略建议必须是单一合法值，不得保留多选项占位",
                    strategy,
                    level="ERROR",
                )
            )

    # --- diagram type enum ---
    diagram_cfg = cfg.get("diagram_types") or {}
    semantic_type = _field(text, "推荐主语义图类型")
    if diagram_cfg.get("enforce_enum") and semantic_type:
        allowed_types = set(rules.semantic_diagram_types)
        custom_prefix = str(diagram_cfg.get("allow_custom_prefix") or "自定义")
        ok = semantic_type in allowed_types or semantic_type.startswith(custom_prefix)
        if not ok:
            issues.append(
                CompositionIssue(
                    "composition-diagram-type",
                    page,
                    "推荐主语义图类型不在权威枚举中",
                    semantic_type,
                    level="ERROR",
                )
            )

    # --- backend required fields ---
    backend_cfg = cfg.get("backend_fields") or {}
    if backend_cfg.get("enforce"):
        aliases = tuple(backend_cfg.get("conclusion_aliases") or ("核心结论", "页面结论"))
        level = str(backend_cfg.get("level") or "WARN")
        for field in rules.page_fields:
            if not field.get("required"):
                continue
            scope = field.get("scope")
            if scope == "substantive" or scope == "all":
                name = str(field["name"])
                if name == "核心结论":
                    value = next((_field(text, alias) for alias in aliases if _field(text, alias)), "")
                elif name in {"页面性质"}:
                    continue  # already validated elsewhere
                else:
                    value = _field(text, name)
                if not value:
                    issues.append(
                        CompositionIssue(
                            "composition-backend-missing",
                            page,
                            f"内容组成缺少必填后台字段：{name}",
                            level=level,
                        )
                    )

    # --- count alignment (backend N项 vs modules) ---
    count_cfg = cfg.get("count_alignment") or {}
    if count_cfg.get("enabled"):
        blob = _backend_blob(text, list(count_cfg.get("backend_fields") or []))
        claimed = _claimed_counts(blob, list(count_cfg.get("patterns") or []))
        level = str(count_cfg.get("level") or "WARN")
        # Prefer the largest claimed count (e.g. 五项 over 三类 if both appear).
        if claimed and module_count:
            target = max(claimed)
            onscreen_circled = len(set(_CIRCLED.findall(onscreen)))
            subtitle_labels = _enumerated_label_count(zones.subtitle)
            aligned = (
                module_count == target
                or onscreen_circled == target
                or subtitle_labels == target
            )
            # Legacy loophole (subtitle merely says「五项」) is closed unless explicitly enabled.
            if (
                not aligned
                and count_cfg.get("accept_subtitle_count_word_only")
                and zones.subtitle
            ):
                for item in count_cfg.get("patterns") or []:
                    if int(item.get("count") or 0) == target and re.search(
                        str(item.get("match") or ""), zones.subtitle
                    ):
                        aligned = True
                        break
            if not aligned:
                issues.append(
                    CompositionIssue(
                        "composition-count-mismatch",
                        page,
                        f"后台声明约{target}项/类，与上屏模块数不同构（仅写“{target}项”字样不算）",
                        f"后台≈{target}，上屏模块≈{module_count}，副标题短名≈{subtitle_labels}",
                        level=level,
                    )
                )

    # --- intra-page anti-repeat ---
    anti = cfg.get("anti_repeat") or {}
    if anti.get("enabled"):
        n = int(anti.get("ngram_chars") or 8)
        level = str(anti.get("level") or "WARN")
        title_only = bool(anti.get("module_title_only_vs_header", True))
        header_names = {"标题", "副标题", "主判断"}
        zone_texts = [
            ("标题", zones.title),
            ("副标题", zones.subtitle),
            ("主判断", zones.main_judgment),
            ("辅助区", zones.auxiliary),
        ]
        for index, mod in enumerate(zones.modules, start=1):
            zone_texts.append((f"模块{index}", mod))
        for i in range(len(zone_texts)):
            for j in range(i + 1, len(zone_texts)):
                left_name, left = zone_texts[i]
                right_name, right = zone_texts[j]
                if not left or not right:
                    continue
                # Skip comparing module bodies that naturally share short anchors.
                if left_name.startswith("模块") and right_name.startswith("模块"):
                    continue
                left_cmp, right_cmp = left, right
                if title_only:
                    if left_name.startswith("模块") and right_name in header_names:
                        left_cmp = _module_title(left)
                    if right_name.startswith("模块") and left_name in header_names:
                        right_cmp = _module_title(right)
                shared = _shared_ngrams(left_cmp, right_cmp, n)
                if shared:
                    issues.append(
                        CompositionIssue(
                            "composition-intra-repeat",
                            page,
                            f"{left_name}与{right_name}存在同义/同字重复片段",
                            shared[0],
                            level=level,
                        )
                    )
                    break
            else:
                continue
            break

    # --- module body overlap (② vs ③ repeating same entities) ---
    body_cfg = cfg.get("module_body_overlap") or {}
    if body_cfg.get("enabled") and len(zones.modules) >= 2:
        n = int(body_cfg.get("ngram_chars") or 8)
        level = str(body_cfg.get("level") or "WARN")
        for i in range(len(zones.modules)):
            for j in range(i + 1, len(zones.modules)):
                left_body = "\n".join(zones.modules[i].splitlines()[1:]).strip()
                right_body = "\n".join(zones.modules[j].splitlines()[1:]).strip()
                if not left_body or not right_body:
                    continue
                shared = _shared_ngrams(left_body, right_body, n)
                if shared:
                    issues.append(
                        CompositionIssue(
                            "composition-module-overlap",
                            page,
                            f"模块{i + 1}与模块{j + 1}正文存在大段同字，疑似并列重复同一批论据",
                            shared[0],
                            level=level,
                        )
                    )
                    break
            else:
                continue
            break

    # --- module title tautology ---
    taut_cfg = cfg.get("module_title_tautology") or {}
    if taut_cfg.get("enabled"):
        level = str(taut_cfg.get("level") or "WARN")
        for index, mod in enumerate(zones.modules, start=1):
            lines = [line.strip() for line in mod.splitlines() if line.strip()]
            if len(lines) < 2:
                continue
            title = _module_title(lines[0])
            first = lines[1]
            title_n = _normalize(title)
            first_n = _normalize(first)
            if not title_n or len(title_n) < 4:
                continue
            if title_n in first_n or (len(title_n) >= 4 and first_n.startswith(title_n)):
                issues.append(
                    CompositionIssue(
                        "composition-title-tautology",
                        page,
                        f"模块{index}标题与首条要点同义空转，缺少信息增量",
                        f"{title} / {first}",
                        level=level,
                    )
                )
                break

    # --- auxiliary overload ---
    aux_cfg = cfg.get("auxiliary") or {}
    max_aux = int(aux_cfg.get("max_chars") or 0)
    if max_aux and zones.auxiliary:
        aux_len = len(re.sub(r"\s+", "", zones.auxiliary))
        if aux_len > max_aux:
            issues.append(
                CompositionIssue(
                    "composition-aux-overload",
                    page,
                    f"辅助区超过{max_aux}字，易过载；完整闭环/五问宜单页主区展开或邻页回指",
                    f"实际 {aux_len} 字",
                    level=str(aux_cfg.get("level") or "WARN"),
                )
            )
    slogan_patterns = [str(item) for item in (aux_cfg.get("slogan_ban_patterns") or []) if str(item).strip()]
    if zones.auxiliary and slogan_patterns:
        hits = [pat for pat in slogan_patterns if pat in zones.auxiliary]
        if hits:
            issues.append(
                CompositionIssue(
                    "composition-aux-slogan",
                    page,
                    "辅助区出现反误读口号，占用上屏空间；请改到讲解词边界说明或后台约束信息",
                    "、".join(hits),
                    level=str(aux_cfg.get("slogan_ban_level") or aux_cfg.get("level") or "WARN"),
                )
            )

    # --- orphan unlabeled blocks before 辅助区 ---
    orphan_cfg = cfg.get("orphan_blocks") or {}
    if orphan_cfg.get("enabled"):
        orphans = _orphan_blocks(onscreen)
        if orphans:
            issues.append(
                CompositionIssue(
                    "composition-orphan-block",
                    page,
                    "①②③之后、辅助区之前出现未编号业务块，应纳入编号模块或改为底部汇聚条/辅助区",
                    "；".join(orphans[:3]),
                    level=str(orphan_cfg.get("level") or "WARN"),
                )
            )

    # --- interface vs onscreen consistency ---
    iface_cfg = cfg.get("interface_consistency") or {}
    if iface_cfg.get("enabled"):
        level = str(iface_cfg.get("level") or "WARN")
        visual_focus_line = _field(text, "视觉转译重点")
        if re.search(r"主判断", visual_focus_line) and not zones.main_judgment:
            issues.append(
                CompositionIssue(
                    "composition-interface-stale",
                    page,
                    "视觉转译重点引用主判断，但上屏未填写主判断字段",
                    visual_focus_line[:60],
                    level=level,
                )
            )

    return issues


def _orphan_blocks(onscreen: str) -> list[str]:
    """Unlabeled business blocks after circled modules and before 辅助区."""
    aux = re.search(r"(?:^|\n)辅助区[：:]", onscreen)
    region = onscreen[: aux.start()] if aux else onscreen
    region = re.sub(r"(?:^|\n)(?:标题|副标题|主判断)[：:][^\n]*", "\n", region)
    if not _CIRCLED.search(region):
        return []
    orphans: list[str] = []
    for raw in re.split(r"\n\s*\n", region):
        block = raw.strip()
        if not block:
            continue
        first = block.splitlines()[0].strip()
        if _CIRCLED.match(first):
            continue
        if first.startswith(("标题", "副标题", "主判断", "辅助区")):
            continue
        if len(re.sub(r"\s+", "", first)) <= 40:
            orphans.append(first)
    return orphans


def audit_adjacent_overlap(
    pages: list[tuple[str, str]],
    rules: ContentRules,
) -> list[CompositionIssue]:
    """pages: list of (page_name, onscreen_text)."""
    cfg = (rules.page_composition or {}).get("adjacent_overlap") or {}
    if not cfg.get("enabled") or len(pages) < 2:
        return []
    threshold = float(cfg.get("min_similarity") or 0.55)
    aux_threshold = float(cfg.get("aux_similarity") or 0.42)
    level = str(cfg.get("level") or "WARN")
    issues: list[CompositionIssue] = []
    for index in range(len(pages) - 1):
        left_name, left_text = pages[index]
        right_name, right_text = pages[index + 1]
        score = _dice(left_text, right_text)
        if score >= threshold:
            issues.append(
                CompositionIssue(
                    "composition-adjacent-overlap",
                    f"{left_name}↔{right_name}",
                    "相邻页上屏内容相似度偏高，疑似换词重复",
                    f"similarity={score:.2f}",
                    level=level,
                )
            )
        left_aux = parse_onscreen_zones(left_text).auxiliary
        right_aux = parse_onscreen_zones(right_text).auxiliary
        if left_aux and right_aux:
            aux_score = _dice(left_aux, right_aux)
            if aux_score >= aux_threshold:
                issues.append(
                    CompositionIssue(
                        "composition-adjacent-aux-overlap",
                        f"{left_name}↔{right_name}",
                        "相邻页辅助区相似度偏高，完整论据应只在一页展开",
                        f"aux_similarity={aux_score:.2f}",
                        level=level,
                    )
                )
    return issues


def audit_cross_page_fingerprints(
    pages: list[tuple[str, str]],
    rules: ContentRules,
) -> list[CompositionIssue]:
    """Flag structural fingerprints that appear complete on multiple pages."""
    cfg = (rules.page_composition or {}).get("cross_page_fingerprints") or {}
    if not cfg.get("enabled") or len(pages) < 2:
        return []
    level = str(cfg.get("level") or "WARN")
    issues: list[CompositionIssue] = []
    for item in cfg.get("patterns") or []:
        pattern = str(item.get("match") or "")
        label = str(item.get("label") or item.get("id") or "指纹")
        if not pattern:
            continue
        hits = [name for name, onscreen in pages if re.search(pattern, onscreen, re.DOTALL)]
        if len(hits) >= 2:
            issues.append(
                CompositionIssue(
                    "composition-fingerprint-dup",
                    "↔".join(hits[:4]),
                    f"跨页重复完整展开「{label}」；信息只在一页完整出现，邻页半行回指",
                    f"{len(hits)}页命中",
                    level=level,
                )
            )
    return issues
