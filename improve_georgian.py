# -*- coding: utf-8 -*-
"""Improve Georgian quality of book chapters (.md) and app lessons (.json) via Gemini.
Editor pass only: polish language, preserve meaning/structure/terminology/quiz answers."""
import urllib.request, urllib.error, json, os, sys, time, re

BOOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(os.path.expanduser("~"), ".gemini_api_key")).read().strip()
MODEL = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"

TERMS = ("ტერმინოლოგია: hard money = „მყარი ფული“, easy money = „მარტივი ფული“ "
         "(არა „რბილი ფული“), salability = „გაყიდვადობა“, time preference = „დროის პრეფერენცია“. "
         "უცხო ტექნიკური ტერმინი ფრჩხილებში დატოვე როგორც არის (მაგ. peer-to-peer).")


MD_PROMPT = """შენ ხარ გამოცდილი ქართული ენის რედაქტორი და კორექტორი. ქვემოთ მოცემულია წიგნის ერთი თავის ქართული თარგმანი markdown ფორმატში.

შენი ამოცანა: გააუმჯობესე მხოლოდ ქართულის ხარისხი — წინადადებების ბუნებრიობა და სიგლუვე, სტილი, გრამატიკა, პუნქტუაცია. გამოიყენე ქართული ბრჭყალები „ “ ASCII-ს ნაცვლად. გაასწორე მოუხეშავი კალკები და გრამატიკული შეცდომები.

მკაცრი წესები:
- არ შეცვალო აზრი, ფაქტები, ციფრები, თარიღები ან მაგალითები.
- სრულად შეინარჩუნე markdown სტრუქტურა: ყველა სათაური (#, ##, ###), სია, ცხრილი, ემოჯი, **bold**, _italic_, ბმული, ჰორიზონტალური ხაზი (---) ზუსტად იმავე ადგილას.
- არ დაამატო და არ წაშალო აბზაცი, სათაური ან სტრუქტურული ელემენტი. რაოდენობა უცვლელი დარჩეს.
- {terms}
- ნუ დაამატებ შენგან კომენტარს, ჩარჩოს ან ახსნას.

დააბრუნე მხოლოდ გაუმჯობესებული markdown ტექსტი, თავიდან ბოლომდე, სხვა არაფერი.


ტექსტი:
{text}
"""

JSON_PROMPT = """შენ ხარ გამოცდილი ქართული ენის რედაქტორი. ქვემოთ მოცემულია ინტერაქტიული კურსის ერთი თავის შიგთავსი JSON-ში (გაკვეთილები + ტესტი).

შენი ამოცანა: გააუმჯობესე მხოლოდ ქართულის ხარისხი ყველა ტექსტურ ველში — ბუნებრიობა, სიგლუვე, სტილი, გრამატიკა, პუნქტუაცია. ქართული ბრჭყალები „ “.


მკაცრი წესები:
- დააბრუნე ზუსტად იგივე JSON სტრუქტურა და გასაღებები: lessons[] (თითო: nav, title, html), quiz[] (თითო: q, opts[4], a, ex).
- გაკვეთილების და კითხვების რაოდენობა უცვლელი. opts ყოველთვის ზუსტად 4.
- "a" (სწორი პასუხის ინდექსი) არ შეცვალო და opts-ის რიგი არ შეცვალო — მხოლოდ ფორმულირება გააუმჯობესე.
- html-ში დაცული დარჩეს ტეგები (<p>, <p class="drop">, <b>, <ul>, <li>, <div class="quote">) იმავე რაოდენობით; <script> არასდროს.
- title-ის დასაწყისში ემოჯი შეინარჩუნე.
- არ შეცვალო აზრი ან ფაქტი. {terms}
- ნუ დაამატებ კომენტარს.

დააბრუნე მხოლოდ JSON.

შიგთავსი:
{text}
"""

def call(prompt, as_json):
    cfg = {"temperature": 0.3, "maxOutputTokens": 65536}
    if as_json:
        cfg["response_mime_type"] = "application/json"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg}).encode("utf-8")
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                r = json.load(resp)
            return r["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            print(f"  HTTP {e.code} (try {attempt+1}): {msg}", flush=True)
            if e.code in (429, 500, 503):
                time.sleep(25 * (attempt + 1)); continue
            raise
        except Exception as e:
            print(f"  err (try {attempt+1}): {e}", flush=True); time.sleep(12)
    raise RuntimeError("gemini failed")

def improve_md(path, label):
    text = open(path, encoding="utf-8").read()
    h_before = len(re.findall(r"(?m)^#{1,6} ", text))
    print(f"{label}: {len(text)//1024} KB, {h_before} headings -> gemini...", flush=True)
    out = call(MD_PROMPT.replace("{terms}", TERMS).replace("{text}", text), as_json=False)
    out = re.sub(r"^```(markdown)?\s*|\s*```$", "", out.strip())
    h_after = len(re.findall(r"(?m)^#{1,6} ", out))
    assert len(out) > len(text) * 0.6, f"output too short ({len(out)} vs {len(text)})"
    assert abs(h_after - h_before) <= 1, f"heading count drift {h_before}->{h_after}"
    open(path, "w", encoding="utf-8").write(out + ("\n" if not out.endswith("\n") else ""))
    print(f"{label}: OK — {h_after} headings, {len(out)//1024} KB", flush=True)

def improve_json(path, label):
    orig = json.load(open(path, encoding="utf-8"))
    print(f"{label}: {len(orig['lessons'])} lessons, {len(orig['quiz'])} quiz -> gemini...", flush=True)
    raw = call(JSON_PROMPT.replace("{terms}", TERMS).replace("{text}", json.dumps(orig, ensure_ascii=False)), as_json=True)
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw.strip())
    data = json.loads(raw)
    assert len(data["lessons"]) == len(orig["lessons"]), "lesson count changed"
    assert len(data["quiz"]) == len(orig["quiz"]) == 8, "quiz count changed"
    for i, (q, o) in enumerate(zip(data["quiz"], orig["quiz"])):
        assert len(q["opts"]) == 4, f"q{i} opts != 4"
        assert q["a"] == o["a"], f"q{i} answer index changed {o['a']}->{q['a']}"
    for l in data["lessons"]:
        assert "<script" not in l["html"].lower(), "script injection"
        assert l["html"].count("<p") >= 1, "lost paragraphs"
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{label}: OK", flush=True)


JOBS = [
    ("01. Money.md", "ch1.json", "თავი 1 (ფული)"),
    ("02. Primitive Moneys.md", "ch2.json", "თავი 2 (პრიმიტიული ფული)"),
]
for md, js, label in JOBS:
    improve_md(os.path.join(BOOK, md), label + " · წიგნი")
    time.sleep(5)
    improve_json(os.path.join(SITE, "content", js), label + " · აპლიკაცია")
    time.sleep(5)
print("ALL DONE", flush=True)
