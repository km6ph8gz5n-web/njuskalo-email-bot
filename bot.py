"""Telegram-бот: UX в Telegram + HTML-письмо в стиле Njuškalo."""

from __future__ import annotations

import asyncio
import html
import logging
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
CTA_LABEL = "Otvori narudžbu"
CANCEL_TEXT = "❌ Отмена"

router = Router()


class Form(StatesGroup):
    waiting_message = State()
    waiting_url = State()
    waiting_email = State()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_from: str
    email_from_name: str
    email_subject: str
    reply_to: str

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Не задан BOT_TOKEN в файле .env")

        port_raw = os.getenv("SMTP_PORT", "587").strip()
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise RuntimeError("SMTP_PORT должен быть числом") from exc

        smtp_user = os.getenv("SMTP_USER", "").strip()
        smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
        email_from = os.getenv("EMAIL_FROM", smtp_user).strip()
        reply_to = os.getenv("REPLY_TO", email_from).strip() or email_from

        missing = [
            name
            for name, value in (
                ("SMTP_HOST", os.getenv("SMTP_HOST", "").strip()),
                ("SMTP_USER", smtp_user),
                ("SMTP_PASSWORD", smtp_password),
                ("EMAIL_FROM", email_from),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"В .env не заданы: {', '.join(missing)}")

        return cls(
            bot_token=token,
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            email_from=email_from,
            email_from_name=os.getenv("EMAIL_FROM_NAME", "Njuškalo Notification").strip()
            or "Njuškalo Notification",
            email_subject=os.getenv("EMAIL_SUBJECT", "Poruka s Njuškala").strip()
            or "Poruka s Njuškala",
            reply_to=reply_to,
        )


def user_label(message_or_user) -> str:
    user = getattr(message_or_user, "from_user", message_or_user)
    if user is None:
        return "unknown"
    username = f"@{user.username}" if getattr(user, "username", None) else "без username"
    return f"{user.id} ({username})"


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Создать и отправить письмо",
                    callback_data="compose",
                )
            ]
        ]
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.fullmatch(value.strip()))


def normalize_order_url(value: str) -> str | None:
    raw = value.strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc or "." not in parsed.netloc:
        return None
    return raw


def sender_domain(email_address: str) -> str:
    if "@" in email_address:
        return email_address.rsplit("@", 1)[-1].lower()
    return "localhost"


def build_email_html(message_text: str, order_url: str) -> str:
    """Адаптивное HTML-письмо: табличная вёрстка + media queries для телефона."""
    safe_paragraphs = html.escape(message_text).replace("\n", "<br>")
    safe_url = html.escape(order_url, quote=True)
    preheader = "Imate novu narudžbu. Otvorite poruku i pogledajte detalje."

    return f"""\
<!DOCTYPE html>
<html lang="hr">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="format-detection" content="telephone=no,address=no,email=no,date=no">
  <title>Njuškalo</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
  <style type="text/css">
    html, body {{ margin: 0 !important; padding: 0 !important; height: 100% !important; width: 100% !important; }}
    * {{ -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; }}
    table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
    img {{ -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }}
    a {{ text-decoration: none; }}
    @media only screen and (max-width: 620px) {{
      .email-wrapper {{ width: 100% !important; max-width: 100% !important; }}
      .email-outer {{ padding: 12px 8px !important; }}
      .email-pad {{ padding: 20px 16px !important; }}
      .email-header {{ padding: 16px !important; }}
      .email-footer {{ padding: 18px 16px !important; }}
      .email-title {{ font-size: 20px !important; line-height: 26px !important; }}
      .email-body {{ font-size: 16px !important; line-height: 24px !important; }}
      .email-brand {{ font-size: 22px !important; }}
      .hide-mobile {{ display: none !important; width: 0 !important; height: 0 !important; overflow: hidden !important; }}
      .btn-cell {{ width: 100% !important; }}
      .btn-link {{ display: block !important; width: auto !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:#f2f2f2;font-family:Arial,Helvetica,sans-serif;width:100%;">
  <div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">
    {html.escape(preheader)}
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-outer" style="background-color:#f2f2f2;padding:24px 12px;width:100%;">
    <tr>
      <td align="center" style="padding:0;">
        <!--[if mso]>
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td>
        <![endif]-->
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" width="100%" style="width:100%;max-width:600px;background-color:#ffffff;border:1px solid #e6e6e6;">
          <tr>
            <td class="email-header" style="background-color:#222222;padding:18px 24px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td class="email-brand" style="font-family:Arial,Helvetica,sans-serif;font-size:26px;font-weight:700;letter-spacing:-0.5px;color:#ffffff;">
                    njuš<span style="color:#ffe000;">kalo</span>
                  </td>
                  <td class="hide-mobile" align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#cccccc;white-space:nowrap;">
                    Oglasnik
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="height:4px;background-color:#ffe000;font-size:0;line-height:0;">&nbsp;</td>
          </tr>
          <tr>
            <td class="email-pad" style="padding:32px 28px 12px 28px;background-color:#ffffff;">
              <p style="margin:0 0 8px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#888888;text-transform:uppercase;letter-spacing:0.6px;">
                Nova poruka
              </p>
              <h1 class="email-title" style="margin:0 0 20px 0;font-family:Arial,Helvetica,sans-serif;font-size:22px;line-height:28px;color:#222222;font-weight:700;">
                Imate novu obavijest
              </h1>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid #e6e6e6;background-color:#fafafa;">
                <tr>
                  <td class="email-body email-pad" style="padding:20px 22px;font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:24px;color:#333333;">
                    {safe_paragraphs}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td class="email-pad" align="center" style="padding:24px 28px 36px 28px;background-color:#ffffff;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" class="btn-cell" style="margin:0 auto;">
                <tr>
                  <td align="center" bgcolor="#ffe000" style="background-color:#ffe000;border-radius:4px;border:1px solid #e6c800;">
                    <a class="btn-link" href="{safe_url}" target="_blank" style="display:inline-block;background-color:#ffe000;color:#111111;font-family:Arial,Helvetica,sans-serif;font-size:16px;font-weight:700;text-decoration:none;padding:14px 36px;border-radius:4px;line-height:20px;">
                      {html.escape(CTA_LABEL)}
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td class="email-footer" style="background-color:#333333;padding:22px 28px;">
              <p style="margin:0 0 8px 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#cccccc;">
                © 2026 Njuškalo. Sva prava pridržana.
              </p>
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#999999;">
                Ova poruka odnosi se na vašu narudžbu.
              </p>
            </td>
          </tr>
        </table>
        <!--[if mso]>
        </td></tr></table>
        <![endif]-->
      </td>
    </tr>
  </table>
</body>
</html>
"""


