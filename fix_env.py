from pathlib import Path

p = Path("scripts/study.py")
s = p.read_text(encoding="utf-8-sig")

s = s.replace(
    'env_file.read_text(encoding="utf-8")',
    'env_file.read_text(encoding="utf-8-sig")'
)

s = s.replace(
    'os.environ.setdefault(k.strip(), v.strip().strip(\'"\'))',
    'os.environ[k.strip()] = v.strip().strip(\'"\').strip("\'")'
)

p.write_text(s, encoding="utf-8")
print("Fixed .env loading.")
