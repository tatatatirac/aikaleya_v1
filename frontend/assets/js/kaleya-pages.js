const PAGE_LANGS = {
    sr: {
        back_home: 'Nazad na početnu',
        demo_badge: 'Klikabilan demo',
        demo_title: 'Kako Kaleya radi u praksi',
        demo_lead: 'Mobilni i laptop prikaz su demo okruženje. Dugmad su klikabilna, a glas se pušta iz MP3 fajla.',
        mobile_title: 'Klijent app',
        laptop_title: 'Klijent app',
        voice_cta: 'Pusti Kaleya glas',
        schedule: 'Zakaži',
        cancel: 'Otkaži',
        check: 'Proveri',
        status_ready: 'Spremna za razgovor',
        status_scheduled: 'Demo termin je zakazan za 15:00',
        status_cancelled: 'Demo sastanak je otkazan',
        status_checked: 'Danas ima 3 slobodna termina',
        online: 'Online',
        offline: 'Offline',
        nav_home: 'Početna',
        nav_calendar: 'Kalendar',
        nav_settings: 'Podešavanja',
        calendar_title: 'Kalendar',
        month: 'Mesec',
        day: 'Dan',
        free: 'Slobodno',
        booked: 'Zakazano',
        cancelled_status: 'Otkazano',
        moved_status: 'Pomereno',
        calls: 'Pozivi',
        clients: 'Klijenti',
        channels: 'Kanali',
        recent: 'Poslednje demo aktivnosti',
        reg_badge: 'Registracija i plaćanje',
        reg_title: 'Aktiviraj paket',
        reg_lead: 'Ova strana je frontend priprema za plaćanje i registraciju klijenta. Prava naplata ide kroz backend.',
        company: 'Naziv firme',
        name: 'Ime i prezime',
        email: 'Email',
        password: 'Lozinka',
        phone: 'Telefon',
        country: 'Država',
        note: 'Napomena',
        start_trial: 'Probaj 14 dana',
        continue_checkout: 'Probaj 14 dana - nastavi na checkout',
        registration_creating: 'Pripremam Kaleya checkout...',
        registration_success: 'Nalog je kreiran. Otvaram Kaleya app...',
        registration_failed: 'Registracija nije uspela.',
        contact_custom: 'BusinessPro+ je custom paket. Posaljite zahtev, pa se dogovaramo oko integracija, cene i roka.',
        payment_note: 'Za produkciju ovde se povezuje payment provider, backend registracija, email potvrda i webhook za aktivaciju paketa.',
        checkout_badge: 'Sigurna naplata',
        checkout_title: 'Kaleya checkout',
        checkout_lead: 'Karticna naplata za Kaleya pakete kroz sigurnu obradu placanja.',
        checkout_package: 'Paket',
        checkout_amount: 'Iznos',
        checkout_today: 'Danas',
        checkout_after_trial: 'Posle probnog perioda',
        checkout_trial: 'Probni period',
        checkout_card: 'Placanje karticom',
        checkout_card_ready: 'Sigurna polja za karticu pojavice se ovde kada je payment sandbox podesen.',
        checkout_button: 'Nastavi na sigurnu karticnu naplatu',
        checkout_button_pending: 'Karticna polja su sledeca integracija',
        checkout_checking: 'Proveravam payment sandbox podesavanja...',
        checkout_ready: 'Payment sandbox je spreman za karticnu naplatu.',
        checkout_not_ready: 'Payment sandbox jos nije kompletno podesen u .env fajlu.',
        checkout_file_mode: 'Checkout radi preko backend adrese: http://127.0.0.1:8000/checkout.html',
        checkout_next_step: 'Sledeci korak je povezivanje sigurnih karticnih polja za stvarni unos kartice.',
        checkout_card_fields_pending: 'Payment planovi su spremni. Sledece povezujemo sigurna karticna polja na Kaleya strani, bez slanja korisnika na login stranu procesora.',
        checkout_trial_note: 'Danas je 0$. Posle 14 dana automatski se naplacuje izabrani paket, osim ako se otkaze pre kraja probnog perioda.',
        god_badge: 'Buy All',
        god_title: 'GOD MODE paket',
        god_lead: 'Kupovina kompletnog Kaleya projekta sa frontendom, backendom, hosting pripremom, domenom i deploy dokumentacijom.',
        god_cta: 'Kontakt za Buy All',
        privacy_title: 'Politika privatnosti',
        privacy_lead: 'Ovaj tekst je standardna početna verzija i treba ga pravno proveriti pre produkcije.',
        terms_title: 'Uslovi korišćenja',
        terms_lead: 'Ovaj tekst je standardna početna verzija uslova za SaaS servis i treba ga pravno proveriti pre produkcije.',
        footer_privacy: 'Privatnost',
        footer_terms: 'Uslovi'
    },
    en: {
        back_home: 'Back home',
        demo_badge: 'Clickable demo',
        demo_title: 'How Kaleya works in practice',
        demo_lead: 'Mobile and laptop views are a demo environment. Buttons are clickable and the voice plays from an MP3 file.',
        mobile_title: 'Client app',
        laptop_title: 'Client app',
        voice_cta: 'Play Kaleya voice',
        schedule: 'Schedule',
        cancel: 'Cancel',
        check: 'Check',
        status_ready: 'Ready to talk',
        status_scheduled: 'Demo appointment is scheduled for 3 PM',
        status_cancelled: 'Demo meeting has been cancelled',
        status_checked: 'There are 3 free slots today',
        online: 'Online',
        offline: 'Offline',
        nav_home: 'Home',
        nav_calendar: 'Calendar',
        nav_settings: 'Settings',
        calendar_title: 'Calendar',
        month: 'Month',
        day: 'Day',
        free: 'Free',
        booked: 'Booked',
        cancelled_status: 'Cancelled',
        moved_status: 'Moved',
        calls: 'Calls',
        clients: 'Clients',
        channels: 'Channels',
        recent: 'Recent demo activity',
        reg_badge: 'Registration and payment',
        reg_title: 'Activate package',
        reg_lead: 'This page is frontend preparation for client registration and payment. Real billing runs through the backend.',
        company: 'Company name',
        name: 'Full name',
        email: 'Email',
        password: 'Password',
        phone: 'Phone',
        country: 'Country',
        note: 'Note',
        start_trial: 'Try 14 days',
        continue_checkout: 'Try 14 days - continue to checkout',
        registration_creating: 'Preparing Kaleya checkout...',
        registration_success: 'Account created. Opening Kaleya app...',
        registration_failed: 'Registration failed.',
        contact_custom: 'BusinessPro+ is a custom package. Send the request and we will agree on integrations, price and timeline.',
        payment_note: 'In production this connects to a payment provider, backend registration, email confirmation and activation webhook.',
        checkout_badge: 'Secure checkout',
        checkout_title: 'Kaleya checkout',
        checkout_lead: 'Card-first checkout for Kaleya packages through secure payment processing.',
        checkout_package: 'Package',
        checkout_amount: 'Amount',
        checkout_today: 'Today',
        checkout_after_trial: 'After trial',
        checkout_trial: 'Trial',
        checkout_card: 'Card payment',
        checkout_card_ready: 'Secure card fields will appear here when payment sandbox is configured.',
        checkout_button: 'Continue to secure card checkout',
        checkout_button_pending: 'Card fields are the next integration',
        checkout_checking: 'Checking payment sandbox configuration...',
        checkout_ready: 'Payment sandbox is ready for card checkout.',
        checkout_not_ready: 'Payment sandbox is not fully configured in the .env file yet.',
        checkout_file_mode: 'Checkout works through the backend address: http://127.0.0.1:8000/checkout.html',
        checkout_next_step: 'Next step is wiring secure card fields for real card entry.',
        checkout_card_fields_pending: 'Payment plans are ready. Next we connect secure card fields on the Kaleya page, without sending the customer to a processor login page.',
        checkout_trial_note: 'Today is $0. After 14 days the selected package is automatically billed unless cancelled before the trial ends.',
        god_badge: 'Buy All',
        god_title: 'GOD MODE package',
        god_lead: 'Purchase the complete Kaleya project with frontend, backend, hosting preparation, domain and deployment documentation.',
        god_cta: 'Contact for Buy All',
        privacy_title: 'Privacy Policy',
        privacy_lead: 'Last updated: May 2026. Please read this policy carefully before using Kaleya.',
        terms_title: 'Terms of Service',
        terms_lead: 'Last updated: May 2026. By using Kaleya you agree to these Terms of Service.',
        footer_privacy: 'Privacy',
        footer_terms: 'Terms'
    },
    es: {
        back_home: 'Volver al inicio',
        demo_badge: 'Demo clicable',
        demo_title: 'Cómo funciona Kaleya en la práctica',
        demo_lead: 'Las vistas móvil y laptop son un entorno demo. Los botones son clicables y la voz se reproduce desde un archivo MP3.',
        mobile_title: 'App del cliente',
        laptop_title: 'App del cliente',
        voice_cta: 'Reproducir voz Kaleya',
        schedule: 'Agendar',
        cancel: 'Cancelar',
        check: 'Revisar',
        status_ready: 'Lista para hablar',
        status_scheduled: 'La cita demo está agendada a las 15:00',
        status_cancelled: 'La reunión demo fue cancelada',
        status_checked: 'Hoy hay 3 horarios libres',
        online: 'Online',
        offline: 'Offline',
        nav_home: 'Inicio',
        nav_calendar: 'Calendario',
        nav_settings: 'Ajustes',
        calendar_title: 'Calendario',
        month: 'Mes',
        day: 'Día',
        free: 'Libre',
        booked: 'Agendado',
        cancelled_status: 'Cancelado',
        moved_status: 'Movido',
        calls: 'Llamadas',
        clients: 'Clientes',
        channels: 'Canales',
        recent: 'Actividad demo reciente',
        reg_badge: 'Registro y pago',
        reg_title: 'Activar paquete',
        reg_lead: 'Esta página prepara el frontend para registro y pago. La facturación real va por backend.',
        company: 'Empresa',
        name: 'Nombre completo',
        email: 'Email',
        password: 'Contraseña',
        phone: 'Teléfono',
        country: 'País',
        note: 'Nota',
        start_trial: 'Probar 14 días',
        registration_creating: 'Creando la cuenta Kaleya...',
        registration_success: 'Cuenta creada. Abriendo la app Kaleya...',
        registration_failed: 'El registro falló.',
        contact_custom: 'BusinessPro+ es un paquete a medida. Envíe la solicitud y acordaremos integraciones, precio y plazo.',
        payment_note: 'En producción se conecta proveedor de pago, registro backend, confirmación por email y webhook de activación.',
        god_badge: 'Buy All',
        god_title: 'Paquete GOD MODE',
        god_lead: 'Compra el proyecto Kaleya completo con frontend, backend, preparación de hosting, dominio y documentación de despliegue.',
        god_cta: 'Contacto para Buy All',
        privacy_title: 'Política de privacidad',
        privacy_lead: 'Este texto es una versión inicial estándar y debe revisarse legalmente antes de producción.',
        terms_title: 'Términos de uso',
        terms_lead: 'Este texto es una versión inicial estándar para SaaS y debe revisarse legalmente antes de producción.',
        footer_privacy: 'Privacidad',
        footer_terms: 'Términos'
    },
    pt: {
        back_home: 'Voltar ao início',
        demo_badge: 'Demo clicável',
        demo_title: 'Como Kaleya funciona na prática',
        demo_lead: 'As visualizações mobile e laptop são um ambiente demo. Os botões são clicáveis e a voz toca por MP3.',
        mobile_title: 'App do cliente',
        laptop_title: 'App do cliente',
        voice_cta: 'Tocar voz Kaleya',
        schedule: 'Agendar',
        cancel: 'Cancelar',
        check: 'Verificar',
        status_ready: 'Pronta para conversar',
        status_scheduled: 'O horário demo foi agendado para 15:00',
        status_cancelled: 'A reunião demo foi cancelada',
        status_checked: 'Hoje há 3 horários livres',
        online: 'Online',
        offline: 'Offline',
        nav_home: 'Início',
        nav_calendar: 'Calendário',
        nav_settings: 'Ajustes',
        calendar_title: 'Calendário',
        month: 'Mês',
        day: 'Dia',
        free: 'Livre',
        booked: 'Agendado',
        cancelled_status: 'Cancelado',
        moved_status: 'Remarcado',
        calls: 'Chamadas',
        clients: 'Clientes',
        channels: 'Canais',
        recent: 'Atividade demo recente',
        reg_badge: 'Registro e pagamento',
        reg_title: 'Ativar pacote',
        reg_lead: 'Esta página prepara o frontend para registro e pagamento. A cobrança real passa pelo backend.',
        company: 'Empresa',
        name: 'Nome completo',
        email: 'Email',
        password: 'Senha',
        phone: 'Telefone',
        country: 'País',
        note: 'Nota',
        start_trial: 'Testar 14 dias',
        registration_creating: 'Criando a conta Kaleya...',
        registration_success: 'Conta criada. Abrindo o app Kaleya...',
        registration_failed: 'O registro falhou.',
        contact_custom: 'BusinessPro+ é um pacote customizado. Envie o pedido e combinaremos integrações, preço e prazo.',
        payment_note: 'Em produção conecta provedor de pagamento, registro backend, confirmação por email e webhook de ativação.',
        god_badge: 'Buy All',
        god_title: 'Pacote GOD MODE',
        god_lead: 'Compra do projeto Kaleya completo com frontend, backend, preparação de hosting, domínio e documentação de deploy.',
        god_cta: 'Contato para Buy All',
        privacy_title: 'Política de privacidade',
        privacy_lead: 'Este texto é uma versão inicial padrão e deve ser revisado juridicamente antes da produção.',
        terms_title: 'Termos de uso',
        terms_lead: 'Este texto é uma versão inicial padrão para SaaS e deve ser revisado juridicamente antes da produção.',
        footer_privacy: 'Privacidade',
        footer_terms: 'Termos'
    },
    ru: {
        back_home: 'Назад на главную',
        demo_badge: 'Кликабельное демо',
        demo_title: 'Как Kaleya работает на практике',
        demo_lead: 'Мобильный и laptop вид являются demo средой. Кнопки кликабельны, а голос воспроизводится из MP3 файла.',
        mobile_title: 'Клиентское приложение',
        laptop_title: 'Клиентское приложение',
        voice_cta: 'Воспроизвести голос Kaleya',
        schedule: 'Записать',
        cancel: 'Отменить',
        check: 'Проверить',
        status_ready: 'Готова к разговору',
        status_scheduled: 'Demo запись назначена на 15:00',
        status_cancelled: 'Demo встреча отменена',
        status_checked: 'Сегодня есть 3 свободных времени',
        online: 'Online',
        offline: 'Offline',
        nav_home: 'Главная',
        nav_calendar: 'Календарь',
        nav_settings: 'Настройки',
        calendar_title: 'Календарь',
        month: 'Месяц',
        day: 'День',
        free: 'Свободно',
        booked: 'Записано',
        cancelled_status: 'Отменено',
        moved_status: 'Перенесено',
        calls: 'Звонки',
        clients: 'Клиенты',
        channels: 'Каналы',
        recent: 'Последние demo действия',
        reg_badge: 'Регистрация и оплата',
        reg_title: 'Активировать пакет',
        reg_lead: 'Эта страница является frontend подготовкой для регистрации и оплаты. Реальная оплата идет через backend.',
        company: 'Компания',
        name: 'Имя и фамилия',
        email: 'Email',
        password: 'Пароль',
        phone: 'Телефон',
        country: 'Страна',
        note: 'Примечание',
        start_trial: '14 дней бесплатно',
        registration_creating: 'Создаю аккаунт Kaleya...',
        registration_success: 'Аккаунт создан. Открываю приложение Kaleya...',
        registration_failed: 'Регистрация не удалась.',
        contact_custom: 'BusinessPro+ это индивидуальный пакет. Отправьте запрос, и мы согласуем интеграции, цену и сроки.',
        payment_note: 'В продакшене здесь подключается платежный провайдер, backend регистрация, email подтверждение и webhook активации.',
        god_badge: 'Buy All',
        god_title: 'Пакет GOD MODE',
        god_lead: 'Покупка полного проекта Kaleya с frontend, backend, подготовкой хостинга, доменом и deploy документацией.',
        god_cta: 'Контакт для Buy All',
        privacy_title: 'Политика конфиденциальности',
        privacy_lead: 'Это стандартная начальная версия, которую нужно юридически проверить перед продакшеном.',
        terms_title: 'Условия использования',
        terms_lead: 'Это стандартная начальная версия условий для SaaS, которую нужно юридически проверить перед продакшеном.',
        footer_privacy: 'Конфиденциальность',
        footer_terms: 'Условия'
    }
};

