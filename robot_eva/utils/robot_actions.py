import json
import re
from typing import Any, Dict, List, Tuple


def extract_robot_actions(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extract a machine-readable robot actions block from assistant text.

    Supported formats:
    1) XML-ish:
       <robot_actions>
       {"actions":[{"type":"emotion","value":"wink"}]}
       </robot_actions>

    2) Markdown-ish:
       *действия для робота*
       {"actions":[...]}
       *конец действий*

    Returns:
      (clean_text_without_block, actions_list)
    """
    s = text or ""
    actions: List[Dict[str, Any]] = []

    # Try <robot_actions>...</robot_actions>
    m = re.search(r"<robot_actions>\s*([\s\S]*?)\s*</robot_actions>", s, re.IGNORECASE)
    if not m:
        # Try *действия для робота* ... *конец действий*
        m = re.search(
            r"\*действия\s+для\s+робота\*\s*([\s\S]*?)\s*\*конец\s+действий\*",
            s,
            re.IGNORECASE,
        )

    if m:
        payload = (m.group(1) or "").strip()
        clean = (s[: m.start()] + s[m.end() :]).strip()

        # Extract JSON from payload
        jm = re.search(r"\{[\s\S]*\}", payload)
        if jm:
            try:
                obj = json.loads(jm.group(0))
                if isinstance(obj, dict) and isinstance(obj.get("actions"), list):
                    actions = [a for a in obj["actions"] if isinstance(a, dict)]
                elif isinstance(obj, list):
                    actions = [a for a in obj if isinstance(a, dict)]
            except Exception:
                actions = []
        return clean, actions

    return s.strip(), []


