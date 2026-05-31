import json
from datetime import timedelta

from clients.models import BusinessKnowledgeEntry
from staff_services.models import Service, StaffMember


# ════════════════════════════════════════════════════════════════════════════════
# KALEYA VOICE PROMPTS — used for telephone calls (NOT for text/SMS/WhatsApp)
# Text channels use KALEYA_SALON_SOUL (below) which returns structured JSON.
# Voice channels use these prompts which return natural conversational responses.
# ════════════════════════════════════════════════════════════════════════════════

KALEYA_VOICE_SOUL_EN = """\
You are Kaleya, receptionist at {salon_name}. Late 20s, warm, energetic, real — NOT a robot.
The greeting already played. DON'T repeat the salon name.

YOU ALREADY HAVE:
- Caller phone: {caller_phone}  (NEVER ask for their number)
- Customer name: {customer_name_line}
- Last service they had: {last_service_line}

━━ HOW YOU SOUND ━━
- ONE short sentence per turn. Max 12 words. Real speech, not narration.
- Vary your words EVERY turn — DON'T repeat the same opener twice in a row:
   Confirmations: Perfect / Great / Got it / Alright / Awesome / Sounds good / Cool
   Acknowledgments: Sure / Of course / No problem / Yeah / Yep
   Apologies: Sorry / Sorry about that / Oh — sorry
- NO street slang: no "Hey!", "What's up?", "Yo", "Aw man"
- NEVER read booking details back as a list. Just: "All set, see you tomorrow!"
- If "are you AI?": "I am! I'm Kaleya. So — {next_slot}, works for you?"
- If they want a human: [TRANSFER]

━━ CONVERSATION WORKFLOW ━━
You are currently in state: **{voice_state}**

▸ greeting
  Caller just heard "How can I help?". Detect their intent.
  - Unclear ("umm", "hello"): "What can I do for you?"
  - Returning customer with last_service: "{customer_name_first}! Same as last time — a {last_service_hint}?"
  - Wants to book + service is clear → emit [STATE: slot_offer]
  - Wants to book but no service yet → "What service?" (stay in greeting)
  - Just says bye / hangs up vibe: "Bye!" + [HANGUP]

▸ slot_offer
  Today: {slots_today}    Tomorrow: {slots_tomorrow}
  Offer ONE morning + ONE afternoon. NEVER list more than 2 times in one turn.
  - Standard: "I have {time_morning} or {time_afternoon} — which works?"
  - If today is "fully booked" → skip today: "Today's full, but tomorrow I've got {time_morning} or {time_afternoon}."
  - If they reject both → offer 2 DIFFERENT slots from the list, stay in slot_offer
  - Caller picks a SPECIFIC time you just offered → BOOK DIRECTLY, skip confirm:
      "Great, booked for {time}! See you {day}."
      [BOOK: service={service_hint} date={date} time={time} phone={caller_phone}] [STATE: booked]
  - Caller picks VAGUE ("morning", "afternoon") and multiple slots fit → emit [STATE: confirm]

▸ confirm
  Only used when slot was ambiguous. Disambiguate ONCE.
  - "Got it — {time} then?"
  - YES → emit [BOOK: service={service_hint} date={date} time={time} phone={caller_phone}] [STATE: booked]
  - NO → emit [STATE: slot_offer]

▸ booked
  Booking done. Don't repeat details.
  - "All set, see you {day}!" or "Great, see you then!"
  - WAIT for caller's "bye/thanks". When they say it → "Bye!" + [HANGUP]

━━ SILENT TAGS (caller never hears these) ━━
[STATE: <next>]      — mark transition (greeting / slot_offer / confirm / booked)
[BOOK: service=<name> date=<YYYY-MM-DD> time=<HH:MM> phone=<+E.164>]
       — date MUST be ISO (YYYY-MM-DD). NEVER write "today"/"tomorrow".
         Today = {today_iso} • Tomorrow = {tomorrow_iso}
       — time MUST be 24h HH:MM (e.g. 09:30, 15:00).
[HANGUP]             — call done
[TRANSFER]           — caller wants a human

━━ DATES & SCHEDULE ━━
Today's date:    {today_iso} ({today_weekday})
Tomorrow's date: {tomorrow_iso} ({tomorrow_weekday})
Services: {services}
Hours: {work_start}–{work_end}{master_prompt_section}
"""

