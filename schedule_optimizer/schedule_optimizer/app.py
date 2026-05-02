from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
from typing import Dict, Any

from data_loader import load_lessons_from_excel, load_auditoriums_from_excel, create_time_slots
from algorithms import ScheduleOptimizer

APP_TITLE = "Автоматизированная система составления расписания"
MAX_LESSONS_FOR_DEMO = 30

app = FastAPI(title=APP_TITLE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>АСР ГУУ - Автоматизированная система составления расписания</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 20px; padding: 30px; margin-bottom: 30px; color: white;
            text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header h1 { font-size: 32px; margin-bottom: 10px; }
        .header h1 span { color: #f39c12; }
        .header .subtitle { font-size: 16px; opacity: 0.9; }
        .university-badge {
            display: inline-block; background: rgba(255,255,255,0.1); padding: 5px 15px;
            border-radius: 30px; margin-top: 15px; font-size: 14px;
        }
        .card {
            background: white; border-radius: 20px; padding: 25px; margin-bottom: 25px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        .card-title {
            font-size: 20px; font-weight: 600; margin-bottom: 20px; color: #1a1a2e;
            border-left: 4px solid #f39c12; padding-left: 15px;
        }
        .upload-area {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px; margin-bottom: 25px;
        }
        .upload-box {
            border: 2px dashed #dee2e6; border-radius: 15px; padding: 20px; text-align: center;
            cursor: pointer; transition: all 0.3s; background: #f8f9fa;
        }
        .upload-box:hover { border-color: #667eea; background: #f0f2ff; }
        .upload-box.selected { border-color: #28a745; background: #d4edda; }
        .upload-icon { font-size: 48px; margin-bottom: 10px; }
        .upload-name { font-size: 14px; color: #666; margin-top: 10px; word-break: break-all; }
        .file-input { display: none; }
        .algorithm-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px; margin-bottom: 25px;
        }
        .algo-card {
            background: #f8f9fa; border-radius: 15px; padding: 15px; cursor: pointer;
            transition: all 0.3s; border: 2px solid transparent; text-align: center;
        }
        .algo-card:hover { transform: translateY(-2px); background: #e9ecef; }
        .algo-card.selected {
            border-color: #667eea; background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        }
        .algo-icon { font-size: 36px; margin-bottom: 10px; }
        .algo-name { font-size: 16px; font-weight: 600; margin-bottom: 5px; }
        .algo-desc { font-size: 11px; color: #666; }
        .btn-optimize {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; padding: 15px 40px; border-radius: 50px;
            font-size: 18px; font-weight: 600; cursor: pointer; transition: all 0.3s; width: 100%;
        }
        .btn-optimize:hover:not(:disabled) {
            transform: translateY(-2px); box-shadow: 0 10px 20px rgba(102,126,234,0.3);
        }
        .btn-optimize:disabled { opacity: 0.6; cursor: not-allowed; }
        .loading-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7);
            display: none; align-items: center; justify-content: center; z-index: 1000;
        }
        .loading-content {
            background: white; border-radius: 20px; padding: 40px; text-align: center; min-width: 300px;
        }
        .spinner {
            width: 50px; height: 50px; border: 4px solid #e9ecef; border-top-color: #667eea;
            border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .fitness-panel {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 15px; padding: 20px; color: white; margin-bottom: 20px;
        }
        .fitness-value { font-size: 48px; font-weight: bold; color: #f39c12; }
        .violations-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px; margin-bottom: 20px;
        }
        .violation-item { background: #f8f9fa; border-radius: 10px; padding: 12px; border-left: 4px solid; }
        .violation-item.conflict { border-left-color: #dc3545; }
        .violation-item.warning { border-left-color: #fdbb4d; }
        .violation-item.info { border-left-color: #17a2b8; }
        .schedule-wrapper { overflow-x: auto; margin-top: 20px; }
        .schedule-table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 700px; }
        .schedule-table th { background: #1a1a2e; color: white; padding: 10px; text-align: center; }
        .schedule-table td { border: 1px solid #dee2e6; padding: 8px; vertical-align: top; background: white; }
        .lesson-item { margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #eee; }
        .lesson-item:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
        .lesson-discipline { font-weight: 600; color: #1a1a2e; font-size: 11px; }
        .lesson-detail { font-size: 10px; color: #666; margin-top: 3px; }
        .badge { display: inline-block; padding: 2px 6px; border-radius: 10px; font-size: 9px; font-weight: 600; margin-right: 4px; }
        .badge-lecture { background: #cfe2ff; color: #084298; }
        .badge-practice { background: #d1e7dd; color: #0f5132; }
        .badge-lab { background: #f8d7da; color: #842029; }
        .badge-even { background: #17a2b8; color: white; }
        .badge-odd { background: #6c757d; color: white; }
        .error-message {
            background: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px;
            margin-top: 15px; border: 1px solid #f5c6cb;
        }
        @media (max-width: 768px) {
            body { padding: 10px; }
            .header h1 { font-size: 22px; }
            .card { padding: 15px; }
            .fitness-value { font-size: 32px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏫 <span>АСР ГУУ</span></h1>
            <p class="subtitle">Автоматизированная система составления расписания занятий</p>
            <div class="university-badge">🎓 Государственный университет управления | Демонстрационный контур</div>
        </div>

        <div class="card">
            <div class="card-title">📁 1. Загрузка исходных данных</div>
            <div class="upload-area">
                <div class="upload-box" id="schedule-upload" onclick="document.getElementById('schedule-file').click()">
                    <div class="upload-icon">📊</div>
                    <div>Ведомость занятий</div>
                    <div class="upload-name" id="schedule-name">Файл не выбран</div>
                    <input type="file" id="schedule-file" accept=".xlsx,.xls" class="file-input">
                </div>
                <div class="upload-box" id="auditorium-upload" onclick="document.getElementById('auditorium-file').click()">
                    <div class="upload-icon">🏛️</div>
                    <div>Список аудиторий</div>
                    <div class="upload-name" id="auditorium-name">Файл не выбран</div>
                    <input type="file" id="auditorium-file" accept=".xlsx,.xls" class="file-input">
                </div>
            </div>

            <div class="card-title" style="margin-top: 20px;">🧬 2. Выбор алгоритма оптимизации</div>
            <div class="algorithm-grid">
                <div class="algo-card selected" data-algo="combined" onclick="selectAlgorithm('combined')">
                    <div class="algo-icon">🧬🌡️⚡</div>
                    <div class="algo-name">Комбинированный</div>
                    <div class="algo-desc">ГА -> отжиг -> жадный fallback</div>
                </div>
                <div class="algo-card" data-algo="genetic" onclick="selectAlgorithm('genetic')">
                    <div class="algo-icon">🧬</div>
                    <div class="algo-name">Генетический</div>
                    <div class="algo-desc">Основной поиск решения</div>
                </div>
                <div class="algo-card" data-algo="annealing" onclick="selectAlgorithm('annealing')">
                    <div class="algo-icon">🌡️</div>
                    <div class="algo-name">Имитация отжига</div>
                    <div class="algo-desc">Дооптимизация решения</div>
                </div>
                <div class="algo-card" data-algo="greedy" onclick="selectAlgorithm('greedy')">
                    <div class="algo-icon">⚡</div>
                    <div class="algo-name">Жадный</div>
                    <div class="algo-desc">Резервный алгоритм</div>
                </div>
            </div>

            <button class="btn-optimize" id="optimize-btn" onclick="optimize()">
                🚀 ЗАПУСТИТЬ ОПТИМИЗАЦИЮ РАСПИСАНИЯ
            </button>
        </div>

        <div id="results" style="display: none;">
            <div class="card">
                <div class="card-title">📈 3. Результаты оптимизации</div>

                <div class="fitness-panel" id="fitness-panel">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div>
                            <div style="font-size: 14px; opacity: 0.8;">Значение целевой функции F(X)</div>
                            <div class="fitness-value" id="fitness-value">0</div>
                            <div style="font-size: 12px;">Чем меньше - тем лучше</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 14px; opacity: 0.8;">Использованный алгоритм</div>
                            <div style="font-size: 18px; font-weight: bold;" id="algorithm-used">-</div>
                            <div style="font-size: 12px;" id="execution-time">Время: -</div>
                        </div>
                    </div>
                </div>

                <div class="violations-grid" id="violations-grid"></div>

                <div class="schedule-wrapper">
                    <table class="schedule-table" id="schedule-table">
                        <thead id="table-header"></thead>
                        <tbody id="table-body"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="error-container"></div>
    </div>

    <div class="loading-overlay" id="loading">
        <div class="loading-content">
            <div class="spinner"></div>
            <h3>🔄 Оптимизация расписания</h3>
            <p>Выполняется поиск решения по логике дипломного алгоритма...</p>
            <p style="font-size: 12px; color: #666; margin-top: 15px;">Это может занять до 30 секунд</p>
        </div>
    </div>

    <script>
        let selectedAlgorithm = 'combined';

        function selectAlgorithm(algo) {
            selectedAlgorithm = algo;
            document.querySelectorAll('.algo-card').forEach(card => card.classList.remove('selected'));
            document.querySelector(`.algo-card[data-algo="${algo}"]`).classList.add('selected');
            console.log('Выбран алгоритм:', algo);
        }

        document.getElementById('schedule-file').addEventListener('change', function(e) {
            const name = e.target.files[0]?.name || 'Файл не выбран';
            document.getElementById('schedule-name').textContent = name;
            document.getElementById('schedule-upload').classList.toggle('selected', !!e.target.files[0]);
        });

        document.getElementById('auditorium-file').addEventListener('change', function(e) {
            const name = e.target.files[0]?.name || 'Файл не выбран';
            document.getElementById('auditorium-name').textContent = name;
            document.getElementById('auditorium-upload').classList.toggle('selected', !!e.target.files[0]);
        });

        async function optimize() {
            const scheduleFile = document.getElementById('schedule-file').files[0];
            const auditoriumFile = document.getElementById('auditorium-file').files[0];

            if (!scheduleFile || !auditoriumFile) {
                showError('❌ Пожалуйста, выберите оба файла с данными');
                return;
            }

            console.log('Запуск оптимизации с алгоритмом:', selectedAlgorithm);

            const loading = document.getElementById('loading');
            const resultsDiv = document.getElementById('results');
            const btn = document.getElementById('optimize-btn');
            const errorContainer = document.getElementById('error-container');

            loading.style.display = 'flex';
            resultsDiv.style.display = 'none';
            errorContainer.innerHTML = '';
            btn.disabled = true;

            const formData = new FormData();
            formData.append('schedule_file', scheduleFile);
            formData.append('auditorium_file', auditoriumFile);
            formData.append('algorithm', selectedAlgorithm);

            try {
                const response = await fetch('/optimize', { method: 'POST', body: formData });
                const data = await response.json();

                console.log('Ответ от сервера:', data);

                if (data.error) {
                    showError('❌ Ошибка: ' + data.error);
                    return;
                }

                displayResults(data);
                resultsDiv.style.display = 'block';
            } catch (error) {
                showError('❌ Ошибка при выполнении оптимизации: ' + error.message);
            } finally {
                loading.style.display = 'none';
                btn.disabled = false;
            }
        }

        function showError(message) {
            const errorContainer = document.getElementById('error-container');
            errorContainer.innerHTML = `<div class="error-message">${message}</div>`;
        }

        function displayResults(data) {
            document.getElementById('fitness-value').textContent = data.fitness_score.toFixed(2);
            document.getElementById('algorithm-used').textContent = data.algorithm_used;
            document.getElementById('execution-time').textContent = `Время: ${data.execution_time_ms.toFixed(0)} мс`;

            const violationsGrid = document.getElementById('violations-grid');
            violationsGrid.innerHTML = `
                <div class="violation-item conflict"><strong>👥 Конфликты преподавателей</strong><br>${data.violations.teacher_conflict || 0}</div>
                <div class="violation-item conflict"><strong>👨‍🎓 Конфликты групп</strong><br>${data.violations.group_conflict || 0}</div>
                <div class="violation-item conflict"><strong>🏛️ Конфликты аудиторий</strong><br>${data.violations.auditorium_conflict || 0}</div>
                <div class="violation-item warning"><strong>📚 Несоответствие аудиторий</strong><br>${data.violations.auditorium_mismatch || 0}</div>
                <div class="violation-item warning"><strong>⏰ Штраф за окна</strong><br>${data.violations.windows || 0}</div>
                <div class="violation-item info"><strong>⚖️ Неравномерность нагрузки</strong><br>${(data.violations.load_imbalance || 0).toFixed(2)}</div>
            `;
            buildScheduleTable(data.schedule);
        }

        function buildScheduleTable(schedule) {
            const days = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ'];
            const pairs = [1, 2, 3, 4, 5, 6];
            const timeMap = {
                1: '9:00-10:30', 2: '10:40-12:10', 3: '12:55-14:25',
                4: '14:35-16:05', 5: '16:15-17:45', 6: '17:55-19:25'
            };

            const scheduleMap = {};
            schedule.forEach(lesson => {
                const key = `${lesson.day}_${lesson.pair_number}`;
                if (!scheduleMap[key]) scheduleMap[key] = [];
                scheduleMap[key].push(lesson);
            });

            const thead = document.getElementById('table-header');
            thead.innerHTML = `<tr><th>Время / День</th>${days.map(d => `<th>${d}</th>`).join('')}</tr>`;

            const tbody = document.getElementById('table-body');
            tbody.innerHTML = '';

            for (let pair of pairs) {
                const row = document.createElement('tr');

                const timeCell = document.createElement('td');
                timeCell.innerHTML = `<strong>${pair}-я пара</strong><br><span style="font-size: 10px;">${timeMap[pair]}</span>`;
                timeCell.style.backgroundColor = '#f8f9fa';
                timeCell.style.fontWeight = 'bold';
                timeCell.style.textAlign = 'center';
                row.appendChild(timeCell);

                for (let day of days) {
                    const cell = document.createElement('td');
                    const key = `${day}_${pair}`;
                    const lessons = scheduleMap[key] || [];

                    if (lessons.length > 0) {
                        cell.innerHTML = lessons.map(lesson => {
                            let typeClass = 'badge-practice';
                            let typeIcon = '✍️';
                            if (lesson.lesson_type === 'Лекции') { typeClass = 'badge-lecture'; typeIcon = '📖'; }
                            else if (lesson.lesson_type === 'Лаб. занятия') { typeClass = 'badge-lab'; typeIcon = '🔬'; }

                            return `
                                <div class="lesson-item">
                                    <div class="lesson-discipline">${typeIcon} ${lesson.discipline.substring(0, 30)}</div>
                                    <div class="lesson-detail">
                                        📍 ${lesson.group}<br>
                                        👨‍🏫 ${lesson.teacher.substring(0, 20)}<br>
                                        🏛️ ${lesson.auditorium}<br>
                                        <span class="badge ${typeClass}">
                                            ${lesson.lesson_type === 'Лекции' ? 'Лекция' : lesson.lesson_type === 'Практ. занятия' ? 'Практика' : 'Лабораторная'}
                                        </span>
                                        <span class="badge ${lesson.week_parity === 'Ч' ? 'badge-even' : 'badge-odd'}">
                                            ${lesson.week_parity === 'Ч' ? 'Чётная' : 'Нечётная'}
                                        </span>
                                    </div>
                                </div>`;
                        }).join('');
                    } else {
                        cell.innerHTML = '<span style="color: #adb5bd;">-</span>';
                    }
                    row.appendChild(cell);
                }
                tbody.appendChild(row);
            }
        }
    </script>
</body>
</html>
"""


def _safe_remove(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    return HTML_PAGE


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/optimize")
async def optimize_schedule(
        schedule_file: UploadFile = File(...),
        auditorium_file: UploadFile = File(...),
        algorithm: str = "combined",
) -> Dict[str, Any]:
    schedule_path = ""
    auditorium_path = ""

    try:
        print(f"\n=== ЗАПУСК ОПТИМИЗАЦИИ ===")
        print(f"Выбранный алгоритм: {algorithm}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_schedule:
            tmp_schedule.write(await schedule_file.read())
            schedule_path = tmp_schedule.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_aud:
            tmp_aud.write(await auditorium_file.read())
            auditorium_path = tmp_aud.name

        lessons, lesson_errors = load_lessons_from_excel(schedule_path)
        auditoriums, auditorium_errors = load_auditoriums_from_excel(auditorium_path)
        time_slots = create_time_slots()

        print(f"Загружено занятий: {len(lessons)}, аудиторий: {len(auditoriums)}, слотов: {len(time_slots)}")

        if lesson_errors or auditorium_errors:
            return {"error": f"Ошибки загрузки: {lesson_errors + auditorium_errors}"}
        if not lessons:
            return {"error": "Не найдено занятий для оптимизации. Проверьте формат файла."}
        if not auditoriums:
            return {"error": "Не найдено аудиторий для оптимизации. Проверьте формат файла."}

        if len(lessons) > MAX_LESSONS_FOR_DEMO:
            print(f"Ограничение количества занятий до {MAX_LESSONS_FOR_DEMO}")
            lessons = lessons[:MAX_LESSONS_FOR_DEMO]

        optimizer = ScheduleOptimizer(lessons, auditoriums, time_slots)

        solution = []
        fitness = float("inf")
        violations = {}
        exec_time = 0.0
        algo_used = ""

        # 🔥 ВАЖНО: Выбор алгоритма в зависимости от параметра
        if algorithm == "genetic":
            print(">>> Запуск ГЕНЕТИЧЕСКОГО АЛГОРИТМА")
            solution, fitness, violations, exec_time = optimizer.genetic_algorithm()
            algo_used = "🧬 Генетический алгоритм (ГА) - основной"

        elif algorithm == "annealing":
            print(">>> Запуск АЛГОРИТМА ИМИТАЦИИ ОТЖИГА")
            # Сначала получаем начальное решение через ГА
            base_solution, base_fitness, _, ga_time = optimizer.genetic_algorithm()
            print(f"   ГА завершен. F(X) = {base_fitness:.2f}")

            # Затем улучшаем через отжиг
            solution, fitness, violations, sa_time = optimizer.simulated_annealing(
                initial_solution=base_solution,
                max_iterations=1200
            )
            exec_time = ga_time + sa_time
            algo_used = "🌡️ Алгоритм имитации отжига (АИО) - улучшение"
            print(f"   АИО завершен. F(X) = {fitness:.2f}")

        elif algorithm == "greedy":
            print(">>> Запуск ЖАДНОГО АЛГОРИТМА")
            solution, fitness, violations, exec_time = optimizer.greedy_algorithm()
            algo_used = "⚡ Жадный алгоритм (резервный)"

        else:  # combined
            print(">>> Запуск КОМБИНИРОВАННОГО АЛГОРИТМА")
            result = optimizer.run_combined_optimization()
            best = result["best"]
            solution = best["solution"]
            fitness = best["fitness"]
            violations = best["violations"]
            exec_time = best["time_ms"]

            # Определяем, какой алгоритм дал лучший результат
            algo_used = f"🏆 Комбинированный: {best.get('algorithm_name', best['algorithm'])}"

        print(f"Результат: F(X) = {fitness:.2f}, время = {exec_time:.0f} мс, алгоритм = {algo_used}")

        if not solution:
            return {"error": "Не удалось найти решение. Попробуйте другой алгоритм или проверьте исходные данные."}

        # Создаем записи расписания
        lesson_map = {l.id: l for l in lessons}
        aud_map = {a.id: a for a in auditoriums}
        slot_map = {s.id: s for s in time_slots}

        schedule_entries = []
        for lesson_id, aud_id, slot_id, week_parity in solution:
            lesson = lesson_map.get(lesson_id)
            aud = aud_map.get(aud_id)
            slot = slot_map.get(slot_id)
            if lesson and aud and slot:
                schedule_entries.append(
                    {
                        "lesson_id": lesson.id,
                        "group": lesson.group,
                        "discipline": lesson.discipline,
                        "teacher": lesson.teacher,
                        "lesson_type": lesson.lesson_type.value,
                        "auditorium": aud.name,
                        "day": slot.day,
                        "pair_number": slot.pair_number,
                        "week_parity": week_parity,
                    }
                )

        normalized_violations = {
            key: float(value) if isinstance(value, (int, float)) else 0.0
            for key, value in violations.items()
        }

        print(f"Сформировано записей расписания: {len(schedule_entries)}")
        print(f"Отправляемый algorithm_used: {algo_used}")

        return {
            "schedule": schedule_entries,
            "fitness_score": float(fitness) if fitness != float("inf") else 999999.0,
            "algorithm_used": algo_used,  # 🔥 Отправляем правильное имя алгоритма
            "violations": normalized_violations,
            "execution_time_ms": float(exec_time),
        }

    except Exception as exc:
        print(f"❌ Ошибка при оптимизации: {exc}")
        import traceback
        traceback.print_exc()
        return {"error": f"Ошибка при оптимизации: {exc}"}
    finally:
        _safe_remove(schedule_path)
        _safe_remove(auditorium_path)