def build_email_plain(message_text: str, order_url: str) -> str:
    return (
        "Njuškalo — nova obavijest\n"
        "========================\n\n"
        "Imate novu poruku:\n\n"
        f"{message_text}\n\n"
        f"{CTA_LABEL}: {order_url}\n\n"
        "© 2026 Njuškalo. Sva prava pridržana.\n"
        "Ako niste očekivali ovu poruku, zanemarite je."
    )


def send_html_email(settings: Settings, to_email: str, message_text: str, order_url: str) -> None:
    html_body = build_email_html(message_text, order_url)
    plain_body = build_email_plain(message_text, order_url)
    domain = sender_domain(settings.email_from)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = settings.email_subject
    msg["From"] = formataddr((settings.email_from_name, settings.email_from))
    msg["To"] = to_email
    msg["Reply-To"] = formataddr((settings.email_from_name, settings.reply_to))
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=domain)
    msg["MIME-Version"] = "1.0"
    msg["Precedence"] = "bulk"
    msg["Auto-Submitted"] = "auto-generated"
    msg["X-Priority"] = "3"
    msg["X-MSMail-Priority"] = "Normal"
    msg["Importance"] = "Normal"
    msg["List-Unsubscribe"] = f"<mailto:{settings.email_from}?subject=unsubscribe>"
    msg["List-Id"] = f"Njuškalo Notifications <notifications.{domain}>"

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info("SMTP: подключение к %s:%s, получатель %s", settings.smtp_host, settings.smtp_port, to_email)
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.email_from, [to_email], msg.as_string())
    logger.info("Письмо на адрес %s успешно отправлено через SMTP", to_email)


WELCOME_TEXT = (
    "🤖 <b>Mail Bot</b>\n\n"
    "Я соберу текст, ссылку на заказ и отправлю HTML-письмо получателю.\n\n"
    "Нажмите кнопку ниже, чтобы начать."
)

ASK_BODY_TEXT = (
    "✉️ <b>Текст письма</b>\n\n"
    "Введите сообщение, которое появится в теле письма.\n\n"
    "<i>Совет:</i> пишите обычным языком, без КАПСА и стоп-слов "
    "(«срочно», «выигрыш», «бесплатно»), чтобы письмо скорее дошло, "
    "а не ушло в спам.\n\n"
    "Чтобы прервать сценарий, нажмите <b>❌ Отмена</b> или отправьте /cancel."
)

ASK_URL_TEXT = (
    "🔗 <b>Ссылка на заказ</b>\n\n"
    "Вставьте полную ссылку. Она попадёт в кнопку <b>Otvori narudžbu</b>.\n\n"
    "Пример: <code>https://shop.example/narudzba/123</code>"
)

INVALID_URL_TEXT = (
    "⚠️ <b>Некорректная ссылка</b>\n\n"
    "Нужен полный адрес с <code>https://</code> и доменом.\n"
    "Пример: <code>https://shop.example/narudzba/123</code>"
)

ASK_EMAIL_TEXT = (
    "🔑 <b>Email получателя</b>\n\n"
    "Ссылка сохранена. Теперь введите адрес получателя.\n\n"
    "Пример: <code>user@example.com</code>"
)

