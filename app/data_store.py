import json
import os
from datetime import datetime
from app.data.dummy_student_data import dummy_student_data


# The folder that stores the JSON files
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# To simplify JSON file extraction going forward
def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

# Load the decision-tree structure that controls the question flow.
def load_decision_tree():
    return _load_json("decision_tree.json")

# Load the compiled resource bank used for recommendations and signposting.
def load_resource_bank():
    return _load_json("resource_bank.json")


# Fetch a specified student record and flatten its module deadlines.
def get_student(student_id):
    if not student_id:
        return None
    student_id = student_id.upper()
    student = dummy_student_data.get("students", {}).get(student_id)
    if student is None:
        return None
    data = dict(student)
    data["student_id"] = student_id
    data["assessments"] = flatten_assessments(data)
    return data


# Unpack the nested module/deadline structure into a sorted list of assessments.
def flatten_assessments(student):
    assessments = []
    for module_code, module in student.get("modules", {}).items():
        deadline = module.get("deadline")
        if not deadline:
            continue
        assessments.append(
            {
                "assessment_id": module_code,
                "module_code": module_code,
                "module_name": module.get("module_name", module_code),
                "lecturer": module.get("lecturer", ""),
                "title": deadline.get("title", "Assessment"),
                "type": deadline.get("type", "assessment"),
                "due_date": deadline.get("due_date", ""),
            }
        )
    assessments.sort(key=lambda item: _parse_date(item.get("due_date", "")) or datetime.max)
    return assessments


# Return the selected assessments in the same order the user chose them.
def get_assessments(student, assessment_ids):
    lookup = {}
    for assessment in student.get("assessments", []):
        lookup[assessment.get("assessment_id")] = assessment
    selected = []
    for assessment_id in assessment_ids:
        if assessment_id in lookup:
            selected.append(lookup[assessment_id])
    return selected


# Format deadlines and create a readable label.
def next_deadline_label(assessment):
    if not assessment:
        return None
    due_date = assessment.get("due_date")
    if not due_date:
        return None
    try:
        parsed = datetime.strptime(due_date, "%d-%m-%Y")
        return parsed.strftime("%d %B %Y")
    except ValueError:
        return due_date


# Parse date formats to sort the assessments.
def _parse_date(value):
    if not value:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None
