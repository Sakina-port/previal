from datetime import datetime, timezone
from zoneinfo import ZoneInfo

for texte in ("2026-07-01 12:00:00", "2026-12-01 12:00:00"):
    utc = datetime.strptime(texte, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    paris = utc.astimezone(ZoneInfo("Europe/Paris"))
    print(texte, "UTC  ->", paris.strftime("%Y-%m-%d %H:%M:%S"), "Paris")