import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI


BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Ключ от OpenRouter

# Подключаемся к OpenRouter API (как к OpenAI, но с другим base_url)
ai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://your-site.com",  # Можно заменить на свой сайт
        "X-Title": "AI Career Navigator",
    }
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()



# 2. ПОИСК ВАКАНСИЙ (Jobicy API)


async def search_vacancies(query: str, limit: int = 5) -> list:
    if not query or len(query.strip()) < 3:
        return []

    keywords = query.lower().split()
    tech_keywords = ['python', 'react', 'javascript', 'java', 'c++', 'c#', 'go', 'rust',
                     'devops', 'frontend', 'backend', 'fullstack', 'data', 'ml', 'ai',
                     'django', 'flask', 'fastapi', 'spring', 'node', 'typescript',
                     'vue', 'angular', 'docker', 'kubernetes', 'aws', 'azure']

    found_keywords = [w for w in keywords if w in tech_keywords]
    search_tag = " ".join(found_keywords[:3]) if found_keywords else " ".join(keywords[:2])

    url = "https://jobicy.com/api/v2/remote-jobs"
    params = {"tag": search_tag, "count": limit}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    jobs = data.get("jobs", [])
                    if not jobs:
                        return []

                    vacancies = []
                    for job in jobs[:limit]:
                        title = job.get("jobTitle") or job.get("title") or "Без названия"
                        company = job.get("companyName") or job.get("company") or "Неизвестная компания"

                        salary_min = job.get("annualSalaryMin") or job.get("salaryMin")
                        salary_max = job.get("annualSalaryMax") or job.get("salaryMax")
                        currency = job.get("salaryCurrency") or "USD"

                        if salary_min and salary_max:
                            salary_text = f"{salary_min} - {salary_max} {currency}"
                        elif salary_min:
                            salary_text = f"от {salary_min} {currency}"
                        elif salary_max:
                            salary_text = f"до {salary_max} {currency}"
                        else:
                            salary_text = "Не указана"

                        vacancies.append({
                            "name": title,
                            "company": company,
                            "salary": salary_text,
                            "url": job.get("url") or job.get("jobUrl") or "#",
                            "location": job.get("jobGeo") or job.get("geo") or "Удалённо",
                            "level": job.get("jobLevel") or job.get("level") or "Не указан"
                        })
                    return vacancies
                return []
        except:
            return []


# 3. КОМАНДА /start


@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я AI Career Navigator — твой карьерный детектив!\n\n"
        "📌 **Что я умею:**\n"
        "🔹 Анализировать твой опыт и навыки\n"
        "🔹 **Находить реальные IT-вакансии** со всего мира\n"
        "🔹 Давать рекомендации по развитию\n\n"
        "✍️ **Напиши мне свой опыт и навыки.**\n"
        "Например: 'Я Python-разработчик с 2 годами опыта, работал с Django и FastAPI.'\n\n"
        "Я найду вакансии и скажу, что тебе нужно подтянуть!",
        parse_mode="Markdown"
    )


# 4. ОСНОВНАЯ ЛОГИКА (AI + ВАКАНСИИ)

@dp.message()
async def analyze_career(message: types.Message):
    user_text = message.text

    status_msg = await message.answer(
        "🔍 **Анализирую профиль и ищу вакансии...**\n⏳ Это займет 15–25 секунд",
        parse_mode="Markdown"
    )

    try:
        # 1. ИЩЕМ ВАКАНСИИ
        vacancies = await search_vacancies(user_text, limit=5)

        #  2. AI-АНАЛИЗ
        if vacancies:
            vac_text = "\n".join([
                f"- {v['name']} в {v['company']} ({v['salary']}) [{v['location']}]"
                for v in vacancies
            ])
            ai_prompt = f"""
            Проанализируй опыт пользователя и скажи, какие навыки ему нужно подтянуть,
            чтобы соответствовать этим вакансиям.

            Опыт пользователя: {user_text}

            Найденные вакансии:
            {vac_text}

            Дай конкретные рекомендации по развитию.
            """
        else:
            ai_prompt = f"""
            Проанализируй опыт пользователя:
            {user_text}

            Подскажи, какие ключевые навыки добавить в резюме.
            """

        response = ai_client.chat.completions.create(
            model="openai/gpt-4o-mini",  # Дешевая и быстрая модель
            messages=[
                {"role": "system", "content": """
                Ты — эксперт по карьерному развитию.

                **ВАЖНО: Форматирование ответа**
                - Используй только **жирный шрифт** через **текст**
                - Используй эмодзи: 📌 🚀 💡 🔥 📊 🛠️ 💼
                - Для списков используй цифры: 1. 2. 3. или маркеры: - 
                - НЕ используй символы: * (звёздочки), ###, ---, ===
                - НЕ используй курсив (*текст*) 
                - Разбивай текст на абзацы пустыми строками

                Структура ответа (пример):
                **🔥 Твой профиль**
                [Текст]

                **📌 Ключевые навыки для развития:**
                1. [Навык 1]
                2. [Навык 2]
                3. [Навык 3]

                **💡 Советы по резюме:**
                - [Совет 1]
                - [Совет 2]
                """},
                {"role": "user", "content": ai_prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        ai_reply = response.choices[0].message.content

        # 3. БЛОК С ВАКАНСИЯМИ
        if vacancies:
            vac_block = "\n\n**💼 Актуальные вакансии для тебя:**\n\n"
            for i, vac in enumerate(vacancies, 1):
                vac_block += (
                    f"{i}. **{vac['name']}**\n"
                    f"   🏢 {vac['company']}\n"
                    f"   📍 {vac['location']}\n"
                    f"   🎯 Уровень: {vac['level']}\n"
                    f"   💰 {vac['salary']}\n"
                    f"   🔗 [Подробнее]({vac['url']})\n\n"
                )
        else:
            vac_block = "\n\n**😕 Не нашёл подходящих вакансий.**\n\n" \
                        "Попробуй указать:\n" \
                        "- конкретные технологии (Python, React, Java)\n" \
                        "- уровень опыта (Junior, Senior)\n\n" \
                        "**Но ты всё равно молодец! AI-анализ ниже — для тебя.**"

        # 4. ОТПРАВЛЯЕМ
        await status_msg.delete()
        await message.answer(
            ai_reply + vac_block,
            parse_mode="Markdown",
            disable_web_page_preview=False
        )

    except Exception as e:
        await status_msg.edit_text(
            f"❌ Ошибка: {e}\n\n"
            "Проверь настройки OpenRouter API."
        )



# ЗАПУСК


async def main():
    print("🚀 Бот запущен на Render с OpenRouter AI!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
