import requests
from bs4 import BeautifulSoup


def get_timetable(link):
    response = requests.get(link).text
    soup = BeautifulSoup(response, 'lxml')
    for day in soup.select('.schedule__day'):
        date = day.select('.schedule__date')[0].text
        print(date)
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
            print(f'{start_time} - {end_time} {lesson_subject} ({lesson_type.lower()})')
            print(f'              {place}')
            print(f'              {teacher}')


        print('\n')


if __name__ == '__main__':
    link = 'https://ruz.spbstu.ru/faculty/125/groups/40399'
    get_timetable(link)