PAGE_LANGS.fr = {
    ...PAGE_LANGS.en,
    back_home: 'Retour accueil',
    demo_badge: 'Demo cliquable',
    demo_title: 'Comment Kaleya fonctionne en pratique',
    demo_lead: 'Les vues mobile et ordinateur sont un environnement demo. Les boutons sont cliquables et la voix se lance depuis un fichier MP3.',
    mobile_title: 'App client',
    laptop_title: 'App client',
    voice_cta: 'Lire la voix Kaleya',
    schedule: 'Planifier',
    cancel: 'Annuler',
    check: 'Verifier',
    status_ready: 'Prete a parler',
    status_scheduled: 'Le rendez-vous demo est planifie a 15:00',
    status_cancelled: 'Le rendez-vous demo a ete annule',
    status_checked: 'Il y a 3 creneaux libres aujourd hui',
    nav_home: 'Accueil',
    nav_calendar: 'Calendrier',
    nav_settings: 'Reglages',
    calendar_title: 'Calendrier',
    month: 'Mois',
    day: 'Jour',
    free: 'Libre',
    booked: 'Reserve',
    cancelled_status: 'Annule',
    moved_status: 'Deplace',
    calls: 'Appels',
    clients: 'Clients',
    channels: 'Canaux',
    recent: 'Activite demo recente',
    reg_badge: 'Inscription et paiement',
    reg_title: 'Activer le forfait',
    reg_lead: 'Cette page prepare le frontend pour l inscription client et le paiement. La facturation reelle passe par le backend.',
    company: 'Nom de l entreprise',
    name: 'Nom complet',
    phone: 'Telephone',
    country: 'Pays',
    note: 'Note',
    start_trial: 'Essayer 14 jours',
    payment_note: 'En production, cette page se connecte au paiement, a l inscription backend, a la confirmation email et au webhook d activation.',
    god_title: 'Forfait GOD MODE',
    god_lead: 'Achat du projet Kaleya complet avec frontend, backend, preparation hosting, domaine et documentation de deploiement.',
    god_cta: 'Contact pour Buy All',
    privacy_title: 'Politique de confidentialite',
    privacy_lead: 'Ce texte est une version standard de depart et doit etre verifie juridiquement avant la production.',
    terms_title: 'Conditions d utilisation',
    terms_lead: 'Ce texte est une version standard de depart pour un service SaaS et doit etre verifie juridiquement avant la production.',
    footer_privacy: 'Confidentialite',
    footer_terms: 'Conditions'
};

