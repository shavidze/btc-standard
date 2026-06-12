# -*- coding: utf-8 -*-
"""Generate lesson/quiz JSON for chapters 2-9 via Gemini from the Georgian translation."""
import urllib.request, urllib.error, json, os, sys, time, re

BOOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")
os.makedirs(OUT, exist_ok=True)
KEY = open(os.path.join(os.path.expanduser("~"), ".gemini_api_key")).read().strip()
MODEL = "gemini-2.5-flash"

CHAPTERS = [
    ("02. Primitive Moneys.md", 2, "პრიმიტიული ფული"),
    ("03. Monetary Metals.md", 3, "მონეტარული ლითონები"),
    ("04. Government Money.md", 4, "სახელმწიფო ფული"),
    ("05. Money and Time Preference.md", 5, "ფული და დროის პრეფერენცია"),
    ("06. Capitalism's Information System.md", 6, "კაპიტალიზმის საინფორმაციო სისტემა"),
    ("07. Sound Money and Individual Freedom.md", 7, "მყარი ფული და თავისუფლება"),
    ("08. Digital Money.md", 8, "ციფრული ფული"),
    ("09. Bitcoin Questions.md", 9, "კითხვები ბიტკოინზე"),
]

PROMPT = """შენ ხარ გამოცდილი ქართველი პედაგოგი და რედაქტორი. ქვემოთ მოცემულია საიფედინ ამმუსის „ბიტკოინ სტანდარტის" ერთი თავის ქართული კონსპექტი. შენი ამოცანაა ის გადააქციო ინტერაქტიული ონლაინ კურსის გაკვეთილებად.

დააბრუნე ზუსტად ეს JSON სტრუქტურა:
{
  "lessons": [
    {"nav": "მოკლე სახელი (1-3 სიტყვა)", "title": "ემოჯი + გაკვეთილის სათაური", "html": "HTML კონტენტი"}
  ],
  "quiz": [
    {"q": "კითხვა", "opts": ["ვარიანტი 1", "ვარიანტი 2", "ვარიანტი 3", "ვარიანტი 4"], "a": 0, "ex": "ახსნა რატომ არის ეს პასუხი სწორი"}
  ]
}

წესები:
- 5-7 გაკვეთილი, თითო 100-180 სიტყვა. ლოგიკური თანმიმდევრობით დაშალე თავის მთავარი იდეები.
- html-ში დასაშვებია მხოლოდ: <p>, <b>, <ul>, <li>, <div class="quote">. პირველი აბზაცი ყოველთვის: <p class="drop">.
- <div class="quote"> გამოიყენე თავის ერთი ყველაზე დასამახსოვრებელი აზრისთვის (გაკვეთილების უმეტესობაში იყოს).
- ენა: ცოცხალი, მარტივი ქართული. მკითხველს მიმართე „შენ"-ით. ნუ გადატვირთავ ტერმინებით — ტერმინი ახსენი პირველივე გამოყენებისას.
- quiz: ზუსტად 8 კითხვა. "a" არის სწორი პასუხის ინდექსი (0-3). სწორი პასუხები სხვადასხვა პოზიციაზე გაანაწილე. "ex" — 1-2 წინადადება.
- არ გამოიგონო ფაქტები, რომლებიც ტექსტში არ არის. მხოლოდ მოცემულ კონსპექტს დაეყრდენი.
- ნუ ახსენებ „კონსპექტს" ან „წიგნს" — წერე როგორც დამოუკიდებელი გაკვეთილი.

თავის სათაური: „{title}"

ტექსტი:
{text}
"""

def call_gemini(prompt, retries=4):
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.4,
            "maxOutputTokens": 65536,
        },
    }).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                r = json.load(resp)
            return r["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            print(f"  HTTP {e.code} (attempt {attempt+1}): {msg}", flush=True)
            if e.code in (429, 500, 503):
                time.sleep(30 * (attempt + 1))
                continue
            raise
        except Exception as e:
            print(f"  error (attempt {attempt+1}): {e}", flush=True)
            time.sleep(15)
    raise RuntimeError("gemini failed after retries")

def validate(data):
    assert isinstance(data.get("lessons"), list) and 4 <= len(data["lessons"]) <= 8, "lessons count"
    assert isinstance(data.get("quiz"), list) and len(data["quiz"]) == 8, "quiz count"
    for l in data["lessons"]:
        assert l.get("nav") and l.get("title") and l.get("html"), "lesson fields"
        assert "<script" not in l["html"].lower(), "script injection"
    for q in data["quiz"]:
        assert q.get("q") and isinstance(q.get("opts"), list) and len(q["opts"]) == 4, "quiz fields"
        assert isinstance(q.get("a"), int) and 0 <= q["a"] <= 3, "answer index"

for fname, num, title in CHAPTERS:
    out_path = os.path.join(OUT, f"ch{num}.json")
    if os.path.exists(out_path):
        print(f"ch{num}: exists, skipping", flush=True)
        continue
    text = open(os.path.join(BOOK, fname), encoding="utf-8").read()
    print(f"ch{num} ({title}): {len(text)//1024} KB -> gemini...", flush=True)
    raw = call_gemini(PROMPT.replace("{title}", title).replace("{text}", text))
    raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.M).strip()
    data = json.loads(raw)
    validate(data)
    json.dump(data, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ch{num}: OK — {len(data['lessons'])} lessons, {len(data['quiz'])} quiz", flush=True)
    time.sleep(8)

print("ALL DONE", flush=True)
