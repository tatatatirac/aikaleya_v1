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
        phone: 'Telefon',
        country: 'Država',
        note: 'Napomena',
        start_trial: 'Probaj 14 dana',
        payment_note: 'Za produkciju ovde se povezuje payment provider, backend registracija, email potvrda i webhook za aktivaciju paketa.',
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
        phone: 'Phone',
        country: 'Country',
        note: 'Note',
        start_trial: 'Try 14 days',
        payment_note: 'In production this connects to a payment provider, backend registration, email confirmation and activation webhook.',
        god_badge: 'Buy All',
        god_title: 'GOD MODE package',
        god_lead: 'Purchase the complete Kaleya project with frontend, backend, hosting preparation, domain and deployment documentation.',
        god_cta: 'Contact for Buy All',
        privacy_title: 'Privacy Policy',
        privacy_lead: 'This is a standard starter version and should be legally reviewed before production.',
        terms_title: 'Terms of Service',
        terms_lead: 'This is a standard starter version for a SaaS service and should be legally reviewed before production.',
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
        phone: 'Teléfono',
        country: 'País',
        note: 'Nota',
        start_trial: 'Probar 14 días',
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
        phone: 'Telefone',
        country: 'País',
        note: 'Nota',
        start_trial: 'Testar 14 dias',
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
        phone: 'Телефон',
        country: 'Страна',
        note: 'Примечание',
        start_trial: '14 дней бесплатно',
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

const PAGE_AUDIO = {
    sr: 'assets/audio/kaleya-demo-sr.mp3',
    en: 'assets/audio/kaleya-demo-en.mp3',
    es: 'assets/audio/kaleya-demo-es.mp3',
    pt: 'assets/audio/kaleya-demo-pt.mp3',
    ru: 'assets/audio/kaleya-demo-ru.mp3',
    fr: 'assets/audio/kaleya-demo-fr.mp3',
    it: 'assets/audio/kaleya-demo-it.mp3'
};

const WORK_HOURS = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00'];
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
            ['Data we collect', 'Kaleya may collect business contact data, account registration data, selected package information and technical data needed to operate the service.'],
            ['How we use data', 'We use data for registration, service delivery, client communication, billing, support and system security.'],
            ['API and voice services', 'AI and voice processing runs through backend integrations. API keys must not be stored in frontend code and are kept in a secure backend environment in production.'],
            ['Data retention', 'Data is kept while the business relationship or legal retention requirement exists. Clients may request correction or deletion where applicable.'],
            ['Contact', 'For privacy questions contact hello@aikaleya.com. This text should be legally reviewed before public launch.']
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
            ['Service description', 'Kaleya is an AI system for automating communication, scheduling, voice replies and notifications for business users.'],
            ['Account and access', 'The client is responsible for accurate data, account security and lawful use of the service.'],
            ['Billing and packages', 'Packages, trial period and billing are activated through the backend registration system and payment provider. Details are confirmed during purchase.'],
            ['Limitations', 'Kaleya does not guarantee that AI can complete every request. When AI cannot complete a process, the request may be escalated to human support.'],
            ['Changes to terms', 'Terms may be updated. Continued use after changes means acceptance of the updated terms.']
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
        const weekdayNames = Array.from({ length: 7 }, (_, index) => {
            const date = new Date(2026, 0, 5 + index);
            return date.toLocaleDateString(lang, { weekday: 'short' }).slice(0, 2);
        });
        const first = new Date(base.getFullYear(), base.getMonth(), 1);
        const last = new Date(base.getFullYear(), base.getMonth() + 1, 0);
        const offset = (first.getDay() + 6) % 7;
        const cells = [];
        weekdayNames.forEach((name) => cells.push(`<span>${name}</span>`));
        for (let i = 0; i < offset; i++) cells.push('<button class="muted" type="button"></button>');
        for (let day = 1; day <= last.getDate(); day++) {
            const date = new Date(base.getFullYear(), base.getMonth(), day);
            const iso = isoDate(date);
            const counts = eventCounts(date);
            const selectedClass = iso === isoDate(selected) ? ' selected' : '';
            cells.push(`
                <button type="button" class="${selectedClass}" onclick="selectCalendarDate(this, '${iso}')">
                    <span class="date-num">${day}</span>
                    <span class="date-badges">
                        ${counts.booked ? `<span class="date-badge booked">${counts.booked}</span>` : ''}
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
            it: 'Ciao, sono Kaleya. Rispondo alle chiamate, organizzo appuntamenti e avviso il tuo team.'
        };
        const map = { sr: 'sr-RS', en: 'en-US', es: 'es-ES', pt: 'pt-PT', ru: 'ru-RU', fr: 'fr-FR', it: 'it-IT' };
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

document.addEventListener('DOMContentLoaded', () => {
    initPageTheme();
    applyPageLang();
});
