from app.data_store import get_assessments, next_deadline_label


# Core decision logic
class TriageEngine:
    # Stores the decision tree and resource bank for reuse across requests.
    def __init__(self, decision_tree):
        self.decision_tree = decision_tree

    # Returns the first question node
    def first_node(self, category):
        return self.decision_tree["routes"][category]["start_node"]

    # Builds current node, including dynamic assessment options and wording tweaks
    def get_node(self, category, node_id, student, answers=None):
        base_node = self.decision_tree["routes"][category]["nodes"][node_id]
        node = dict(base_node)
        answers = answers or {}
        selected_assessments = get_assessments(student, answers.get("selected_assessments", []))
        if node.get("type") == "assessment_select":
            node["options"] = []
            for assessment in student.get("assessments", []):
                node["options"].append(
                    {
                        "value": assessment["assessment_id"],
                        "label": self._assessment_label(assessment),
                        "next": node.get("next"),
                    }
                )
        if category == "academic" and node_id == "academic_setback":
            node = self._setback_node(node, selected_assessments)
        elif category == "academic" and node_id == "academic_prevent_step":
            node = self._prevent_step_node(node, selected_assessments)
        return node

    # Reads submitted answer and finds the next node
    def next_from_answer(self, category, node_id, answer_value):
        node = self.decision_tree["routes"][category]["nodes"][node_id]
        if node.get("type") == "assessment_select":
            return node["next"]
        options = {}
        for option in node["options"]:
            options[option["value"]] = option
        if answer_value not in options:
            raise ValueError("Unknown answer value")
        return options[answer_value]["next"]

    # Checks whether the next node is a leaf or not
    def is_outcome(self, category, node_id):
        return node_id in self.decision_tree["routes"][category]["outcomes"]

    def build_result(self, category, answers, outcome_id, student):
        outcome_source = self.decision_tree["routes"][category]["outcomes"][outcome_id]
        outcome = dict(outcome_source)
        selected_assessments = get_assessments(student, answers.get("selected_assessments", []))
        issue_id = outcome["issue_id"]
        return {
            "category": category,
            "issue_id": issue_id,
            "title": outcome["title"],
            "summary": outcome["summary"],
            "assessments": selected_assessments,
            "resources": [],
            "checklist": [],
            "extra_supports": [],
        }

    # Adjusts the setback question so its wording matches the selected assessment types
    def _setback_node(self, node, assessments):
        assessment_types = self._assessment_types(assessments)
        has_submission = any(self._is_submission(item) for item in assessment_types)
        has_timed = any(self._is_timed(item) for item in assessment_types)
        if assessment_types and has_submission and not has_timed:
            node["title"] = "What best describes what has happened with this work?"
            node["text"] = "Choose the closest fit for the selected coursework or submitted work."
        elif assessment_types and has_timed and not has_submission:
            node["title"] = "What best describes what has happened with this exam or test?"
            node["text"] = "Choose the closest fit for the selected timed assessment."
        else:
            node["title"] = "What best describes what has happened?"
            node["text"] = "Choose the closest fit so we can point you to the most relevant next step."
        options = []
        if not assessment_types or has_submission:
            options.append(
                {
                    "value": "missed_submission",
                    "label": "I missed a submission deadline or I know I will miss it.",
                    "next": "academic_route_ai2",
                }
            )
        if not assessment_types or has_timed:
            options.append(
                {
                    "value": "missed_exam",
                    "label": "I missed an exam or test, or it was badly affected by serious circumstances.",
                    "next": "academic_route_ai2",
                }
            )
        options.append(
            {
                "value": "formal_decision_concern",
                "label": "I already have a decision or result and I think there may be grounds to question it.",
                "next": "academic_route_ai2",
            }
        )
        node["options"] = options
        return node

    # Adjusts the preventive support question so timed assessments and coursework read differently
    def _prevent_step_node(self, node, assessments):
        assessment_types = self._assessment_types(assessments)
        has_submission = any(self._is_submission(item) for item in assessment_types)
        has_timed = any(self._is_timed(item) for item in assessment_types)
        if assessment_types and has_timed and not has_submission:
            node["title"] = "What would help most before this gets harder to manage?"
            node["text"] = "Pick the kind of help that would make the next step clearer for the selected exam or test."
            node["options"] = [
                {
                    "value": "need_more_time",
                    "label": "I need to understand what to do if I may not be able to sit it as planned.",
                    "next": "academic_route_ai1",
                },
                {
                    "value": "need_clear_process",
                    "label": "I need clear guidance on what I should do before the date gets closer.",
                    "next": "academic_route_ai1",
                },
                {
                    "value": "need_study_support",
                    "label": "I need practical revision or preparation support so I can get back on track.",
                    "next": "academic_route_ai3",
                },
            ]
        else:
            node["title"] = "What would help most right now?"
            node["text"] = "Pick the kind of help that would make the next step clearer."
            node["options"] = [
                {
                    "value": "need_more_time",
                    "label": "I need to understand whether I can ask for more time.",
                    "next": "academic_route_ai1",
                },
                {
                    "value": "need_clear_process",
                    "label": "I need clear guidance on what I should do before the deadline gets closer.",
                    "next": "academic_route_ai1",
                },
                {
                    "value": "need_study_support",
                    "label": "I need practical study or revision support so I can get back on track.",
                    "next": "academic_route_ai3",
                },
            ]
        return node

    # Formats one assessment to an option in the multi-select list
    def _assessment_label(self, assessment):
        type_label = assessment.get("type", "assessment").replace("_", " ")
        due_label = next_deadline_label(assessment) or "date not listed"
        return "{0} — {1} ({2}, due {3})".format(
            assessment["module_name"],
            assessment["title"],
            type_label,
            due_label,
        )

    # Extracts the assessment types from the selected items
    def _assessment_types(self, assessments):
        return {assessment.get("type", "").lower() for assessment in assessments if assessment.get("type")}

    # Treats coursework as submission-based assessments for wording purposes
    def _is_submission(self, assessment_type):
        return assessment_type in {"coursework", "essay", "report", "project", "portfolio", "presentation"}

    # Treats exams and tests as timed assessments
    def _is_timed(self, assessment_type):
        return assessment_type in {"exam", "test"}
