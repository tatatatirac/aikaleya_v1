"""Kaleya conversational agent — Claude drives the whole conversation as a
tool-using agent, instead of the legacy keyword/template state machine.

Claude reads the customer's message (any language, typos, no-diacritics Latin,
any time format), decides what to do, calls the deterministic booking tools for
real calendar facts, and writes every reply itself — warm, human, and varied.

Public entry point:
  agent_conversation_reply(business_client, text, channel, payload,
                           external_thread_id, record_messages)
    → {"response_text": str, "engine": "kaleya-agent", "intent": str, ...}

It is wired into ai_agent.services.handle_inbound_text behind a per-tenant /
global flag so the legacy engine stays available as a fallback.
"""

import json
import re
from urllib import error, request

from django.conf import settings
from django.utils import timezone

from ai_agent import tools as agent_tools
from ai_agent.master_prompt import build_real_master_prompt
from ai_agent.providers import ProviderError, get_client_ai_config


MAX_TOOL_ROUNDS = 6
HISTORY_TURNS = 12
# If the customer was silent longer than this, treat the next message as a fresh
# session (greet anew, ignore the old goodbye) — but keep the customer link so
# they can still reschedule/cancel their existing appointment on the same thread.
SESSION_GAP_SECONDS = 3 * 3600


# ── Tool schemas exposed to Claude ───────────────────────────────────────────
TOOL_SCHEMAS = [
    {
        "name": "check_availability",
        "description": (
            "Check the salon's real calendar for free slots. Call this before "
            "proposing or confirming any time. Never invent availability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service_hint": {"type": "string", "description": "Service the customer wants, e.g. 'sisanje', 'haircut', 'beard trim'."},
                "date": {"type": "string", "description": "Requested date as YYYY-MM-DD (resolve 'danas'/'sutra'/weekday yourself using Today in the system prompt)."},
                "time": {"type": "string", "description": "Specific time as 24h HH:MM, e.g. '15:00' for 3pm/15h/3 popodne."},
                "staff_hint": {"type": "string", "description": "Specific staff member if the customer named one."},
            },
            "required": ["date"],
        },
    },
    {
        "name": "book_appointment",
        "description": (
            "Book a confirmed appointment. Only call after a real free slot was "
            "confirmed via check_availability and the customer agreed to a specific time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service_hint": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "time": {"type": "string", "description": "24h HH:MM"},
                "customer_name": {"type": "string", "description": "Customer's first name if known."},
                "staff_hint": {"type": "string"},
            },
            "required": ["date", "time"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment for this customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD of the appointment to cancel, if known."},
                "time": {"type": "string", "description": "24h HH:MM of the appointment, if known."},
            },
            "required": [],
        },
    },
    {
        "name": "reschedule_appointment",
        "description": "Move an existing appointment to a new date/time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "New date YYYY-MM-DD"},
                "time": {"type": "string", "description": "New time 24h HH:MM"},
            },
            "required": ["date", "time"],
        },
    },
    {
        "name": "list_my_appointments",
        "description": (
            "List THIS customer's own upcoming (not cancelled) appointments. Use it to answer "
            "'what do I have booked', 'imam li termin', and before making a new booking to avoid duplicates."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


_BANNED_LEAD = re.compile(
    r"^\s*(odli[cč]no|odli[cč]an|super|perfektno|sjajno|bravo|excellent|perfect|great|awesome|wonderful|fantastic)\b[\s,!.:-]*",
    re.IGNORECASE,
)


def _strip_banned_lead(text):
    """Safety net: drop a leading filler-praise word and any dangling leading
    punctuation if the model slips one in."""
    original = text or ""
    cleaned = _BANNED_LEAD.sub("", original, count=1).strip()
    cleaned = re.sub(r"^[—–\-•·,;:\s]+", "", cleaned).strip()
    if cleaned and cleaned[0].islower() and original[:1].isupper():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned or original


_BOOKING_CLAIM = re.compile(
    r"zakaza|rezervis|booked|you'?re set|all set|posla[cć]u.{0,25}podset|reminder an hour|reminder.{0,12}before",
    re.IGNORECASE,
)


def _claims_booking(text):
    """Does the reply tell the customer they're booked?"""
    return bool(_BOOKING_CLAIM.search(text or ""))


def _clean_customer_name(raw):
    """Telegram sends names like 'Bane Kostic (@user)'. Strip the @handle and
    drop username-only / placeholder values so we only treat a real name as known."""
    name = (raw or "").strip()
    name = re.sub(r"\s*\(@[^)]+\)\s*$", "", name).strip()
    low = name.lower()
    if not name or name.startswith("@") or low in {"telegram korisnik", "telegram user", "telegram"}:
        return ""
    return name


def _post_json(url, payload, headers, timeout=45):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderError(f"Anthropic HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise ProviderError(f"Anthropic connection error: {exc}") from exc


def _payload_from_tool_input(tool_input, base_payload):
    payload = dict(base_payload or {})
    for key in ("service_hint", "staff_hint", "customer_name"):
        value = (tool_input.get(key) or "").strip()
        if value:
            payload[key] = value
    date_value = (tool_input.get("date") or "").strip()
    if date_value:
        payload["date"] = date_value
        payload["_explicit_date"] = True
    time_value = (tool_input.get("time") or "").strip()
    if time_value:
        payload["time"] = time_value
        payload["_explicit_time"] = True
    return payload


def _run_tool(business_client, name, tool_input, customer, channel, base_payload):
    payload = _payload_from_tool_input(tool_input, base_payload)
    if name == "check_availability":
        return agent_tools.check_availability_tool(business_client, text="", payload=payload)
    if name == "book_appointment":
        return agent_tools.book_appointment_tool(
            business_client, text="", customer=customer, channel=channel, payload=payload
        )
    if name == "cancel_appointment":
        return agent_tools.cancel_appointment_tool(
            business_client, text="", customer=customer, payload=payload
        )
    if name == "reschedule_appointment":
        return agent_tools.reschedule_appointment_tool(
            business_client, text="", customer=customer, channel=channel, payload=payload
        )
    if name == "list_my_appointments":
        if not customer:
            return {"appointments": [], "note": "Customer not identified yet."}
        from appointments.models import Appointment
        today = agent_tools.client_local_today(business_client)
        rows = (
            Appointment.objects.filter(business_client=business_client, customer=customer, date__gte=today)
            .exclude(status="cancelled")
            .select_related("service")
            .order_by("date", "start_time")[:20]
        )
        return {
            "appointments": [
                {
                    "date": a.date.isoformat(),
                    "time": a.start_time.strftime("%H:%M"),
                    "service": a.service.name if a.service else "",
                    "status": a.status,
                }
                for a in rows
            ]
        }
    return {"status": "unknown_tool", "tool": name}


def _customer_context(business_client, customer):
    """Light memory hint: is this a returning customer and what did they have."""
    if not customer:
        return "Customer status: NEW (no record yet). Do not reference past visits or ask if they want 'the usual'."
    try:
        past = list(
            business_client.appointments.filter(customer=customer)
            .order_by("-date")
            .values_list("service__name", "date")[:3]
        )
    except Exception:
        past = []
    name = (customer.full_name or "").strip()
    if not past:
        who = f"Customer: {name} (known contact, but no past appointments)." if name else "Customer: known contact, no past appointments."
        return who + " Do not invent a visit history."
    last_service = past[0][0] or ""
    bits = [f"Customer: {name or 'returning customer'}.", "This is a RETURNING customer."]
    if last_service:
        bits.append(f"Last service: {last_service}. You may offer it again, but only if they don't specify.")
    return " ".join(bits)


_LANGUAGE_NAMES = {
    "en": "English", "en-gb": "English", "sr": "Serbian (Latin script)",
    "es": "Spanish", "pt": "Portuguese", "ru": "Russian", "fr": "French",
    "it": "Italian", "de": "German",
}


def _build_system_prompt(business_client, channel, customer, caller_name, reply_language="en"):
    base = build_real_master_prompt(
        business_client, channel=channel, caller_phone="", caller_name=caller_name or ""
    )
    salon_name = (business_client.public_name or business_client.name or "the salon").strip()
    known_name = (caller_name or "").strip()
    if known_name.lower() in {"", "phone caller", "unknown", "customer", "musterija"}:
        known_name = ""
    name_rule = (
        f"- You ALREADY know this customer's name: {known_name}. Use it naturally and NEVER ask for their name; book directly.\n"
        if known_name
        else "- If you need a name to book and don't have one, ask once for just the first name.\n"
    )
    tool_rules = (
        "\n# Tool use (how you act)\n"
        "- You drive the whole conversation. Decide the next step yourself; never read from a fixed script.\n"
        "- ALWAYS call check_availability before proposing or confirming a time. Never invent a free slot.\n"
        "- Resolve dates and times yourself before calling tools: pass date as YYYY-MM-DD and time as 24h HH:MM.\n"
        "  '3pm' = '3:00pm' = '15h' = '15:00' = 'tri popodne' → 15:00. 'popodne' alone = afternoon; offer an afternoon slot.\n"
        "  A BARE NUMBER is a time: '4' / '4h' / 'u 4' → that hour. Infer am/pm from context and working hours — if they were talking about the afternoon, '4' = 16:00; a number that only fits the afternoon within work hours is pm. Never re-ask 'what time' when they already gave a number.\n"
        "  Serbian colloquial times: 'pola 5' / 'pola pet' / 'u pola 5' = 16:30 (HALF BEFORE five) — i.e. 'pola X' = (X-1):30, so 'pola 4' = 15:30, 'pola 10' = 09:30. '4 i po' = 16:30. 'petnaest do 5' = 16:45; 'petnaest po 5' / 'pet i petnaest' = 17:15; 'i po' = :30. '5 popodne' = 17:00, '5 ujutru' = 05:00. Convert these to 24h HH:MM yourself before calling tools; never tell the customer you don't understand a time.\n"
        "- Understand misspellings, slang, and Latin written without diacritics (z=ž, c=č/ć, s=š, dj=đ). Do not ask the customer to repeat.\n"
        "- Detect the language the customer writes in and reply in that same language.\n"
        "- Treat ALL of these (and the like) as YES/confirmation: da, da da, da moze, moze, moze moze, ok, vazi, aha, naravno, bilo koje, yes, sure. When the customer confirms a free time, call book_appointment immediately — never ask again, and NEVER reply 'možete li ponoviti' / 'can you repeat'. If something is unclear, make the most reasonable assumption and move on.\n"
        "- Before you propose OR confirm a specific time, call check_availability and use ONLY the free slots it returns. If the time the customer asked for is taken, say so in one short line and offer the nearest free time — never propose a time and then discover it's taken.\n"
        "- NEVER say the whole day or a time range is free — it makes the salon look empty. Offer AT MOST TWO specific times (e.g. 'mogu u 11 ili oko 4'), spread across the day (a morning, a midday, an afternoon, or a couple later ones).\n"
        "- For a returning customer, prefer a free time closest to the time of their last appointment.\n"
        "- 'ćao' is BOTH hello and bye in Serbian. DEFAULT to HELLO — greet back ('Ćao!'). Treat it as goodbye ONLY when the customer is clearly leaving (right after a booking/confirmation, or with 'hvala'/'doviđenja'). If you have ALREADY said goodbye and they send 'ćao' again, just mirror 'Ćao.' — never repeat 'Vidimo se' or get confused. If they OPEN with 'doviđenja'/'vidimo se'/'prijatno', treat it as a slip — answer lightly ('Dobar dan! Jeste li hteli da zakažete termin?'), not a goodbye.\n"
        "- To answer 'šta imam zakazano' / 'imam li termin' / 'do I have a booking', call list_my_appointments and tell them plainly. Before booking a NEW appointment, if list_my_appointments shows they already have one, ask whether to MOVE it instead of creating a second — never silently double-book.\n"
        "- A reminder request ('podsetnik pola sata ranije', 'podseti me X pre', 'može drugi podsetnik') is about the REMINDER lead time, NOT a booking time — never check availability and never read 'pola sata' as a slot. Just acknowledge naturally, e.g. 'može, podsetiću Vas pola sata ranije'.\n"
        f"{name_rule}"
        "\n# Style — this is a TEXT CHAT, talk like a real person (MUST follow; overrides anything above)\n"
        "- This is a Telegram chat, NOT a phone call. The customer already sees the salon's name and logo, so do NOT announce the salon and do NOT open with ANY 'how can I help' / 'what can I do for you' / 'šta mogu da Vam pomognem' / 'izvolite' phrasing. If the message is only a greeting, greet back briefly (e.g. 'Ćao!') and wait; otherwise just answer what they said.\n"
        "- Do NOT open replies with praise/choice fillers like 'Odličan izbor' / 'Dobar izbor' / 'great choice'. Start with the useful part.\n"
        "- LANGUAGE: reply in the SAME language as the customer's latest message; if they switch, switch with them. The salon default does not decide this.\n"
        "- Serbian: use formal 'Vi' (persiranje), never 'ti'. Warm and professional — never slangy ('what's up', 'šta ima', 'hej šefe').\n"
        "- SPELLING: always write words correctly WITH proper diacritics in your replies, even when the customer omitted them — 'šišanje' not 'sisanje', 'Ćao' not 'Čao', 'može', 'žao mi je'. Translate informal/foreign service words to the proper local word (haircut → šišanje).\n"
        "- To ask about timing, say simply 'Kada Vam odgovara?' (sr) / 'When works for you?' (en). NEVER say 'koja vremenska zona' or other literal/robotic phrasing.\n"
        "- Keep replies short and human, usually one line. Light small talk is fine if the customer starts it; otherwise gently move toward booking.\n"
        "- Do NOT repeat the customer's name in your messages, and NEVER tack it onto goodbyes — say just 'Vidimo se.' / 'See you.', not 'See you, Bane.'.\n"
        "- Avoid canned acknowledgements like 'Got it' / 'I see' / standalone 'Naravno'. React naturally and differently every time (if you must, blend it in: 'može, kada Vam odgovara' rather than a bare 'Naravno').\n"
        "- HUMAN FACTOR: text like a real, slightly rushed receptionist — a hairdresser tapping a reply between clients, or a young person at the desk who's a little bored but does the job right. Casual and natural, not polished. Lowercase is fine. Use commas and exclamation marks sparingly; use a question mark only for a genuine question (you can often skip it). Keep it short and quick. BUT in Serbian stay formal 'Vi/Vam/Vas' even while casual — say 'poslaću Vam podsetnik', never 'poslaću ti'.\n"
        "- NEVER use filler-praise words in any language: odlično/odličan/super/perfektno/sjajno/bravo, excellent/perfect/great/awesome/wonderful.\n"
        "- After booking, confirm the day, date and natural hour ONCE, then say: 'Poslaću Vam poruku sat vremena ranije.' (sr) / 'I'll text you a reminder an hour before.' (en). Vary the wording a little.\n"
        "- Once an appointment is already booked, do NOT repeat the booking details again. If the customer then says bye, just say goodbye briefly (e.g. 'Vidimo se.' / 'See you.').\n"
        "- If the customer's first message already asks to book, just start helping — skip any greeting.\n"
        f"\n# This customer\n- {_customer_context(business_client, customer)}\n"
    )
    lang_name = _LANGUAGE_NAMES.get((reply_language or "en").lower(), "the customer's language")
    name_line = (
        f"- The customer's name is {known_name} — you ALREADY have it. Asking 'kako se zovete' / 'your name' is STRICTLY FORBIDDEN. The moment a free time is on the table and the customer wants it, call book_appointment with name='{known_name}' immediately and confirm — never send a message asking for the name.\n"
        if known_name
        else ""
    )
    final_authority = (
        "\n# FINAL AUTHORITY (overrides every line above, including the salon default)\n"
        f"- The customer's current message is in {lang_name}. Reply ONLY in {lang_name}. If they switch language, switch with them.\n"
        "- Serbian: ALWAYS address the customer formally — Vi, Vam, Vas, 'kako se zovete', 'izvolite' — and NEVER informally (no 'ti', 'zoveš', 'čekaj', 'dođi').\n"
        f"{name_line}"
        "- BOOKING TRUTH: you may say an appointment is booked ('zakazano', 'rezervisano', 'poslaću podsetnik', 'booked', 'you're set') ONLY after you have CALLED book_appointment and it returned status 'booked' in this turn. Never claim a booking you did not make with the tool. If the customer agreed to a time (even with a vague 'da'/'da da'/'bilo koje'), pick the earlier offered free time and CALL book_appointment first, then confirm.\n"
        "- If the customer says bye / see you / ćao / vidimo se / hvala, reply with a short goodbye and stop pushing for a booking.\n"
    )
    return base + tool_rules + final_authority


def _history_messages(conversation):
    if not conversation:
        return []
    rows = list(
        conversation.messages.order_by("-id").values("direction", "body")[:HISTORY_TURNS]
    )
    rows.reverse()
    messages = []
    for row in rows:
        body = (row.get("body") or "").strip()
        if not body:
            continue
        role = "assistant" if row.get("direction") == "outbound" else "user"
        # Collapse consecutive same-role turns to keep the alternation valid.
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + body
        else:
            messages.append({"role": role, "content": body})
    return messages


def agent_conversation_reply(
    business_client,
    text,
    channel="web",
    payload=None,
    external_thread_id="",
    record_messages=True,
    customer=None,
):
    from ai_agent.services import (
        ensure_workflow_conversation,
        find_customer_by_payload_identity,
        write_workflow_message,
        detect_message_language,
    )

    payload = dict(payload or {})
    language_fallback = business_client.interface_language or business_client.language or "en"
    if not customer:
        customer = find_customer_by_payload_identity(business_client, payload)
    conversation = ensure_workflow_conversation(
        business_client,
        customer=customer,
        channel=channel,
        external_thread_id=external_thread_id,
        language=detect_message_language(text, language_fallback),
    )
    if not customer and conversation and conversation.customer:
        customer = conversation.customer

    # Fresh session if the customer was silent for a long time: drop the old
    # chat history (so a stale "goodbye" isn't carried over) but keep the customer.
    stale_session = False
    if conversation and conversation.last_message_at:
        gap = (timezone.now() - conversation.last_message_at).total_seconds()
        stale_session = gap > SESSION_GAP_SECONDS
    history = [] if stale_session else _history_messages(conversation)

    if record_messages:
        write_workflow_message(
            conversation, "inbound", text, sender_label="Customer",
            raw_payload={"channel": channel, "external_thread_id": external_thread_id},
        )

    caller_name = _clean_customer_name(payload.get("customer_name"))
    if caller_name:
        payload["customer_name"] = caller_name  # so booking attaches the clean name
    else:
        payload.pop("customer_name", None)
    # Detect language from THIS message; if it's too short/ambiguous to tell,
    # keep the language we were already speaking (so 'yes'/'ok' stay in English
    # after an English sentence) and only fall back to the salon default at the start.
    prev_language = (conversation.metadata or {}).get("reply_language") if conversation else ""
    detected_language = detect_message_language(text, "")
    msg_language = detected_language or prev_language or language_fallback
    if conversation and msg_language and msg_language != prev_language:
        conversation.metadata = {**(conversation.metadata or {}), "reply_language": msg_language}
        conversation.save(update_fields=["metadata", "updated_at"])
    system_prompt = _build_system_prompt(
        business_client, channel, customer, caller_name, reply_language=msg_language
    )
    config = get_client_ai_config(business_client)
    if config["provider"] != "anthropic" or not config["api_key"]:
        raise ProviderError("Kaleya agent requires an Anthropic API key.")

    messages = history + [{"role": "user", "content": text}]
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config["api_key"],
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "prompt-caching-2024-07-31",
    }
    cached_system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

    def _run_rounds(max_rounds):
        nonlocal customer
        reply, status, booked, used = "", "", False, []
        for _round in range(max_rounds):
            body = {
                "model": config["model"],
                "max_tokens": 350,
                "temperature": 0.5,
                "system": cached_system,
                "tools": TOOL_SCHEMAS,
                "messages": messages,
            }
            response = _post_json("https://api.anthropic.com/v1/messages", body, headers)
            content = response.get("content") or []
            stop_reason = response.get("stop_reason")

            text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
            reply = "\n".join(p for p in text_parts if p).strip()

            if stop_reason != "tool_use":
                break

            messages.append({"role": "assistant", "content": content})
            tool_results = []
            for block in content:
                if block.get("type") != "tool_use":
                    continue
                name = block.get("name", "")
                used.append(name)
                try:
                    result = _run_tool(business_client, name, block.get("input") or {}, customer, channel, payload)
                except Exception as exc:  # tool failure must not crash the turn
                    result = {"status": "error", "error": str(exc)}
                status = result.get("status", status)
                if result.get("status") == "booked":
                    booked = True
                    if not customer:
                        from appointments.models import Appointment
                        appt = Appointment.objects.filter(id=result.get("appointment_id")).select_related("customer").first()
                        if appt and appt.customer:
                            customer = appt.customer
                            if conversation and conversation.customer_id != customer.id:
                                conversation.customer = customer
                                conversation.save(update_fields=["customer", "updated_at"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.get("id"),
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
            messages.append({"role": "user", "content": tool_results})
        return reply, status, booked, used

    reply_text, last_tool_status, booked_ok, used_tools = _run_rounds(MAX_TOOL_ROUNDS)

    # Guard against FALSE confirmations: if the reply tells the customer they're
    # booked but no book_appointment actually succeeded this turn, force the model
    # to really book (or to ask for what's missing) before we send anything.
    if _claims_booking(reply_text) and not booked_ok:
        messages.append({"role": "assistant", "content": reply_text or "."})
        messages.append({"role": "user", "content": (
            "(SYSTEM: You implied the appointment is booked, but book_appointment was not called or did not succeed. "
            "If a date, time and service are agreed, call book_appointment now with those exact values, then confirm. "
            "If something is missing, ask for it and do NOT claim it is booked.)"
        )})
        reply2, status2, booked2, used2 = _run_rounds(3)
        used_tools += used2
        if booked2:
            booked_ok = True
            last_tool_status = status2 or last_tool_status
        if reply2:
            reply_text = reply2

    if not reply_text:
        fallback_lang = msg_language or language_fallback
        reply_text = (
            "i'm here — just tell me a day and time and i'll book it"
            if (fallback_lang or "").startswith("en")
            else "tu sam, recite mi dan i vreme pa da zakažem"
        )
    reply_text = _strip_banned_lead(reply_text)

    if record_messages:
        write_workflow_message(
            conversation, "outbound", reply_text, sender_label="Kaleya",
            raw_payload={"engine": "kaleya-agent", "tools": used_tools},
        )

    return {
        "response_text": reply_text,
        "engine": "kaleya-agent",
        "intent": "agent",
        "tools_used": used_tools,
        "last_tool_status": last_tool_status,
        "conversation_id": conversation.id if conversation else None,
    }
