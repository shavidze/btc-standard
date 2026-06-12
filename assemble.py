# -*- coding: utf-8 -*-
"""Assemble content/ch*.json into content.js for the static site."""
import json, os

SITE = os.path.dirname(os.path.abspath(__file__))
content = {}
for n in range(1, 10):
    p = os.path.join(SITE, "content", f"ch{n}.json")
    if os.path.exists(p):
        content[n] = json.load(open(p, encoding="utf-8"))

out = "window.COURSE_CONTENT = " + json.dumps(content, ensure_ascii=False) + ";\n"
open(os.path.join(SITE, "content.js"), "w", encoding="utf-8").write(out)
print(f"content.js: {len(content)} chapters — {', '.join('ch'+str(k) for k in content)}")
