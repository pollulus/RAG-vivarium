"""Настройки проекта: пути к папкам и значения из файла .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Корень проекта: папка на уровень выше src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Для результатов парсинга
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Исходные файлы книг и извлеченный из них текст
BOOKS_SOURCE_DIR = DATA_DIR / "books" / "source"
BOOKS_RAW_DIR = DATA_DIR / "books" / "raw"

# Сообщения с форумов: по одному файлу JSONL на раздел
FORUMS_RAW_DIR = DATA_DIR / "forums" / "raw"
# Статьи с сайтов: по одному файлу JSONL на сайт
SITES_RAW_DIR = DATA_DIR / "sites" / "raw"

# Переменные из .env
load_dotenv(PROJECT_ROOT / ".env")

GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Загрузка страниц
USER_AGENT = "Mozilla/5.0 (compatible; StudyRAGBot/0.1; educational project)"
# Пауза между запросами (если в robots.txt Crawl-delay больше, берется он)
REQUEST_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 15
REQUEST_RETRIES = 3
# Столько неудач подряд считаем признаком того, что сайт не работает
MAX_CONSECUTIVE_FAILURES = 5

# Форум fanfishka.ru
FANFISHKA_URL = "https://fanfishka.ru/forum/"
# Разделы и сколько обычных тем брать из каждого (всего около 700 тысяч слов).
# Подразделы парсер находит сам и берет из них столько же тем.
ALL_TOPICS = 10_000  # больше, чем тем в любом маленьком разделе
FANFISHKA_SECTIONS = {
    # Аквариум для начинающих
    "https://fanfishka.ru/forum/forum/35-zapusk-perezapusk-i-obustroystvo-akvariuma/": 80,
    "https://fanfishka.ru/forum/forum/36-uhod-i-oformlenie-akvariuma-poleznye-sovety/": 80,
    "https://fanfishka.ru/forum/forum/37-problemy-voznikshie-pri-zapuske-i-obustroystve-akvariuma/": 80,
    # Аквариумные рыбки: общие вопросы
    "https://fanfishka.ru/forum/forum/50-obschie-voprosy-o-soderzhanii-rybok/": 80,
    "https://fanfishka.ru/forum/forum/134-sovmestimost-akvariumnyh-ryb-otzyvy-i-sovety/": 40,
    # Семейства рыб: популярным больше, маленьким меньше
    "https://fanfishka.ru/forum/forum/43-cihlidy-afriki/": 35,
    "https://fanfishka.ru/forum/forum/44-cihlidy-ameriki/": 35,
    "https://fanfishka.ru/forum/forum/46-zhivorodyaschie-rybki/": 35,
    "https://fanfishka.ru/forum/forum/47-semeystvo-zolotyh-rybok/": 35,
    "https://fanfishka.ru/forum/forum/42-nomernye-l-somy/": 25,
    "https://fanfishka.ru/forum/forum/45-labirintovye-rybki/": 25,
    "https://fanfishka.ru/forum/forum/48-haracinovye-tetry/": 25,
    "https://fanfishka.ru/forum/forum/49-somopodobnye-ryby/": 25,
    "https://fanfishka.ru/forum/forum/95-karpozubye-ryby/": 15,
    "https://fanfishka.ru/forum/forum/167-vyunovye-ryby/": 15,
    "https://fanfishka.ru/forum/forum/51-ostalnye-rybki/": 15,
    # Заболевания рыб: темы короткие, поэтому их больше
    "https://fanfishka.ru/forum/forum/91-bazovye-i-chastye-voprosy-po-lecheniyu-akvariumnyh-rybok/": 150,
    "https://fanfishka.ru/forum/forum/90-obschie-voprosy-po-zabolevaniyam-i-lecheniyu-vseh-rybok/": 150,
    "https://fanfishka.ru/forum/forum/86-zabolevaniya-cihlid-i-ih-lechenie/": 40,
    "https://fanfishka.ru/forum/forum/85-zabolevaniya-zolotyh-rybok-i-ih-lechenie/": 40,
    "https://fanfishka.ru/forum/forum/87-zabolevaniya-somopodobnyh-ryb-i-ih-lechenie/": 40,
    "https://fanfishka.ru/forum/forum/89-zabolevaniya-zhivorodyaschih-rybok-i-ih-lechenie/": 40,
    "https://fanfishka.ru/forum/forum/84-zabolevaniya-rybok-petushkov-i-ih-lechenie/": 40,
    "https://fanfishka.ru/forum/forum/88-zabolevaniya-haracinovyh-karpovyh-ryb-i-ih-lechenie/": 40,
    # Другие обитатели, размножение, растения
    "https://fanfishka.ru/forum/forum/14-krevetki-v-akvariume-soderzhanie-uhod-sovmestimost/": 40,
    "https://fanfishka.ru/forum/forum/7-mollyuski-cherepashki-krabiki-rachki/": 40,
    "https://fanfishka.ru/forum/forum/11-razmnozhenie-i-razvedenie-rybok/": 40,
    "https://fanfishka.ru/forum/forum/6-akvariumnye-rasteniya-uhod-razvedenie-akvaskeyp/": 40,
    # Оборудование
    "https://fanfishka.ru/forum/forum/19-akvariumy-otzyvy-instrukcii-rekomendacii/": 20,
    "https://fanfishka.ru/forum/forum/16-akvariumnye-filtry-pompy-otzyvy-instrukcii-rekomendacii/": 20,
    "https://fanfishka.ru/forum/forum/17-akvariumnye-kompressory-i-oksidatory-otzyvy-instrukcii-rekomendacii/": 20,
    "https://fanfishka.ru/forum/forum/18-akvariumnye-nagrevateli-i-sistemy-ohlazhdeniya-otzyvy-instrukcii-rekomendacii/": 20,
    "https://fanfishka.ru/forum/forum/20-akvariumnoe-osveschenie-otzyvy-instrukcii-rekomendacii/": 20,
    "https://fanfishka.ru/forum/forum/21-akvariumnye-grunty-i-podlozhki-otzyvy-instrukcii-rekomendacii/": 20,
    "https://fanfishka.ru/forum/forum/25-akvariumnye-preparaty-udobreniya-i-testy-otzyvy-instrukcii/": 20,
    # Производители: разделы маленькие, берем все, кроме новостей и акций
    "https://fanfishka.ru/forum/forum/78-kompaniya-tetra/": ALL_TOPICS,
    "https://fanfishka.ru/forum/forum/77-kompaniya-aquael/": ALL_TOPICS,
    "https://fanfishka.ru/forum/forum/170-kompaniya-sera/": ALL_TOPICS,
}
# Темы и подразделы с такими словами в названии пропускаем: новости и акции
SKIP_TITLE_WORDS = ("новинк", "акци", "скидк", "распродаж", "конкурс", "розыгрыш", "новост")
# Сколько страниц одной темы читать (на странице около 35 сообщений)
MAX_PAGES_PER_TOPIC = 3
# У производителей почти все темы о товарах закреплены, берем их все
TAKE_ALL_PINNED_SECTIONS = {
    "https://fanfishka.ru/forum/forum/78-kompaniya-tetra/",
    "https://fanfishka.ru/forum/forum/77-kompaniya-aquael/",
    "https://fanfishka.ru/forum/forum/170-kompaniya-sera/",
}
# Из остальных закрепленных тем берем только справочные (каталоги видов,
# руководства), отобраны вручную. Правила и огромные ветки пропускаем.
PINNED_TOPICS_TO_KEEP = {
    # Запуск, перезапуск и обустройство аквариума
    "https://fanfishka.ru/forum/topic/2191-primer-zapuska-akvariuma-na-100-litrov-s-liricheskimi-otstupleniyami-i-poznavatelnymi-spoylerami/",
    "https://fanfishka.ru/forum/topic/1120-karantinnyy-akvarium-osobennosti-soderzhaniya/",
    "https://fanfishka.ru/forum/topic/116-obustroystvo-akvariuma-rasteniyami-chto-dlya-etogo-nuzhno/",
    # Уход и оформление аквариума, полезные советы
    "https://fanfishka.ru/forum/topic/1662-kak-pomenyat-grunt-v-deystvuyuschem-akvariume/",
    "https://fanfishka.ru/forum/topic/431-osmos-dlya-akvariuma-sovety-rekomendacii/",
    "https://fanfishka.ru/forum/topic/274-koryagi-dlya-akvariuma-kak-podgotovit-vymochit-vyvarit-vysushit-prodezinficirovat/",
    "https://fanfishka.ru/forum/topic/519-perevozka-akvariumov/",
    "https://fanfishka.ru/forum/topic/293-listya-duba-mindalya-shishki-olhi-v-akvariume/",
    "https://fanfishka.ru/forum/topic/9-uborka-akvariuma-kak-sifonit-kogda-i-skolko/",
    "https://fanfishka.ru/forum/topic/436-biofiltraciya-akvariuma/",
    "https://fanfishka.ru/forum/topic/195-preparaty-kotrye-delayut-akvaruimnuyu-vodu-kristalno-chistoy/",
    "https://fanfishka.ru/forum/topic/314-recepty-samodelnyh-kormov-dlya-akvariumnyh-ryb-farshi-miksy/",
    "https://fanfishka.ru/forum/topic/593-nezhelatelnye-vodorosli-v-akvariume/",
    "https://fanfishka.ru/forum/topic/292-akvariumnye-preparaty-himiya-dlya-nachinayuschih/",
    # Проблемы возникшие при запуске и обустройстве аквариума
    "https://fanfishka.ru/forum/topic/9299-povyshennye-no3-nitrat-i-no2-nitrit-posle-zaseleniya-ryb-v-akvarium-chto-delat/",
    "https://fanfishka.ru/forum/topic/877-cvetet-voda-v-akvariume-kak-borotsya/",
    "https://fanfishka.ru/forum/topic/523-bolshaya-koncentraciya-ammiaka-v-akvariume/",
    "https://fanfishka.ru/forum/topic/1921-kak-pravilno-pochistit-akvarium/",
    # Общие вопросы о содержании рыбок
    "https://fanfishka.ru/forum/topic/1235-zamachivanie-suhih-kormov-dlya-akvariumnyh-rybok/",
    "https://fanfishka.ru/forum/topic/1270-kak-pravilno-vybirat-akvariumnyh-rybok/",
    # Цихлиды Африки
    "https://fanfishka.ru/forum/topic/768-sovmestimost-cihlid/",
    "https://fanfishka.ru/forum/topic/9083-cihlidy-ozera-malavi-mbuna-i-utaka-opisanie-vidov-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/9087-cihlidy-centralnoy-i-zapadnoy-afriki-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/9089-karlikovye-cihlidy-vseh-biotopov-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/9086-vse-afrikanskie-cihlidy-opisanie-vidov-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/9085-aziatskie-cihlidy-vidy-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/9084-cihlidy-ozera-tanganika-opisanie-vidov-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/9060-cihlidy-vidy-opisanie-nazvaniya-i-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/7966-cihlidy-ozera-viktoriya/",
    # Цихлиды Америки
    "https://fanfishka.ru/forum/topic/249-diskusy-zametki-sovety-nablyudeniya/",
    "https://fanfishka.ru/forum/topic/9088-amerikanskie-cihlidy-opisanie-vidov-foto-video-obzor/",
    # Живородящие рыбки
    "https://fanfishka.ru/forum/topic/1406-zhivorodyaschie-akvariumnye-rybki-spisok-opisanie-foto-vidy/",
    # Номерные L сомы
    "https://fanfishka.ru/forum/topic/309-nomernye-l-somy-opisanie-katalog-s-foto/",
    # Лабиринтовые рыбки
    "https://fanfishka.ru/forum/topic/9059-labirintovye-rybki-spisok-vidov-perechen-nazvaniy-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/11190-opyt-razdelnogo-soderzhaniya-samca-i-samochki-betta-splendense/",
    "https://fanfishka.ru/forum/topic/7221-klassifikaciya-betta-bett/",
    "https://fanfishka.ru/forum/topic/48-rybki-kotorym-ne-nuzhen-vozduh-spisok-rekomendacii/",
    # Харациновые - тетры
    "https://fanfishka.ru/forum/topic/9058-tetry-i-prochie-haracinovye-rybki-vidy-katalog-semeystva-nazvaniya-foto-video-obzor/",
    # Сомоподобные рыбы
    "https://fanfishka.ru/forum/topic/9064-akvariumnye-somy-vse-vidy-s-foto-i-nazvaniyami-somov-video-opisanie/",
    "https://fanfishka.ru/forum/topic/9063-krapchatye-somiki-vidy-s-nazvaniyami-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/9062-pancirnye-kallihtovye-somy-vidy-katalog-foto-video-obzor/",
    "https://fanfishka.ru/forum/topic/9061-kolchuzhnye-%E2%80%93-lorikarievye-somy-vidy-katalog-foto-video-obzor/",
    # Карпозубые рыбы
    "https://fanfishka.ru/forum/topic/9072-karpozubye-rybki-vidy-nazvaniya-foto-video-obzor/",
    # Вьюновые рыбы
    "https://fanfishka.ru/forum/topic/9091-vyunovye-ryby-vidy-foto-obzor/",
    # Базовые и частые вопросы по лечению аквариумных рыбок
    "https://fanfishka.ru/forum/topic/98-belye-tochki-u-rybok-mankaihtioftirioz-simptomatika-i-lechenie/",
    "https://fanfishka.ru/forum/topic/275-geksamitoz-u-cihlid/",
    "https://fanfishka.ru/forum/topic/1313-tuberkulez-ryb-simptomatika-lechenie-profilaktika/",
    "https://fanfishka.ru/forum/topic/1414-recept-lecheniya-tuberkuleza-i-geksamitoza-rybok/",
    "https://fanfishka.ru/forum/topic/382-lechenie-rybok-antibiotikami/",
    # Заболевания рыбок петушков и их лечение
    "https://fanfishka.ru/forum/topic/7971-lechim-petushka-ot-vodyanki-s-gribkom-zhivitelnyy-recept-ot-stasa/",
    "https://fanfishka.ru/forum/topic/16857-u-petushka-obodrana-cheshuyapushok-prim-moderatora-lechenie-furacilinom/",
    "https://fanfishka.ru/forum/topic/10294-plavnikovaya-gnil-u-petushkov-i-drugih-rybok-kak-byt-chto-delat-i-kto-vinovat/",
    "https://fanfishka.ru/forum/topic/7588-operaciya-prokol-bryushiny-u-rybki-petushka/",
    # Креветки в аквариуме: содержание, уход, совместимость
    "https://fanfishka.ru/forum/topic/482-neprihotlivye-akvaruimnye-krevetki-dlya-novichkov/",
    # Моллюски, черепашки, крабики, рачки
    "https://fanfishka.ru/forum/topic/225-kak-izbavitsya-ot-ulitok-v-akvariume-100-i-navsegda/",
    "https://fanfishka.ru/forum/topic/987-teodoksus-vse-o-soderzhanie-ulitok-v-akvariume/",
    "https://fanfishka.ru/forum/topic/318-umirayut-ampulyarii-kak-byt/",
    "https://fanfishka.ru/forum/topic/305-razmnozhenie-ampulyariy-ot-a-do-yau/",
    # Размножение и разведение рыбок
    "https://fanfishka.ru/forum/topic/289-ancistrus-razvedenie-nuzhno-li-otsazhivat-i-kormit-samca/",
    "https://fanfishka.ru/forum/topic/1379-kak-spasti-malkov-pecilii-guppi-mechenosca-ot-poedaniya-proizvoditelyami/",
    # Аквариумные растения: уход, разведение, акваскейп
    "https://fanfishka.ru/forum/topic/1930-recepty-samomesov-udobreniy-dlya-akvariumnyh-rasteniy-svoimi-rukami/",
    "https://fanfishka.ru/forum/topic/2022-kaliy-v-akvariume-s-rasteniyami-obsuzhdenie/",
    "https://fanfishka.ru/forum/topic/366-akvariumnye-vodorosli-i-rasteniya-kak-dostignut-balansa/",
    "https://fanfishka.ru/forum/topic/159-podbor-akvariumnyh-rasteniy-dlya-novichkov/",
    "https://fanfishka.ru/forum/topic/2005-parametry-vody-dlya-soderzhaniya-akvariuma-s-rasteniyami/",
    "https://fanfishka.ru/forum/topic/9635-azotnyy-cikl-biobalans-v-akvariume-s-rasteniyami-travnike/",
    "https://fanfishka.ru/forum/topic/1964-pochvopokrovnye-nizkoroslye-akvariumnye-rasteniya-dlya-perednego-plana-posadki/",
    "https://fanfishka.ru/forum/topic/1991-akvariumnye-rasteniya-dlya-zadnego-plana-vysokie/",
    # Аквариумные фильтры, помпы: отзывы, инструкции, рекомендации
    "https://fanfishka.ru/forum/topic/1352-vneshniy-ili-vnutrenniy-akvariumnyy-filtr-chto-luchshe/",
    "https://fanfishka.ru/forum/topic/2027-aerliftnyy-filtr-chto-delat-kogda-byudzhet-na-hobbi-nebolshoy/",
    # Аквариумные нагреватели и системы охлаждения: отзывы, инструкции, рекомендации
    "https://fanfishka.ru/forum/topic/1970-ohlazhdenie-akvariuma-s-pomoschyu-elementa-pelte/",
    "https://fanfishka.ru/forum/topic/3223-ohlazhdenie-vody-v-akvariume-kak-ponizit-temperaturu/",
    # Аквариумные препараты, удобрения и тесты: отзывы, инструкции
    "https://fanfishka.ru/forum/topic/9261-testiruem-testy-uhe/",
    "https://fanfishka.ru/forum/topic/3076-testy-sera-opisanie-i-instrukcii-v-odnoy-tablice/",
    "https://fanfishka.ru/forum/topic/9020-testiruem-testy-vladox-otzyvy-i-rekomendacii/",
    "https://fanfishka.ru/forum/topic/1179-instrukcii-dlya-vseh-testov-%C2%ABnilpa%C2%BB-v-tablice/",
    "https://fanfishka.ru/forum/topic/2804-testiruem-testy-tetra/",
}
# Из закрепленной темы читаем только первую страницу: там сама статья
MAX_PAGES_PER_PINNED_TOPIC = 1

# Сайт cherepahi.ru: разделы со статьями (форум /tforum запрещен в robots.txt)
CHEREPAHI_URL = "https://cherepahi.ru/"
CHEREPAHI_SECTIONS = {
    "soderzhanie": "Содержание",
    "articles": "Статьи",
    "vidy-cherepax": "Виды черепах",
}
# Более короткие страницы не сохраняем
MIN_ARTICLE_CHARS = 300
