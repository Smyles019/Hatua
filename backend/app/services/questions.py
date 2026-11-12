"""Questions as the caregiver sees them, and how answers are coded.

ECDI2030 (24 to 59 months): wording follows the KDHS 2022 variable labels for
ecd21..ecd40. Answers are coded exactly as hatua_ml.features.ecdi2030.harmonise does for
DHS data: 1 achieved, 0 not achieved, None don't know (scored as not achieved by the model).

Under-24 model (0 to 23 months): Dutch Development Instrument items, reworded for
caregivers. Same yes / no / don't know coding; don't know is left blank for this model.

WHO gross motor milestones (4 to 23 months, fallback when the under-24 model is not
available): plain-language versions of the WHO Motor Development Study definitions
(hatua_ml.norms.who_motor). Same yes / no / don't know coding.
"""

from app.services.growth import GROWTH_FLAGS
from app.services.i18n import tr

YES_NO = [("yes", "Yes", 1), ("no", "No", 0), ("dont_know", "Don't know", None)]

# ecd39: achieved if "a few times a year" or "never"
SAD = [("daily", "Daily", 0), ("weekly", "Weekly", 0), ("monthly", "Monthly", 0),
       ("few_times_year", "A few times a year", 1), ("never", "Never", 1),
       ("dont_know", "Don't know", None)]

# ecd40 (DHS coding): achieved if "not at all" or "the same or less"
HITS = [("not_at_all", "Not at all", 1), ("same_or_less", "The same or less", 1),
        ("more", "More", 0), ("a_lot_more", "A lot more", 0),
        ("dont_know", "Don't know", None)]


def _q(text: str, short: str, options=YES_NO, hint: str | None = None) -> dict:
    """text: the question, kept short. hint: an optional example or how to try it, shown in
    smaller type under the question, so the question itself stays easy to read."""
    return {"text": text, "short": short, "options": options, "hint": hint}


