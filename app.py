from flask import Flask, render_template, request, jsonify
from flask_caching import Cache
from hh_api import HHVacancyAnalyzer
import logging

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

# Создаем один экземпляр HHVacancyAnalyzer для всего приложения
analyzer = HHVacancyAnalyzer()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/form')
def form():
    return render_template('form.html')


@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


@app.route('/hh_api', methods=['POST'])
def hh_api():
    job_title = request.form.get('job_title')
    region = request.form.get('region')
    experience = request.form.get('experience')
    employment = request.form.get('employment')
    salary = request.form.get('salary')

    logging.debug(
        f"Received request: job_title={job_title}, region={region}, "
        f"experience={experience}, employment={employment}, salary={salary}"
    )

    try:
        # Вызываем метод analyze_vacancies
        results = analyzer.analyze_vacancies(job_title, region, experience, employment, salary)
        return render_template('results.html', results=results)
    except Exception as e:
        logging.error(f"Error in analyze_vacancies: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 400


@app.route('/send_message', methods=['POST'])
def send_message():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    # Здесь должна быть логика для обработки сообщения
    # Например, отправка email или сохранение в базу данных

    logging.info(f"Получено сообщение от {name} ({email}): {message}")

    # В реальном приложении здесь должна быть более сложная логика

    return jsonify({'success': True, 'message': 'Сообщение успешно отправлено'}), 200


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
