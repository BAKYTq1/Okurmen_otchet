import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import BOT_TOKEN, ADMIN_ID, MENTORS, REVIEWS_FILE

# ─── Логирование ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ─── FSM-состояния ──────────────────────────────────────────────────────────
class ReviewForm(StatesGroup):
    full_name  = State()   # шаг 1: ввод ФИО
    mentor     = State()   # шаг 2: выбор ментора
    review     = State()   # шаг 3: написание отзыва
    rating     = State()   # шаг 4: оценка (1–5)
    confirm    = State()   # шаг 5: подтверждение


# ─── Вспомогательные функции ────────────────────────────────────────────────
def mentors_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками-менторами."""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"mentor:{i}")]
        for i, name in enumerate(MENTORS)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def rating_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура оценки 1–5 звёзд."""
    stars = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
    buttons = [
        [InlineKeyboardButton(text=stars[i], callback_data=f"rating:{i+1}")]
        for i in range(5)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отправки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm:yes"),
            InlineKeyboardButton(text="❌ Отменить",  callback_data="confirm:no"),
        ]
    ])


def save_review(data: dict) -> None:
    """Сохраняет отзыв в JSON-файл."""
    reviews: list = []
    if os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
            try:
                reviews = json.load(f)
            except json.JSONDecodeError:
                reviews = []

    reviews.append({
        "id":        len(reviews) + 1,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "full_name": data["full_name"],
        "mentor":    data["mentor"],
        "rating":    data["rating"],
        "review":    data["review"],
    })

    with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)


# ─── Инициализация бота ─────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


# ─── Команда /start ─────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👋 Привет! Это бот для <b>анонимных отзывов</b> о менторах.\n\n"
        "Ваш отзыв будет сохранён, но <b>личность студента не раскрывается</b> другим.\n\n"
        "Нажмите /review чтобы оставить отзыв.",
        parse_mode="HTML",
    )


# ─── Команда /review — начало сбора отзыва ──────────────────────────────────
@dp.message(Command("review"))
async def cmd_review(message: Message, state: FSMContext) -> None:
    await state.set_state(ReviewForm.full_name)
    await message.answer(
        "📝 <b>Шаг 1 из 4</b>\n\n"
        "Введите ваше <b>ФИО</b> (полностью):\n\n"
        "<i>Пример: Алибеков Нурлан Серикович</i>",
        parse_mode="HTML",
    )