PAGE_LANGS.it = {
    ...PAGE_LANGS.en,
    back_home: 'Torna alla home',
    demo_badge: 'Demo cliccabile',
    demo_title: 'Come funziona Kaleya in pratica',
    demo_lead: 'Le viste mobile e laptop sono un ambiente demo. I pulsanti sono cliccabili e la voce parte da un file MP3.',
    mobile_title: 'App cliente',
    laptop_title: 'App cliente',
    voice_cta: 'Riproduci voce Kaleya',
    schedule: 'Prenota',
    cancel: 'Annulla',
    check: 'Controlla',
    status_ready: 'Pronta a parlare',
    status_scheduled: 'L appuntamento demo e prenotato per le 15:00',
    status_cancelled: 'La riunione demo e stata annullata',
    status_checked: 'Oggi ci sono 3 slot liberi',
    nav_home: 'Home',
    nav_calendar: 'Calendario',
    nav_settings: 'Impostazioni',
    calendar_title: 'Calendario',
    month: 'Mese',
    day: 'Giorno',
    free: 'Libero',
    booked: 'Prenotato',
    cancelled_status: 'Annullato',
    moved_status: 'Spostato',
    calls: 'Chiamate',
    clients: 'Clienti',
    channels: 'Canali',
    recent: 'Attivita demo recente',
    reg_badge: 'Registrazione e pagamento',
    reg_title: 'Attiva pacchetto',
    reg_lead: 'Questa pagina prepara il frontend per registrazione cliente e pagamento. La fatturazione reale passa dal backend.',
    company: 'Nome azienda',
    name: 'Nome completo',
    phone: 'Telefono',
    country: 'Paese',
    note: 'Nota',
    start_trial: 'Prova 14 giorni',
    payment_note: 'In produzione qui si collega payment provider, registrazione backend, conferma email e webhook di attivazione.',
    god_title: 'Pacchetto GOD MODE',
    god_lead: 'Acquisto del progetto Kaleya completo con frontend, backend, preparazione hosting, dominio e documentazione deploy.',
    god_cta: 'Contatto per Buy All',
    privacy_title: 'Privacy Policy',
    privacy_lead: 'Questo testo e una versione standard iniziale e deve essere verificato legalmente prima della produzione.',
    terms_title: 'Termini di servizio',
    terms_lead: 'Questo testo e una versione standard iniziale per un servizio SaaS e deve essere verificato legalmente prima della produzione.',
    footer_privacy: 'Privacy',
    footer_terms: 'Termini'
};

PAGE_LANGS.de = {
    ...PAGE_LANGS.en,
    back_home: 'Zurueck zur Startseite',
    demo_badge: 'Klickbare Demo',
    demo_title: 'So funktioniert Kaleya in der Praxis',
    demo_lead: 'Mobile und Laptop Ansicht sind eine Demo Umgebung. Die Buttons sind klickbar und die Stimme wird aus einer MP3 Datei abgespielt.',
    mobile_title: 'Kunden App',
    laptop_title: 'Kunden App',
    voice_cta: 'Kaleya Stimme abspielen',
    schedule: 'Buchen',
    cancel: 'Absagen',
    check: 'Pruefen',
    status_ready: 'Bereit zum Gespraech',
    status_scheduled: 'Demo Termin ist fuer 15:00 gebucht',
    status_cancelled: 'Demo Termin wurde abgesagt',
    status_checked: 'Heute gibt es 3 freie Termine',
    online: 'Online',
    offline: 'Offline',
    nav_home: 'Start',
    nav_calendar: 'Kalender',
    nav_settings: 'Einstellungen',
    calendar_title: 'Kalender',
    month: 'Monat',
    day: 'Tag',
    free: 'Frei',
    booked: 'Gebucht',
    cancelled_status: 'Abgesagt',
    moved_status: 'Verschoben',
    calls: 'Anrufe',
    clients: 'Kunden',
    channels: 'Kanaele',
    recent: 'Letzte Demo Aktivitaeten',
    reg_badge: 'Registrierung und Zahlung',
    reg_title: 'Paket aktivieren',
    reg_lead: 'Diese Seite ist die Frontend Vorbereitung fuer Registrierung und Zahlung. Echte Abrechnung laeuft ueber das Backend.',
    company: 'Firmenname',
    name: 'Vollstaendiger Name',
    email: 'Email',
    password: 'Passwort',
    phone: 'Telefon',
    country: 'Land',
    note: 'Notiz',
    start_trial: '14 Tage testen',
    registration_creating: 'Kaleya Konto wird erstellt...',
    registration_success: 'Konto erstellt. Kaleya App wird geoeffnet...',
    registration_failed: 'Registrierung fehlgeschlagen.',
    contact_custom: 'BusinessPro+ ist ein Custom Paket. Senden Sie eine Anfrage, dann stimmen wir Integrationen, Preis und Zeitplan ab.',
    payment_note: 'In Produktion werden hier Payment Provider, Backend Registrierung, Email Bestaetigung und Aktivierungs Webhook verbunden.',
    god_badge: 'Buy All',
    god_title: 'GOD MODE Paket',
    god_lead: 'Kauf des kompletten Kaleya Projekts mit Frontend, Backend, Hosting Vorbereitung, Domain und Deploy Dokumentation.',
    god_cta: 'Kontakt fuer Buy All',
    privacy_title: 'Datenschutz',
    privacy_lead: 'Dieser Text ist eine Standard Startversion und sollte vor Produktion rechtlich geprueft werden.',
    terms_title: 'Nutzungsbedingungen',
    terms_lead: 'Dieser Text ist eine Standard Startversion fuer einen SaaS Service und sollte vor Produktion rechtlich geprueft werden.',
    footer_privacy: 'Datenschutz',
    footer_terms: 'Bedingungen'
};

const PAGE_AUDIO = {
    sr: 'assets/audio/kaleya-demo-sr.mp3',
    en: 'assets/audio/kaleya-demo-en.mp3',
    es: 'assets/audio/kaleya-demo-es.mp3',
    pt: 'assets/audio/kaleya-demo-pt.mp3',
    ru: 'assets/audio/kaleya-demo-ru.mp3',
    fr: 'assets/audio/kaleya-demo-fr.mp3',
    it: 'assets/audio/kaleya-demo-it.mp3',
    de: 'assets/audio/kaleya-demo-en.mp3'
};

