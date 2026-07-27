import os, json, html, asyncio
from datetime import datetime
from urllib.parse import urlencode
from http.server import BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ── Конфиг ──────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
SITE_URL = os.environ.get("SITE_URL", "https://noir42.ru").rstrip("/")

_raw = os.environ.get("LEADS_CHAT_ID", "").strip()
LEADS_CHAT_ID = int(_raw) if _raw and _raw.lstrip("-").isdigit() else OWNER_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ── Состояния ───────────────────────────────────────────
class Form(StatesGroup):
    wait_name = State()
    wait_contact = State()
    wait_task = State()


# ── Клавиатуры ──────────────────────────────────────────
def main_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="🚀 Рассчитать проект")
    b.button(text="📦 Пакеты и цены")
    b.button(text="🎨 Портфолио")
    b.button(text="❓ Вопрос")
    b.button(text="📞 Контакты")
    b.adjust(1, 2, 2)
    return b.as_markup(resize_keyboard=True, input_field_placeholder="Выберите пункт меню")


def cancel_kb(placeholder: str, skip: bool = False) -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    if skip:
        b.button(text="Пропустить")
    b.button(text="❌ Отмена")
    b.adjust(1)
    return b.as_markup(resize_keyboard=True, input_field_placeholder=placeholder)


# ── Тексты ──────────────────────────────────────────────
WELCOME = (
    "👋 Привет! Я бот цифровой студии <b>NOIR</b>.\n\n"
    "Делаем сайты, Telegram-ботов, автоматизацию и AI для бизнеса в Кемерово и по всей России.\n\n"
    "Здесь можно за 30 секунд оставить заявку, посмотреть пакеты и цены или открыть наши работы. "
    "Выберите пункт ниже 👇"
)

PACKAGES = (
    "📦 <b>Пакеты под ключ</b> (первым 3 клиентам — цена ниже рынка):\n\n"
    "▫️ <b>Старт — 29 000 ₽</b>\nЛендинг + онлайн-оплата + метрика + заявки в Telegram.\n\n"
    "▫️ <b>Бизнес — 59 000 ₽</b>\nВсё из «Старта» + Telegram-бот + CRM.\n\n"
    "▫️ <b>Премиум — 112 000 ₽</b>\nВсё из «Бизнеса» + AI-ассистент + полная автоматизация.\n\n"
    "По отдельности услуги дороже. Нажмите пакет — начнём заявку 👇"
)

PORTFOLIO = "🎨 <b>Наши работы</b> — каждый проект рабочий, можно открыть и потрогать:"

FAQ = (
    "❓ <b>Частые вопросы</b>\n\n"
    "• <b>Сколько стоит?</b> Пакеты 29 / 59 / 112 тыс. ₽, отдельные услуги — от 10 000 ₽.\n"
    "• <b>Сроки?</b> Старт — 2–3 недели, Бизнес — 3–4, Премиум — от месяца.\n"
    "• <b>Официально?</b> Да, договор + чек (самозанятый, НПД).\n"
    "• <b>Оплата?</b> 50/50, не всё сразу.\n\n"
    "Свой вопрос — кнопкой «Задать вопрос» ниже 👇"
)

CONTACTS = (
    "📞 <b>Связь с NOIR</b>\n\n"
    "Telegram: @noir_lab42\n"
    "Телефон / WhatsApp: +7 951 592-26-18\n"
    "Почта: hello@noirlab.ru\n"
    "Кемерово · Пн–Пт 9:00–19:00"
)


# ── Утилиты ─────────────────────────────────────────────
def contract_url(name, contact, task, price=""):
    params = {"name": name, "phone": contact, "task": task}
    if price:
        params["price"] = price
    return f"{SITE_URL}/dogovor.html?{urlencode(params)}"


