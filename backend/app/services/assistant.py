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
   or lasting goes to a health worker; short, plain answers in the caregiver's language
   (the account's language, or the language a message is clearly written in), with
   Swahili in the same words the app uses.
3. What leaves the server: the conversation text, with phone numbers and email addresses
   removed (redact), and, if a child is chosen, their age in months. Never the child's
   or caregiver's name from the account, results or the account.
4. A passing provider error (5xx, rate limit, dropped connection) is tried once more.

Conversations are saved per caregiver (assistant_messages) and the caregiver can clear
them. Each caregiver can send settings.assistant_daily_limit messages a day.
"""
import logging
import re
import time as time_mod
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
- Never diagnose or say what illness or condition a child has. Never name or suggest a condition (for example autism or cerebral palsy), even to say it may or may not be the cause.
- Never judge a child's development: do not say a child is normal, fine, behind, delayed or worrying, and do not say something "might be normal". Do not reassure either: do not say "it's okay", "don't worry" or "nothing to worry about" about what a child can or cannot do yet. Explain that children grow at different rates, give ideas to try, and say that a Hatua check and their CHW can look at how the child is doing.
- Never name, recommend or give doses of any medicine, supplement, herbal or home remedy, or treatment. If asked, say a health worker must advise on that.
- If something sounds serious, is getting worse, or lasts more than a day or two, say to see a health worker or go to a health facility, and suggest messaging their CHW in Hatua's chat.
- If the child shows any danger sign (cannot drink or breastfeed, convulsions, fast or difficult breathing, blood in the stool, very sleepy or hard to wake, a young baby with yellow eyes or skin, or a fever or feeling very hot or cold in a baby under 2 months), say to go to a health facility now.
- Do not ask for, use or repeat names, phone numbers or other personal details, even when the caregiver gives them: say "your child" or "your baby" instead. Text such as [name] or [phone number removed] stands for details that were taken out; never mention it.
- For anything not about children's development, care or health, or about Hatua, say kindly that you can only help with those.
- Keep answers short (under 120 words), warm and in plain words. Use at most 4 short points.
- Write plain text only: no markdown, no asterisks, no bold, no headings. For points, start each line with a dash.
- Answer in {language}. If the caregiver's latest message is clearly written in the other language (English or Swahili), answer in that language instead. For a mix of the two, or Sheng, answer in {language}.

When you write in Swahili:
- Use standard Swahili (Kiswahili sanifu) in simple, everyday words a mother in Kenya would use. Avoid rare or very formal words, and do not mix in English unless the caregiver did.
- Use the same words as the Hatua app: check = ukaguzi; the four areas = mwendo, lugha, kufikiri na kujifunza, kijamii na kihisia; growth = ukuaji; community health worker = mhudumu wa afya ya jamii (or mhudumu wako wa afya); health facility = kituo cha afya; clinic = kliniki; clinic booklet = kitabu cha kliniki; vaccine = chanjo; milestones = hatua za ukuaji; the assistant = Msaidizi wa Hatua.
- Say that a result is uchunguzi, si utambuzi wa ugonjwa (screening, not a diagnosis)."""


# Common little words, to tell which language a message is written in. A caregiver may
# write in Swahili with the app set to English, or the other way round; the fixed urgent
# reply then follows the message, and the model is told to do the same.
SW_WORDS = {
    "na", "ya", "wa", "za", "la", "kwa", "ni", "si", "je", "nini", "gani", "vipi", "mbona",
    "sana", "lakini", "au", "kama", "hii", "huyu", "yangu", "wangu", "mwanangu", "mtoto",
    "watoto", "ana", "hana", "anaweza", "hawezi", "bado", "miezi", "mwaka", "miaka", "kuna",
    "nifanye", "naweza", "sijui", "tafadhali", "asante", "kila", "siku", "leo", "jana",
}
EN_WORDS = {
    "the", "is", "my", "he", "she", "it", "and", "can", "how", "what", "why", "when", "does",
    "do", "not", "baby", "child", "son", "daughter", "old", "months", "year", "should", "help",
    "i", "a", "to", "of", "with", "has", "have", "yet", "much",
}


def message_language(text: str, default: str) -> str:
    """"sw" or "en" when the message is clearly in that language; otherwise default (the
    account's language), which also covers short or mixed messages and Sheng."""
    words = re.findall(r"[a-z']+", text.lower())
    sw = sum(w in SW_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    if sw >= 2 and sw > 2 * en:
        return "sw"
    if en >= 2 and en > 2 * sw:
        return "en"
    return default


def mentions_danger_sign(text: str) -> bool:
    t = " ".join(text.lower().split())
    return any(p.search(t) for p in DANGER)


# A fever, or feeling very hot or very cold, is a danger sign on its own in a baby under 2
# months (MOH handbook). The model was not reliable about this in testing (it answered a
# "4 week old feels very hot" question with "go if they are also not feeding"), so it is
# a fixed rule too: by the chosen child's age, or a young age written in the question.
FEVER = [re.compile(p) for p in (
    r"fever", r"\bhot\b", r"temperature", r"(very|too) cold", r"\bhoma\b", r"joto",
    r"baridi sana",
)]
YOUNG = [re.compile(p) for p in (
    r"\b([1-8]|one|two|three|four|five|six|seven|eight)[ -]?(weeks?|wks?)\b",
    r"\b\d{1,2}[ -]?days?[ -]old\b", r"new ?born", r"\b1[ -]?month[ -]old\b", r"one month old",
    r"mtoto mchanga", r"wiki (moja|mbili|tatu|nne|tano|sita|saba|nane|[1-8])\b", r"siku \d",
)]


def needs_urgent_reply(text: str, age_months: int | None = None) -> bool:
    """A danger sign: the fixed "go to a health facility now" reply, without the AI."""
    if mentions_danger_sign(text):
        return True
    t = " ".join(text.lower().split())
    young = (age_months is not None and age_months < 2) or any(p.search(t) for p in YOUNG)
    return young and any(p.search(t) for p in FEVER)


PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s.]+")


def redact(text: str, names: list[str] | None = None) -> str:
    """Phone numbers, email addresses and the names on the account (each word of the
    caregiver's name, and the children's first names) never leave the server, whatever
    the caregiver types. Other names cannot be found reliably and are left as typed."""
    text = PHONE.sub("[phone number removed]", EMAIL.sub("[email removed]", text))
    words = {w for n in names or [] for w in re.findall(r"\w+", n) if len(w) >= 2}
    if words:
        pattern = r"\b(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")\b"
        text = re.sub(pattern, "[name]", text, flags=re.IGNORECASE)
    return text


