"""The Hatua assistant: answers caregivers' questions about child development, play and
general child health, through the OpenAI API (or OpenRouter, which serves the same
models: an sk-or- key is sent there).

Safety, in order:
1. Danger signs first, without the AI. A message that mentions a danger sign from the MOH
   Mother and Child Health Handbook (convulsions, difficult breathing, blood in the
   stool, cannot drink, will not wake, yellow eyes...) gets a fixed reply: go to a
   health facility now. OpenAI is not called, so this answer cannot go wrong.
2. Instructions to the model (SYSTEM): development, play, how Hatua works and general
   care only; never a diagnosis, never a medicine, dose or treatment; anything serious
   or lasting goes to a health worker; short, plain answers in the caregiver's language.
3. What leaves the server: the conversation text and, if a child is chosen, their age in
   months. Never names, results or the account.

Conversations are saved per caregiver (assistant_messages) and the caregiver can clear
them. Each caregiver can send settings.assistant_daily_limit messages a day.
"""
import logging
import re
from datetime import datetime, time, timedelta, timezone

import requests

from app.core.config import settings
from app.services.i18n import tr

log = logging.getLogger("uvicorn.error")
OPENAI = "https://api.openai.com/v1"
OPENROUTER = "https://openrouter.ai/api/v1"
HISTORY = 10  # earlier messages sent along, so follow-up questions make sense
EAT = timezone(timedelta(hours=3))


class AssistantOff(Exception):
    """No API key is set."""


class AssistantFailed(Exception):
    """OpenAI could not be reached or gave no answer."""


# English and Swahili ways of describing the handbook's danger signs. Lower case.
DANGER = [re.compile(p) for p in (
    r"convuls", r"seizure", r"\b(having|has|had|a|having a) fits?\b", r"\bfitting\b",
    r"degedege", r"kifafa",
    r"(not|n't|cannot|can't|unable to|struggl\w* to|hard to|trouble) breath",
    r"(fast|difficult|rapid|noisy) breathing", r"breathing (fast|very fast|with difficulty)",
    r"hapumui", r"anapumua (kwa shida|haraka)", r"kupumua kwa shida",
    r"blood in (the |his |her )?(stool|poo|poop|nappy|diaper)", r"bloody (stool|poo)",
    r"damu (kwenye|katika) (kinyesi|choo)",
    r"(not|n't|cannot|can't|won't|will not|refus\w*( to)?) (drink|breastfeed|feed|suck)",
    r"(not|n't) (drinking|breastfeeding|feeding|sucking)", r"hawezi kunywa", r"hanyonyi",
    r"unconscious", r"(won't|will not|can't|cannot|hard to|not) wak",
    r"hazinduki", r"hajitambui", r"very sleepy",
    r"yellow (eyes|skin|palms|soles)", r"(eyes|skin) (look |are |is )?yellow", r"manjano",
)]

URGENT = ("This could be a danger sign. Take your child to a health facility now. Do not "
          "wait for an answer here. If you can, call your community health worker on the "
          "way.")

SYSTEM = """You are the Hatua assistant. Hatua is an app that helps caregivers in Kenya follow how their children under five are developing, with short checks reviewed by community health workers (CHWs).

You may help with:
- child development and milestones, and play and learning ideas
- how Hatua works: checks look at four areas (movement, language, thinking and learning, social and emotional); a result is screening, not a diagnosis; a CHW follows up on results that need a look
- general child care and health: feeding and breastfeeding, sleep, hygiene, safety, and what to watch for with common illnesses

Rules you must always follow:
- Never diagnose or say what illness or condition a child has. Never say a child is or is not developing normally; say that a Hatua check and their CHW can help.
- Never name, recommend or give doses of any medicine, supplement, herbal or home remedy, or treatment. If asked, say a health worker must advise on that.
- If something sounds serious, is getting worse, or lasts more than a day or two, say to see a health worker or go to a health facility, and suggest messaging their CHW in Hatua's chat.
- If the child shows any danger sign (cannot drink or breastfeed, convulsions, fast or difficult breathing, blood in the stool, very sleepy or hard to wake, a young baby with yellow eyes or skin, or a fever or feeling very hot or cold in a baby under 2 months), say to go to a health facility now.
- Do not ask for, use or repeat names, phone numbers or other personal details.
- For anything not about children's development, care or health, or about Hatua, say kindly that you can only help with those.
- Keep answers short (under 120 words), warm and in plain words. Use at most 4 short points.
- Answer in {language}."""


def mentions_danger_sign(text: str) -> bool:
    t = " ".join(text.lower().split())
    return any(p.search(t) for p in DANGER)


def urgent_reply(lang: str) -> str:
    return tr(URGENT, lang)


def day_start() -> datetime:
    """Start of today in East Africa Time, for the daily limit."""
    return datetime.combine(datetime.now(EAT).date(), time.min, EAT)


def endpoint() -> tuple[str, str, bool]:
    """(chat completions URL, model, via OpenRouter). An OpenRouter key (sk-or-...) is
    sent to OpenRouter, which serves the same OpenAI models with the same API."""
    via_openrouter = settings.openai_api_key.startswith("sk-or-")
    base = OPENROUTER if via_openrouter else OPENAI
    model = settings.openai_model
    if via_openrouter and "/" not in model:
        model = "openai/" + model  # OpenRouter names models by provider
    return f"{base}/chat/completions", model, via_openrouter


def ask(history: list[tuple[str, str]], question: str, lang: str,
        age_months: int | None) -> str:
    """history: earlier (role, text) pairs, oldest first. Returns the assistant's reply."""
    if not settings.openai_api_key:
        raise AssistantOff()
    system = SYSTEM.replace("{language}", "Swahili" if lang == "sw" else "English")
    if age_months is not None:
        system += f"\nThe caregiver is asking about a child who is {age_months} months old."
    messages = [{"role": "system", "content": system}]
    messages += [{"role": r, "content": t} for r, t in history[-HISTORY:]]
    messages.append({"role": "user", "content": question})
    url, model, via_openrouter = endpoint()
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    if via_openrouter:
        headers["X-Title"] = "Hatua"
    # OpenRouter takes max_tokens; OpenAI's newer models only max_completion_tokens.
    limit = {"max_tokens" if via_openrouter else "max_completion_tokens": 400}
    try:
        r = requests.post(url, timeout=30, headers=headers,
                          json={"model": model, "messages": messages, **limit})
        r.raise_for_status()
        reply = r.json()["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError, ValueError, AttributeError) as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        log.warning("assistant: OpenAI call failed (%s %s)", type(e).__name__, status)
        raise AssistantFailed() from e
    if not reply:
        raise AssistantFailed()
    return reply
