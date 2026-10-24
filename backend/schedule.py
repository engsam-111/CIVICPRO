from datetime import date, timedelta


def _d(s):
    try:
        return date.fromisoformat(s[:10]) if s else None
    except ValueError:
        return None


def planned_at(start, end, day):
    """Standard S-curve (smoothstep) between project start and finish."""
    s, e = _d(start), _d(end)
    if not s or not e or e <= s:
        return None
    x = min(1, max(0, (day - s).days / (e - s).days))
    return round(100 * (3 * x ** 2 - 2 * x ** 3), 1)


def build_curve(project, snapshots, today):
    s, e = _d(project.get("start_date")), _d(project.get("end_date"))
    if not s or not e or e <= s:
        return None
    last = max(e, today)
    step = max(1, (last - s).days // 40)
    days = [s + timedelta(days=i) for i in range(0, (last - s).days + 1, step)]
    for extra in (today, e, last):
        if s <= extra <= last and extra not in days:
            days.append(extra)
    days.sort()
    snaps = sorted((_d(x["date"]), x["progress"]) for x in snapshots if _d(x["date"]))
    points = []
    for day in days:
        actual = None
        if day <= today:
            prior = [p for d, p in snaps if d <= day]
            actual = prior[-1] if prior else (0 if day <= (snaps[0][0] if snaps else today) else None)
        points.append({"date": day.isoformat(), "planned": planned_at(project["start_date"], project["end_date"], day), "actual": actual})
    planned_today = planned_at(project["start_date"], project["end_date"], today)
    return {"points": points, "planned_today": planned_today, "actual_today": project["progress"], "variance": round(project["progress"] - planned_today, 1), "today": today.isoformat()}
