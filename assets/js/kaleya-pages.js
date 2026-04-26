const PAGE_LANGS = {
    sr: {
        back_home: 'Nazad na početnu',
        demo_badge: 'Klikabilan demo',
        demo_title: 'Kako Kaleya radi u praksi',
        demo_lead: 'Mobilni i laptop prikaz su demo okruženje. Dugmad su klikabilna, a glas se pušta iz MP3 fajla.',
        mobile_title: 'Klijent app',
        laptop_title: 'Admin dashboard',
        voice_cta: 'Pusti Kaleya glas',
        schedule: 'Zakaži',
        cancel: 'Otkaži',
        check: 'Proveri',
        status_ready: 'Spremna za razgovor',
        status_scheduled: 'Demo termin je zakazan za 15:00',
        status_cancelled: 'Demo sastanak je otkazan',
        status_checked: 'Danas ima 3 slobodna termina',
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
        laptop_title: 'Admin dashboard',
        voice_cta: 'Play Kaleya voice',
        schedule: 'Schedule',
        cancel: 'Cancel',
        check: 'Check',
        status_ready: 'Ready to talk',
        status_scheduled: 'Demo appointment is scheduled for 3 PM',
        status_cancelled: 'Demo meeting has been cancelled',
        status_checked: 'There are 3 free slots today',
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
        laptop_title: 'Panel admin',
        voice_cta: 'Reproducir voz Kaleya',
        schedule: 'Agendar',
        cancel: 'Cancelar',
        check: 'Revisar',
        status_ready: 'Lista para hablar',
        status_scheduled: 'La cita demo está agendada a las 15:00',
        status_cancelled: 'La reunión demo fue cancelada',
        status_checked: 'Hoy hay 3 horarios libres',
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
        laptop_title: 'Dashboard admin',
        voice_cta: 'Tocar voz Kaleya',
        schedule: 'Agendar',
        cancel: 'Cancelar',
        check: 'Verificar',
        status_ready: 'Pronta para conversar',
        status_scheduled: 'O horário demo foi agendado para 15:00',
        status_cancelled: 'A reunião demo foi cancelada',
        status_checked: 'Hoje há 3 horários livres',
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
        laptop_title: 'Админ панель',
        voice_cta: 'Воспроизвести голос Kaleya',
        schedule: 'Записать',
        cancel: 'Отменить',
        check: 'Проверить',
        status_ready: 'Готова к разговору',
        status_scheduled: 'Demo запись назначена на 15:00',
        status_cancelled: 'Demo встреча отменена',
        status_checked: 'Сегодня есть 3 свободных времени',
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

const PAGE_AUDIO = {
    sr: 'assets/audio/kaleya-demo-sr.mp3',
    en: 'assets/audio/kaleya-demo-en.mp3',
    es: 'assets/audio/kaleya-demo-es.mp3',
    pt: 'assets/audio/kaleya-demo-pt.mp3',
    ru: 'assets/audio/kaleya-demo-ru.mp3'
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

function pageLang() {
    const saved = localStorage.getItem('kaleya_lang') || 'sr';
    return PAGE_LANGS[saved] ? saved : 'sr';
}

function pageText(key) {
    const lang = pageLang();
    return PAGE_LANGS[lang][key] || PAGE_LANGS.sr[key] || key;
}

function applyPageLang() {
    const lang = pageLang();
    document.documentElement.lang = lang;
    const selector = document.getElementById('pageLangSelect');
    if (selector) selector.value = lang;
    document.querySelectorAll('[data-i18n]').forEach((el) => {
        el.textContent = pageText(el.dataset.i18n);
    });
    renderLegalPage();
}

function setPageLang(lang) {
    if (!PAGE_LANGS[lang]) return;
    localStorage.setItem('kaleya_lang', lang);
    applyPageLang();
}

function setDemoStatus(key) {
    const el = document.getElementById('demoStatus');
    if (el) el.textContent = pageText(key);
    const row = document.getElementById('demoActivity');
    if (row) row.textContent = pageText(key);
}

function playKaleyaDemo() {
    const lang = pageLang();
    const audio = document.getElementById('kaleyaAudio') || new Audio();
    audio.src = PAGE_AUDIO[lang] || PAGE_AUDIO.sr;
    audio.play().catch(() => {
        if (!('speechSynthesis' in window)) return;
        const fallback = {
            sr: 'Zdravo, ja sam Kaleya. Odgovaram na pozive, zakazujem termine i obaveštavam vaš tim.',
            en: 'Hello, I am Kaleya. I answer calls, schedule appointments and alert your team.',
            es: 'Hola, soy Kaleya. Atiendo llamadas, agendo citas y aviso a tu equipo.',
            pt: 'Olá, eu sou Kaleya. Atendo chamadas, agendo horários e aviso sua equipe.',
            ru: 'Здравствуйте, я Kaleya. Я отвечаю на звонки, записываю клиентов и уведомляю команду.'
        };
        const map = { sr: 'sr-RS', en: 'en-US', es: 'es-ES', pt: 'pt-PT', ru: 'ru-RU' };
        const utter = new SpeechSynthesisUtterance(fallback[lang] || fallback.sr);
        utter.lang = map[lang] || 'sr-RS';
        speechSynthesis.cancel();
        speechSynthesis.speak(utter);
    });
}

function renderLegalPage() {
    const holder = document.getElementById('legalBody');
    if (!holder) return;
    const type = holder.dataset.legal;
    const content = PAGE_LEGAL[type]?.[pageLang()] || PAGE_LEGAL[type]?.sr || [];
    holder.innerHTML = content.map(([title, body]) => `<h2>${title}</h2><p>${body}</p>`).join('');
}

document.addEventListener('DOMContentLoaded', applyPageLang);
