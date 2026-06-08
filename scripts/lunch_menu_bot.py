import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


MENU_URL = "https://www.kopo.ac.kr/gm/content.do?menu=12623"

DAYS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def get_today_kst():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    return now.strftime("%Y-%m-%d"), DAYS[now.weekday()]


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def scrape_today_menu():
    today, today_day = get_today_kst()

    response = requests.get(
        MENU_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    text = clean_text(soup.get_text("\n", strip=True))

    print("==== 페이지 텍스트 일부 확인 ====")
    for line in text.splitlines():
        if any(day in line for day in DAYS):
            print(line)

    # 식단정보 영역부터 잘라서 사용
    start_index = text.find("식단정보 구분")
    if start_index != -1:
        text = text[start_index:]

    # 각 요일과 다음 요일 사이의 내용을 추출
    menu_by_day = {}

    for i, day in enumerate(DAYS):
        next_day = DAYS[i + 1] if i + 1 < len(DAYS) else "content_footer"

        pattern = rf"{day}\s*(.*?)(?={next_day}|content_footer|만족도 조사)"
        match = re.search(pattern, text, re.DOTALL)

        if match:
            menu = clean_text(match.group(1))
            menu = menu.replace("\n", " ")
            menu = menu.strip(" ,")
            menu_by_day[day] = menu

    print("==== 추출된 메뉴 ====")
    print(menu_by_day)

    today_menu = menu_by_day.get(today_day, "").strip()

    if not today_menu:
        today_menu = "오늘 등록된 식단이 없습니다."

    return today, today_day, today_menu


def send_to_teams(today: str, weekday: str, menu: str):
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")

    if not webhook_url:
        raise ValueError("TEAMS_WEBHOOK_URL Secret이 없습니다.")

    menu_items = [item.strip() for item in menu.split(",") if item.strip()]

    if menu_items:
        menu_text = "\n".join(f"- {item}" for item in menu_items)
    else:
        menu_text = menu

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": "오늘의 점심 메뉴",
        "themeColor": "FFB6C1",
        "title": f"오늘의 점심 메뉴 | {today} {weekday}",
        "text": menu_text,
    }

    response = requests.post(webhook_url, json=payload, timeout=15)
    response.raise_for_status()


def main():
    try:
        today, weekday, menu = scrape_today_menu()
        print(f"오늘 날짜: {today}")
        print(f"오늘 요일: {weekday}")
        print(f"오늘 메뉴: {menu}")

        send_to_teams(today, weekday, menu)
        print("Teams webhook 전송 완료")

    except Exception as error:
        print(f"오류 발생: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()