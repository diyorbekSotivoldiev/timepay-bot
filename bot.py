"""
Time Pay — ishga qabul (rezume) boti
aiogram 3.x

Ishga tushirishdan oldin pastdagi 2 ta sozlamani to'ldiring:
  BOT_TOKEN — @BotFather bergan token
  GROUP_ID  — rezumelar yuboriladigan guruh ID si (-100... bilan boshlanadi)
Guruh ID sini bilish uchun: botni guruhga qo'shing va guruhda /id deb yozing.
"""

import asyncio
import html
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# ====================== SOZLAMALAR ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "BU_YERGA_BOT_TOKENINI_QOYING")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))   # masalan: -1001234567890
MIN_VOICE_SECONDS = 60                        # ovozli xabar minimal davomiyligi
TZ = ZoneInfo("Asia/Tashkent")
# ========================================================

logging.basicConfig(level=logging.INFO)
router = Router()
e = html.escape  # foydalanuvchi matnini xavfsiz qilish uchun


class Form(StatesGroup):
    age = State()
    experience = State()
    address = State()
    child_order = State()
    max_income = State()
    expense = State()
    voice = State()
    phone = State()
    confirm = State()


# ---------------------- Klaviaturalar ----------------------
no_exp_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Tajribam yo'q")]],
    resize_keyboard=True, one_time_keyboard=True,
)
phone_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
    resize_keyboard=True, one_time_keyboard=True,
)
confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm")],
    [InlineKeyboardButton(text="🔄 Qaytadan to'ldirish", callback_data="restart")],
])


# ---------------------- Guruh ID sini bilish ----------------------
@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"Chat ID: <code>{message.chat.id}</code>")


# Quyidagi barcha handlerlar faqat shaxsiy chatda ishlaydi
private = Router()
private.message.filter(F.chat.type == ChatType.PRIVATE)


@private.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Assalomu alaykum! Men <b>Time Pay</b> kompaniyasining yordamchisiman.\n\n"
        "Sizni ishga olishimiz uchun bir nechta savollarga javob berishingiz kerak.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("<b>1. Yoshingiz nechida?</b>\n(faqat raqam, masalan: 22)")
    await state.set_state(Form.age)


