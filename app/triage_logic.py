from app.data_store import get_assessments, next_deadline_label


# Core decision logic
class TriageEngine:
    # Stores the decision tree and resource bank for reuse across requests.
    def __init__(self, decision_tree, resource_bank):
        self.decision_tree = decision_tree
        self.resource_bank = resource_bank

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

    # Assembles result page content once an outcome is reached
    def build_result(self, category, answers, outcome_id, student):
        outcome_source = self.decision_tree["routes"][category]["outcomes"][outcome_id]
        outcome = dict(outcome_source)
        selected_assessments = get_assessments(student, answers.get("selected_assessments", []))
        issue_id = outcome["issue_id"]
        resources = self._select_resources(issue_id, answers, selected_assessments)
        checklist = self._build_checklist(issue_id, answers, selected_assessments, resources)
        extra_supports = self._extra_supports(issue_id)
        return {
            "category": category,
            "issue_id": issue_id,
            "title": outcome["title"],
            "summary": outcome["summary"],
            "assessments": selected_assessments,
            "resources": resources,
            "checklist": checklist,
            "extra_supports": extra_supports,
        }

    # Filters the resource bank using issue IDs, tags, and priority scoring
    def _select_resources(self, issue_id, answers, assessments):
        issue_context = set()
        for value in answers.values():
            if isinstance(value, list):
                for item in value:
                    issue_context.add(str(item))
            else:
                issue_context.add(str(value))
        for assessment in assessments:
            issue_context.add(assessment.get("type", "").lower())
        if len(assessments) > 1:
            issue_context.add("multi_assessment")
        selected = []
        for resource in self.resource_bank["resource_bank"]:
            if issue_id not in resource.get("issue_ids", []):
                continue
            required_any = resource.get("required_any_tags", [])
            if required_any and not any(tag in issue_context for tag in required_any):
                continue
            blocked_any = resource.get("blocked_if_tags", [])
            if blocked_any and any(tag in issue_context for tag in blocked_any):
                continue
            item = dict(resource)
            score = item.get("priority", 99)
            if any(tag in issue_context for tag in item.get("boost_if_tags", [])):
                score -= 2
            item["_score"] = score
            selected.append(item)
        selected.sort(key=lambda item: (item["_score"], item.get("name", "")))
        for item in selected:
            if "_score" in item:
                del item["_score"]
        return selected[:6]

    # Builds a practical and tailored action-list
    def _build_checklist(self, issue_id, answers, assessments, resources):
        titles = []
        modules = []
        lecturers = []
        for assessment in assessments:
            titles.append(assessment.get("title", "assessment"))
            modules.append(assessment.get("module_name", "module"))
            if assessment.get("lecturer"):
                lecturers.append(assessment.get("lecturer"))
        unique_modules = list(dict.fromkeys(modules))
        unique_lecturers = list(dict.fromkeys(lecturers))
        assessment_phrase = self._assessment_text(titles)
        module_phrase = self._module_text(unique_modules)
        contact_phrase = self._contact_text(unique_lecturers)
        first_resource = None
        if resources:
            first_resource = resources[0]
        checklist = []
        if issue_id == "AI1":
            if first_resource:
                checklist.append(
                    {
                        "title": "Start with {0}".format(first_resource["name"]),
                        "detail": "This is the clearest place to begin for {0}. It should help you work out what can still be done and what to do first.".format(assessment_phrase),
                    }
                )
            checklist.append(
                {
                    "title": "Check the module page before sending a message",
                    "detail": "Open the {0} canvas home page to find the module organisers' contact details and enquire about {1}. {2} If you are still unsure who to approach, your personal tutor is also a sensible place to start.".format(
                        module_phrase, assessment_phrase, contact_phrase
                    ),
                }
            )
            checklist.append(
                {
                    "title": "Write down the basics before you contact anyone",
                    "detail": "Keep it short; which assessment is affected, the relevant deadlines, and what kind of help you are hoping for. That makes the next message much easier to send.",
                }
            )
            checklist.append(
                {
                    "title": "Open one support page before you leave this screen",
                    "detail": "Choose one option from the support options on this page and open it now, so this does not stay as a vague worry in the background.",
                }
            )
        elif issue_id == "AI2":
            if first_resource:
                checklist.append(
                    {
                        "title": "Read {0} first".format(first_resource["name"]),
                        "detail": "Start there before trying to work out every possibility at once. It is the most relevant route for what has happened with {0}.".format(assessment_phrase),
                    }
                )
            checklist.append(
                {
                    "title": "Write down what happened while it is still clear",
                    "detail": "Make a brief note of what affected {0}, when it happened, and anything you may need to explain later.".format(assessment_phrase),
                }
            )
            checklist.append(
                {
                    "title": "Check the teaching contacts linked to these modules",
                    "detail": "Start with the {0} canvas home page. {1} If you are not sure who to approach after that, your personal tutor is a reasonable place to start.".format(
                        module_phrase, contact_phrase
                    ),
                }
            )
            if answers.get("academic_setback") == "formal_decision_concern":
                checklist.append(
                    {
                        "title": "Treat formal review information carefully",
                        "detail": "Only follow an appeals route if the guidance genuinely matches your situation. It is there if needed, but it is not the default answer to every setback.",
                    }
                )
            checklist.append(
                {
                    "title": "Give yourself one clear next action, not five",
                    "detail": "After you read the main guidance page, decide on the single next thing you will do today: send a message, gather information, or complete the relevant form.",
                }
            )
        elif issue_id == "AI3":
            if first_resource:
                checklist.append(
                    {
                        "title": "Open {0}".format(first_resource["name"]),
                        "detail": "That is the best-fit support option for {0} based on what you chose.".format(assessment_phrase),
                    }
                )
            checklist.append(
                {
                    "title": "Check the assessment brief alongside the module page",
                    "detail": "Look at the brief for {0} together with the {1} page. {2} That should make it easier to work out what to ask and what support fits best.".format(
                        assessment_phrase, module_phrase, contact_phrase
                    ),
                }
            )
            checklist.append(
                {
                    "title": "Turn your worry into one clear question",
                    "detail": "If something still feels unclear, write one specific question you could ask the module teaching team or your personal tutor.",
                }
            )
            checklist.append(
                {
                    "title": "Choose one support route and act on it now",
                    "detail": "Book it, open it, or save the contact details before leaving the page. That makes it much more likely you will actually use it.",
                }
            )
        elif issue_id == "AI4":
            if first_resource:
                checklist.append(
                    {
                        "title": "Start with {0}".format(first_resource["name"]),
                        "detail": "Use the clearest career-support route first rather than trying to deal with every possible next step at once.",
                    }
                )
            checklist.append(
                {
                    "title": "Write down the next deadline or decision point",
                    "detail": "That might be an application deadline, an employer event, a placement decision, or the point where you need to choose what to focus on next.",
                }
            )
            if assessments:
                checklist.append(
                    {
                        "title": "Check what university work is being affected",
                        "detail": "List the assessment or assessments being knocked by this so you can see what needs protecting now: {0}.".format(assessment_phrase),
                    }
                )
            checklist.append(
                {
                    "title": "Separate career actions from university actions",
                    "detail": "Make one very short list for career tasks and one for university tasks. That makes it easier to see what is urgent and what can wait.",
                }
            )
            checklist.append(
                {
                    "title": "Choose one action you can complete today",
                    "detail": "For example, book guidance, update one application document, or decide which opportunity matters most this week.",
                }
            )
        elif issue_id == "WS1":
            checklist.append(
                {
                    "title": "Choose the gentlest first step",
                    "detail": "Pick the option that feels easiest to manage today. You do not need to tackle everything at once.",
                }
            )
            checklist.append(
                {
                    "title": "Give yourself permission to come back for more support",
                    "detail": "If things start to feel heavier, you can move on to a more direct support option. Starting small does not lock you into staying small.",
                }
            )
        elif issue_id == "WS2":
            checklist.append(
                {
                    "title": "Choose one direct support route today",
                    "detail": "The aim is to make one real contact point, not to research every option perfectly.",
                }
            )
            checklist.append(
                {
                    "title": "Let academic staff know if study is being affected",
                    "detail": "If this is affecting deadlines, attendance, or concentration, your personal tutor or module team may need a brief heads-up once you feel able.",
                }
            )
        elif issue_id == "WS3":
            checklist.append(
                {
                    "title": "Use urgent support now",
                    "detail": "What you described sounds serious enough that urgent support should come first. Go straight to the urgent help options on this page now.",
                }
            )
            checklist.append(
                {
                    "title": "Use emergency help if you are in immediate danger",
                    "detail": "If you feel unable to keep yourself safe right now, call 999 or go to A&E immediately.",
                }
            )
        if not checklist and first_resource:
            checklist.append(
                {
                    "title": "Start with {0}".format(first_resource["name"]),
                    "detail": "This is the clearest first step based on what you selected.",
                }
            )
        return checklist

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

    # Adds a small wellbeing nudge to academic outcomes where wider stress may also matter
    def _extra_supports(self, issue_id):
        if not issue_id.startswith("AI"):
            return []
        extras = []
        for resource in self.resource_bank.get("resource_bank", []):
            if resource.get("id") in {"R12", "R11", "R9"}:
                extras.append(
                    {
                        "id": resource["id"],
                        "name": resource["name"],
                        "description": resource["description"],
                        "link": resource["link"],
                        "priority": resource.get("priority", 99),
                    }
                )
        extras.sort(key=lambda item: (item["priority"], item["name"]))
        for item in extras:
            del item["priority"]
        return extras

    # Blends lecturer lists into the checklist sentences
    def _contact_text(self, lecturers):
        if not lecturers:
            return "The module page should also list the teaching contacts for you."
        if len(lecturers) == 1:
            return "The teaching contact shown for this module is {0}.".format(lecturers[0])
        if len(lecturers) == 2:
            return "The teaching contacts shown here are {0} and {1}.".format(lecturers[0], lecturers[1])
        return "The teaching contacts shown here include {0}, and {1}.".format(", ".join(lecturers[:-1]), lecturers[-1])

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

    # Joins assessment titles into a short phrase
    def _assessment_text(self, titles):
        if not titles:
            return "your selected assessment"
        if len(titles) == 1:
            return titles[0]
        if len(titles) == 2:
            return "{0} and {1}".format(titles[0], titles[1])
        return "{0}, and {1}".format(", ".join(titles[:-1]), titles[-1])

    # Joins module names into a short phrase
    def _module_text(self, modules):
        if not modules:
            return "module"
        if len(modules) == 1:
            return modules[0]
        if len(modules) == 2:
            return "{0} and {1}".format(modules[0], modules[1])
        return "{0}, and {1}".format(", ".join(modules[:-1]), modules[-1])

    # Extracts the assessment types from the selected items
    def _assessment_types(self, assessments):
        return {assessment.get("type", "").lower() for assessment in assessments if assessment.get("type")}

    # Treats coursework as submission-based assessments for wording purposes
    def _is_submission(self, assessment_type):
        return assessment_type in {"coursework", "essay", "report", "project", "portfolio", "presentation"}

    # Treats exams and tests as timed assessments
    def _is_timed(self, assessment_type):
        return assessment_type in {"exam", "test"}
