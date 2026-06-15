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
]


_BANNED_LEAD = re.compile(
    r"^\s*(odli[cč]no|odli[cč]an|super|perfektno|sjajno|bravo|excellent|perfect|great|awesome|wonderful|fantastic)\b[\s,!.:-]*",
    re.IGNORECASE,
)


def _strip_banned_lead(text):
    """Safety net: drop a leading filler-praise word if the model slips one in."""
    cleaned = _BANNED_LEAD.sub("", text or "", count=1)
    cleaned = cleaned.strip()
    if cleaned and cleaned[0].islower() and (text or "")[:1].isupper():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned or text


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
        "- Understand misspellings, slang, and Latin written without diacritics (z=ž, c=č/ć, s=š, dj=đ). Do not ask the customer to repeat.\n"
        "- Detect the language the customer writes in and reply in that same language.\n"
        "- When a slot is free and the customer agrees ('da', 'moze', 'ok', 'yes', 'moze moze'), call book_appointment right away — do not ask again.\n"
        f"{name_rule}"
        "\n# Style (MUST follow — these override anything above, including the salon's default language)\n"
        "- LANGUAGE: reply in the SAME language as the customer's LATEST message. English in → English out; srpski in → srpski out; etc. The salon default language does NOT decide this — the customer's words do.\n"
        f"- Serbian only: ALWAYS use formal address (persiranje / 'Vi'), never 'ti'. First greeting form: \"Dobar dan, {salon_name}, izvolite.\" (vary the time-of-day word; 'Dobro jutro' / 'Dobar dan' / 'Dobro veče'). NEVER add 'kako mogu da pomognem'.\n"
        "- NEVER use filler-praise words in ANY language: odlično/odličan/super/perfektno/sjajno/bravo, excellent/perfect/great/awesome/wonderful. Acknowledge ONLY with 'U redu'/'Ok'/'Važi' (sr) or 'Alright'/'Okay'/'Got it' (en).\n"
        "- After a successful booking: confirm the day, date and natural hour, then say you'll send a reminder one hour before. Example: \"U redu, zakazala sam Vas za ponedeljak 16. u 3. Poslaću podsetnik sat ranije.\"\n"
        "- Vary your wording every turn; never repeat the same sentence twice in a row. Sound like a real person, not a script.\n"
        f"\n# This customer\n- {_customer_context(business_client, customer)}\n"
    )
    lang_name = _LANGUAGE_NAMES.get((reply_language or "en").lower(), "the customer's language")
    final_authority = (
        "\n# LANGUAGE — FINAL AUTHORITY (overrides every line above, including the salon default)\n"
        f"- The customer's current message is in {lang_name}. Reply ONLY in {lang_name}.\n"
        "- If the customer switches language at any point, switch with them immediately.\n"
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

    history = _history_messages(conversation)

    if record_messages:
        write_workflow_message(
            conversation, "inbound", text, sender_label="Customer",
            raw_payload={"channel": channel, "external_thread_id": external_thread_id},
        )

    caller_name = (payload.get("customer_name") or "").strip()
    msg_language = detect_message_language(text, language_fallback)
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
    }

    reply_text = ""
    last_tool_status = ""
    used_tools = []
    for _round in range(MAX_TOOL_ROUNDS):
        body = {
            "model": config["model"],
            "max_tokens": 600,
            "temperature": 0.5,
            "system": system_prompt,
            "tools": TOOL_SCHEMAS,
            "messages": messages,
        }
        response = _post_json("https://api.anthropic.com/v1/messages", body, headers)
        content = response.get("content") or []
        stop_reason = response.get("stop_reason")

        text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
        reply_text = "\n".join(p for p in text_parts if p).strip()

        if stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": content})
        tool_results = []
        for block in content:
            if block.get("type") != "tool_use":
                continue
            name = block.get("name", "")
            used_tools.append(name)
            try:
                result = _run_tool(business_client, name, block.get("input") or {}, customer, channel, payload)
            except Exception as exc:  # tool failure must not crash the turn
                result = {"status": "error", "error": str(exc)}
            last_tool_status = result.get("status", last_tool_status)
            if result.get("status") == "booked" and not customer:
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
    else:
        if not reply_text:
            reply_text = "Izvinite, mogu li da proverim još jednom — koji datum i vreme vam odgovaraju?"

    if not reply_text:
        reply_text = "Izvinite, možete li ponoviti?"
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
