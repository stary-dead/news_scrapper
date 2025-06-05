"""Main bot module"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import BotConfig
import sys
import os

# Add parent directory to path to import parser
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parser.news_parser import NewsParser
from parser.categories import CategoryStructure

# Initialize bot and dispatcher
bot = Bot(token=BotConfig().token)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Initialize parser
news_parser = NewsParser()
category_structure = CategoryStructure()

@router.message(CommandStart())
async def start_command(message: Message):
    """Handle /start command"""
    await message.answer(
        "Привет! Я бот для чтения новостей с rp.pl\n"
        "Отправь мне название категории (например, 'ekonomia'), "
        "и я пришлю тебе последние новости из этой категории."
    )

@router.message()
async def process_category(message: Message):
    """Process category name and return news"""
    category = message.text.lower()
    
    # Check if category exists in level 1
    if not category_structure.is_valid_category(category):
        await message.answer(
            f"Категория '{category}' не найдена.\n"
            f"Доступные категории:\n"
            f"- ekonomia (Экономика)\n"
            f"- biznes (Бизнес)\n"
            f"- kraj (Страна)\n"
            f"- swiat (Мир)\n"
            f"и другие."
        )
        return

    # Send initial message
    status_message = await message.answer(f"Ищу новости в категории '{category}' и её подкатегориях...")

    try:
        # Get all subcategory paths for the selected category
        subcategory_paths = category_structure.get_all_subcategory_paths(category)
        
        if not subcategory_paths:
            await status_message.edit_text(
                f"Не найдено подкатегорий для категории '{category}'.\n"
                f"Пожалуйста, выберите другую категорию."
            )
            return

        articles_found = False
        processed_urls = set()  # To avoid duplicate articles

        # Process each subcategory path
        for path in subcategory_paths:
            try:
                cat_args = {}
                if len(path) >= 1:
                    cat_args['cat_lv1'] = path[0]
                if len(path) >= 2:
                    cat_args['cat_lv2'] = path[1]
                if len(path) >= 3:
                    cat_args['cat_lv3'] = path[2]

                # Get one latest article from this subcategory
                result = await asyncio.wait_for(
                    news_parser.parse_by_category(**cat_args, limit=1),
                    timeout=10  # 10 seconds timeout per subcategory
                )

                if result and result.get("articles"):
                    for article in result["articles"]:
                        if article.get('title') and article.get('url'):
                            # Skip if we already sent this article
                            if article['url'] in processed_urls:
                                continue
                                
                            processed_urls.add(article['url'])
                            articles_found = True
                            
                            # Get the full category path name
                            subcategory_name = " > ".join([
                                category_structure.get_category_name(*path[:i+1]) or path[i]
                                for i in range(len(path))
                            ])
                            
                            message_text = (
                                f"📰 *{article['title']}*\n\n"
                                f"📁 {subcategory_name}\n"
                                f"🔍 {article.get('subtitle', '')}\n\n"
                                f"📅 {article.get('publication_date', 'Дата не указана')}\n"
                                f"✍️ {article.get('author', 'Автор не указан')}\n\n"
                                f"🔗 [Читать полностью]({article['url']})"
                            )
                            
                            await message.answer(
                                message_text,
                                parse_mode="Markdown",
                                disable_web_page_preview=True
                            )
                            await asyncio.sleep(0.5)  # Small delay between messages

            except asyncio.TimeoutError:
                logging.warning(f"Timeout while processing subcategory {' > '.join(path)}")
                continue
            except Exception as e:
                logging.error(f"Error processing subcategory {' > '.join(path)}: {e}")
                continue

        if not articles_found:
            await status_message.edit_text(
                f"В категории '{category}' и её подкатегориях не найдено актуальных статей.\n"
                f"Попробуйте:\n"
                f"1. Проверить другие категории\n"
                f"2. Подождать некоторое время\n"
                f"3. Уточнить запрос"
            )
            return
            
        await status_message.delete()

    except Exception as e:
        logging.error(f"Error processing category {category}: {e}")
        await status_message.edit_text(
            f"❌ Произошла ошибка при поиске новостей.\n"
            f"Мы уже работаем над её устранением.\n"
            f"Пожалуйста, попробуйте позже или выберите другую категорию."
        )

async def main():
    """Main function"""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
