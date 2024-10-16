import requests
import json
from collections import Counter
import datetime
import statistics
from cachetools import TTLCache, cached
from functools import lru_cache
from database import get_db_connection


class HHVacancyAnalyzer:
    """Класс для анализа вакансий с HeadHunter."""

    def __init__(self):
        self.base_url = "https://api.hh.ru/vacancies"
        self.headers = {"User-Agent": "VacancyAnalyzer/1.0"}
        self.cache = TTLCache(maxsize=100, ttl=3600)  # Кэш на 100 элементов, время жизни 1 час

    @cached(cache=TTLCache(maxsize=100, ttl=3600))
    def get_vacancies(self, query, area="1", experience="", employment="", salary=""):
        """Получает вакансии с API HeadHunter."""
        params = {
            "text": query,
            "area": area,
            "experience": experience,
            "employment": employment,
            "salary": salary,
            "per_page": 100
        }
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к API HeadHunter: {e}")
            return None

    @lru_cache(maxsize=1000)
    def parse_requirements(self, description):
        """Извлекает требования из описания вакансии."""
        return tuple([req.strip().lower() for req in description.split() if len(req) > 2])

    def save_to_db(self, vacancies):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for vacancy in vacancies:
                cursor.execute('''
                       INSERT INTO vacancies (title, company, salary_from, salary_to, area, experience, employment, url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ''', (
                    vacancy['name'],
                    vacancy['employer']['name'],
                    vacancy['salary']['from'] if vacancy.get('salary') else None,
                    vacancy['salary']['to'] if vacancy.get('salary') else None,
                    vacancy['area']['name'],
                    vacancy['experience']['name'],
                    vacancy['employment']['name'],
                    vacancy['alternate_url']
                ))
                vacancy_id = cursor.lastrowid

                description = vacancy.get('snippet', {}).get('requirement', '')
                if description:
                    requirements = self.parse_requirements(description)
                    for req in set(requirements):
                        cursor.execute('INSERT OR IGNORE INTO requirements (name) VALUES (?)', (req,))
                        cursor.execute('SELECT id FROM requirements WHERE name = ?', (req,))
                        req_id = cursor.fetchone()[0]
                        cursor.execute('INSERT INTO vacancy_requirements (vacancy_id, requirement_id) VALUES (?, ?)',
                                       (vacancy_id, req_id))
            conn.commit()

    def analyze_vacancies(self, query, area="1", experience="", employment="", salary=""):
        """Анализирует вакансии и возвращает результаты."""
        cache_key = f"{query}_{area}_{experience}_{employment}_{salary}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        data = self.get_vacancies(query, area, experience, employment, salary)
        if data is None:
            return None
        vacancies = data['items']

        # Сохраняем вакансии в базу данных
        self.save_to_db(vacancies)

        total_vacancies = len(vacancies)
        salaries = [v['salary']['from'] for v in vacancies if v.get('salary') and v['salary'].get('from')]
        avg_salary = sum(salaries) / len(salaries) if salaries else 0
        median_salary = statistics.median(salaries) if salaries else 0

        all_requirements = []
        for vacancy in vacancies:
            description = vacancy.get('snippet', {}).get('requirement', '')
            if description:
                requirements = self.parse_requirements(description)
                all_requirements.extend(requirements)

        req_count = Counter(all_requirements)
        req_percentage = {req: (count / total_vacancies) * 100 for req, count in req_count.items()}
        sorted_req = sorted(req_count.items(), key=lambda x: x[1], reverse=True)

        experience_distribution = Counter(v['experience']['name'] for v in vacancies if v.get('experience'))
        employment_distribution = Counter(v['employment']['name'] for v in vacancies if v.get('employment'))
        companies = Counter(v['employer']['name'] for v in vacancies if v.get('employer'))

        result = {
            "query": query,
            "total_vacancies": total_vacancies,
            "average_salary": round(avg_salary, 2),
            "median_salary": round(median_salary, 2),
            "requirements": {
                "count": dict(sorted_req),
                "percentage": {k: round(v, 2) for k, v in req_percentage.items()}
            },
            "top_skills": sorted_req[:10],
            "unique_requirements": len(req_count),
            "experience_distribution": dict(experience_distribution),
            "employment_distribution": dict(employment_distribution),
            "top_companies": companies.most_common(10)
        }
        self.cache[cache_key] = result
        return result

    @staticmethod
    def save_results(result, query):
        """Сохраняет результаты в JSON файл."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{query.replace(' ', '_')}_analysis_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"Результаты сохранены в файл: {filename}")


def main():
    analyzer = HHVacancyAnalyzer()
    query = input("Введите название вакансии: ")
    area = input("Введите ID региона (по умолчанию 1 - Москва): ") or "1"
    experience = input("Введите опыт работы (noExperience, between1And3, between3And6, moreThan6): ") or ""
    employment = input("Введите тип занятости (full, part, project, volunteer): ") or ""
    salary = input("Введите желаемую зарплату: ") or ""
    result = analyzer.analyze_vacancies(query, area, experience, employment, salary)
    if result:
        print("\nРезультаты анализа:")
        print(f"Всего вакансий: {result['total_vacancies']}")
        print(f"Средняя зарплата: {result['average_salary']} руб.")
        print(f"Медианная зарплата: {result['median_salary']} руб.")
        print("\nТоп-10 требований:")
        for req, count in result['top_skills']:
            print(f"{req}: {count} раз")
        print(f"\nУникальных требований: {result['unique_requirements']}")
        print("\nРаспределение по опыту работы:")
        for exp, count in result['experience_distribution'].items():
            print(f"{exp}: {count}")
        print("\nРаспределение по типу занятости:")
        for emp, count in result['employment_distribution'].items():
            print(f"{emp}: {count}")
        print("\nТоп-10 компаний:")
        for company, count in result['top_companies']:
            print(f"{company}: {count} вакансий")
        analyzer.save_results(result, query)
    else:
        print("Не удалось получить данные для анализа.")


if __name__ == "__main__":
    main()