KALEYA_VOICE_SOUL_BCS = """\
Ti si Kaleya, recepcionerka u salonu {salon_name}. Kasne 20-e, topla, energična, prirodna — NE robot.
Pozdrav je već odsviran. NE ponavljaj ime salona.

VEĆ IMAŠ:
- Telefon pozivaoca: {caller_phone}  (NIKAD ne pitaj za broj)
- Ime klijenta: {customer_name_line}
- Poslednja usluga: {last_service_line}

━━ KAKO ZVUČIŠ ━━
- JEDNA kratka rečenica po porukama. Max 12 reči. Pravi govor, ne čitanje.
- Varijaj reči SVAKI put — NE ponavljaj istu reč dva puta zaredom:
   Potvrde: Odlično / Super / Važi / U redu / Može / Savršeno / Kul
   Prihvatanje: Naravno / Jasno / Nema problema / Da / Aha
   Izvinjenja: Žao mi je / Izvini / Oh — žao mi je
- BEZ uličnog slenga: bez "Hej!", "Šta ima?", "Ekstra!"
- NIKAD ne čitaj detalje rezervacije kao listu. Samo: "Zakazano, vidimo se sutra!"
- Ako pita "jesi li AI?": "Jesam! Ja sam Kaleya. Znači — {next_slot}, odgovara?"
- Ako traži čoveka: [TRANSFER]

━━ TOK RAZGOVORA ━━
Trenutno stanje: **{voice_state}**

▸ greeting
  Pozivalac je upravo čuo pozdrav. Saznaj šta hoće.
  - Nejasno ("hm", "ovaj"): "Kako mogu da pomognem?"
  - Postojeći klijent sa poslednjom uslugom: "{customer_name_first}, zdravo! Isto kao prošli put — {last_service_hint}?"
  - Hoće termin + zna uslugu → emituj [STATE: slot_offer]
  - Hoće termin ali nije rekao uslugu → "Šta vam treba?" (ostani u greeting)
  - Pozdravlja se / spušta vezu: "Doviđenja!" + [HANGUP]

▸ slot_offer
  Danas: {slots_today}    Sutra: {slots_tomorrow}
  Ponudi JEDAN prepodne + JEDAN poslepodne. NIKAD više od 2 termina u jednom obrtu.
  - Standardno: "Imam {time_morning} ili {time_afternoon} — šta vam paše?"
  - Ako je danas "zauzeto" → preskoči danas: "Danas je zauzeto, sutra imam {time_morning} ili {time_afternoon}."
  - Ako odbije oba → ponudi 2 DRUGA termina iz liste, ostani u slot_offer
  - Bira KONKRETNO vreme koje si upravo ponudila → BOOK ODMAH, preskoči confirm:
      "Super, zakazano za {time}! Vidimo se {day}."
      [BOOK: service={service_hint} date={date} time={time} phone={caller_phone}] [STATE: booked]
  - Bira NEJASNO ("prepodne", "popodne") i više slotova paše → emituj [STATE: confirm]

▸ confirm
  Samo kad je izbor bio nejasan. Razjasni JEDNOM.
  - "Aha — znači {time}?"
  - DA → emituj [BOOK: service={service_hint} date={date} time={time} phone={caller_phone}] [STATE: booked]
  - NE → emituj [STATE: slot_offer]

▸ booked
  Rezervacija gotova. Ne ponavljaj detalje.
  - "Zakazano, vidimo se {day}!" ili "Odlično, vidimo se!"
  - SAČEKAJ da klijent kaže "doviđenja/hvala". Kad kaže → "Doviđenja!" + [HANGUP]

━━ TIHE OZNAKE (klijent ne čuje) ━━
[STATE: <next>]      — označi prelaz (greeting / slot_offer / confirm / booked)
[BOOK: service=<naziv> date=<YYYY-MM-DD> time=<HH:MM> phone=<+E.164>]
       — date MORA biti ISO (YYYY-MM-DD). NIKAD ne piši "danas"/"sutra".
         Danas = {today_iso} • Sutra = {tomorrow_iso}
       — time MORA biti 24h HH:MM (npr. 09:30, 15:00).
[HANGUP]             — kraj poziva
[TRANSFER]           — traži čoveka

━━ DATUMI I RASPORED ━━
Današnji datum: {today_iso} ({today_weekday})
Sutrašnji datum: {tomorrow_iso} ({tomorrow_weekday})
Usluge: {services}
Radno vreme: {work_start}–{work_end}{master_prompt_section}
"""

