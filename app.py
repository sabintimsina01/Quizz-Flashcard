from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import json
import random
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ✅ Session config
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session_data'
Session(app)

quiz_data = []



@app.route("/start", methods=["GET", "POST"])
def start():
    if request.method == "POST":
        selected_category = request.form.get("category")

        with open('questions.json') as f:
            all_questions = json.load(f)

        filtered = [q for q in all_questions if q.get("category") == selected_category]

        if not filtered:
            return "No questions found for selected category.", 400

        random.shuffle(filtered)

        global quiz_data
        quiz_data = filtered

        session['current_q'] = 0
        session['score'] = 0
        session['feedback'] = None
        session['start_time'] = datetime.now().isoformat()
        session['category'] = selected_category
        session['question_start_time'] = datetime.now().isoformat()

        return redirect(url_for('index'))

    with open('questions.json') as f:
        data = json.load(f)

    categories = sorted(set(q.get("category", "General") for q in data))

    return render_template("start.html", categories=categories)

@app.route("/")
def index():
    global quiz_data

    if session.get('current_q') is None:
        return redirect(url_for('start'))

    current_index = session.get('current_q', 0)

    if current_index >= len(quiz_data):
        return redirect(url_for('result'))

    question = quiz_data[current_index]
    feedback = session.get('feedback')

    return render_template(
        "index.html",
        question=question,
        q_number=current_index + 1,
        feedback=feedback
    )

@app.route("/submit", methods=["POST"])
def submit():
    global quiz_data

    current_index = session.get('current_q', 0)

    if current_index >= len(quiz_data):
        return redirect(url_for('result'))

    # ⏱ Time tracking per question
    start_str = session.get('question_start_time')
    time_spent = 0
    if start_str:
        start = datetime.fromisoformat(start_str)
        time_spent = (datetime.now() - start).seconds

    selected = request.form.get("option")
    correct_answer = quiz_data[current_index]["answer"]
    explanation = quiz_data[current_index].get("explanation", "No explanation provided.")

    if time_spent > 30:
        selected = "No answer (timed out)"
        result = "incorrect"
    elif selected == correct_answer:
        session['score'] += 1
        result = "correct"
    else:
        result = "incorrect"

    session['feedback'] = {
        "selected": selected,
        "correct": correct_answer,
        "result": result,
        "explanation": explanation
    }

    session[f'q{current_index}'] = {
        "selected": selected,
        "correct": correct_answer,
        "result": result,
        "explanation": explanation,
        "time_spent": time_spent
    }

    return redirect(url_for("index"))

@app.route("/next")
def next_question():
    session['current_q'] += 1
    session['feedback'] = None
    session['question_start_time'] = datetime.now().isoformat()
    return redirect(url_for("index"))

@app.route("/result")
def result():
    score = session.get('score', 0)
    total = len(quiz_data)

    # ✅ Time tracking
    start_time_str = session.get('start_time')
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
        time_taken = datetime.now() - start_time
        minutes, seconds = divmod(time_taken.seconds, 60)
        time_display = f"{minutes} min {seconds} sec" if minutes else f"{seconds} sec"
    else:
        time_display = "Unknown"

    # ✅ Missed questions
    missed_questions = []
    for i in range(total):
        entry = session.get(f'q{i}')
        if entry and entry['result'] != 'correct':
            missed_questions.append(entry)

    percentage = (score / total) * 100 if total > 0 else 0
    status = "PASS" if percentage >= 70 else "FAIL"

    # ✅ Render first, then clear session
    response = render_template(
        "result.html",
        score=score,
        total=total,
        percentage=percentage,
        status=status,
        time_display=time_display,
        missed=missed_questions
    )

    session.clear()
    return response
