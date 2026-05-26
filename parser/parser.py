from datetime import datetime

import requests
from bs4 import BeautifulSoup


class Parser:
    def __init__(self, url: str):
        self.url = url

    async def get_weekly_timetable(self) -> str:
        res = ""
        response = requests.get(self.url).text
        soup = BeautifulSoup(response, "lxml")
        for day in soup.select(".schedule__day"):
            date = day.select(".schedule__date")[0].text
            res += date + "\n\n"
            for lesson in day.select(".lesson"):
                start_time = lesson.select(".lesson__time")[0].find_all("span")[0].text
                end_time = lesson.select(".lesson__time")[0].find_all("span")[2].text
                lesson_subject = lesson.find_all("span")[5].text
                lesson_type = lesson.select(".lesson__type")[0].text
                teacher = lesson.select(".lesson__teachers")
                if teacher:
                    teacher = teacher[0].find_all("span")[2].text
                else:
                    teacher = ""
                place = lesson.select(".lesson__places")[0].find_all("span")
                place = (
                    f"{place[0].text.strip()} {place[6].text.strip()} {place[7].text}"
                )
                res += (
                    f"{start_time} - {end_time}\n"
                    f"{lesson_subject}\n"
                    f"{lesson_type}\n"
                    f"{teacher}\n"
                    f"{place}\n\n"
                )
            res += "\n"
        return res

    async def get_daily_timetable(self) -> str:
        res = ""
        response = requests.get(self.url).text
        soup = BeautifulSoup(response, "lxml")
        date = ""
        for day in soup.select(".schedule__day"):
            date = day.select(".schedule__date")[0].text
            if int(date[:2]) == datetime.now().day:
                break
        else:
            return "Ошибка: не получено расписание на текущую дату"
        res += date + "\n\n"
        for lesson in day.select(".lesson"):
            start_time = lesson.select(".lesson__time")[0].find_all("span")[0].text
            end_time = lesson.select(".lesson__time")[0].find_all("span")[2].text
            lesson_subject = lesson.find_all("span")[5].text
            lesson_type = lesson.select(".lesson__type")[0].text
            teacher = lesson.select(".lesson__teachers")
            if teacher:
                teacher = teacher[0].find_all("span")[2].text
            else:
                teacher = "Неизвестно"
            place = lesson.select(".lesson__places")[0].find_all("span")
            place = f"{place[0].text.strip()} {place[6].text.strip()} {place[7].text}"
            res += (
                f"{start_time} - {end_time}\n"
                f"{lesson_subject}\n"
                f"{lesson_type}\n"
                f"{teacher}\n"
                f"{place}\n\n"
            )
        return res
