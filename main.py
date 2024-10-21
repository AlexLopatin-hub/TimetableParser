import requests
import asyncio
import logging

from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command


logging.basicConfig(level=logging.INFO)

BOT_TOKEN = '7527348944:AAHPqtbr7qAFPGoSVf5w9vdYEPDYb5ZYX-8'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_timetable(link):
    res = ''
    response = requests.get(link).text
    soup = BeautifulSoup(response, 'lxml')
    for day in soup.select('.schedule__day'):
        date = day.select('.schedule__date')[0].text
        res += date + '\n\n'
        for lesson in day.select('.lesson'):
            start_time = lesson.select('.lesson__time')[0].find_all('span')[0].text
            end_time = lesson.select('.lesson__time')[0].find_all('span')[2].text
            lesson_subject = lesson.find_all('span')[5].text
            lesson_type = lesson.select('.lesson__type')[0].text
            teacher = lesson.select('.lesson__teachers')
            if teacher:
                teacher = teacher[0].find_all('span')[2].text
            else:
                teacher = ''
            place = lesson.select('.lesson__places')[0].find_all('span')
            place = f'{place[0].text.strip()} {place[6].text.strip()} {place[7].text}'
            res += (f'{start_time} - {end_time} {lesson_subject} ({lesson_type.lower()})\n\n'
                    f'{place}\n\n'
                    f'{teacher}\n\n')


        res += '\n\n'
    return res


@dp.message(Command('start'))
async def start_command(message: types.Message):
    await message.answer('Введи команду /timetable, чтобы получить расписание на неделю')


@dp.message(Command('timetable'))
async def print_timetable(message: types.Message):
    link = 'https://ruz.spbstu.ru/faculty/125/groups/40399'
    await message.answer(get_timetable(link))


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())