# ─── Шаг 1: получаем ФИО ────────────────────────────────────────────────────
@dp.message(ReviewForm.full_name)
async def process_full_name(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip() if message.text else ""

    if len(full_name.split()) < 2:
        await message.answer(
            "⚠️ Пожалуйста, введите <b>полное ФИО</b> (минимум имя и фамилия).",
            parse_mode="HTML",
        )
        return

    await state.update_data(full_name=full_name)
    await state.set_state(ReviewForm.mentor)
    await message.answer(
        "👨‍🏫 <b>Шаг 2 из 4</b>\n\n"
        "Выберите ментора, которому хотите оставить отзыв:",
        reply_markup=mentors_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 2: выбор ментора ───────────────────────────────────────────────────
@dp.callback_query(ReviewForm.mentor, F.data.startswith("mentor:"))
async def process_mentor(callback: CallbackQuery, state: FSMContext) -> None:
    idx = int(callback.data.split(":")[1])
    mentor_name = MENTORS[idx]

    await state.update_data(mentor=mentor_name)
    await state.set_state(ReviewForm.review)

    await callback.message.edit_text(
        f"✅ Выбран ментор: <b>{mentor_name}</b>\n\n"
        "💬 <b>Шаг 3 из 4</b>\n\n"
        "Напишите ваш <b>отзыв</b> (что понравилось, что улучшить, пожелания):",
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Шаг 3: текст отзыва ────────────────────────────────────────────────────
@dp.message(ReviewForm.review)
async def process_review(message: Message, state: FSMContext) -> None:
    review_text = message.text.strip() if message.text else ""

    if len(review_text) < 10:
        await message.answer(
            "⚠️ Отзыв слишком короткий. Напишите хотя бы несколько предложений."
        )
        return

    await state.update_data(review=review_text)
    await state.set_state(ReviewForm.rating)
    await message.answer(
        "⭐ <b>Шаг 4 из 4</b>\n\n"
        "Поставьте оценку ментору:",
        reply_markup=rating_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 4: оценка ──────────────────────────────────────────────────────────
@dp.callback_query(ReviewForm.rating, F.data.startswith("rating:"))
async def process_rating(callback: CallbackQuery, state: FSMContext) -> None:
    rating = int(callback.data.split(":")[1])
    stars  = "⭐" * rating

    await state.update_data(rating=rating)
    data = await state.get_data()

    await state.set_state(ReviewForm.confirm)
    await callback.message.edit_text(
        "📋 <b>Проверьте ваш отзыв перед отправкой:</b>\n\n"
        f"👤 <b>Студент:</b> {data['full_name']}\n"
        f"👨‍🏫 <b>Ментор:</b> {data['mentor']}\n"
        f"⭐ <b>Оценка:</b> {stars} ({rating}/5)\n"
        f"💬 <b>Отзыв:</b>\n{data['review']}\n\n"
        "Всё верно? Нажмите <b>Отправить</b> или <b>Отменить</b>.",
        reply_markup=confirm_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Шаг 5: подтверждение ───────────────────────────────────────────────────
@dp.callback_query(ReviewForm.confirm, F.data.startswith("confirm:"))
async def process_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":")[1]

    if action == "no":
        await state.clear()
        await callback.message.edit_text(
            "❌ Отзыв отменён. Чтобы начать заново — нажмите /review."
        )
        await callback.answer("Отменено")
        return

    # Сохраняем отзыв
    data = await state.get_data()
    save_review(data)
    await state.clear()

    stars = "⭐" * data["rating"]
    await callback.message.edit_text(
        "✅ <b>Спасибо! Ваш отзыв отправлен.</b>\n\n"
        "Он будет учтён при оценке работы менторов.\n\n"
        "Оставить ещё один отзыв — /review",
        parse_mode="HTML",
    )
    await callback.answer("Отправлено!")

    # Уведомляем администратора (если ADMIN_ID задан)
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                "🔔 <b>Новый отзыв!</b>\n\n"
                f"👨‍🏫 <b>Ментор:</b> {data['mentor']}\n"
                f"⭐ <b>Оценка:</b> {stars} ({data['rating']}/5)\n"
                f"💬 <b>Отзыв:</b>\n{data['review']}\n\n"
                "<i>ФИО студента доступно только администратору.</i>\n"
                f"👤 <b>Студент:</b> {data['full_name']}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Не удалось уведомить администратора: %s", e)


# ─── Команда /reviews (только для администратора) ────────────────────────────
@dp.message(Command("reviews"))
async def cmd_reviews(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    if not os.path.exists(REVIEWS_FILE):
        await message.answer("📭 Отзывов пока нет.")
        return

    with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
        reviews: list = json.load(f)

    if not reviews:
        await message.answer("📭 Отзывов пока нет.")
        return

    # Группируем по менторам
    summary: dict[str, list] = {}
    for r in reviews:
        summary.setdefault(r["mentor"], []).append(r)

    text = f"📊 <b>Всего отзывов: {len(reviews)}</b>\n\n"
    for mentor, rev_list in summary.items():
        avg = sum(r["rating"] for r in rev_list) / len(rev_list)
        text += f"👨‍🏫 <b>{mentor}</b>\n"
        text += f"   Отзывов: {len(rev_list)} | Средняя оценка: {avg:.1f}⭐\n\n"

    await message.answer(text, parse_mode="HTML")


# ─── Обработка непредвиденных сообщений ─────────────────────────────────────
@dp.message()
async def fallback(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Используйте /review чтобы оставить отзыв.\n"
            "Или /start для начала."
        )


# ─── Запуск ─────────────────────────────────────────────────────────────────
async def main() -> None:
    logger.info("Бот запущен...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