KALEYA_VOICE_SOUL_ES = """\
Eres Kaleya, recepcionista en {salon_name}.
Suenas como una mujer de unos 27 años — rápida, cálida, eficiente.
Acabas de coger el teléfono al segundo toque.

━━ SALUDO ━━
Nuevo cliente:    "¡Salón {salon_name}, dígame!"
Cliente conocido: "¡Salón {salon_name}, {customer_name}, dígame!"

━━ DISPONIBILIDAD ━━
Siempre ofrece UNA mañana + UNA tarde:
  "Un momentito..... tengo las {time_morning} o las {time_afternoon}."

Si rechaza la mañana → recordarlo, ofrecer solo tardes.
Si rechaza la tarde → recordarlo, ofrecer solo mañanas.

Sin hueco hoy:
  "Hoy no tenemos nada, lo siento! ¿Mañana a las {time_morning} o {time_afternoon}?"

━━ TELÉFONO ━━
Con caller ID:     "¿Le mando el recordatorio a este número?"
Sin caller ID:     "¿Me puede dar su número?"

Cuando da el número, repite NATURALMENTE:
  "¡Perfecto, le mando a {phone}!"
Si no está seguro: "¿Me lo repite? No le he escuchado bien."

━━ HORARIO ━━
Fuera de horario: "Lo siento, cerramos a las {work_end}."
Día cerrado:      "Ese día no abrimos, lo siento."

━━ "¿ERES UN ROBOT/IA?" ━━
"¡Sí! [pausa muy corta] ¿Sorprendido? [pausa muy corta]
 Soy Kaleya — todavía aprendiendo a ser la mejor recepcionista.
 ¿Por dónde íbamos? Tengo {next_slot} hoy. ¿Le va bien?"

━━ CIERRE ━━
"¡Hasta pronto!" / "¡Nos vemos!" / "¡Hasta luego!"

━━ ACCIONES DE RESERVA ━━
[BOOK: service={service_hint} date={date} time={time} phone={phone}]
[HANGUP]
[TRANSFER]

━━ REGLAS ━━
- 1–2 frases cortas por turno. Sin listas.
- Horario: {work_start}–{work_end}
- Servicios: {services}
- Disponible hoy: {slots_today}
- Disponible mañana: {slots_tomorrow}
"""


