#!/usr/bin/env python3
"""101 文例に使う日付の曜日を、Pythonのカレンダーで確かめる。"""
import calendar, datetime
W = "月火水木金土日"
calendar.setfirstweekday(calendar.SUNDAY)
print(calendar.month(2026, 12)); print(calendar.month(2027, 1))
for label, s, want in [("休業開始", "2026-12-29", "火"), ("休業最終日", "2027-01-04", "月"), ("営業開始", "2027-01-05", "火")]:
    d = datetime.date.fromisoformat(s)
    got = W[d.weekday()]
    print(f"{label} {s}: {got}曜日 {'一致' if got == want else '不一致（記事は' + want + '）'}")
start, end = datetime.date(2026, 12, 29), datetime.date(2027, 1, 4)
print("休業日数（初日と最終日を含む）:", (end - start).days + 1, "日")
print("最終日の翌日 = 営業開始日:", end + datetime.timedelta(days=1) == datetime.date(2027, 1, 5))
