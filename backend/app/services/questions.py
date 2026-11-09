"""Questions as the caregiver sees them, and how answers are coded.

ECDI2030 (24 to 59 months): wording follows the KDHS 2022 variable labels for
ecd21..ecd40. Answers are coded exactly as hatua_ml.features.ecdi2030.harmonise does for
DHS data: 1 achieved, 0 not achieved, None don't know (scored as not achieved by the model).

WHO gross motor milestones (4 to 23 months): plain-language versions of the WHO Motor
Development Study definitions (hatua_ml.norms.who_motor). Same yes / no / don't know coding.
"""

YES_NO = [("yes", "Yes", 1), ("no", "No", 0), ("dont_know", "Don't know", None)]

# ecd39: achieved if "a few times a year" or "never"
SAD = [("daily", "Daily", 0), ("weekly", "Weekly", 0), ("monthly", "Monthly", 0),
       ("few_times_year", "A few times a year", 1), ("never", "Never", 1),
       ("dont_know", "Don't know", None)]

# ecd40 (DHS coding): achieved if "not at all" or "the same or less"
HITS = [("not_at_all", "Not at all", 1), ("same_or_less", "The same or less", 1),
        ("more", "More", 0), ("a_lot_more", "A lot more", 0),
        ("dont_know", "Don't know", None)]


def _q(text: str, short: str, options=YES_NO) -> dict:
    return {"text": text, "short": short, "options": options}


QUESTIONS = {
    "ecd21": _q("Can {name} walk on an uneven surface, like bumpy or hilly ground, without falling?",
                "walking on uneven ground"),
    "ecd22": _q("Can {name} jump up with both feet leaving the ground?", "jumping with both feet"),
    "ecd23": _q("Can {name} put on trousers and a shirt without help?", "dressing without help"),
    "ecd24": _q("Can {name} fasten and unfasten buttons without help?", "doing buttons"),
    "ecd25": _q("Can {name} say 10 or more words, like 'mama' or 'ball'?", "saying 10 or more words"),
    "ecd26": _q("Can {name} speak using sentences of 3 or more words that go together?",
                "3-word sentences"),
    "ecd27": _q("Can {name} speak using sentences of 5 or more words that go together?",
                "5-word sentences"),
    "ecd28": _q("Can {name} correctly use any of the words 'I', 'you', 'she' or 'he'?",
                "using I, you, she, he"),
    "ecd29": _q("If you show {name} an object they know well, like a cup or an animal, "
                "can they always name it?", "naming familiar objects"),
    "ecd30": _q("Can {name} recognise at least 5 letters of the alphabet?", "recognising letters"),
    "ecd31": _q("Can {name} write their own name?", "writing their name"),
    "ecd32": _q("Can {name} recognise all the numbers from 1 to 5?", "recognising numbers 1 to 5"),
    "ecd33": _q("If you ask {name} to give you 3 objects, like 3 stones or 3 beans, "
                "do they give you the right number?", "giving 3 objects"),
    "ecd34": _q("Can {name} count 10 objects without mistakes?", "counting 10 objects"),
    "ecd35": _q("Can {name} colour or play with building blocks without repeatedly asking "
                "for help or giving up?", "playing on their own without giving up"),
    "ecd36": _q("Does {name} ask about familiar people, other than parents, when they are not there?",
                "asking about familiar people"),
    "ecd37": _q("Does {name} offer to help someone who seems to need help?", "offering to help"),
    "ecd38": _q("Does {name} get along well with other children?", "getting along with others"),
    "ecd39": _q("How often does {name} seem very sad or depressed?", "mood", SAD),
    "ecd40": _q("Compared with other children of the same age, how much does {name} kick, "
                "bite or hit other children or adults?", "kicking, biting or hitting", HITS),

    # WHO gross motor milestones, under 24 months
    "who_sit": _q("Can {name} sit up straight on their own, without any support, for at "
                  "least 10 seconds?", "sitting without support"),
    "who_stand_assist": _q("Can {name} stand on both feet while holding on to furniture "
                           "or a person?", "standing while holding on"),
    "who_crawl": _q("Can {name} crawl forwards on hands and knees?", "crawling on hands and knees"),
    "who_walk_assist": _q("Can {name} take steps while holding on to furniture or a person?",
                          "walking while holding on"),
    "who_stand_alone": _q("Can {name} stand on their own, without holding on, for at least "
                          "10 seconds?", "standing alone"),
    "who_walk_alone": _q("Can {name} take at least 5 steps on their own without holding on?",
                         "walking alone"),
}


def code(item: str, answer: str) -> float | None:
    """Raise ValueError for an answer that is not one of the item's options."""
    for key, _label, value in QUESTIONS[item]["options"]:
        if key == answer:
            return value
    raise ValueError(f"{item}: '{answer}' is not a valid answer")


def questionnaire(items: list[str]) -> list[dict]:
    return [{"item": i, "text": QUESTIONS[i]["text"],
             "options": [{"value": k, "label": label} for k, label, _ in QUESTIONS[i]["options"]]}
            for i in items]