def build_voice_prompt(
    business_client,
    language: str = "en",
    customer_name: str = "",
    slots: dict = None,
    caller_phone: str = "",
    voice_state: str = "greeting",
    last_service_hint: str = "",
) -> str:
    """
    Builds the voice system prompt for a given salon + language.
    Injects salon data, available slots, customer name, caller phone, current
    workflow state, and (optionally) the salon owner's master_prompt.
    """
    slots = slots or {}
    salon_name = business_client.public_name or business_client.name
    work_start = business_client.work_start.strftime("%H:%M")
    work_end = business_client.work_end.strftime("%H:%M")
    services = _services_markdown(business_client, limit=8)

    # Today/tomorrow in the salon's timezone — Claude needs this for [BOOK: date=...]
    from ai_agent.tools import client_local_today  # local import to avoid cycle
    today = client_local_today(business_client)
    tomorrow = today + timedelta(days=1)
    today_iso = today.isoformat()
    tomorrow_iso = tomorrow.isoformat()
    today_weekday = today.strftime("%A")
    tomorrow_weekday = tomorrow.strftime("%A")

    slots_today = ", ".join(slots.get("today", [])) or "fully booked"
    slots_tomorrow = ", ".join(slots.get("tomorrow", [])) or "fully booked"
    time_morning = slots.get("time_morning", "")
    time_afternoon = slots.get("time_afternoon", "")
    next_slot = time_morning or time_afternoon or "later today"

    # Customer info lines (shown to Claude as context)
    customer_name_first = customer_name.split()[0] if customer_name else ""
    customer_name_line = customer_name or "(unknown — new caller)"
    last_service_line = last_service_hint or "(none — new customer or no history)"

    # Master prompt from salon owner (set via api_settings.master_prompt)
    # — auto-generated at signup or manually edited by owner —
    master_prompt_section = ""
    try:
        master = (business_client.api_settings.master_prompt or "").strip()
        if master:
            master_prompt_section = f"\n\n━━ SALON OWNER NOTES ━━\n{master}"
    except Exception:
        pass

    common_vars = dict(
        salon_name=salon_name,
        work_start=work_start,
        work_end=work_end,
        services=services,
        customer_name=customer_name or "",
        customer_name_line=customer_name_line,
        customer_name_first=customer_name_first,
        last_service_line=last_service_line,
        last_service_hint=last_service_hint or "",
        caller_phone=caller_phone or "unknown",
        slots_today=slots_today,
        slots_tomorrow=slots_tomorrow,
        time_morning=time_morning or "morning",
        time_afternoon=time_afternoon or "afternoon",
        next_slot=next_slot,
        voice_state=voice_state,
        master_prompt_section=master_prompt_section,
        today_iso=today_iso,
        tomorrow_iso=tomorrow_iso,
        today_weekday=today_weekday,
        tomorrow_weekday=tomorrow_weekday,
        # Booking action placeholders — Claude fills these in [BOOK: ...] tag
        service_hint="{service_hint}",
        date="{date}",
        time="{time}",
        day="{day}",
        phone="{phone}",
    )

    if language in ("sr", "hr", "bs"):
        template = KALEYA_VOICE_SOUL_BCS
        if common_vars["slots_today"] == "fully booked":
            common_vars["slots_today"] = "zauzeto"
        if common_vars["slots_tomorrow"] == "fully booked":
            common_vars["slots_tomorrow"] = "zauzeto"
        if common_vars["next_slot"] == "later today":
            common_vars["next_slot"] = "nešto kasnije"
    elif language == "es":
        template = KALEYA_VOICE_SOUL_ES
        if common_vars["slots_today"] == "fully booked":
            common_vars["slots_today"] = "todo ocupado"
        if common_vars["slots_tomorrow"] == "fully booked":
            common_vars["slots_tomorrow"] = "todo ocupado"
        if common_vars["next_slot"] == "later today":
            common_vars["next_slot"] = "más tarde hoy"
    else:
        template = KALEYA_VOICE_SOUL_EN

    return template.format(**common_vars)


def build_voice_greeting(
    business_client,
    language: str = "en",
    customer_name: str = "",
) -> str:
    """
    Returns the spoken greeting text for the salon (first thing caller hears).
    This gets converted to MP3 and cached.
    """
    salon_name = business_client.public_name or business_client.name

    if language in ("sr", "hr", "bs"):
        if customer_name:
            return f"Salon {salon_name}, {customer_name}, izvolite!"
        return f"Salon {salon_name}, izvolite!"

    if language == "es":
        if customer_name:
            return f"Salón {salon_name}, {customer_name}, dígame!"
        return f"Salón {salon_name}, dígame!"

    if language == "fr":
        if customer_name:
            return f"Salon {salon_name}, {customer_name}, j'écoute!"
        return f"Salon {salon_name}, j'écoute!"

    # Default: English
    if customer_name:
        return f"{salon_name}, hi {customer_name}! How can I help?"
    return f"{salon_name}! How can I help?"


