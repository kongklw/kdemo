import json
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.core.management.base import BaseCommand, CommandError

from baby.models import BabytreeWeeklyInfo


def _safe_json_loads(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        return None


def _fetch(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, data: Any = None) -> Tuple[int, str, Dict[str, str]]:
    method = (method or "GET").upper()
    headers = headers or {}
    timeout = 30
    if method == "POST":
        resp = requests.post(url, headers=headers, data=data, timeout=timeout)
    else:
        resp = requests.get(url, headers=headers, timeout=timeout)
    return resp.status_code, resp.text, dict(resp.headers)


def _extract_embedded_json(html: str) -> Optional[Any]:
    patterns = [
        r'__NEXT_DATA__\s*=\s*({.*?})\s*</script>',
        r'window\.__NUXT__\s*=\s*({.*?})\s*;?\s*</script>',
        r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;?\s*</script>',
        r'window\.__APOLLO_STATE__\s*=\s*({.*?})\s*;?\s*</script>',
        r'window\.APP_STATE\s*=\s*({.*?})\s*;?\s*</script>',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, flags=re.DOTALL | re.IGNORECASE)
        if not m:
            continue
        candidate = m.group(1)
        obj = _safe_json_loads(candidate)
        if obj is not None:
            return obj
    return None


def _normalize_payload(status_code: int, body_text: str, headers: Dict[str, str]) -> Dict[str, Any]:
    content_type = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        obj = _safe_json_loads(body_text)
        if obj is not None:
            return {"kind": "json", "payload": obj}
    obj = _safe_json_loads(body_text)
    if obj is not None:
        return {"kind": "json", "payload": obj}
    embedded = _extract_embedded_json(body_text)
    if embedded is not None:
        return {"kind": "html_embedded_json", "payload": embedded}
    return {"kind": "html_or_text", "payload": {"status_code": status_code, "body": body_text}}


def _har_pick_entry(har: Dict[str, Any], match: Optional[str], entry_index: Optional[int]) -> Dict[str, Any]:
    log = har.get("log") or {}
    entries = log.get("entries") or []
    if not isinstance(entries, list) or not entries:
        raise CommandError("HAR 文件里没有 entries")

    if entry_index is not None:
        if entry_index < 0 or entry_index >= len(entries):
            raise CommandError("entry-index 超出范围")
        return entries[entry_index]

    match = (match or "").strip()
    if match:
        for entry in entries:
            req = entry.get("request") or {}
            url = req.get("url") or ""
            if match in url:
                return entry

    return entries[-1]


def _har_to_request(entry: Dict[str, Any]) -> Tuple[str, str, Dict[str, str], Any]:
    req = entry.get("request") or {}
    method = (req.get("method") or "GET").upper()
    url = req.get("url") or ""
    if not url:
        raise CommandError("HAR entry 缺少 request.url")
    headers_list = req.get("headers") or []
    headers: Dict[str, str] = {}
    for h in headers_list:
        name = h.get("name")
        value = h.get("value")
        if name and value:
            headers[name] = value
    post_data = req.get("postData") or {}
    data = None
    if method == "POST":
        data = post_data.get("text")
    return url, method, headers, data


def _deep_find_strings(obj: Any, keywords: List[str], max_hits: int = 200) -> List[Tuple[str, str]]:
    hits: List[Tuple[str, str]] = []

    def walk(node: Any, path: str) -> None:
        nonlocal hits
        if len(hits) >= max_hits:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            for kw in keywords:
                if kw in node:
                    hits.append((path, node))
                    break

    walk(obj, "")
    return hits


def _find_dict_nodes(obj: Any, predicate, max_hits: int = 50) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []

    def walk(node: Any) -> None:
        nonlocal hits
        if len(hits) >= max_hits:
            return
        if isinstance(node, dict):
            try:
                if predicate(node):
                    hits.append(node)
            except Exception:
                pass
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(obj)
    return hits


def _pick_text_field(node: Dict[str, Any], preferred_keys: List[str]) -> Optional[str]:
    for k in preferred_keys:
        v = node.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    for v in node.values():
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_weekly_fields(payload: Any) -> Dict[str, Any]:
    keywords = ["宝宝在这周", "成长速查", "成长速查表", "宝宝变化"]
    hits = _deep_find_strings(payload, keywords)

    result: Dict[str, Any] = {
        "this_week_title": None,
        "this_week_content": None,
        "baby_change_text": None,
        "baby_change_question": None,
        "growth_quicklook": {},
        "hits": hits[:50],
    }

    this_week_nodes = _find_dict_nodes(
        payload,
        predicate=lambda d: any(isinstance(v, str) and "宝宝在这周" in v for v in d.values()),
    )
    if this_week_nodes:
        node = this_week_nodes[0]
        result["this_week_title"] = _pick_text_field(node, ["title", "name", "header"])
        result["this_week_content"] = _pick_text_field(node, ["content", "text", "desc", "description", "body", "detail"])

    growth_nodes = _find_dict_nodes(
        payload,
        predicate=lambda d: any(isinstance(v, str) and ("成长速查" in v or "成长速查表" in v) for v in d.values()),
    )
    if growth_nodes:
        result["growth_quicklook"] = growth_nodes[0]

    change_nodes = _find_dict_nodes(
        payload,
        predicate=lambda d: any(isinstance(v, str) and "宝宝变化" in v for v in d.values()),
    )
    if change_nodes:
        node = change_nodes[0]
        result["baby_change_text"] = _pick_text_field(node, ["subtitle", "title", "name", "text", "content"])
        question = _pick_text_field(node, ["question", "ask", "prompt"])
        if isinstance(question, str) and question.strip():
            result["baby_change_question"] = question.strip()

    for path, value in hits:
        if result["this_week_title"] is None and "宝宝在这周" in value:
            result["this_week_title"] = value
        if result["baby_change_text"] is None and "宝宝变化" in value:
            result["baby_change_text"] = value
        if result["baby_change_question"] is None and ("吗" in value or "?" in value) and ("宝宝" in value and "变化" not in value):
            if 8 <= len(value) <= 80:
                result["baby_change_question"] = value
        if "成长速查" in value and not result["growth_quicklook"]:
            result["growth_quicklook"] = {"matched_text": value, "path": path}

    return result


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--url", type=str, default=None)
        parser.add_argument("--har", type=str, default=None)
        parser.add_argument("--match", type=str, default=None)
        parser.add_argument("--entry-index", type=int, default=None)
        parser.add_argument("--week-index", type=int, default=None)
        parser.add_argument("--age-range", type=str, default=None)
        parser.add_argument("--date-range", type=str, default=None)
        parser.add_argument("--stage", type=str, default="baby")
        parser.add_argument("--save", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        url = options.get("url")
        har_path = options.get("har")
        match = options.get("match")
        entry_index = options.get("entry_index")
        stage = options.get("stage") or "baby"

        if not url and not har_path:
            raise CommandError("必须提供 --url 或 --har")

        method = "GET"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Accept": "application/json, text/plain, */*",
        }
        data = None

        if har_path:
            with open(har_path, "r", encoding="utf-8") as f:
                har = json.load(f)
            entry = _har_pick_entry(har, match=match, entry_index=entry_index)
            url, method, har_headers, data = _har_to_request(entry)
            headers.update(har_headers)

        status_code, body_text, resp_headers = _fetch(url, method=method, headers=headers, data=data)
        normalized = _normalize_payload(status_code, body_text, resp_headers)

        parsed_fields = _extract_weekly_fields(normalized["payload"])
        parsed_fields["source_url"] = url
        parsed_fields["stage"] = stage
        parsed_fields["week_index"] = options.get("week_index")
        parsed_fields["age_range_text"] = options.get("age_range")
        parsed_fields["date_range_text"] = options.get("date_range")

        if options.get("dry_run"):
            self.stdout.write(json.dumps(parsed_fields, ensure_ascii=False))
            return

        if options.get("save"):
            defaults = {
                "stage": stage,
                "age_range_text": options.get("age_range"),
                "date_range_text": options.get("date_range"),
                "this_week_title": parsed_fields.get("this_week_title"),
                "this_week_content": parsed_fields.get("this_week_content"),
                "baby_change_text": parsed_fields.get("baby_change_text"),
                "baby_change_question": parsed_fields.get("baby_change_question"),
                "growth_quicklook": parsed_fields.get("growth_quicklook") or {},
                "source_url": url,
                "raw_payload": normalized,
            }
            week_index = options.get("week_index")
            age_range_text = options.get("age_range")
            if week_index is None and age_range_text is None:
                raise CommandError("保存入库时建议提供 --week-index 或 --age-range 用于去重")
            obj, _ = BabytreeWeeklyInfo.objects.update_or_create(
                source="babytree",
                stage=stage,
                week_index=week_index,
                age_range_text=age_range_text,
                defaults=defaults,
            )
            self.stdout.write(json.dumps({"id": obj.id, "source_url": obj.source_url}, ensure_ascii=False))
            return

        self.stdout.write(json.dumps(parsed_fields, ensure_ascii=False))