QUESTIONS = {
    # Kept short: the example sits in the hint. Every number and the meaning of each KDHS
    # item stay as they were.
    "ecd21": _q("Can {name} walk on bumpy or hilly ground without falling?",
                "walking on uneven ground"),
    "ecd22": _q("Can {name} jump with both feet off the ground?", "jumping with both feet"),
    "ecd23": _q("Can {name} put on trousers and a shirt without help?", "dressing without help"),
    "ecd24": _q("Can {name} do and undo buttons without help?", "doing buttons"),
    "ecd25": _q("Can {name} say 10 or more words?", "saying 10 or more words",
                hint="Like 'mama' or 'ball'."),
    "ecd26": _q("Does {name} speak in sentences of 3 or more words?", "3-word sentences",
                hint="Words that go together, like 'I want water'."),
    "ecd27": _q("Does {name} speak in sentences of 5 or more words?", "5-word sentences",
                hint="Words that go together."),
    "ecd28": _q("Does {name} use 'I', 'you', 'she' or 'he' correctly?", "using I, you, she, he"),
    "ecd29": _q("Can {name} always name things they know well?", "naming familiar objects",
                hint="When you show them, like a cup or an animal."),
    "ecd30": _q("Can {name} recognise at least 5 letters of the alphabet?", "recognising letters"),
    "ecd31": _q("Can {name} write their own name?", "writing their name"),
    "ecd32": _q("Can {name} recognise all the numbers from 1 to 5?", "recognising numbers 1 to 5"),
    "ecd33": _q("If you ask for 3 things, does {name} give you exactly 3?", "giving 3 objects",
                hint="Like 3 stones or 3 beans."),
    "ecd34": _q("Can {name} count 10 things without mistakes?", "counting 10 objects"),
    "ecd35": _q("Can {name} colour or build with blocks without giving up?",
                "playing on their own without giving up",
                hint="Without asking for help again and again."),
    "ecd36": _q("Does {name} ask about people they know when those people are away?",
                "asking about familiar people", hint="Other than their parents."),
    "ecd37": _q("Does {name} offer to help someone who needs it?", "offering to help"),
    "ecd38": _q("Does {name} get along well with other children?", "getting along with others"),
    "ecd39": _q("How often does {name} seem very sad or depressed?", "mood", SAD),
    "ecd40": _q("Compared with children the same age, how much does {name} kick, bite or "
                "hit others?", "kicking, biting or hitting", HITS),

    # WHO gross motor milestones, under 24 months
    "who_sit": _q("Can {name} sit up straight without support for 10 seconds?",
                  "sitting without support"),
    "who_stand_assist": _q("Can {name} stand while holding on to furniture or a person?",
                           "standing while holding on"),
    "who_crawl": _q("Can {name} crawl forwards on hands and knees?", "crawling on hands and knees"),
    "who_walk_assist": _q("Can {name} take steps while holding on to furniture or a person?",
                          "walking while holding on"),
    "who_stand_alone": _q("Can {name} stand without holding on for 10 seconds?",
                          "standing alone"),
    "who_walk_alone": _q("Can {name} take 5 or more steps without holding on?", "walking alone"),

    # Under-24 model questions: Dutch Development Instrument (Van Wiechen) items used by
    # the short-form model (hatua_ml.models.train_under2). Reworded for caregivers to
    # answer from what they see at home; the clinic version is in
    # ml/src/hatua_ml/features/ddi_items.csv. Language items come first, then movement.
    #
    # Where the MOH Mother and Child Health Handbook (2020, Developmental Milestones table)
    # has the same milestone, the wording and examples follow the handbook. The meaning of
    # each item, and any number in it, stays that of the DDI item the model was trained on.
    "ddicmm030": _q("Does {name} smile when you speak to them?", "smiling back"),
    # Turning towards a sound (the DDI item). Kept apart from the hearing red flag
    # rf_hearing, which asks about any reaction to sound.
    "ddicmd116": _q("Does {name} turn their head towards a sound?", "turning to sounds",
                    hint="Like a rattle or your voice beside them."),
    "ddicmm034": _q("Does {name} babble, repeating sounds?", "babbling while playing",
                    hint="Like 'bababa' or 'mamama' while playing."),
    "ddicmd136": _q("Does {name} do simple things when you ask?", "reacting to simple requests",
                    hint="Like 'clap hands' or 'wave bye'."),
    "ddicmm037": _q("Does {name} use two words that mean something?", "using two words",
                    hint="Like 'mama' and 'water'."),
    "ddicmm039": _q("Does {name} say at least 3 words?", "saying three words",
                    hint="Even if not said perfectly."),
    "ddicmd141": _q("Can {name} point to two things you name?", "showing two named objects",
                    hint="Things they know, like a cup and a ball."),
    "ddifmd001": _q("Does {name} look at your face for a moment?", "looking at faces"),
    "ddifmd002": _q("Do {name}'s eyes follow your face or a toy as it moves?",
                    "following with the eyes", hint="Move it slowly to one side."),
    "ddifmm004": _q("Does {name} look at and watch their own hands?", "watching own hands"),
    "ddigmd006": _q("Does {name} reach for a toy and grasp it?", "reaching for toys"),
    "ddifmd007": _q("Can {name} move a toy from one hand to the other?",
                    "passing a toy between hands"),
    "ddifmd008": _q("Can {name} hold a toy in each hand?", "holding two toys",
                    hint="Picking up a second toy while holding the first."),
    "ddifmm009": _q("Does {name} play with their feet?", "playing with feet",
                    hint="Like grabbing or holding them."),
    "ddifmd010": _q("Can {name} pick up something very small with two fingers?",
                    "picking up small things", hint="Like a bean or a piece of string."),
    "ddifmm012": _q("Does {name} play 'give and take' with you?", "playing give and take",
                    hint="Handing you a toy and taking it back."),
    "ddifmd013": _q("Can {name} put one block on top of another?", "stacking two blocks",
                    hint="Or a small box, so it stays."),
    "ddifmd017": _q("Can {name} build a tower of six blocks or small boxes?",
                    "stacking six blocks"),
    "ddigmd055": _q("When you pull {name} up to sitting, do they hold their head up?",
                    "holding up the head",
                    hint="Gently, by the hands. The head should not fall back."),
    "ddigmd057": _q("Lying on their tummy, can {name} lift their head?",
                    "lifting the head on the tummy"),
    "ddigmd058": _q("Lying on their tummy, can {name} hold their head up and look around?",
                    "looking around on the tummy"),
    "ddigmm060": _q("Can {name} roll over from their back onto their tummy?", "rolling over"),
    "ddigmd062": _q("Can {name} sit with legs out in front and back straight?",
                    "sitting with legs out"),
    "ddigmd063": _q("Can {name} sit steadily without support?", "sitting without support"),
    "ddigmm064": _q("Can {name} move forward on their tummy, pulling with their arms?",
                    "creeping on the tummy"),
    "ddigmm066": _q("Can {name} crawl on hands and knees, tummy off the floor?",
                    "crawling on hands and knees"),
    "ddigmm065": _q("Can {name} pull up to standing by holding on to something?",
                    "pulling up to stand"),
    "ddigmm067": _q("Can {name} take steps while holding on to furniture?", "walking holding on"),
    "ddigmd068": _q("Can {name} walk without holding on to anything?", "walking alone"),
    "ddigmd070": _q("Can {name} bend down to pick something up, then stand again?",
                    "squatting to pick things up"),
}


