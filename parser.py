"""中文任务 & 截止时间解析器"""

import re
from datetime import datetime, timedelta

_WEEKDAY = {"一":0,"二":1,"三":2,"四":3,"五":4,"六":5,"日":6,"天":6}
_PERIOD_HOUR = {"凌晨":0,"早上":7,"早晨":7,"上午":9,"中午":12,"下午":14,"傍晚":17,"晚上":20}
_DAY_OFFSET = {"今天":0,"明天":1,"后天":2,"大后天":3}


def parse_message(content: str, now: datetime = None) -> tuple:
    """解析消息,返回 (task_desc, deadline)"""
    if now is None:
        now = datetime.now()
    cleaned = re.sub(r"@\S+\s*", "", content).strip()
    if not cleaned:
        return None, None
    deadline = _extract_deadline(cleaned, now)
    task_desc = _clean_time_tokens(cleaned).strip()
    if not task_desc:
        task_desc = cleaned.strip()
    return (task_desc or cleaned, deadline)


def _extract_deadline(text: str, now: datetime):
    apply = lambda b,h,m: b.replace(hour=h,minute=m,second=0,microsecond=0)

    # 1. "X月X日 HH:MM" or "X月X日"
    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]\s*(?:(\d{1,2}):(\d{2}))?", text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = now.year + (1 if month < now.month else 0)
        try:
            base = datetime(year, month, day)
        except ValueError:
            return None
        if m.group(3):
            return apply(base, int(m.group(3)), int(m.group(4)))
        return base.replace(hour=23, minute=59, second=0)

    # 2. relative day + period + time
    m = re.search(r"(今天|明天|后天|大后天)\s*(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上)?\s*(\d{1,2})?\s*[点:：]\s*(\d{1,2})?\s*分?\s*(半)?", text)
    if m:
        base = now + timedelta(days=_DAY_OFFSET[m.group(1)])
        h = int(m.group(3) or 0)
        mi = int(m.group(4) or 0) or (30 if m.group(5) else 0)
        p = m.group(2)
        if p and p in ('下午','晚上','傍晚') and h < 12:
            h += 12
        return apply(base, h, mi)

    # 3. "下周一 下午3点"
    m = re.search(r"(下下?)\s*周\s*([一二三四五六日天])\s*(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上)?\s*(\d{1,2})?\s*[点:：]\s*(\d{1,2})?\s*分?\s*(半)?", text)
    if m:
        weeks = 2 if m.group(1) and "下下" in m.group(1) else 1
        days = (7 * weeks) + (_WEEKDAY[m.group(2)] - now.weekday()) % 7
        base = now + timedelta(days=days)
        h = int(m.group(4) or 0)
        mi = int(m.group(5) or 0) or (30 if m.group(6) else 0)
        if m.group(3) and m.group(3) in ('下午','晚上','傍晚') and h < 12:
            h += 12
        return apply(base, h, mi)

    # 4. "周一 下午3点" (this week)
    m = re.search(r"周\s*([一二三四五六日天])\s*(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上)?\s*(\d{1,2})?\s*[点:：]\s*(\d{1,2})?\s*分?\s*(半)?", text)
    if m:
        days = (_WEEKDAY[m.group(1)] - now.weekday()) % 7
        base = now + timedelta(days=days)
        h = int(m.group(3) or 0)
        mi = int(m.group(4) or 0) or (30 if m.group(5) else 0)
        if m.group(2) and m.group(2) in ("下午","晚上","傍晚") and h < 12:
            h += 12
        r = apply(base, h, mi)
        return r if r > now else r + timedelta(days=7)

    # 5. "N天后"
    m = re.search(r"(\d{1,3})\s*天\s*[后内以]", text)
    if m:
        return (now + timedelta(days=int(m.group(1)))).replace(hour=23,minute=59,second=0)

    # 6. "N小时后"
    m = re.search(r"(\d{1,3})\s*[小个]?\s*时\s*[后内以]", text)
    if m:
        return now + timedelta(hours=int(m.group(1)))

    # 7. "下午3点" (period + time only)
    m = re.search(r"(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上)\s*(\d{1,2})\s*[点:：]\s*(\d{1,2})?\s*分?\s*(半)?", text)
    if m:
        h = int(m.group(2))
        mi = int(m.group(3) or 0) or (30 if m.group(4) else 0)
        if m.group(1) in ("下午","晚上","傍晚") and h < 12:

            h += 12
        r = apply(now, h, mi)
        return r if r > now else r + timedelta(days=1)

    # 8. "HH:MM"
    m = re.search(r"(\d{1,2}):(\d{2})", text)
    if m:
        r = apply(now, int(m.group(1)), int(m.group(2)))
        return r if r > now else r + timedelta(days=1)

    return None


_CLEANUP = [
    r"(今天|明天|后天|大后天)\s*(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上)?\s*\d{1,2}\s*[点:：]\s*\d{0,2}\s*分?\s*(半)?",
    r"下下?\s*周\s*[一二三四五六日天]\s*(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上)?\s*\d{0,2}\s*[点:：]?\s*\d{0,2}\s*分?\s*(半)?",
    r"周\s*[一二三四五六日天]\s*(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上)?\s*\d{1,2}\s*[点:：]\s*\d{0,2}\s*分?\s*(半)?",
    r"(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上)\s*\d{1,2}\s*[点:：]\s*\d{0,2}\s*分?\s*(半)?",
    r"\d{1,2}\s*月\s*\d{1,2}\s*[日号]",
    r"\d{1,3}\s*[天小个]?\s*时?\s*[后内以]",
    r"\d{1,2}:\d{2}",
    r"下下?周[一二三四五六日天]?",
    r"[在到于至].*?(前|之前|截止|deadline|ddl)",
]


def _clean_time_tokens(text: str) -> str:
    for pat in _CLEANUP:
        text = re.sub(pat, "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" ,，。；;、")