async def send_lead(text, markup=None):
    try:
        await bot.send_message(LEADS_CHAT_ID, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        if LEADS_CHAT_ID != OWNER_ID:
            await bot.send_message(
                OWNER_ID,
                f"⚠️ Не удалось отправить в группу ({e}). Заявка ниже:\n\n{text}",
                parse_mode="HTML",
                reply_markup=markup,
            )


# ── Хендлеры ────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state):
    await state.clear()
    await message.answer(WELCOME, parse_mode="HTML", reply_markup=main_kb())


@router.message(Command("whoami"))
async def cmd_whoami(message: Message):
    await message.answer(
        f"🆔 <b>id чата:</b> <code>{message.chat.id}</code>\n"
        f"👤 <b>ваш id:</b> <code>{message.from_user.id}</code>\n"
        f"📌 тип: {message.chat.type}",
        parse_mode="HTML",
    )


@router.message(F.text == "❌ Отмена")
async def cancel(message: Message, state):
    await state.clear()
    await message.answer("Отменили. Возвращаю меню 👇", reply_markup=main_kb())


@router.message(F.text == "🚀 Рассчитать проект")
async def menu_calc(message: Message, state):
    await state.set_state(Form.wait_name)
    await state.update_data(package="", price="")
    await message.answer("Отлично, начнём. Как к вам обращаться?", reply_markup=cancel_kb("Ваше имя"))


@router.message(F.text == "📦 Пакеты и цены")
async def menu_packages(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="Хочу «Старт»", callback_data="pkg:Старт|29 000 ₽")
    kb.button(text="Хочу «Бизнес»", callback_data="pkg:Бизнес|59 000 ₽")
    kb.button(text="Хочу «Премиум»", callback_data="pkg:Премиум|112 000 ₽")
    kb.adjust(1)
    await message.answer(PACKAGES, parse_mode="HTML", reply_markup=kb.as_markup())


@router.message(F.text == "🎨 Портфолио")
async def menu_portfolio(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 Главный сайт NOIR", url=f"{SITE_URL}/index.html")
    kb.button(text="📂 Все кейсы", url=f"{SITE_URL}/cases.html")
    kb.button(text="🦷 Демо: стоматология ТопДент", url=f"{SITE_URL}/topdent.html")
    kb.adjust(1)
    await message.answer(PORTFOLIO, parse_mode="HTML", reply_markup=kb.as_markup())


@router.message(F.text == "❓ Вопрос")
async def menu_faq(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="Задать свой вопрос", callback_data="ask")
    await message.answer(FAQ, parse_mode="HTML", reply_markup=kb.as_markup())


@router.message(F.text == "📞 Контакты")
async def menu_contacts(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="✈️ Написать в Telegram", url="https://t.me/noir_lab42")
    kb.button(text="📞 Позвонить", url="tel:+79515922618")
    kb.adjust(1)
    await message.answer(CONTACTS, parse_mode="HTML", reply_markup=kb.as_markup())


@router.callback_query(F.callback_data.startswith("pkg:"))
async def cb_package(callback: CallbackQuery, state):
    pkg, price = callback.data[4:].split("|", 1)
    await state.set_state(Form.wait_name)
    await state.update_data(package=pkg, price=price)
    await callback.answer()
    await callback.message.answer(
        f"Выбран пакет «{pkg}». Оформим заявку.\nКак к вам обращаться?",
        reply_markup=cancel_kb("Ваше имя"),
    )


@router.callback_query(F.callback_data == "ask")
async def cb_ask(callback: CallbackQuery, state):
    await state.set_state(Form.wait_name)
    await state.update_data(package="Вопрос с сайта/бота", price="")
    await callback.answer()
    await callback.message.answer("Принято. Как к вам обращаться?", reply_markup=cancel_kb("Ваше имя"))


@router.message(StateFilter(Form.wait_name))
async def fsm_name(message: Message, state):
    await state.update_data(name=message.text.strip())
    await state.set_state(Form.wait_contact)
    await message.answer("Телефон или Telegram для связи?", reply_markup=cancel_kb("+7 ... или @ник"))


@router.message(StateFilter(Form.wait_contact))
async def fsm_contact(message: Message, state):
    await state.update_data(contact=message.text.strip())
    await state.set_state(Form.wait_task)
    await message.answer(
        "Коротко опишите задачу (или нажмите «Пропустить»):",
        reply_markup=cancel_kb("Например: лендинг для салона с записью", skip=True),
    )


@router.message(StateFilter(Form.wait_task))
async def fsm_task(message: Message, state):
    task = "" if message.text.strip() == "Пропустить" else message.text.strip()
    data = await state.get_data()
    name = html.escape(data.get("name", ""))
    contact = html.escape(data.get("contact", ""))
    task_safe = html.escape(task) if task else "—"
    pkg = data.get("package", "") or "—"
    price = data.get("price", "")
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    url = contract_url(data.get("name", ""), data.get("contact", ""), task or "Заявка с бота", price)

    lead = (
        f"🔔 <b>Новая заявка</b>\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Контакт: {contact}\n"
        f"📝 Задача: {task_safe}\n"
        f"📦 Пакет: {html.escape(pkg)}\n"
        f"🕒 {now}"
    )
    lead_kb = InlineKeyboardBuilder()
    lead_kb.button(text="📄 Договор клиента", url=url)
    if data.get("contact", "").startswith("@"):
        lead_kb.button(text="✈️ Написать в TG", url=f"https://t.me/{data['contact'].lstrip('@')}")
    await send_lead(lead, lead_kb.as_markup())

    await state.clear()
    await message.answer(
        f"Спасибо, {name}! ✅ Заявка у нас.\n\n"
        f"Ответим в течение 15 минут в рабочее время.\n"
        f"Пока ждёте — вот ваш договор, данные уже подставлены:\n{url}\n\n"
        f"Меню ниже 👇",
        reply_markup=main_kb(),
    )


# ── Обработка формы с сайта ─────────────────────────────
async def handle_form(payload):
    name = html.escape(payload.get("name", "—"))
    phone = html.escape(payload.get("phone", "—"))
    message = html.escape(payload.get("message", "—"))
    source = payload.get("source", "")
    url = contract_url(payload.get("name", ""), payload.get("phone", ""), payload.get("message", ""))

    lead = (
        f"🌐 <b>Заявка с сайта</b>\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Сообщение: {message}"
    )
    if source:
        lead += f"\n\n📂 Источник: {source}"

    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Договор", url=url)
    await send_lead(lead, kb.as_markup())
    return {"ok": True, "contract_url": url}


# ── Vercel entry point ──────────────────────────────────
# ponytail: no explicit init needed — aiogram handles it on first feed_update


class handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def do_GET(self):
        self._send(200, json.dumps({"status": "ok", "bot": "NOIR"}))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)

            # Форма с сайта
            if body.get("_form"):
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(handle_form(body["_form"]))
                loop.close()
                self._send(200, json.dumps(result))
                return

            # Telegram update
            loop = asyncio.new_event_loop()
            loop.run_until_complete(dp.feed_update(bot, body))
            loop.close()
            self._send(200, "ok")
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))
