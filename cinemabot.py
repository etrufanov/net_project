import aiohttp
import asyncio
from datetime import datetime
import string
import typing as tp
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from bs4 import BeautifulSoup
import os


bot = Bot(token=os.environ['BOT_TOKEN'])
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply(("Привет! Я асинхронная поисковая система в необъятном океане объектов-совокупностей "
                         "движущихся изображений, связанных единым сюжетом. Сложно? Просто введи название фильма"))

@dp.message_handler(commands=['help'])
async def send_welcome(message: types.Message):
    await message.reply("Какой фильм хочешь найти?")

async def get_film(session, url: str, title: str, query: str) -> tp.Dict[str, str]:
    async with session.get(url) as resp:
        film_html = await resp.text()
        film_soup = BeautifulSoup(film_html, 'lxml')
        try:
            p_descs = film_soup.find('div', class_='synopsis').find_all('p')
            desc = ''
            for p_desc in p_descs:
                desc += p_desc.text + '\n'
            if not desc:
                desc = 'Обойдемся без спойлеров\n'
        except AttributeError:
            desc = 'Обойдемся без спойлеров\n'
        try:
            img = ('https://www.film.ru' +
                    film_soup.find('div', class_='movies-left').find('img')['src'])
        except AttributeError:
            img = 'https://www.film.ru/images/empty/posters/400x450.png'
        try:
            rus_title = film_soup.find('div', class_='movies-center') \
                                    .find('h1').text
        except AttributeError:
            rus_title = 'Без названия'
        try:
            genre = film_soup.find('div', class_='movies-center') \
                                    .find('h3').text
        except AttributeError:
            genre = ''
        try:
            play_a = film_soup.find('a', class_='play_online', href=True)
            if play_a:
                play_ref = play_a.get('href', '')
            else:
                play_ref = ''
        except AttributeError:
            play_ref = ''
        return {'rus_title': rus_title, 'desc': desc,
                'img': img, 'genre': genre, 'play_ref': play_ref}


async def get_answer(message: types.Message, film: tp.Dict[str, str]):
    await message.answer("*{}*".format(film['rus_title']),
                                       parse_mode="Markdown")
    await message.answer_photo(film['img'])
    if film['play_ref'][:4] == 'http':
        await message.answer("{}\n\n_{}_\nСмотрите в okko: [{}]({})"
                             .format(film['genre'], film['desc'], film['rus_title'], film['play_ref']),
                                     parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await message.answer("{}\n\n_{}_\nСмотрите в okko: (ищите на просторах торрентов)"
                             .format(film['genre'], film['desc'], film['rus_title'], film['play_ref']),
                                     parse_mode="Markdown", disable_web_page_preview=True)


@dp.message_handler()
async def echo(message: types.Message):
    waiting = await message.answer_sticker('CAACAgIAAxkBAAECT4lgoZ2v3BKvGlhZZYVuaEeOH3vdFgACIwADKA9qFCdRJeeMIKQGHwQ')
    async with aiohttp.ClientSession() as session:
        search_url = "https://www.film.ru/search/result?text={}&type=movies&s=rel".format(message.text.lower())
        async with session.get(search_url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, 'lxml')
            try:
                a_films = soup.find('div', class_='rating').find_all('a', href=True)
            except AttributeError:
                a_films = []
            for a_film in a_films:
                try:
                    if (a_film['title'].translate(str.maketrans('', '', string.punctuation)).lower() ==
                        message.text.translate(str.maketrans('', '', string.punctuation)).lower() or
                        a_film.find('span').text.translate(str.maketrans('', '', string.punctuation)).lower() ==
                        message.text.translate(str.maketrans('', '', string.punctuation)).lower()):
                        await get_answer(message, await get_film(session,
                                                        'https://www.film.ru' + a_film['href'],
                                                        a_film['title'],
                                                        message.text))
                        break
                except AttributeError:
                    continue
            else:
                if a_films:
                    await get_answer(message, await get_film(session,
                                                       'https://www.film.ru' + a_films[0]['href'],
                                                        a_films[0]['title'],
                                                        message.text))
                else:
                    await message.answer('По вашему запросу найден только коть')
                    await message.answer_sticker('CAACAgIAAxkBAAECT5BgoaKryFeFlWH0vKA7IReI-Y_HrgACJQADKA9qFF60Uhxmag7DHwQ')
        await waiting.delete()


if __name__ == '__main__':
    executor.start_polling(dp)
