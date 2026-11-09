import re, sys
for f in sys.argv[1:]:
    t = open(f, encoding="utf-8").read()
    body = t.split("\n---\n", 1)[1] if t.startswith("---") else t
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    n = lambda s: len(re.sub(r"\s", "", s))
    code = "".join(re.findall(r"```.*?```", body, flags=re.S))
    line = f"{f}: 本文{n(body)}字（空白を除く。コード{n(code)}字を含む）"
    if "ここから有料" in body:
        free = body.split("ここから有料")[0]; line += f"／無料部分{n(free)}字（{n(free)*100//n(body)}%）"
    long = []
    prose = re.sub(r"```.*?```", "", body, flags=re.S)
    for l in prose.splitlines():
        for s in re.split(r"(?<=[。])", l.strip()):
            if len(s) > 60 and not s.startswith(("［", "この記事は", "ChatGPTは", "#")): long.append((len(s), s[:40]))
    print(line, "／60字超の文", len(long), long[:6])