INVALID_EMAIL_TEXT = (
    "⚠️ <b>Некорректный адрес</b>\n\n"
    "Пожалуйста, введите корректный Email.\n"
    "Пример: <code>user@example.com</code>"
)


async def show_welcome(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=start_keyboard())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    logger.info("Пользователь %s открыл /start", user_label(message))
    await message.answer(
        WELCOME_TEXT,
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("👇 Выберите действие:", reply_markup=start_keyboard())


@router.callback_query(F.data == "compose")
async def on_compose(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Form.waiting_message)
    logger.info("Пользователь %s начал сценарий", user_label(callback))
    await callback.answer()
    if callback.message:
        await callback.message.answer(ASK_BODY_TEXT, reply_markup=cancel_keyboard())


@router.message(Command("cancel"))
@router.message(F.text == CANCEL_TEXT)
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    logger.info("Пользователь %s отменил сценарий (было: %s)", user_label(message), current)
    await message.answer(
        "❌ Сценарий остановлен. Можете начать заново.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await show_welcome(message)


@router.message(Form.waiting_message, F.text)
async def process_message_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text == CANCEL_TEXT:
        return
    if not text:
        await message.answer("⚠️ Текст не может быть пустым. Введите сообщение ещё раз.")
        return

    await state.update_data(letter_text=text)
    await state.set_state(Form.waiting_url)
    logger.info("Пользователь %s сохранил текст письма (%s символов)", user_label(message), len(text))
    await message.answer(ASK_URL_TEXT, reply_markup=cancel_keyboard())


@router.message(Form.waiting_message)
async def process_message_invalid(message: Message) -> None:
    await message.answer(
        "⚠️ Нужен обычный текст. Введите сообщение для письма или нажмите <b>❌ Отмена</b>."
    )


@router.message(Form.waiting_url, F.text)
async def process_order_url(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw == CANCEL_TEXT:
        return
    order_url = normalize_order_url(raw)
    if not order_url:
        logger.info("Пользователь %s ввёл некорректную ссылку", user_label(message))
        await message.answer(INVALID_URL_TEXT)
        return

    host = urlparse(order_url).netloc
    await state.update_data(order_url=order_url)
    await state.set_state(Form.waiting_email)
    logger.info("Пользователь %s сохранил ссылку на заказ (%s)", user_label(message), host)
    await message.answer(ASK_EMAIL_TEXT, reply_markup=cancel_keyboard())


@router.message(Form.waiting_url)
async def process_url_invalid(message: Message) -> None:
    await message.answer(INVALID_URL_TEXT)


@router.message(Form.waiting_email, F.text)
async def process_email(message: Message, state: FSMContext, settings: Settings) -> None:
    email = (message.text or "").strip()
    if email == CANCEL_TEXT:
        return
    if not is_valid_email(email):
        logger.info("Пользователь %s ввёл некорректный email", user_label(message))
        await message.answer(INVALID_EMAIL_TEXT)
        return

    data = await state.get_data()
    letter_text = data.get("letter_text", "")
    order_url = data.get("order_url", "")
    if not order_url:
        await message.answer("⚠️ Ссылка на заказ потеряна. Начните заново: /start")
        await state.clear()
        return
    safe_email = html.escape(email)
    await message.answer(f"📤 Отправляю письмо на <code>{safe_email}</code>…")
    logger.info("Пользователь %s инициировал отправку на %s", user_label(message), email)

    try:
        await asyncio.to_thread(send_html_email, settings, email, letter_text, order_url)
    except smtplib.SMTPAuthenticationError:
        logger.exception("Ошибка авторизации SMTP")
        await message.answer(
            "❌ Не удалось войти на SMTP-сервер. Проверьте <code>SMTP_USER</code> и "
            "<code>SMTP_PASSWORD</code> в .env.",
            reply_markup=cancel_keyboard(),
        )
        return
    except (smtplib.SMTPException, OSError, TimeoutError):
        logger.exception("Ошибка SMTP при отправке на %s", email)
        await message.answer(
            "❌ Ошибка подключения к SMTP или отправки письма. "
            "Проверьте хост, порт и сеть, затем попробуйте снова.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        f"✅ Письмо успешно отправлено на <code>{safe_email}</code>.\n\n"
        "Можете создать следующее.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await show_welcome(message)


@router.message(Form.waiting_email)
async def process_email_invalid(message: Message) -> None:
    await message.answer(INVALID_EMAIL_TEXT)


@router.message(StateFilter(None), F.text)
async def fallback_idle(message: Message) -> None:
    await message.answer(
        "ℹ️ Сейчас нет активного сценария. Нажмите /start или кнопку ниже.",
        reply_markup=start_keyboard(),
    )


async def main() -> None:
    settings = Settings.from_env()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp["settings"] = settings
    dp.include_router(router)

    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error("Ошибка polling: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