const WORK_HOURS = ['09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30'];
const DEMO_EVENT_PATTERN = {
    3: [{ time: '10:00', titleKey: 'person1', status: 'booked' }],
    5: [{ time: '09:00', titleKey: 'person2', status: 'booked' }, { time: '13:00', titleKey: 'person3', status: 'cancelled' }],
    10: [{ time: '11:00', titleKey: 'business1', status: 'moved' }, { time: '15:00', titleKey: 'person4', status: 'booked' }],
    18: [{ time: '12:00', titleKey: 'person5', status: 'booked' }],
    24: [{ time: '09:00', titleKey: 'team', status: 'moved' }, { time: '14:00', titleKey: 'checkup', status: 'booked' }],
    26: [{ time: '10:00', titleKey: 'exam', status: 'booked' }, { time: '15:00', titleKey: 'consult', status: 'cancelled' }]
};

const HOME_DEMO_EVENTS = [
    { time: '09:00', titleKey: 'person1', status: 'booked' },
    { time: '12:00', titleKey: 'person5', status: 'moved' },
    { time: '15:00', titleKey: 'person3', status: 'cancelled' }
];

const DEMO_NAMES = {
    sr: {
        person1: 'Ana Jović',
        person2: 'Dr. Petrović',
        person3: 'Milica Jovanović',
        person4: 'Novi klijent',
        person5: 'Marko Petrović',
        business1: 'Salon Bella',
        team: 'Tim sastanak',
        checkup: 'Kontrola',
        exam: 'Pregled',
        consult: 'Konsultacije'
    },
    en: {
        person1: 'Emily Carter',
        person2: 'Dr. Michael Johnson',
        person3: 'Sarah Miller',
        person4: 'New client',
        person5: 'David Anderson',
        business1: 'Bella Studio',
        team: 'Team meeting',
        checkup: 'Follow-up',
        exam: 'Consultation',
        consult: 'Strategy call'
    },
    es: {
        person1: 'Lucía García',
        person2: 'Dr. Alejandro Ruiz',
        person3: 'María Fernández',
        person4: 'Nuevo cliente',
        person5: 'Carlos Martínez',
        business1: 'Salon Bella',
        team: 'Reunión de equipo',
        checkup: 'Control',
        exam: 'Revisión',
        consult: 'Consulta'
    },
    pt: {
        person1: 'Ana Silva',
        person2: 'Dr. João Pereira',
        person3: 'Mariana Costa',
        person4: 'Novo cliente',
        person5: 'Pedro Santos',
        business1: 'Studio Bella',
        team: 'Reunião da equipe',
        checkup: 'Controle',
        exam: 'Consulta',
        consult: 'Orientação'
    },
    ru: {
        person1: 'Анна Иванова',
        person2: 'Др. Алексей Петров',
        person3: 'Мария Смирнова',
        person4: 'Новый клиент',
        person5: 'Дмитрий Волков',
        business1: 'Студия Bella',
        team: 'Встреча команды',
        checkup: 'Контроль',
        exam: 'Осмотр',
        consult: 'Консультация'
    },
    fr: {
        person1: 'Camille Martin',
        person2: 'Dr. Thomas Bernard',
        person3: 'Sophie Dubois',
        person4: 'Nouveau client',
        person5: 'Julien Moreau',
        business1: 'Studio Bella',
        team: 'Reunion equipe',
        checkup: 'Controle',
        exam: 'Rendez-vous',
        consult: 'Consultation'
    },
    it: {
        person1: 'Giulia Rossi',
        person2: 'Dr. Marco Bianchi',
        person3: 'Sofia Romano',
        person4: 'Nuovo cliente',
        person5: 'Luca Ferrari',
        business1: 'Studio Bella',
        team: 'Riunione team',
        checkup: 'Controllo',
        exam: 'Visita',
        consult: 'Consulenza'
    },
    de: {
        person1: 'Anna Schneider',
        person2: 'Dr. Lukas Weber',
        person3: 'Sophie Mueller',
        person4: 'Neuer Kunde',
        person5: 'Max Fischer',
        business1: 'Studio Bella',
        team: 'Teammeeting',
        checkup: 'Kontrolle',
        exam: 'Beratung',
        consult: 'Konsultation'
    }
};

