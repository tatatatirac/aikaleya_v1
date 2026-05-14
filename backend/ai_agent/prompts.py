import json

from clients.models import BusinessKnowledgeEntry
from staff_services.models import Service, StaffMember


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