# 1. Yosh
@private.message(Form.age)
async def q_age(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit() or not (14 <= int(text) <= 70):
        await message.answer("Iltimos, yoshingizni raqam bilan yozing (masalan: 22).")
        return
    await state.update_data(age=text)
    await message.answer(
        "<b>2. Sotuv sohasida, call centerda yoki umuman sotuvchi bo'lib qancha vaqtdan "
        "beri ishlaysiz?</b> Aniq muddatini yozing.\n\n"
        "(Tajriba yo'q bo'lsa, pastdagi tugmani bosing)",
        reply_markup=no_exp_kb,
    )
    await state.set_state(Form.experience)


async def need_text(message: Message) -> str | None:
    if not message.text:
        await message.answer("Iltimos, javobni matn ko'rinishida yozing.")
        return None
    return message.text.strip()


# 2. Tajriba
@private.message(Form.experience)
async def q_experience(message: Message, state: FSMContext):
    text = await need_text(message)
    if text is None:
        return
    await state.update_data(experience=text)
    await message.answer(
        "<b>3. Yashash manzilingiz?</b>\nMasalan: Yunusobod tumani 12-kvartal",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(Form.address)


# 3. Manzil
@private.message(Form.address)
async def q_address(message: Message, state: FSMContext):
    text = await need_text(message)
    if text is None:
        return
    await state.update_data(address=text)
    await message.answer("<b>4. Oilada nechanchi farzandsiz?</b>")
    await state.set_state(Form.child_order)


# 4. Nechanchi farzand
@private.message(Form.child_order)
async def q_child(message: Message, state: FSMContext):
    text = await need_text(message)
    if text is None:
        return
    await state.update_data(child_order=text)
    await message.answer("<b>5. Eng ko'p qancha daromad qilgansiz?</b>")
    await state.set_state(Form.max_income)


# 5. Eng ko'p daromad
@private.message(Form.max_income)
async def q_income(message: Message, state: FSMContext):
    text = await need_text(message)
    if text is None:
        return
    await state.update_data(max_income=text)
    await message.answer("<b>6. 1 oylik xarajatingiz qancha?</b>")
    await state.set_state(Form.expense)


# 6. Oylik xarajat
@private.message(Form.expense)
async def q_expense(message: Message, state: FSMContext):
    text = await need_text(message)
    if text is None:
        return
    await state.update_data(expense=text)
    await message.answer(
        "<b>7. Ovozli xabar yuboring.</b>\n\n"
        "Nimanidir o'qib bering yoki o'zingiz haqingizda gapirib bering "
        "(yuqoridagi savollardan tashqari).\n"
        "⏱ Ovozli xabar <b>kamida 1 daqiqa</b> bo'lishi kerak."
    )
    await state.set_state(Form.voice)


# 7. Ovozli xabar
@private.message(Form.voice, F.voice)
async def q_voice(message: Message, state: FSMContext):
    dur = message.voice.duration
    if dur < MIN_VOICE_SECONDS:
        await message.answer(
            f"Ovozli xabaringiz {dur} soniya. Kamida {MIN_VOICE_SECONDS} soniya "
            "bo'lishi kerak. Iltimos, qaytadan yuboring."
        )
        return
    await state.update_data(voice_id=message.voice.file_id, voice_dur=dur)
    await message.answer(
        "<b>8. Telefon raqamingizni yuboring.</b>\n"
        "Pastdagi tugmani bosing yoki raqamni yozing (masalan: +998901234567).",
        reply_markup=phone_kb,
    )
    await state.set_state(Form.phone)


@private.message(Form.voice)
async def q_voice_wrong(message: Message):
    await message.answer("Iltimos, aynan <b>ovozli xabar</b> (🎤) yuboring.")


# 8. Telefon
@private.message(Form.phone)
async def q_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = (message.text or "").strip()
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) < 9:
            await message.answer("Raqam noto'g'ri ko'rinadi. Masalan: +998901234567")
            return
    if not phone.startswith("+") and phone.startswith("998"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await message.answer("Rahmat! Javoblaringizni tekshiring:", reply_markup=ReplyKeyboardRemove())
    data = await state.get_data()
    await message.answer(build_summary(data, message.from_user), reply_markup=confirm_kb)
    await state.set_state(Form.confirm)


def build_summary(data: dict, user, for_group: bool = False) -> str:
    tg = f"@{user.username}" if user.username else "username yo'q"
    link = f'<a href="tg://user?id={user.id}">{e(user.full_name)}</a>'
    head = "🆕 <b>YANGI REZYUME</b>\n\n" if for_group else "📋 <b>Sizning javoblaringiz</b>\n\n"
    body = (
        f"1. <b>Yoshi:</b> {e(data['age'])}\n"
        f"2. <b>Sotuvdagi tajribasi:</b> {e(data['experience'])}\n"
        f"3. <b>Manzili:</b> {e(data['address'])}\n"
        f"4. <b>Oilada nechanchi farzand:</b> {e(data['child_order'])}\n"
        f"5. <b>Eng ko'p daromadi:</b> {e(data['max_income'])}\n"
        f"6. <b>Oylik xarajati:</b> {e(data['expense'])}\n"
        f"7. <b>Ovozli xabar:</b> {data['voice_dur']} soniya\n"
        f"8. <b>Telefon:</b> {e(data['phone'])}\n"
        f"    <b>Telegram:</b> {tg} ({link})\n"
    )
    if for_group:
        body += f"\n🕒 {datetime.now(TZ):%d.%m.%Y %H:%M}"
    return head + body


@private.message(Form.confirm)
async def q_confirm_wait(message: Message):
    await message.answer("Iltimos, yuqoridagi tugmalardan birini bosing: ✅ yoki 🔄")


# ---------------------- Tasdiqlash ----------------------
@router.callback_query(Form.confirm, F.data == "confirm")
async def cb_confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = call.from_user
    try:
        sent = await bot.send_message(GROUP_ID, build_summary(data, user, for_group=True))
        await bot.send_voice(
            GROUP_ID, data["voice_id"],
            caption=f"🎤 {e(user.full_name)} — ovozli xabar",
            reply_to_message_id=sent.message_id,
        )
    except Exception as ex:
        logging.exception("Guruhga yuborishda xato: %s", ex)
        await call.answer("Texnik xatolik. Birozdan so'ng qayta urinib ko'ring.", show_alert=True)
        return

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        "Savollarga javob berganingiz uchun rahmat! 🙏\n"
        "Agar bizga to'g'ri kelsangiz, tez orada siz bilan bog'lanamiz."
    )
    await state.clear()
    await call.answer()


@router.callback_query(F.data == "restart")
async def cb_restart(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup(reply_markup=None)
    await state.clear()
    await call.message.answer("<b>1. Yoshingiz nechida?</b>\n(faqat raqam, masalan: 22)")
    await state.set_state(Form.age)
    await call.answer()


@private.message()
async def fallback(message: Message):
    await message.answer("Anketani boshlash uchun /start ni bosing.")


async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp.include_router(private)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