# ---- Hearing and vision red flags ----
#
# Borrowed from the eye checks in the MOH Mother and Child Health Handbook, plus one
# hearing question. They are a rule, not a prediction: they are asked after the model's
# questions, never go into the model, and a "No" sends the result to the CHW whatever
# the model said. Every question is worded so that "Yes" is the reassuring answer.
# (text, kind, from age in months, what the CHW reads when the answer is "No")
RED_FLAGS = {
    "rf_hearing": ("Does {name} react to sounds?",
                   "hearing", 0, "Does not seem to react to sounds"),
    "rf_pupil": ("Is the dark centre of each eye black, with no white or grey spot?",
                 "vision", 0, "White or grey spot seen in the centre of an eye"),
    "rf_sight": ("Does {name} look at your face or follow a moving toy with their eyes?",
                 "vision", 3, "Does not look at faces or follow objects"),
    "rf_eyes_straight": ("Do {name}'s eyes look straight and move together?",
                         "vision", 6, "One eye seems to turn in or out (squint)"),
}
# The example under each red-flag question, as for the model's questions.
RED_FLAG_HINTS = {
    "rf_hearing": "Like turning or going quiet when you speak, or startling at a loud noise.",
    "rf_eyes_straight": "Neither eye turns in or out.",
}
RED_FLAG_KINDS = {"hearing": "Hearing", "vision": "Eyes and seeing", "growth": "Growth"}


def red_flag_items(age_months: int) -> list[str]:
    return [i for i, (_t, _k, from_age, _l) in RED_FLAGS.items() if age_months >= from_age]


def red_flag_questions(age_months: int, lang: str = "en") -> list[dict]:
    return [{"item": i, "text": tr(RED_FLAGS[i][0], lang), "hint": tr(RED_FLAG_HINTS.get(i), lang),
             "screening": RED_FLAGS[i][1],
             "options": [{"value": k, "label": tr(label, lang)} for k, label, _ in YES_NO]}
            for i in red_flag_items(age_months)]


def raised_red_flags(answers: dict[str, str]) -> list[str]:
    """Ids of the red-flag questions answered "no". Raises ValueError for an answer that
    is not yes / no / dont_know. "Don't know" raises no flag."""
    raised = []
    for item, answer in answers.items():
        if answer not in ("yes", "no", "dont_know"):
            raise ValueError(f"{item}: '{answer}' is not a valid answer")
        if answer == "no":
            raised.append(item)
    return raised


def describe_red_flags(ids: list[str], lang: str = "en") -> list[dict]:
    """Hearing and vision flags (from answers) and growth flags (from weight and height)."""
    out = []
    for i in ids:
        if i in RED_FLAGS:
            kind, label = RED_FLAGS[i][1], RED_FLAGS[i][3]
        elif i in GROWTH_FLAGS:
            kind, label = "growth", GROWTH_FLAGS[i]
        else:
            continue
        out.append({"flag": i, "kind": kind, "kind_label": tr(RED_FLAG_KINDS[kind], lang),
                    "label": tr(label, lang)})
    return out


def code(item: str, answer: str) -> float | None:
    """Raise ValueError for an answer that is not one of the item's options."""
    for key, _label, value in QUESTIONS[item]["options"]:
        if key == answer:
            return value
    raise ValueError(f"{item}: '{answer}' is not a valid answer")


def questionnaire(items: list[str], lang: str = "en") -> list[dict]:
    return [{"item": i, "text": tr(QUESTIONS[i]["text"], lang), "hint": tr(QUESTIONS[i]["hint"], lang),
             "options": [{"value": k, "label": tr(label, lang)}
                         for k, label, _ in QUESTIONS[i]["options"]]}
            for i in items]


def short_label(item: str, fallback: str, lang: str = "en") -> str:
    """The few-word name of a question ("walking alone"), for result reasons."""
    return tr(QUESTIONS[item]["short"], lang) if item in QUESTIONS else fallback
