import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


MENU_URL = "https://www.kopo.ac.kr/gm/content.do?menu=12623"

WEEKDAY_NAMES = {
    0: "월요일",
    1: "화요일",
    2: "수요일",
    3: "목요일",
    4: "금요일",
    5: "토요일",
    6: "일요일",
}


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def scrape_today_menu() -> tuple[str, str, str]:
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    today = now.strftime("%Y-%m-%d")
    weekday_name = WEEKDAY_NAMES[now.weekday()]

    response = requests.get(
        MENU_URL,
        headers={"User-Agent": "Mozilla/5.0 lunch-menu-bot"},
        timeout=15,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    page_text = clean_text(soup.get_text("\n", strip=True))

    lines = [line.strip() for line in page_text.splitlines() if line.strip()]

    menu_by_day = {}

    for line in lines:
        for day in WEEKDAY_NAMES.values():
            if line.startswith(day):
                menu = line.replace(day, "", 1).strip()
                menu = menu.strip(" ,")
                menu_by_day[day] = menu
                break

    today_menu = menu_by_day.get(weekday_name, "").strip()

    if not today_menu:
        today_menu = "등록된 식단이 없거나 식단 정보가 비어 있습니다."

    return today, weekday_name, today_menu


def send_to_teams(today: str, weekday_name: str, menu: str) -> None:
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")

    if not webhook_url:
        raise ValueError("TEAMS_WEBHOOK_URL Secret이 없습니다.")

    menu_lines = [item.strip() for item in menu.split(",") if item.strip()]

    if menu_lines:
        menu_markdown = "<br>".join(f"- {item}" for item in menu_lines)
    else:
        menu_markdown = menu

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": "오늘의 점심 메뉴",
        "themeColor": "FFB6C1",
        "title": f"🍱 오늘의 점심 메뉴 | {today} {weekday_name}",
        "text": menu_markdown,
    }

    response = requests.post(webhook_url, json=payload, timeout=15)
    response.raise_for_status()


def main() -> None:
    try:
        today, weekday_name, menu = scrape_today_menu()
        print(f"{today} {weekday_name} 메뉴: {menu}")

        send_to_teams(today, weekday_name, menu)
        print("Teams webhook 전송 완료")

    except Exception as error:
        print(f"오류 발생: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()