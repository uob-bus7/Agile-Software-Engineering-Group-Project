# Student Support Triage and Signposting Tool

BUS7 coursework repository for the **Student Support Triage and Signposting Tool**.


## Current prototype scope

- student ID lookup using dummy student data
- short guided issue capture under two main facets: academic and wellbeing
- classification to a suggested support path


## Run locally

This prototype runs as a small Flask application. For a fuller Windows/PyCharm setup guide, including virtual environment creation, activation, dependency installation, troubleshooting, and `flask run`, see [PyCharm virtual environment setup and troubleshooting (Windows only)](docs/PyCharm%20Virtual%20Environment%20Setup%20&%20Troubleshooting%20(Windows%20only).md).

A minimal run path is:

```bash
python -m venv .venv
# activate the environment
pip install -r requirements.txt
flask run
```


## Structure

* `app/__init__.py` creates the Flask app
* `app/routes.py` handles the page flow
* `app/triage_logic.py` handles tree progression and recommendation logic
* `app/data/decision_tree.json` contains the question tree and outcome copy
* `app/data/dummy_student_data.py` contains the student dataset
