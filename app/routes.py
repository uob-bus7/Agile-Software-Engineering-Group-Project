from flask import redirect, render_template, request, session, url_for
from app import app
from app.data_store import get_student, load_decision_tree, load_resource_bank
from app.triage_logic import TriageEngine


# Load static app content so it can be reused across requests.
decision_tree = load_decision_tree()
resource_bank = load_resource_bank()
triage_engine = TriageEngine(decision_tree, resource_bank)


# Remove all saved flow data if user restarts/session becomes invalid.
def _clear_flow():
    session.pop("student_id", None)
    session.pop("category", None)
    session.pop("current_node", None)
    session.pop("answers", None)
    session.pop("outcome_id", None)
    session.pop("history", None)


# Keep answers that belong to the active path after moving backwards.
def _prune_answers(category, answers, history, current_node):
    route_nodes = decision_tree["routes"].get(category, {}).get("nodes", {})
    keep_node_ids = set(history)
    if current_node:
        keep_node_ids.add(current_node)
    pruned = {}
    for key, value in answers.items():
        if key == "selected_assessments":
            continue
        if key in keep_node_ids:
            pruned[key] = value
    selected_assessments = []
    ordered_nodes = list(history)
    if current_node:
        ordered_nodes.append(current_node)
    for node_id in ordered_nodes:
        node = route_nodes.get(node_id, {})
        if node.get("type") == "assessment_select" and node_id in pruned:
            selected_assessments = pruned[node_id]
    if selected_assessments:
        pruned["selected_assessments"] = selected_assessments
    return pruned


# Show landing page and start a new triage session after form submission.
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        category = request.form.get("category", "").strip()
        student = get_student(student_id)
        error_message = None
        if not student_id or not category:
            error_message = "Please enter your student ID and choose the kind of help that feels closest to your situation."
        elif student is None:
            error_message = "We could not find a record for that student ID."
        if error_message:
            return render_template("index.html", tree=decision_tree, error_message=error_message, form_values=request.form)
        _clear_flow()
        session["student_id"] = student_id
        session["category"] = category
        session["answers"] = {}
        session["history"] = []
        session["current_node"] = triage_engine.first_node(category)
        return redirect(url_for("question"))

    return render_template("index.html", tree=decision_tree, error_message=None, form_values={})


# Show current question, validate answer, and move to next node.
@app.route("/question", methods=["GET", "POST"])
def question():
    student_id = session.get("student_id", "")
    category = session.get("category", "")
    current_node = session.get("current_node", "")
    answers = session.get("answers", {})
    history = session.get("history", [])
    student = get_student(student_id)
    if student is None or category not in decision_tree["routes"] or not current_node:
        _clear_flow()
        return redirect(url_for("index"))
    node = triage_engine.get_node(category, current_node, student, answers)
    if request.method == "POST":
        if node.get("type") == "assessment_select":
            selected_answers = request.form.getlist("selected_answers")
            if not selected_answers:
                return render_template(
                    "question.html",
                    tree=decision_tree,
                    student=student,
                    category=category,
                    node=node,
                    error_message="Please choose at least one assessment before continuing.",
                    selected_values=[],
                    selected_value="",
                    can_go_back=bool(history),
                )
            answers[current_node] = selected_answers
            answers["selected_assessments"] = selected_answers
            session["answers"] = answers
            next_node = triage_engine.next_from_answer(category, current_node, selected_answers)
        else:
            selected_answer = request.form.get("selected_answer", "").strip()
            if not selected_answer:
                return render_template(
                    "question.html",
                    tree=decision_tree,
                    student=student,
                    category=category,
                    node=node,
                    error_message="Please choose the option that feels closest before continuing.",
                    selected_values=[],
                    selected_value="",
                    can_go_back=bool(history),
                )
            answers[current_node] = selected_answer
            session["answers"] = answers
            next_node = triage_engine.next_from_answer(category, current_node, selected_answer)
        new_history = list(history)
        if not new_history or new_history[-1] != current_node:
            new_history.append(current_node)
        session["history"] = new_history
        if triage_engine.is_outcome(category, next_node):
            session["outcome_id"] = next_node
            return redirect(url_for("results"))
        session.pop("outcome_id", None)
        session["current_node"] = next_node
        return redirect(url_for("question"))
    selected_values = []
    selected_value = ""
    if node.get("type") == "assessment_select":
        selected_values = answers.get(current_node, answers.get("selected_assessments", []))
    else:
        selected_value = answers.get(current_node, "")
    return render_template(
        "question.html",
        tree=decision_tree,
        student=student,
        category=category,
        node=node,
        error_message=None,
        selected_values=selected_values,
        selected_value=selected_value,
        can_go_back=bool(history),
    )


# Build and display the final page.
@app.route("/results", methods=["GET"])
def results():
    student_id = session.get("student_id", "")
    category = session.get("category", "")
    outcome_id = session.get("outcome_id", "")
    answers = session.get("answers", {})
    history = session.get("history", [])
    student = get_student(student_id)
    if student is None or category not in decision_tree["routes"] or not outcome_id:
        _clear_flow()
        return redirect(url_for("index"))
    result = triage_engine.build_result(category=category, answers=answers, outcome_id=outcome_id, student=student)
    return render_template(
        "results.html",
        tree=decision_tree,
        student=student,
        result=result,
        can_go_back=bool(history or session.get("current_node")),
    )


# "Previous Question" button
@app.route("/previous")
def previous_question():
    student_id = session.get("student_id", "")
    category = session.get("category", "")
    current_node = session.get("current_node", "")
    answers = session.get("answers", {})
    history = session.get("history", [])
    if not student_id or category not in decision_tree["routes"] or not current_node:
        _clear_flow()
        return redirect(url_for("index"))
    if session.get("outcome_id"):
        session.pop("outcome_id", None)
        return redirect(url_for("question"))
    if not history:
        return redirect(url_for("question"))
    previous_node = history[-1]
    new_history = history[:-1]
    session["history"] = new_history
    session["current_node"] = previous_node
    session["answers"] = _prune_answers(category, answers, new_history, previous_node)
    session.pop("outcome_id", None)
    return redirect(url_for("question"))


# "Start Again" button
@app.route("/restart")
def restart():
    _clear_flow()
    return redirect(url_for("index"))