const PAGE_LEGAL = {
    privacy: {
        sr: [
            ['Koje podatke prikupljamo', 'Kaleya može prikupljati poslovne kontakt podatke, podatke za registraciju naloga, informacije o izabranom paketu i tehničke podatke potrebne za rad servisa.'],
            ['Kako koristimo podatke', 'Podatke koristimo za registraciju, pružanje usluge, komunikaciju sa klijentom, naplatu, podršku i bezbednost sistema.'],
            ['API i glasovni servisi', 'AI i voice obrada se izvršava kroz backend integracije. API ključevi ne smeju biti čuvani u frontend kodu i u produkciji se drže u sigurnom backend okruženju.'],
            ['Zadržavanje podataka', 'Podaci se čuvaju dok postoji poslovni odnos ili zakonska obaveza čuvanja. Klijent može zatražiti izmenu ili brisanje podataka kada je to primenjivo.'],
            ['Kontakt', 'Za pitanja o privatnosti kontaktirajte hello@aikaleya.com. Ovaj tekst treba pravno proveriti pre javnog lansiranja.']
        ],
        en: [
            ['Information We Collect', 'We collect information you provide directly: business name, contact name, email address, phone number, password and country when you register. We also collect usage data (pages visited, features used, session timestamps), technical data (IP address, browser type, device identifiers) and billing information processed by our payment provider. Voice and AI interaction logs may be stored to improve service quality and for audit purposes.'],
            ['How We Use Your Information', 'We use your information to: create and manage your account; deliver and improve the Kaleya service; process payments and send billing communications; send service notifications and support responses; detect fraud and maintain platform security; comply with legal obligations. We do not sell your personal information to third parties.'],
            ['Third-Party Services', 'Kaleya uses the following third-party processors who may handle your data: (1) Anthropic — AI language model processing (your messages are sent to Anthropic API to generate responses); (2) ElevenLabs — voice synthesis for AI replies; (3) Lemon Squeezy — payment processing and subscription management (acts as Merchant of Record); (4) Sentry — error monitoring and diagnostics. Each processor is bound by their own data processing agreements and privacy policies.'],
            ['Cookies and Tracking', 'Kaleya uses essential cookies for authentication (session token) and preference storage (language, theme). If you select "Accept all", we may also use analytics cookies. You can manage your cookie preference at any time using the banner at the bottom of this page. We do not use advertising cookies or cross-site tracking.'],
            ['Data Retention', 'We retain your account data for as long as your subscription is active, plus up to 30 days after cancellation to allow account recovery. After that period, personal data is permanently deleted. Billing records may be retained for up to 7 years as required by law. You can request immediate deletion by submitting an account deletion request from your dashboard.'],
            ['Your Rights (GDPR & CCPA)', 'Depending on your location, you have the right to: access a copy of your personal data (use the Export function in your dashboard); correct inaccurate data; request deletion of your data; object to or restrict certain processing; data portability. California residents have the additional right to know what personal information is sold or disclosed (we do not sell personal information). To exercise any right, contact hello@aikaleya.com. We will respond within 30 days.'],
            ['Data Security', 'We use industry-standard safeguards: HTTPS/TLS encryption in transit, hashed passwords, httpOnly authentication tokens, and server-side secrets management. API keys are never exposed in frontend code. Despite these measures, no system is completely secure. We encourage you to use a strong, unique password.'],
            ['Children', 'Kaleya is a business service intended for users 18 years of age or older. We do not knowingly collect personal information from children under 13.'],
            ['Changes to This Policy', 'We may update this Privacy Policy. When we do, we will update the date at the top and notify active users by email. Continued use of the service after changes constitutes acceptance.'],
            ['Contact', 'For privacy questions, data requests or concerns: hello@aikaleya.com · aikaleya.com. This policy was last updated May 2026 and should be reviewed by a qualified attorney before commercial launch.']
        ],
        es: [
            ['Datos que recopilamos', 'Kaleya puede recopilar datos de contacto empresarial, datos de registro, información del paquete elegido y datos técnicos necesarios para operar el servicio.'],
            ['Cómo usamos los datos', 'Usamos los datos para registro, prestación del servicio, comunicación, facturación, soporte y seguridad del sistema.'],
            ['API y servicios de voz', 'El procesamiento de IA y voz se realiza mediante integraciones backend. Las claves API no deben guardarse en el frontend y en producción se mantienen en backend seguro.'],
            ['Retención de datos', 'Los datos se conservan mientras exista relación comercial u obligación legal. El cliente puede solicitar corrección o eliminación cuando corresponda.'],
            ['Contacto', 'Para preguntas de privacidad contacte hello@aikaleya.com. Este texto debe revisarse legalmente antes del lanzamiento público.']
        ],
        pt: [
            ['Dados que coletamos', 'Kaleya pode coletar dados de contato empresarial, dados de registro, informações do pacote escolhido e dados técnicos necessários para operar o serviço.'],
            ['Como usamos os dados', 'Usamos os dados para registro, entrega do serviço, comunicação, cobrança, suporte e segurança do sistema.'],
            ['API e serviços de voz', 'O processamento de IA e voz ocorre por integrações backend. Chaves API não devem ficar no frontend e em produção ficam em ambiente backend seguro.'],
            ['Retenção de dados', 'Os dados são mantidos enquanto houver relação comercial ou obrigação legal. O cliente pode solicitar correção ou exclusão quando aplicável.'],
            ['Contato', 'Para questões de privacidade contacte hello@aikaleya.com. Este texto deve ser revisado juridicamente antes do lançamento público.']
        ],
        ru: [
            ['Какие данные мы собираем', 'Kaleya может собирать деловые контактные данные, данные регистрации аккаунта, информацию о выбранном пакете и технические данные для работы сервиса.'],
            ['Как мы используем данные', 'Данные используются для регистрации, предоставления услуги, связи с клиентом, оплаты, поддержки и безопасности системы.'],
            ['API и голосовые сервисы', 'AI и голосовая обработка выполняются через backend интеграции. API ключи не должны храниться во frontend коде и в продакшене находятся в защищенном backend окружении.'],
            ['Хранение данных', 'Данные хранятся пока существует деловое отношение или юридическая обязанность хранения. Клиент может запросить исправление или удаление, где это применимо.'],
            ['Контакт', 'По вопросам приватности пишите hello@aikaleya.com. Этот текст нужно юридически проверить перед публичным запуском.']
        ]
    },
    terms: {
        sr: [
            ['Opis usluge', 'Kaleya je AI sistem za automatizaciju komunikacije, zakazivanja, glasovnih odgovora i obaveštenja za poslovne korisnike.'],
            ['Nalog i pristup', 'Klijent je odgovoran za tačnost unetih podataka, sigurnost naloga i korišćenje servisa u skladu sa važećim propisima.'],
            ['Plaćanje i paketi', 'Paketi, probni period i naplata aktiviraju se kroz backend sistem za registraciju i payment provider. Detalji se potvrđuju tokom kupovine.'],
            ['Ograničenja', 'Kaleya ne garantuje da AI može završiti svaki zahtev. Kada AI ne može da završi proces, zahtev se može proslediti human support sistemu.'],
            ['Promene uslova', 'Uslovi se mogu ažurirati. Nastavak korišćenja servisa nakon promene znači prihvatanje ažuriranih uslova.']
        ],
        en: [
            ['Service Description', 'Kaleya ("Service", "we", "us") is a subscription-based AI receptionist platform that automates appointment scheduling, voice replies, client communication and business notifications. The Service is operated by Kaleya AI (aikaleya.com). By creating an account you agree to these Terms of Service.'],
            ['Eligibility and Account', 'You must be at least 18 years old and authorized to enter contracts on behalf of your business to use Kaleya. You are responsible for: providing accurate registration information; maintaining the confidentiality of your login credentials; all activity that occurs under your account; ensuring your use of the Service complies with applicable laws. Notify us immediately at hello@aikaleya.com if you suspect unauthorized access.'],
            ['Subscription, Billing and Cancellation', 'Kaleya offers paid subscription plans with a free trial period. Payment is processed by Lemon Squeezy (Merchant of Record — they handle tax, VAT and receipts). Your subscription renews automatically at the end of each billing period unless cancelled. You may cancel at any time from your dashboard; access continues until the end of the current period. Refunds are issued at our discretion for exceptional cases — contact support within 7 days of a charge. Prices may change with 30 days notice to active subscribers.'],
            ['Acceptable Use', 'You agree not to: use the Service for illegal, fraudulent or harmful purposes; impersonate any person or entity; attempt to reverse-engineer, scrape or overload the platform; use the AI to generate spam, misleading content or content that violates third-party rights; resell or sublicense the Service without written permission. We reserve the right to suspend or terminate accounts that violate these terms without refund.'],
            ['AI Service and Limitations', 'Kaleya\'s AI is powered by third-party language models (Anthropic Claude). AI responses are generated automatically and may occasionally be inaccurate, incomplete or inappropriate for a given situation. Kaleya does not guarantee that the AI will complete every request correctly. You are responsible for reviewing AI-generated communications before relying on them for critical business decisions. When the AI cannot resolve a request, it may escalate to human support.'],
            ['Data and Privacy', 'Your use of the Service is governed by our Privacy Policy (aikaleya.com/privacy). By using the Service you consent to the data practices described there. You retain ownership of your business data. You grant Kaleya a limited license to process your data solely to provide the Service.'],
            ['Intellectual Property', 'Kaleya, its logo, platform design and underlying software are owned by Kaleya AI. You may not copy, modify or distribute any part of the Service without express written permission. You retain full ownership of your business content, customer data and configurations.'],
            ['Disclaimer of Warranties', 'The Service is provided "as is" and "as available" without warranties of any kind, express or implied, including but not limited to merchantability, fitness for a particular purpose or uninterrupted operation. We do not warrant that the Service will be error-free or that AI responses will always be accurate.'],
            ['Limitation of Liability', 'To the maximum extent permitted by law, Kaleya AI shall not be liable for indirect, incidental, special, consequential or punitive damages, including lost profits or data, arising from your use of or inability to use the Service. Our total liability to you for any claim shall not exceed the amount you paid for the Service in the 3 months preceding the claim.'],
            ['Governing Law', 'These Terms are governed by the laws of the State of Delaware, United States, without regard to conflict of law principles. Any disputes shall be resolved by binding arbitration under AAA rules, except that either party may seek injunctive relief in a court of competent jurisdiction.'],
            ['Changes to Terms', 'We may update these Terms. We will notify active subscribers by email at least 14 days before material changes take effect. Continued use of the Service after the effective date constitutes acceptance. If you do not agree to updated Terms, you may cancel your subscription before they take effect.'],
            ['Contact', 'Questions about these Terms: hello@aikaleya.com · aikaleya.com. These Terms were last updated May 2026 and should be reviewed by a qualified attorney before commercial launch.']
        ],
        es: [
            ['Descripción del servicio', 'Kaleya es un sistema de IA para automatizar comunicación, agenda, respuestas de voz y notificaciones para empresas.'],
            ['Cuenta y acceso', 'El cliente es responsable de datos correctos, seguridad de la cuenta y uso legal del servicio.'],
            ['Pagos y paquetes', 'Los paquetes, prueba y facturación se activan mediante backend y proveedor de pago. Los detalles se confirman durante la compra.'],
            ['Limitaciones', 'Kaleya no garantiza que la IA complete cada solicitud. Si no puede hacerlo, puede escalarse a soporte humano.'],
            ['Cambios en los términos', 'Los términos pueden actualizarse. Continuar usando el servicio implica aceptar los términos actualizados.']
        ],
        pt: [
            ['Descrição do serviço', 'Kaleya é um sistema de IA para automatizar comunicação, agendamento, respostas de voz e notificações para empresas.'],
            ['Conta e acesso', 'O cliente é responsável por dados corretos, segurança da conta e uso legal do serviço.'],
            ['Pagamento e pacotes', 'Pacotes, teste e cobrança são ativados pelo backend e provedor de pagamento. Os detalhes são confirmados na compra.'],
            ['Limitações', 'Kaleya não garante que a IA conclua toda solicitação. Quando não conseguir, a solicitação pode ir para suporte humano.'],
            ['Alterações dos termos', 'Os termos podem ser atualizados. Continuar usando o serviço significa aceitar os termos atualizados.']
        ],
        ru: [
            ['Описание услуги', 'Kaleya это AI система для автоматизации коммуникации, записи, голосовых ответов и уведомлений для бизнеса.'],
            ['Аккаунт и доступ', 'Клиент отвечает за точность данных, безопасность аккаунта и законное использование сервиса.'],
            ['Оплата и пакеты', 'Пакеты, пробный период и оплата активируются через backend регистрацию и платежного провайдера. Детали подтверждаются при покупке.'],
            ['Ограничения', 'Kaleya не гарантирует, что AI сможет выполнить каждый запрос. Если AI не может завершить процесс, запрос может быть передан human support.'],
            ['Изменения условий', 'Условия могут обновляться. Продолжение использования после изменений означает принятие обновленных условий.']
        ]
    }
};