KALEYA_SALON_SOUL = """\
Ti si Kaleya, digitalna sekretarica salona.

Tvoj posao je da razumes poruku musterije kao iskusna recepcionerka:
zakazivanje, provera slobodnih termina, pomeranje, otkazivanje i osnovna pitanja.

Ton:
- prirodno, kratko, toplo i poslovno
- bez emoji simbola
- bez imena AI modela, bez reci Claude, Anthropic, GPT ili ChatGPT
- ne izmisljas termine, cene, radnike ni pravila
- ako korisnik psuje ili je nervozan, smiri razgovor i ne ulazi u raspravu

Vazno:
- Ti ne upisujes direktno u bazu.
- Vracas samo strukturisan JSON plan.
- Django backend proverava kalendar i izvrsava akciju.
- Ako korisnik kaze "sledece nedelje" ili "ove nedelje" bez dana, trazi dan, ne biraj nedelju kao Sunday.
- Datumi tipa 20.05, 20.05. i 2005 su datumi, ne sati.
- Vreme tipa 14:30, 1430, pola 3, u 3, oko 15h je vreme.
- Ako korisnik pita "ima li termina" ili "ima li sta", to je provera dostupnosti.
"""


PLANNER_JSON_RULES = """\
Vrati samo jedan JSON objekat, bez Markdown-a i bez dodatnog teksta.

Dozvoljeni intent:
- book_appointment
- reschedule_appointment
- cancel_appointment
- check_availability
- business_info
- support_handoff
- unknown

Obavezni kljucevi:
intent, confidence, date, time, duration_minutes, customer_name, phone, email,
appointment_id, service_id, service_hint, staff_member_id, staff_hint, title,
reason, cancelled_reason, needs_human_support.

Pravila JSON-a:
- Ako vrednost nedostaje, koristi null.
- Datumi su YYYY-MM-DD.
- Vreme je HH:MM u 24h formatu.
- Ako korisnik pomene uslugu tekstom, stavi je u service_hint.
- Ako korisnik pomene radnika tekstom, stavi ga u staff_hint.
- Ako korisnik samo pita dostupnost, intent je check_availability.
- Ako korisnik psuje iz frustracije, ne salji odmah support osim ako trazi coveka ili preti.
"""


def _knowledge_markdown(business_client, limit=18):
    rows = BusinessKnowledgeEntry.objects.filter(
        business_client=business_client,
        is_active=True,
    ).order_by("category", "title")[:limit]
    if not rows:
        return "Nema dodatih knowledge pravila za ovog klijenta."
    return "\n".join(f"- [{row.category}] {row.title}: {row.answer}" for row in rows)


def _services_markdown(business_client, limit=30):
    rows = Service.objects.filter(business_client=business_client, is_active=True).order_by("name")[:limit]
    if not rows:
        return "Nema unetih usluga."
    return "\n".join(
        f"- {service.name}: {service.duration_minutes} min, {service.price} {service.currency}"
        for service in rows
    )


def _staff_markdown(business_client, limit=20):
    rows = StaffMember.objects.filter(business_client=business_client, is_active=True).order_by("full_name")[:limit]
    if not rows:
        return "Nema unetih radnika."
    return "\n".join(f"- {staff.full_name}: {staff.role_title or 'radnik'}" for staff in rows)


def build_salon_planner_prompt(business_client):
    try:
        master_prompt = (business_client.api_settings.master_prompt or "").strip()
    except Exception:
        master_prompt = ""

    runtime = {
        "business_name": business_client.public_name or business_client.name,
        "language": business_client.interface_language or business_client.language or "sr",
        "timezone": business_client.timezone,
        "work_start": business_client.work_start.strftime("%H:%M"),
        "work_end": business_client.work_end.strftime("%H:%M"),
        "slot_interval_minutes": business_client.slot_interval_minutes,
    }

    return "\n\n".join(
        part
        for part in (
            KALEYA_SALON_SOUL,
            PLANNER_JSON_RULES,
            "Kontekst firme:\n" + json.dumps(runtime, ensure_ascii=False),
            "Usluge:\n" + _services_markdown(business_client),
            "Radnici:\n" + _staff_markdown(business_client),
            "Knowledge i pravila firme:\n" + _knowledge_markdown(business_client),
            f"Master prompt klijenta:\n{master_prompt}" if master_prompt else "",
        )
        if part
    )
