from aiogram.filters.command import Command
from aiogram import Router
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.handlers.callback_query import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums.parse_mode import ParseMode
from magic_filter import F
import os
from dotenv import dotenv_values
from typing import Optional

from bot_init import sd_bot
from gsheets_client import GSheets


config = {
    **dotenv_values(".env"),
    **os.environ,
}


dp = sd_bot.dispatcher
bot = sd_bot.bot
form_router = Router()
dp.include_router(form_router)

TECH_FIELDS_NAMES = ['Картинка 1', 'Картинка 2', 'Картинка 3', 'Картинка 4', 'Ссылка на товар', 'Номер']
LINK_PARTS = ['http://', 'https://']


class AnswerCallback(CallbackData, prefix='new-user'):
    answer: str
    val: Optional[str]


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    gsheets = GSheets(creds_json_file=config.get('SHEETS_CREDS_FILE'))
    sheet_names = gsheets.get_sheet_names(config.get('SHEET_URL'))

    builder = InlineKeyboardBuilder()
    for sheet_name in sheet_names:
        builder.button(
            text=f'{sheet_name}',
            callback_data=AnswerCallback(answer="go-to-catalog", val=f'{sheet_name}').pack()
        )

    builder.adjust(2)
    await bot.send_message(chat_id=message.chat.id,
                           reply_markup=builder.as_markup(),
                           text='Добро пожаловать в наш магазин!')


@form_router.callback_query(AnswerCallback.filter(F.answer == "go-to-catalog"))
async def go_to_catalog(query: CallbackQuery, callback_data: dict, state: FSMContext) -> None:
    gsheets = GSheets(creds_json_file='google_creds.json')
    sheet_name = callback_data.val
    await state.set_data({'sheet_name': sheet_name})
    catalog_values = gsheets.get_sheet_values(config.get('SHEET_URL'), sheet_name)
    # если нет даже заголовков или есть только заголовки в таблице
    if not catalog_values or len(catalog_values) < 2:
        builder = InlineKeyboardBuilder()
        builder.button(text="В главное меню", callback_data=AnswerCallback(answer="go-home", val='').pack())

        await bot.send_message(
            chat_id=query.message.chat.id,
            reply_markup=builder.as_markup(),
            text='Каталог пуст!'
        )
    else:
        for catalog_val in catalog_values[1:]:
            builder = InlineKeyboardBuilder()
            builder.button(text="Связаться с продавцом", url=config.get('ADMIN_CHAT_URL'))

            text = ''
            media_group = MediaGroupBuilder()

            desc_dict = dict(zip(catalog_values[0], catalog_val))
            for k, v in desc_dict.items():
                if k in TECH_FIELDS_NAMES:
                    if 'картинка' in k.lower() and v is not None and len(v):
                        media_group.add_photo(media=v)
                else:
                    if len(text):
                        text += f', <b>{k}:</b> {v}'
                    else:
                        text = f'<b>{k}:</b> {v}'

            text += f'\n\n{config.get("MANAGER_USERNAME")}\n{config.get("MANAGER_PHONE")}'
            product_number = desc_dict.get("Номер", '')

            builder.button(
                text="Запросить информацию о товаре",
                callback_data=AnswerCallback(answer="send-request", val=product_number).pack()
            )
            builder.button(text="Назад", callback_data=AnswerCallback(answer="go-home", val='').pack())
            builder.adjust(1)

            mg_list = media_group.build()
            if mg_list:
                await bot.send_message(
                    chat_id=query.message.chat.id,
                    text='\n\n---------------------------------------\n\n'
                )
                await bot.send_media_group(chat_id=query.message.chat.id, media=mg_list)
                await bot.send_message(
                    chat_id=query.message.chat.id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
                await bot.send_message(
                    chat_id=query.message.chat.id,
                    reply_markup=builder.as_markup(),
                    text='Вы можете:'
                )
            else:
                await bot.send_message(
                    chat_id=query.message.chat.id,
                    reply_markup=builder.as_markup(),
                    text=f'\n\n---------------------------------------\n\n{text}\n\nВы можете:'
                )


@form_router.callback_query(AnswerCallback.filter(F.answer == "send-request"))
async def send_request(query: CallbackQuery, callback_data: dict, state: FSMContext) -> None:
    await bot.send_message(chat_id=query.message.chat.id,
                           text='Запрос отправляется...')

    username = query.message.chat.username
    product_number = callback_data.val if callback_data.val else ''
    gclient = GSheets(creds_json_file=config.get('SHEETS_CREDS_FILE'))
    data_dict = await state.get_data()

    product_info = gclient.get_row_by_primary_field(config.get('SHEET_ID'), data_dict['sheet_name'], 'Номер', product_number)

    text = f'Пользователь @{username} запросил информацию о товаре {product_info.get("Ссылка на товар")}'

    await bot.send_message(
        chat_id=config.get('ADMIN_CHAT_ID'),
        text=text
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="В главное меню", callback_data=AnswerCallback(answer="go-home", val='').pack())

    await bot.send_message(
        chat_id=query.message.chat.id,
        reply_markup=builder.as_markup(),
        text=f'Ваш запрос отправлен! Администратор магазина свяжется с вами в ближайшее время'
    )


@form_router.callback_query(AnswerCallback.filter(F.answer == "go-home"))
async def go_home(query: CallbackQuery) -> None:
    await cmd_start(query.message)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