PAGE_LEGAL.privacy.fr = [
    ['Donnees collectees', 'Kaleya peut collecter des donnees de contact professionnel, des donnees d inscription, des informations sur le forfait choisi et des donnees techniques necessaires au service.'],
    ['Utilisation des donnees', 'Les donnees sont utilisees pour l inscription, la livraison du service, la communication client, la facturation, le support et la securite du systeme.'],
    ['API et services vocaux', 'Le traitement IA et vocal passe par des integrations backend. Les cles API ne doivent pas etre stockees dans le frontend et restent securisees cote backend en production.'],
    ['Conservation', 'Les donnees sont conservees tant que la relation commerciale ou une obligation legale existe. Le client peut demander une correction ou suppression lorsque cela s applique.'],
    ['Contact', 'Pour les questions de confidentialite, contactez hello@aikaleya.com. Ce texte doit etre verifie juridiquement avant le lancement public.']
];

PAGE_LEGAL.privacy.it = [
    ['Dati raccolti', 'Kaleya puo raccogliere dati di contatto aziendale, dati di registrazione, informazioni sul pacchetto scelto e dati tecnici necessari al servizio.'],
    ['Uso dei dati', 'I dati vengono usati per registrazione, erogazione del servizio, comunicazione con il cliente, fatturazione, supporto e sicurezza del sistema.'],
    ['API e servizi vocali', 'Il trattamento AI e voce passa da integrazioni backend. Le API key non devono stare nel frontend e in produzione restano in un backend sicuro.'],
    ['Conservazione', 'I dati vengono conservati finche esiste il rapporto commerciale o un obbligo legale. Il cliente puo richiedere correzione o cancellazione dove applicabile.'],
    ['Contatto', 'Per domande sulla privacy contattare hello@aikaleya.com. Questo testo deve essere verificato legalmente prima del lancio pubblico.']
];

PAGE_LEGAL.terms.fr = [
    ['Description du service', 'Kaleya est un systeme IA pour automatiser la communication, la planification, les reponses vocales et les notifications pour les entreprises.'],
    ['Compte et acces', 'Le client est responsable de l exactitude des donnees, de la securite du compte et de l utilisation conforme a la loi.'],
    ['Paiement et forfaits', 'Les forfaits, l essai et la facturation sont actives via le backend d inscription et le prestataire de paiement. Les details sont confirmes pendant l achat.'],
    ['Limites', 'Kaleya ne garantit pas que l IA puisse terminer chaque demande. Si l IA ne peut pas terminer un processus, la demande peut etre transmise au support humain.'],
    ['Modifications', 'Les conditions peuvent etre mises a jour. Continuer a utiliser le service apres modification signifie accepter les nouvelles conditions.']
];

PAGE_LEGAL.terms.it = [
    ['Descrizione del servizio', 'Kaleya e un sistema AI per automatizzare comunicazione, prenotazioni, risposte vocali e notifiche per utenti business.'],
    ['Account e accesso', 'Il cliente e responsabile della correttezza dei dati, della sicurezza dell account e dell uso conforme alla legge.'],
    ['Pagamenti e pacchetti', 'Pacchetti, prova e fatturazione vengono attivati dal backend di registrazione e dal payment provider. I dettagli si confermano durante l acquisto.'],
    ['Limiti', 'Kaleya non garantisce che l AI completi ogni richiesta. Quando non puo completare il processo, la richiesta puo essere inoltrata al supporto umano.'],
    ['Modifiche', 'I termini possono essere aggiornati. Continuare a usare il servizio dopo le modifiche significa accettare i termini aggiornati.']
];

PAGE_LEGAL.privacy.de = [
    ['Welche Daten wir sammeln', 'Kaleya kann geschäftliche Kontaktdaten, Registrierungsdaten, Informationen zum gewaehlten Paket und technische Daten sammeln, die fuer den Betrieb des Services erforderlich sind.'],
    ['Wie wir Daten nutzen', 'Daten werden fuer Registrierung, Servicebereitstellung, Kundenkommunikation, Abrechnung, Support und Systemsicherheit genutzt.'],
    ['API und Sprachdienste', 'AI und Sprachverarbeitung laufen ueber Backend Integrationen. API Schluessel duerfen nicht im Frontend gespeichert werden und bleiben in Produktion im sicheren Backend.'],
    ['Aufbewahrung', 'Daten werden gespeichert, solange eine Geschaeftsbeziehung oder gesetzliche Pflicht besteht. Kunden koennen Korrektur oder Loeschung verlangen, wo dies anwendbar ist.'],
    ['Kontakt', 'Bei Datenschutzfragen kontaktieren Sie hello@aikaleya.com. Dieser Text sollte vor dem oeffentlichen Launch rechtlich geprueft werden.']
];

PAGE_LEGAL.terms.de = [
    ['Servicebeschreibung', 'Kaleya ist ein AI System zur Automatisierung von Kommunikation, Terminplanung, Sprachantworten und Benachrichtigungen fuer Unternehmen.'],
    ['Konto und Zugang', 'Der Kunde ist fuer korrekte Daten, Kontosicherheit und gesetzeskonforme Nutzung des Services verantwortlich.'],
    ['Zahlung und Pakete', 'Pakete, Testphase und Abrechnung werden ueber Backend Registrierung und Payment Provider aktiviert. Details werden beim Kauf bestaetigt.'],
    ['Grenzen', 'Kaleya garantiert nicht, dass AI jede Anfrage abschliessen kann. Wenn AI einen Prozess nicht abschliessen kann, kann die Anfrage an Human Support eskaliert werden.'],
    ['Aenderungen', 'Bedingungen koennen aktualisiert werden. Die weitere Nutzung nach Aenderungen bedeutet Zustimmung zu den aktualisierten Bedingungen.']
];

function pageLang() {
    const saved = localStorage.getItem('kaleya_lang') || 'en';
    if (!localStorage.getItem('kaleya_lang_user_set') && saved === 'sr') return 'en';
    return PAGE_LANGS[saved] ? saved : 'en';
}

function pageText(key) {
    const lang = pageLang();
    return PAGE_LANGS[lang][key] || PAGE_LANGS.en[key] || PAGE_LANGS.sr[key] || key;
}

function applyPageLang() {
    const lang = pageLang();
    document.documentElement.lang = lang;
    const selector = document.getElementById('pageLangSelect');
    if (selector) selector.value = lang;
    document.querySelectorAll('[data-i18n]').forEach((el) => {
        el.textContent = pageText(el.dataset.i18n);
    });
    updateOnlineLabels();
    renderHomeLists();
    renderDemoCalendars();
    renderLegalPage();
    renderRegistrationPaymentSummaries();
}

function setPageLang(lang) {
    if (!PAGE_LANGS[lang]) return;
    localStorage.setItem('kaleya_lang', lang);
    localStorage.setItem('kaleya_lang_user_set', '1');
    applyPageLang();
}

function setDemoStatus(key) {
    const el = document.getElementById('demoStatus');
    if (el) el.textContent = pageText(key);
    const row = document.getElementById('demoActivity');
    if (row) row.textContent = pageText(key);
}