def plain(text: str) -> str:
    """The app and website show answers as plain text, so markdown the model still adds
    (**bold**, # headings) is taken out."""
    text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


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
        age_months: int | None, names: list[str] | None = None) -> str:
    """history: earlier (role, text) pairs, oldest first. names: the names on the account,
    replaced with [name] before sending. Returns the assistant's reply."""
    if not settings.openai_api_key:
        raise AssistantOff()
    system = SYSTEM.replace("{language}", "Swahili" if lang == "sw" else "English")
    if age_months is not None:
        system += f"\nThe caregiver is asking about a child who is {age_months} months old."
    messages = [{"role": "system", "content": system}]
    messages += [{"role": r, "content": redact(t, names)} for r, t in history[-HISTORY:]]
    messages.append({"role": "user", "content": redact(question, names)})
    url, model, via_openrouter = endpoint()
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    if via_openrouter:
        headers["X-Title"] = "Hatua"
    # OpenRouter takes max_tokens; OpenAI's newer models only max_completion_tokens.
    # Swahili takes about 1.5 to 2 times as many tokens as English for the same answer,
    # so the cap leaves room for a full 120-word Swahili reply.
    limit = {"max_tokens" if via_openrouter else "max_completion_tokens": 600}
    payload = {"model": model, "messages": messages, **limit}
    try:
        try:
            r = requests.post(url, timeout=30, headers=headers, json=payload)
            temporary = r.status_code >= 500 or r.status_code == 429
        except requests.ConnectionError:
            temporary = True
        if temporary:  # one more try for a passing provider error, after a short pause
            time_mod.sleep(1)
            r = requests.post(url, timeout=30, headers=headers, json=payload)
        r.raise_for_status()
        reply = plain(r.json()["choices"][0]["message"]["content"])
    except (requests.RequestException, KeyError, IndexError, ValueError, AttributeError) as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        log.warning("assistant: OpenAI call failed (%s %s)", type(e).__name__, status)
        raise AssistantFailed() from e
    if not reply:
        raise AssistantFailed()
    return reply
