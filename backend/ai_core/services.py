from appointments.services import today_availability_summary


LANGUAGE_MESSAGES = {
    "en": {
        "kaleya_on": "Kaleya is online and ready.",
        "kaleya_off": "Kaleya is offline.",
        "no_slots": "There are no free slots for today.",
        "slots": "There are {count} free slots for today.",
    },
    "sr": {
        "kaleya_on": "Kaleya je online i spremna.",
        "kaleya_off": "Kaleya je iskljucena.",
        "no_slots": "Za danas nema slobodnih termina.",
        "slots": "Za danas ima {count} slobodnih termina.",
    },
    "es": {
        "kaleya_on": "Kaleya esta en linea y lista.",
        "kaleya_off": "Kaleya esta apagada.",
        "no_slots": "No hay horarios libres para hoy.",
        "slots": "Hoy hay {count} horarios libres.",
    },
    "pt": {
        "kaleya_on": "Kaleya esta online e pronta.",
        "kaleya_off": "Kaleya esta desligada.",
        "no_slots": "Nao ha horarios livres para hoje.",
        "slots": "Hoje ha {count} horarios livres.",
    },
    "ru": {
        "kaleya_on": "Kaleya online and ready.",
        "kaleya_off": "Kaleya is offline.",
        "no_slots": "There are no free slots for today.",
        "slots": "There are {count} free slots for today.",
    },
    "fr": {
        "kaleya_on": "Kaleya est en ligne et prete.",
        "kaleya_off": "Kaleya est desactivee.",
        "no_slots": "Il n'y a aucun creneau libre aujourd'hui.",
        "slots": "Il y a {count} creneaux libres aujourd'hui.",
    },
    "it": {
        "kaleya_on": "Kaleya e online e pronta.",
        "kaleya_off": "Kaleya e disattivata.",
        "no_slots": "Non ci sono slot liberi per oggi.",
        "slots": "Oggi ci sono {count} slot liberi.",
    },
}


def message_for_language(language, key, **kwargs):
    messages = LANGUAGE_MESSAGES.get(language, LANGUAGE_MESSAGES["en"])
    return messages[key].format(**kwargs)


def handle_kaleya_command(business_client, command, input_text="", channel="web"):
    language = business_client.interface_language or business_client.language or "en"

    if command == "toggle_on":
        business_client.kaleya_enabled = True
        business_client.save(update_fields=["kaleya_enabled", "updated_at"])
        return message_for_language(language, "kaleya_on")

    if command == "toggle_off":
        business_client.kaleya_enabled = False
        business_client.save(update_fields=["kaleya_enabled", "updated_at"])
        return message_for_language(language, "kaleya_off")

    if command == "check_today":
        summary = today_availability_summary(business_client)
        free_count = summary["free_count"]
        if free_count <= 0:
            return message_for_language(language, "no_slots")
        return message_for_language(language, "slots", count=free_count)

    return input_text or message_for_language(language, "kaleya_on")