function initPageTheme() {
    const saved = localStorage.getItem('kaleya_page_theme');
    const wantsDark = saved === 'dark' || (!saved && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('page-dark', wantsDark);
}

function togglePageTheme() {
    document.documentElement.classList.toggle('page-dark');
    localStorage.setItem('kaleya_page_theme', document.documentElement.classList.contains('page-dark') ? 'dark' : 'light');
}

function updateOnlineLabels() {
    document.querySelectorAll('[data-online-toggle]').forEach((button) => {
        button.textContent = button.classList.contains('off') ? pageText('offline') : pageText('online');
    });
}

function toggleDemoOnline(button) {
    button.classList.toggle('off');
    updateOnlineLabels();
}

function toggleDeviceTheme(button) {
    const device = button.closest('.device-app');
    if (device) device.classList.toggle('device-dark');
}

function switchAppView(button, view) {
    const device = button.closest('.device-app');
    if (!device) return;
    device.querySelectorAll('.app-screen').forEach((screen) => screen.classList.remove('active'));
    device.querySelectorAll('.app-footer-item').forEach((item) => item.classList.remove('active'));
    const target = device.querySelector(view === 'calendar' ? '.app-calendar' : '.app-home');
    if (target) target.classList.add('active');
    button.classList.add('active');
    renderDemoCalendars();
}

function switchCalendarMode(button, mode) {
    const calendar = button.closest('.app-calendar');
    if (!calendar) return;
    calendar.dataset.mode = mode;
    calendar.querySelectorAll('.segmented button').forEach((item) => item.classList.remove('active'));
    calendar.querySelectorAll('.calendar-month, .calendar-day').forEach((view) => view.classList.remove('active'));
    button.classList.add('active');
    const target = calendar.querySelector(mode === 'day' ? '.calendar-day' : '.calendar-month');
    if (target) target.classList.add('active');
    renderCalendar(calendar);
}

function isoDate(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

function parseIsoDate(value) {
    const [y, m, d] = value.split('-').map(Number);
    return new Date(y, m - 1, d);
}

function calendarBaseDate(calendar) {
    const now = new Date();
    const offset = Number(calendar.dataset.monthOffset || 0);
    return new Date(now.getFullYear(), now.getMonth() + offset, 1);
}

function demoEventsForDate(date) {
    return DEMO_EVENT_PATTERN[date.getDate()] || [];
}

function eventCounts(date) {
    const events = demoEventsForDate(date);
    const active = events.filter((event) => event.status !== 'cancelled').length;
    return { booked: active, free: Math.max(WORK_HOURS.length - active, 0) };
}

function statusLabel(status) {
    if (status === 'cancelled') return pageText('cancelled_status');
    if (status === 'moved') return pageText('moved_status');
    if (status === 'booked') return pageText('booked');
    return pageText('free');
}

function eventTitle(event) {
    if (!event) return pageText('free');
    const lang = pageLang();
    return DEMO_NAMES[lang]?.[event.titleKey] || DEMO_NAMES.en[event.titleKey] || event.titleKey;
}

function renderHomeLists() {
    document.querySelectorAll('[data-home-list]').forEach((list) => {
        list.innerHTML = HOME_DEMO_EVENTS.map((event) => `
            <div class="appt-card ${event.status}">
                <strong>${event.time}</strong>
                <span>${eventTitle(event)} - ${statusLabel(event.status).toLowerCase()}</span>
            </div>
        `).join('');
    });
}

function selectCalendarDate(button, dateIso) {
    const calendar = button.closest('.app-calendar');
    if (!calendar) return;
    calendar.dataset.selectedDate = dateIso;
    renderCalendar(calendar);
    const dayButton = calendar.querySelector('.segmented button:nth-child(2)');
    if (dayButton) switchCalendarMode(dayButton, 'day');
}

function moveCalendar(button, direction) {
    const calendar = button.closest('.app-calendar');
    if (!calendar) return;
    if ((calendar.dataset.mode || 'month') === 'day') {
        const current = parseIsoDate(calendar.dataset.selectedDate || isoDate(new Date()));
        current.setDate(current.getDate() + direction);
        calendar.dataset.selectedDate = isoDate(current);
        const now = new Date();
        calendar.dataset.monthOffset = (current.getFullYear() - now.getFullYear()) * 12 + current.getMonth() - now.getMonth();
    } else {
        calendar.dataset.monthOffset = String(Number(calendar.dataset.monthOffset || 0) + direction);
        const base = calendarBaseDate(calendar);
        calendar.dataset.selectedDate = isoDate(base);
    }
    renderCalendar(calendar);
}

function renderDemoCalendars() {
    document.querySelectorAll('.app-calendar').forEach((calendar) => {
        if (!calendar.dataset.mode) calendar.dataset.mode = 'month';
        if (!calendar.dataset.selectedDate) calendar.dataset.selectedDate = isoDate(new Date());
        if (!calendar.dataset.monthOffset) calendar.dataset.monthOffset = '0';
        renderCalendar(calendar);
    });
}

function renderCalendar(calendar) {
    const lang = pageLang();
    const base = calendarBaseDate(calendar);
    const selected = parseIsoDate(calendar.dataset.selectedDate || isoDate(new Date()));
    const label = calendar.querySelector('[data-calendar-label]');
    const mode = calendar.dataset.mode || 'month';
    if (label) {
        label.textContent = mode === 'day'
            ? selected.toLocaleDateString(lang, { day: '2-digit', month: 'long', year: 'numeric' })
            : base.toLocaleDateString(lang, { month: 'long', year: 'numeric' });
    }

    const grid = calendar.querySelector('[data-calendar-grid]');
    if (grid) {
        const weekStartsOnSunday = lang === 'en';
        const weekdayNames = Array.from({ length: 7 }, (_, index) => {
            const date = new Date(2026, 0, (weekStartsOnSunday ? 4 : 5) + index);
            return date.toLocaleDateString(lang, { weekday: 'short' }).slice(0, 2);
        });
        const first = new Date(base.getFullYear(), base.getMonth(), 1);
        const last = new Date(base.getFullYear(), base.getMonth() + 1, 0);
        const offset = weekStartsOnSunday ? first.getDay() : (first.getDay() + 6) % 7;
        const cells = [];
        weekdayNames.forEach((name) => cells.push(`<span>${name}</span>`));
        for (let i = 0; i < offset; i++) cells.push('<button class="muted" type="button"></button>');
        for (let day = 1; day <= last.getDate(); day++) {
            const date = new Date(base.getFullYear(), base.getMonth(), day);
            const iso = isoDate(date);
            const counts = eventCounts(date);
            const selectedClass = iso === isoDate(selected) ? ' selected' : '';
            const todayClass = iso === isoDate(new Date()) ? ' today' : '';
            cells.push(`
                <button type="button" class="${selectedClass}${todayClass}" onclick="selectCalendarDate(this, '${iso}')">
                    <span class="date-num">${day}</span>
                    <span class="date-badges">
                        <span class="date-badge booked">${counts.booked}</span>
                        <span class="date-badge free">${counts.free}</span>
                    </span>
                </button>
            `);
        }
        grid.innerHTML = cells.join('');
    }

    const dayList = calendar.querySelector('[data-day-list]');
    if (dayList) {
        const events = demoEventsForDate(selected);
        dayList.innerHTML = WORK_HOURS.map((time) => {
            const event = events.find((item) => item.time === time);
            const status = event ? event.status : 'free';
            const title = eventTitle(event);
            return `
                <div class="slot-row ${status}">
                    <strong>${time}</strong>
                    <span>${title}</span>
                    <span class="slot-status">${statusLabel(status)}</span>
                </div>
            `;
        }).join('');
    }
}

function playKaleyaDemo() {
    const lang = pageLang();
    const audio = document.getElementById('kaleyaAudio') || new Audio();
    audio.src = PAGE_AUDIO[lang] || PAGE_AUDIO.en;
    audio.play().catch(() => {
        if (!('speechSynthesis' in window)) return;
        const fallback = {
            sr: 'Zdravo, ja sam Kaleya. Odgovaram na pozive, zakazujem termine i obaveštavam vaš tim.',
            en: 'Hello, I am Kaleya. I answer calls, schedule appointments and alert your team.',
            es: 'Hola, soy Kaleya. Atiendo llamadas, agendo citas y aviso a tu equipo.',
            pt: 'Olá, eu sou Kaleya. Atendo chamadas, agendo horários e aviso sua equipe.',
            ru: 'Здравствуйте, я Kaleya. Я отвечаю на звонки, записываю клиентов и уведомляю команду.',
            fr: 'Bonjour, je suis Kaleya. Je reponds aux appels, je planifie les rendez-vous et j informe votre equipe.',
            it: 'Ciao, sono Kaleya. Rispondo alle chiamate, organizzo appuntamenti e avviso il tuo team.',
            de: 'Hallo, ich bin Kaleya. Ich beantworte Anrufe, plane Termine und informiere Ihr Team.'
        };
        const map = { sr: 'sr-RS', en: 'en-US', es: 'es-ES', pt: 'pt-PT', ru: 'ru-RU', fr: 'fr-FR', it: 'it-IT', de: 'de-DE' };
        const utter = new SpeechSynthesisUtterance(fallback[lang] || fallback.en);
        utter.lang = map[lang] || 'en-US';
        speechSynthesis.cancel();
        speechSynthesis.speak(utter);
    });
}

function renderLegalPage() {
    const holder = document.getElementById('legalBody');
    if (!holder) return;
    const type = holder.dataset.legal;
    const content = PAGE_LEGAL[type]?.[pageLang()] || PAGE_LEGAL[type]?.en || PAGE_LEGAL[type]?.sr || [];
    holder.innerHTML = content.map(([title, body]) => `<h2>${title}</h2><p>${body}</p>`).join('');
}

const CHECKOUT_PLAN_DETAILS = {
    basic: { name: 'Starter', price: '$59 / month', trial: '14 days' },
    pro: { name: 'Pro', price: '$89 / month', trial: '14 days' },
    business: { name: 'Business', price: '$349 / month', trial: '14 days' },
    business_plus: { name: 'Business+', price: '$579 / month', trial: '14 days' },
    business_pro_plus: { name: 'BusinessPro+', price: 'Custom', trial: 'By agreement' }
};

function checkoutPlanCode() {
    const params = new URLSearchParams(window.location.search);
    return params.get('plan') || params.get('package') || 'basic';
}

function checkoutMoney(currency, amount) {
    const value = Number(amount || 0);
    const rounded = Number.isInteger(value) ? String(value) : value.toFixed(2);
    if (currency === 'USD') return `$${rounded}`;
    if (currency === 'EUR') return `€${rounded}`;
    return `${currency} ${rounded}`;
}

function renderRegistrationPaymentSummaries() {
    document.querySelectorAll('[data-payment-summary]').forEach((summary) => {
        const planCode = summary.dataset.paymentSummary || 'basic';
        const plan = CHECKOUT_PLAN_DETAILS[planCode] || CHECKOUT_PLAN_DETAILS.basic;
        summary.innerHTML = `
            <div><span>${pageText('checkout_today')}</span><strong>$0</strong></div>
            <div><span>${pageText('checkout_after_trial')}</span><strong>${plan.price}</strong></div>
            <p>${pageText('checkout_trial_note')}</p>
        `;
    });
}

async function loadPaymentPublicConfig() {
    const response = await fetch('/api/billing/payment/public-config/');
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || pageText('checkout_not_ready'));
    return data;
}

async function loadCheckoutSession(publicId) {
    const response = await fetch(`/api/billing/checkout-sessions/public/${publicId}/`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || pageText('checkout_not_ready'));
    return data;
}

async function initKaleyaCheckoutPage() {
    const button = document.getElementById('paymentCheckoutBtn');
    if (!button) return;

    const status = document.getElementById('checkoutStatus');
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session');
    const planCode = checkoutPlanCode();
    const plan = CHECKOUT_PLAN_DETAILS[planCode] || CHECKOUT_PLAN_DETAILS.basic;
    const planLabel = document.getElementById('checkoutPlan');
    const amountLabel = document.getElementById('checkoutAmount');
    const todayLabel = document.getElementById('checkoutToday');
    const trialLabel = document.getElementById('checkoutTrial');

    if (planLabel) planLabel.textContent = plan.name;
    if (amountLabel) amountLabel.textContent = plan.price;
    if (todayLabel) todayLabel.textContent = '$0';
    if (trialLabel) trialLabel.textContent = plan.trial;

    if (window.location.protocol === 'file:') {
        if (status) status.textContent = pageText('checkout_file_mode');
        button.disabled = true;
        return;
    }

    try {
        if (sessionId) {
            const checkout = await loadCheckoutSession(sessionId);
            if (planLabel) planLabel.textContent = checkout.plan?.name || plan.name;
            if (amountLabel) amountLabel.textContent = `${checkoutMoney(checkout.currency, checkout.amount)} / month`;
            if (todayLabel) todayLabel.textContent = checkoutMoney(checkout.currency, 0);
            if (trialLabel) trialLabel.textContent = `${checkout.trial_days || 14} days`;
            if (checkout.payment_ready && checkout.provider_checkout_url) {
                if (checkout.provider === 'lemonsqueezy') {
                    button.disabled = false;
                    button.dataset.checkoutReady = '1';
                    button.dataset.providerCheckoutUrl = checkout.provider_checkout_url;
                    button.textContent = pageText('checkout_button');
                    if (status) status.textContent = pageText('checkout_ready');
                    return;
                }
                button.disabled = true;
                button.dataset.checkoutReady = '0';
                button.dataset.providerCheckoutUrl = '';
                button.textContent = pageText('checkout_button_pending');
                if (status) status.textContent = pageText('checkout_card_fields_pending');
                return;
            }
            button.disabled = true;
            button.dataset.checkoutReady = '0';
            if (status) status.textContent = pageText('checkout_not_ready');
            return;
        }

        const config = await loadPaymentPublicConfig();
        if (config.ready && config.client_id_configured) {
            button.disabled = false;
            button.dataset.checkoutReady = '1';
            if (status) status.textContent = `${pageText('checkout_ready')} (${config.environment})`;
            return;
        }
        button.disabled = true;
        button.dataset.checkoutReady = '0';
        if (status) status.textContent = pageText('checkout_not_ready');
    } catch (error) {
        button.disabled = true;
        button.dataset.checkoutReady = '0';
        if (status) status.textContent = error.message || pageText('checkout_not_ready');
    }
}

function startKaleyaCardCheckout() {
    const button = document.getElementById('paymentCheckoutBtn');
    const status = document.getElementById('checkoutStatus');
    if (!button || button.dataset.checkoutReady !== '1') {
        if (status) status.textContent = pageText('checkout_not_ready');
        return;
    }
    if (button.dataset.providerCheckoutUrl) {
        window.location.href = button.dataset.providerCheckoutUrl;
        return;
    }
    if (status) status.textContent = pageText('checkout_next_step');
}

function registrationErrorText(data) {
    if (!data || typeof data !== 'object') return pageText('registration_failed');
    if (data.detail) return data.detail;
    return Object.values(data)
        .flatMap((value) => Array.isArray(value) ? value : [value])
        .map((value) => typeof value === 'object' ? JSON.stringify(value) : String(value))
        .join(' ') || pageText('registration_failed');
}

function getPageCookie(name) {
    const cookie = `; ${document.cookie || ''}`;
    const parts = cookie.split(`; ${name}=`);
    if (parts.length !== 2) return '';
    return decodeURIComponent(parts.pop().split(';').shift() || '');
}

function pageJsonHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const csrfToken = getPageCookie('csrftoken');
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    return headers;
}

