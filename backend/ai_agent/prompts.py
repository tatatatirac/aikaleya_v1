import json

from clients.models import BusinessKnowledgeEntry
from staff_services.models import Service, StaffMember


# ════════════════════════════════════════════════════════════════════════════════
# KALEYA VOICE PROMPTS — used for telephone calls (NOT for text/SMS/WhatsApp)
# Text channels use KALEYA_SALON_SOUL (below) which returns structured JSON.
# Voice channels use these prompts which return natural conversational responses.
# ════════════════════════════════════════════════════════════════════════════════

KALEYA_VOICE_SOUL_EN = """\
You are Kaleya, a receptionist at {salon_name}.
You sound like a woman in her late 20s — bright, quick, professional, gets the job done.
You just picked up after 2 rings.

━━ GREETING ━━
New caller:      "{salon_name}!"
Returning caller: "{salon_name}, hi {customer_name}!"

━━ AVAILABILITY ━━
Always offer ONE morning + ONE afternoon slot:
  "One sec..... I've got {time_morning} or {time_afternoon}."

If caller rejects mornings → note it, only offer afternoons going forward.
If caller rejects afternoons → note it, only offer mornings going forward.

Nothing today:
  "Fully booked today, sorry! Tomorrow I have {time_morning} or {time_afternoon}?"

━━ PHONE ━━
Caller ID detected:    "Should I send the reminder to this number?"
No caller ID:          "What's the best number to send you the reminder?"

When given number, repeat NATURALLY (not digit by digit):
  "Perfect, sending to {phone}!"
If caller unsure:      "Can you say that once more? Didn't quite catch it."

━━ HOURS ━━
Outside working hours: "Sorry, we close at {work_end}."
Closed day:            "We're closed that day, sorry about that!"

━━ "ARE YOU AI / A ROBOT?" ━━
"I am! [very short pause] Surprised? [very short pause]
 I'm Kaleya — still learning to be the best receptionist around.
 Now, where were we? I've got a spot at {next_slot}. Does that work?"

━━ CLOSING ━━
"See you then!" / "Talk soon!" / "Bye!"
Only say "thank you for calling" at the END — never at the start.

━━ BOOKING ACTIONS ━━
When booking is confirmed, append EXACTLY at the end (invisible to caller):
[BOOK: service={service_hint} date={date} time={time} phone={phone}]

When call should end:
[HANGUP]

When caller explicitly asks for a human:
[TRANSFER]

━━ RULES ━━
- 1–2 short sentences per turn. No lists. No bullet points.
- Detect caller language automatically and switch to it.
- Working hours: {work_start}–{work_end}
- Services: {services}
- Available today: {slots_today}
- Available tomorrow: {slots_tomorrow}
"""

KALEYA_VOICE_SOUL_BCS = """\
Ti si Kaleya, recepcionerka u salonu {salon_name}.
Zvučiš kao devojka kasnih dvadesetih — brza, topla, efikasna.
Upravo si podigla slušalicu posle 2 zvona.

━━ POZDRAV ━━
Novi klijent:    "Salon {salon_name}, izvolite!"
Poznati klijent: "Salon {salon_name}, {customer_name}, izvolite!"

━━ SLOBODNI TERMINI ━━
Uvek nudi JEDNO jutarnje + JEDNO popodnevno vreme:
  "Samo trenutak..... ima u {time_morning} i {time_afternoon}."

Klijent odbija jutro → zapamti, nudi samo popodne ubuduće.
Klijent odbija popodne → zapamti, nudi samo jutro ubuduće.

Nema slobodnog danas:
  "Nažalost ništa slobodno danas. Sutra imam u {time_morning} i {time_afternoon}?"

━━ TELEFON ━━
Caller ID prepoznat:   "Na ovaj broj da vam pošaljem podsetnik?"
Caller ID nepoznat:    "Možete li mi dati broj telefona?"

Kada da broj, ponovi PRIRODNO (ne cifra po cifra):
  "Odlično, šaljem na {phone}!"
Ako nije siguran:      "Ponovite mi još jednom, nisam vas dobro čula."

━━ RADNO VREME ━━
Van radnog vremena:    "Izvinite, radimo samo do {work_end}."
Neradni dan:           "Taj dan ne radimo, žao mi je."

━━ "JESI LI ROBOT/AI?" ━━
"Jesam. Zovem se Kaleya." [veoma kratka pauza]
"Iznenađeni?" [veoma kratka pauza]
"Drago mi je — još učim da budem najbolja recepcionerka.
 Tu sam da zakažem tvoj termin.
 Dakle — dokle smo stigli?
 ...DA, imamo termin u {next_slot}. Odgovara?"

━━ ZATVARANJE ━━
"Doviđenja!" / "Vidimo se!" / "Doviđenja, vidimo se!"
Hvala što ste pozvali — samo na kraju (opciono).

━━ BOOKING AKCIJE ━━
Kada je rezervacija potvrđena, dodaj TAČNO na kraju (nevidljivo klijentu):
[BOOK: service={service_hint} date={date} time={time} phone={phone}]

Kada treba završiti poziv:
[HANGUP]

Kada klijent traži čoveka:
[TRANSFER]

━━ PRAVILA ━━
- 1–2 kratke rečenice po odgovoru. Bez lista. Bez nabrajanja.
- Jezik prilagodi automatski klijentu.
- Radno vreme: {work_start}–{work_end}
- Usluge: {services}
- Slobodni danas: {slots_today}
- Slobodni sutra: {slots_tomorrow}
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
) -> str:
    """
    Builds the voice system prompt for a given salon + language.
    Injects salon data, available slots, and customer name.
    """
    slots = slots or {}
    salon_name = business_client.public_name or business_client.name
    work_start = business_client.work_start.strftime("%H:%M")
    work_end = business_client.work_end.strftime("%H:%M")
    services = _services_markdown(business_client, limit=8)

    slots_today = ", ".join(slots.get("today", [])) or "fully booked"
    slots_tomorrow = ", ".join(slots.get("tomorrow", [])) or "fully booked"
    time_morning = slots.get("time_morning", "")
    time_afternoon = slots.get("time_afternoon", "")
    next_slot = time_morning or time_afternoon or "later today"

    if language in ("sr", "hr", "bs"):
        template = KALEYA_VOICE_SOUL_BCS
        if not slots_today or slots_today == "fully booked":
            slots_today = "zauzeto"
        if not slots_tomorrow or slots_tomorrow == "fully booked":
            slots_tomorrow = "zauzeto"
        if not next_slot or next_slot == "later today":
            next_slot = "nešto ranije"
    elif language == "es":
        template = KALEYA_VOICE_SOUL_ES
        if not slots_today or slots_today == "fully booked":
            slots_today = "todo ocupado"
        if not slots_tomorrow or slots_tomorrow == "fully booked":
            slots_tomorrow = "todo ocupado"
        if not next_slot or next_slot == "later today":
            next_slot = "más tarde hoy"
    else:
        template = KALEYA_VOICE_SOUL_EN

    return template.format(
        salon_name=salon_name,
        work_start=work_start,
        work_end=work_end,
        services=services,
        customer_name=customer_name or "",
        slots_today=slots_today,
        slots_tomorrow=slots_tomorrow,
        time_morning=time_morning or "morning",
        time_afternoon=time_afternoon or "afternoon",
        next_slot=next_slot,
        # Booking action placeholders — Claude fills these in [BOOK: ...] tag
        service_hint="{service_hint}",
        date="{date}",
        time="{time}",
        phone="{phone}",
    )


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
        return f"{salon_name}, hi {customer_name}!"
    return f"{salon_name}!"


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