async function createCheckoutSession(payload) {
    const response = await fetch('/api/billing/checkout-sessions/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: pageJsonHeaders(),
        body: JSON.stringify({
            plan_code: payload.plan_code,
            email: payload.email,
            company: payload.company,
            full_name: payload.full_name,
            password: payload.password,
            phone: payload.phone,
            country: payload.country,
            note: payload.note
        })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(registrationErrorText(data));
    return data;
}

async function submitRegistrationForm(form) {
    const status = document.getElementById('registrationStatus');
    const packageCode = form.querySelector('[name="package"]')?.value || 'basic';

    if (status) {
        status.hidden = false;
        status.textContent = packageCode === 'business_pro_plus' ? pageText('contact_custom') : pageText('registration_creating');
    }

    if (packageCode === 'business_pro_plus') return;

    if (window.location.protocol === 'file:') {
        if (status) status.textContent = 'Registracija radi preko backend adrese: http://127.0.0.1:8000/';
        return;
    }

    const payload = {
        plan_code: packageCode,
        company: form.elements.company?.value.trim() || '',
        full_name: form.elements.name?.value.trim() || '',
        email: form.elements.email?.value.trim() || '',
        password: form.elements.password?.value || '',
        phone: form.elements.phone?.value.trim() || '',
        country: form.elements.country?.value.trim() || '',
        note: form.elements.note?.value.trim() || ''
    };

    try {
        const checkout = await createCheckoutSession(payload);
        if (checkout.checkout_url) {
            window.location.href = checkout.checkout_url;
            return;
        }
        if (checkout.local_checkout_url) {
            window.location.href = checkout.local_checkout_url;
            return;
        }

        const response = await fetch('/api/auth/register-client/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: pageJsonHeaders(),
            body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(registrationErrorText(data));

        localStorage.setItem('kaleya_auth_token', data.token);
        localStorage.setItem('kaleya_user_role', data.user.role);
        localStorage.setItem('kaleya_user_email', data.user.email);

        if (status) status.textContent = pageText('registration_success');
        window.location.href = '/';
    } catch (error) {
        if (status) status.textContent = error.message || pageText('registration_failed');
    }
}

function initRegistrationForms() {
    document.querySelectorAll('form.form-card').forEach((form) => {
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            submitRegistrationForm(form);
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initPageTheme();
    applyPageLang();
    initRegistrationForms();
    initKaleyaCheckoutPage();
    renderRegistrationPaymentSummaries();
});
