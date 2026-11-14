/**
 * ZONATA — Internationalisation runtime (English + Arabic)
 *
 * A deliberately small runtime: dictionary lookup, `data-i18n` application,
 * document direction, and Indian (lakh/crore) number and currency formatting.
 * It is not a framework and it adds no dependency.
 *
 * Usage:
 *   I18n.t('company.add.title')
 *   I18n.setLanguage('ar')        // sets <html lang="ar" dir="rtl">
 *   I18n.formatCurrency(1200000)  // ₹12,00,000
 *   I18n.formatCurrency(1200000, 'INR', { compact: true }) // ₹12 L
 *
 * Elements can declare translations:
 *   <h1 data-i18n="company.add.title"></h1>
 *   <button data-i18n-aria-label="common.close"></button>
 */

(function() {
  'use strict';

  const STORAGE_KEY = 'zonata_language';
  const SUPPORTED = ['en', 'ar'];

  const DICTIONARIES = {
    en: {
      'common.cancel': 'Cancel',
      'common.close': 'Close',
      'common.back': 'Back',
      'common.retry': 'Try again',
      'common.loading': 'Loading…',
      'common.english': 'English',
      'common.arabic': 'العربية',
      'common.language': 'Language',

      'status.draft': 'Draft',
      'status.creating': 'Creating',
      'status.onboarding': 'Onboarding',
      'status.operational': 'Operational',
      'status.needs_attention': 'Needs attention',
      'status.pending_export': 'Pending export',
      'status.pending_deletion': 'Pending deletion',
      'status.deleted': 'Deleted',
      'status.suspended': 'Suspended',
      'status.unknown': 'Unknown status',

      'company.switcher.title': 'Switch company',
      'company.switcher.subtitle': 'Your current company is shown first.',
      'company.switcher.current': 'Current',
      'company.switcher.empty.title': 'No companies yet',
      'company.switcher.empty.body': 'Add your first company to start operating.',
      'company.switcher.empty.sidebar': 'No company yet',
      'company.switcher.empty.status': 'Add a company to begin',
      'company.switcher.add': 'Add company',
      'company.switcher.switched': 'Switched to {name}',
      'company.switcher.refresh_failed': 'Could not refresh. Showing the companies last loaded on this device.',
      'company.switcher.refreshing': 'Refreshing companies…',
      'company.switcher.portfolio': 'All companies (portfolio)',
      'company.switcher.unknown_industry': 'Operating company',

      'company.add.back': 'Companies',
      'company.add.title': 'Add a company',
      'company.add.subtitle': 'Choose how this company joins ZONATA. You can edit or delete it later.',
      'company.add.new.badge': 'New',
      'company.add.new.title': 'Create a new company',
      'company.add.new.body': 'For a business that does not exist yet. ZONATA builds the company with you.',
      'company.add.new.point1': 'Starts with status Creating',
      'company.add.new.point2': 'Guided build, typically 1–3 days',
      'company.add.new.point3': 'Legal and operating setup drafted for your review',
      'company.add.new.point4': 'You can edit or delete it later',
      'company.add.new.cta': 'Create new company',
      'company.add.existing.badge': 'Existing',
      'company.add.existing.title': 'Add an existing company',
      'company.add.existing.body': 'For a business already operating. ZONATA studies it and diagnoses what to improve.',
      'company.add.existing.point1': 'Starts with status Onboarding',
      'company.add.existing.point2': 'Read-only connections — nothing is written back',
      'company.add.existing.point3': 'Diagnosis and readiness findings with evidence',
      'company.add.existing.point4': 'Your data stays in your own systems',
      'company.add.existing.cta': 'Add existing company',
      'company.add.not_sure': 'Not sure which one?',
      'company.add.help.title': 'A quick way to decide',
      'company.add.help.new': 'Choose Create new if the company has no history in ZONATA and little or no operating data.',
      'company.add.help.existing': 'Choose Add existing if it already has customers, revenue, tools, or records.',
      'company.add.help.note': 'Both paths start as a draft. Nothing is submitted until you review and confirm.',
      'company.add.denied.title': 'You cannot add a company',
      'company.add.denied.body': 'Only the owner or an allowed admin can add a company. You can still ask the assistant to prepare a draft.',
      'company.add.intent_new': 'Opening the new company setup. Nothing has been created yet.',
      'company.add.intent_existing': 'Opening the existing company intake. Nothing has been connected yet.',
      'company.add.footnote': 'Your company list is scoped to your organisation. Other tenants can never see or change it.',


      'company.create.back': 'Companies',
      'company.create.steps_label': 'Setup steps',
      'company.create.step.details': 'Details',
      'company.create.step.review': 'Review',
      'company.create.title': 'Create a new company',
      'company.create.subtitle': 'A short brief. ZONATA turns it into a build plan, then shows you exactly what is real and what is still waiting.',
      'company.create.optional': 'Optional',
      'company.create.example': 'Example: {example}',
      'company.create.basics.title': 'The company',
      'company.create.basics.note': 'Write it the way you would explain it to a new colleague.',
      'company.create.name.label': 'Company name',
      'company.create.name.hint': 'The name customers will see. You can rename it later.',
      'company.create.name.example': 'Northwind Labs',
      'company.create.tagline.label': 'One-line title',
      'company.create.tagline.hint': 'What the company does, in one line.',
      'company.create.tagline.example': 'Applied AI studio for mid-market retailers',
      'company.create.description.label': 'What the company does',
      'company.create.description.mode_label': 'How to describe the company',
      'company.create.description.free': 'Write freely',
      'company.create.description.guided': 'Answer four questions',
      'company.create.description.free_label': 'Description',
      'company.create.description.hint': 'At least a couple of sentences. Who it serves, what it sells, and how it makes money.',
      'company.create.description.example': 'We build ordering tools for neighbourhood bakeries. Owners pay a monthly fee and we take a small cut of online orders.',
      'company.create.guided.offer.label': 'What do you offer?',
      'company.create.guided.offer.hint': 'The product or service in plain words.',
      'company.create.guided.offer.example': 'Online ordering and delivery software for bakeries',
      'company.create.guided.audience.label': 'Who is it for?',
      'company.create.guided.audience.hint': 'Be specific: the kind of customer, not everyone.',
      'company.create.guided.audience.example': 'Independent bakery owners with one to six stores',
      'company.create.guided.difference.label': 'Why choose you?',
      'company.create.guided.difference.hint': 'The one thing you do better or differently.',
      'company.create.guided.difference.example': 'Setup in a day, with no new hardware',
      'company.create.guided.revenue.label': 'How does it make money?',
      'company.create.guided.revenue.hint': 'Pricing, fees or commission.',
      'company.create.guided.revenue.example': 'A monthly subscription plus a small commission on orders',
      'company.create.guided.preview': 'This is the description we will use',
      'company.create.guided.empty': 'Answer the questions above and the description appears here.',
      'company.create.guided.sentence.audience': 'It serves',
      'company.create.guided.sentence.difference': 'It stands out because',
      'company.create.guided.sentence.revenue': 'It makes money by',
      'company.create.you.title': 'You',
      'company.create.you.note': 'Used for the audit trail and for the export copy of this company.',
      'company.create.owner.label': 'Your name',
      'company.create.owner.hint': 'The person accountable for this company.',
      'company.create.email.label': 'Email',
      'company.create.email.hint': 'Needed for a verified export copy later. You can add it then.',
      'company.create.email.example': 'you@company.com',
      'company.create.role.label': 'Your role',
      'company.create.role.hint': 'For example founder, director or operations lead.',
      'company.create.role.example': 'Founder',
      'company.create.where.title': 'Where you operate',
      'company.create.where.note': 'This decides which legal and tax drafts are prepared.',
      'company.create.country.label': 'Country',
      'company.create.country.hint': 'Two-letter code or country name.',
      'company.create.industry.label': 'Industry',
      'company.create.industry.hint': 'The closest match, in your own words.',
      'company.create.industry.example': 'Food & Beverage',
      'company.create.optional.title': 'Optional details',
      'company.create.optional.note': 'Website, customers, budget, timeline and notes. You can add these later too.',
      'company.create.website.label': 'Website',
      'company.create.website.hint': 'Leave empty if there is no website yet.',
      'company.create.assets.label': 'Asset links',
      'company.create.assets.hint': 'One link per line. Brand kit, deck, product photos, existing documents.',
      'company.create.customers.label': 'Target customers',
      'company.create.customers.hint': 'Who you want to reach first.',
      'company.create.customers.example': 'Independent retailers in India with 1-6 stores',
      'company.create.budget.label': 'Starting budget',
      'company.create.budget.hint': 'An estimate is fine. Numbers only.',
      'company.create.budget.currency': 'Currency',
      'company.create.budget.currency_hint': 'Three-letter code.',
      'company.create.timeline.label': 'Preferred timeline',
      'company.create.timeline.hint': 'When you would like the company ready.',
      'company.create.timeline.example': 'Ready in about two weeks',
      'company.create.notes.label': 'Anything else',
      'company.create.notes.hint': 'Constraints, existing commitments, things to avoid.',
      'company.create.review_button': 'Review',
      'company.create.footnote': 'Nothing is created yet. The next screen shows exactly what will be submitted.',
      'company.create.review.title': 'Review the setup',
      'company.create.review.subtitle': 'Check the details. After you confirm, the company is created and the build starts.',
      'company.create.review.region': 'Company setup summary',
      'company.create.review.basics': 'Company',
      'company.create.review.edit': 'Edit',
      'company.create.review.owner': 'Owner',
      'company.create.review.not_set': 'Not set',
      'company.create.review.next.title': 'What happens after you confirm',
      'company.create.review.next.one': 'The company is created with the status Creating.',
      'company.create.review.next.two': 'The build reads the brief, drafts the plan and prepares legal drafts for your review.',
      'company.create.review.next.three': 'Anything that needs a connected provider is shown as waiting on you, never marked done.',
      'company.create.review.next.estimate': 'The build is estimated at 1-3 days. That is an estimate, not a promise.',
      'company.create.review.footnote': 'You can edit or delete the company later. Deletion is protected and exports your data first.',
      'company.create.submitting': 'Creating company...',
      'company.create.submit': 'Create company and start the build',
      'company.create.errors.title': 'Please fix these before continuing',
      'company.create.denied.title': 'You cannot create a company',
      'company.create.denied.body': 'Only the owner or an allowed admin can create a company. The server enforces this.',
      'company.create.draft.idle': 'Your answers stay on this device until you review.',
      'company.create.draft.saving': 'Saving your answers...',
      'company.create.draft.saved': 'Draft saved',
      'company.create.draft.local': 'Saved on this device. It will sync when you are back online.',
      'company.create.draft.error': 'Could not save the draft online. Your answers are still on this device.',
      'company.create.error.name_required': 'Enter the company name.',
      'company.create.error.name_short': 'The name must be at least 2 characters.',
      'company.create.error.title_required': 'Add a one-line title.',
      'company.create.error.description_required': 'Describe what the company does.',
      'company.create.error.description_short': 'Use at least 20 characters so the plan has something to work with.',
      'company.create.error.owner_required': 'Add the name of the accountable person.',
      'company.create.error.email': 'Enter a valid email address.',
      'company.create.error.country_required': 'Add the country where the company operates.',
      'company.create.error.industry_required': 'Add the closest industry.',
      'company.create.error.url': 'Links must start with http:// or https://.',
      'company.create.error.assets': 'Every asset link must start with http:// or https://.',
      'company.create.error.budget': 'Enter a number, or leave the budget empty.',
      'company.create.error.currency': 'Use a three-letter currency code.',
      'company.create.error.duplicate': 'A company with this name already exists. Choose a different name.',
      'company.create.error.submit_failed': 'The company was created as a draft, but the build did not start. You can submit it from the overview.',
      'company.create.error.create_failed': 'The company could not be created. Nothing was saved.',
      'company.create.error.network': 'Could not reach the server. Your answers are still on this device.',
      'company.create.created': 'Company created. The build has started.',

      'company.build.back': 'Overview',
      'company.build.title': 'Company build',
      'company.build.eyebrow': 'Build progress',
      'company.build.subtitle': 'Every phase below is real. Anything that needs a provider is shown as waiting on you.',
      'company.build.progress.title': 'Progress',
      'company.build.progress.value': '{percent} percent complete',
      'company.build.progress.caption': '{done} of {total} phases finished',
      'company.build.live': 'This build is running. The page updates by itself.',
      'company.build.phases.title': 'Phases',
      'company.build.phase.pending': 'Not started',
      'company.build.phase.running': 'Running',
      'company.build.phase.done': 'Done',
      'company.build.phase.done_with_gaps': 'Done with gaps',
      'company.build.phase.skipped': 'Skipped',
      'company.build.phase.failed': 'Failed',
      'company.build.phase_label.INTAKE': 'Understanding your brief',
      'company.build.phase_label.RESEARCH': 'Researching the market',
      'company.build.phase_label.PLAN': 'Planning the company',
      'company.build.phase_label.BUILD': 'Building base systems',
      'company.build.phase_label.LEGAL_PACK': 'Drafting the legal pack',
      'company.build.phase_label.VERIFY': 'Checking everything',
      'company.build.phase_label.OPERATIONAL': 'Going operational',
      'company.build.phase_label.CONNECT_VERIFY': 'Connecting and verifying sources',
      'company.build.phase_label.STUDY': 'Studying the business',
      'company.build.phase_label.DIAGNOSE': 'Diagnosing what to improve',
      'company.build.phase_label.ACT': 'Acting on approved work',
      'company.build.run.pending': 'Queued',
      'company.build.run.running': 'Running',
      'company.build.run.done': 'Operational',
      'company.build.run.gaps': 'Needs attention',
      'company.build.run.failed': 'Build failed',
      'company.build.waiting.title': 'Waiting on you',
      'company.build.waiting.note': 'These steps need something connected or a decision from you. Nothing was faked to fill the gap.',
      'company.build.waiting.item': 'A step needs attention',
      'company.build.retry.button': 'Try the build again',
      'company.build.retry.running': 'Retrying...',
      'company.build.retry.started': 'A new build attempt has started.',
      'company.build.error.title': 'Could not load the build',
      'company.build.error.no_company': 'No company was selected.',
      'company.build.error.not_found': 'This company was not found in your organisation.',
      'company.build.error.load': 'The build details could not be loaded.',
      'company.build.error.offline': 'You are offline. Reconnect and try again.',
      'company.build.error.network': 'Could not reach the server. Try again.',
      'company.build.error.retry': 'The build could not be retried.',
      'company.build.empty.title': 'No build has started',
      'company.build.empty.body': 'This company has no build run yet. Submit the company again from its overview, or start a new company.',
      'company.build.done.title': 'The build finished',
      'company.build.done.body': 'Every phase passed. The company is operational.',
      'company.build.failed.title': 'The build stopped',
      'company.build.log.title': 'What happened',
      'company.build.log.all': 'Show all',
      'company.build.log.less': 'Show less',
      'company.build.log.empty': 'No entries yet.',
      'company.build.estimate.range': 'Estimate: {min}-{max} days',
      'company.build.estimate.one': 'Estimate: {days} day',
      'company.build.attempt': 'Attempt {attempt}',
      'company.build.overview': 'Back to overview',
      'company.build.footnote': 'Times are shown in your local timezone. The build never marks a skipped step as done.',
      'assistant.add_opened': 'Opening the Add company page. Nothing has been created yet.',
      'assistant.switch_opened': 'Opening your companies. Nothing has been switched yet.',

      'format.lakh': 'L',
      'format.crore': 'Cr',
      'format.thousand': 'K'
    },

    ar: {
      'common.cancel': 'إلغاء',
      'common.close': 'إغلاق',
      'common.back': 'رجوع',
      'common.retry': 'إعادة المحاولة',
      'common.loading': 'جارٍ التحميل…',
      'common.english': 'English',
      'common.arabic': 'العربية',
      'common.language': 'اللغة',

      'status.draft': 'مسودة',
      'status.creating': 'قيد الإنشاء',
      'status.onboarding': 'قيد التهيئة',
      'status.operational': 'تعمل',
      'status.needs_attention': 'تحتاج إلى انتباه',
      'status.pending_export': 'بانتظار التصدير',
      'status.pending_deletion': 'بانتظار الحذف',
      'status.deleted': 'محذوفة',
      'status.suspended': 'موقوفة',
      'status.unknown': 'حالة غير معروفة',

      'company.switcher.title': 'تبديل الشركة',
      'company.switcher.subtitle': 'تظهر شركتك الحالية أولاً.',
      'company.switcher.current': 'الحالية',
      'company.switcher.empty.title': 'لا توجد شركات بعد',
      'company.switcher.empty.body': 'أضف شركتك الأولى لبدء العمل.',
      'company.switcher.empty.sidebar': 'لا توجد شركة بعد',
      'company.switcher.empty.status': 'أضف شركة للبدء',
      'company.switcher.add': 'إضافة شركة',
      'company.switcher.switched': 'تم التبديل إلى {name}',
      'company.switcher.refresh_failed': 'تعذّر التحديث. يتم عرض الشركات المحمّلة سابقاً على هذا الجهاز.',
      'company.switcher.refreshing': 'جارٍ تحديث الشركات…',
      'company.switcher.portfolio': 'كل الشركات (المحفظة)',
      'company.switcher.unknown_industry': 'شركة عاملة',

      'company.add.back': 'الشركات',
      'company.add.title': 'إضافة شركة',
      'company.add.subtitle': 'اختر كيف تنضم هذه الشركة إلى ZONATA. يمكنك تعديلها أو حذفها لاحقاً.',
      'company.add.new.badge': 'جديدة',
      'company.add.new.title': 'إنشاء شركة جديدة',
      'company.add.new.body': 'لعمل لم يوجد بعد. تبني ZONATA الشركة معك خطوة بخطوة.',
      'company.add.new.point1': 'تبدأ بحالة قيد الإنشاء',
      'company.add.new.point2': 'بناء موجّه، عادة من يوم إلى ثلاثة أيام',
      'company.add.new.point3': 'مسودة للهيكل القانوني والتشغيلي لمراجعتك',
      'company.add.new.point4': 'يمكنك تعديلها أو حذفها لاحقاً',
      'company.add.new.cta': 'إنشاء شركة جديدة',
      'company.add.existing.badge': 'موجودة',
      'company.add.existing.title': 'إضافة شركة موجودة',
      'company.add.existing.body': 'لعمل يعمل بالفعل. تدرسه ZONATA وتشخّص ما يحتاج إلى تحسين.',
      'company.add.existing.point1': 'تبدأ بحالة قيد التهيئة',
      'company.add.existing.point2': 'اتصالات للقراءة فقط — لا يُكتب أي شيء في أنظمتك',
      'company.add.existing.point3': 'تشخيص ونتائج جاهزية مع الأدلة',
      'company.add.existing.point4': 'تبقى بياناتك في أنظمتك',
      'company.add.existing.cta': 'إضافة شركة موجودة',
      'company.add.not_sure': 'لست متأكداً من الاختيار؟',
      'company.add.help.title': 'طريقة سريعة للقرار',
      'company.add.help.new': 'اختر «إنشاء شركة جديدة» إذا لم يكن للشركة سجل في ZONATA ولا تملك بيانات تشغيلية تُذكر.',
      'company.add.help.existing': 'اختر «إضافة شركة موجودة» إذا كان لديها عملاء أو إيرادات أو أدوات أو سجلات.',
      'company.add.help.note': 'يبدأ المساران كمسودة. لا يُرسل أي شيء حتى تراجع وتؤكد.',
      'company.add.denied.title': 'لا يمكنك إضافة شركة',
      'company.add.denied.body': 'يمكن للمالك أو المسؤول المصرّح له فقط إضافة شركة. يمكنك دائماً أن تطلب من المساعد إعداد مسودة.',
      'company.add.intent_new': 'جارٍ فتح إعداد الشركة الجديدة. لم يتم إنشاء أي شيء بعد.',
      'company.add.intent_existing': 'جارٍ فتح استقبال الشركة الموجودة. لم يتم ربط أي شيء بعد.',
      'company.add.footnote': 'قائمة شركاتك مرتبطة بمؤسستك فقط. لا يمكن لمستأجر آخر رؤيتها أو تغييرها.',


      'company.create.back': 'الشركات',
      'company.create.steps_label': 'خطوات الإعداد',
      'company.create.step.details': 'التفاصيل',
      'company.create.step.review': 'المراجعة',
      'company.create.title': 'إنشاء شركة جديدة',
      'company.create.subtitle': 'موجز قصير. تحوّله ZONATA إلى خطة بناء، ثم تعرض لك ما هو حقيقي وما ينتظرك.',
      'company.create.optional': 'اختياري',
      'company.create.example': 'مثال: {example}',
      'company.create.basics.title': 'الشركة',
      'company.create.basics.note': 'اكتبها كما تشرحها لزميل جديد.',
      'company.create.name.label': 'اسم الشركة',
      'company.create.name.hint': 'الاسم الذي سيراه العملاء. يمكنك تغييره لاحقاً.',
      'company.create.name.example': 'مختبرات نورث ويند',
      'company.create.tagline.label': 'وصف من سطر واحد',
      'company.create.tagline.hint': 'ما تفعله الشركة في سطر واحد.',
      'company.create.tagline.example': 'استوديو ذكاء اصطناعي تطبيقي لمتاجر التجزئة المتوسطة',
      'company.create.description.label': 'ماذا تفعل الشركة',
      'company.create.description.mode_label': 'طريقة وصف الشركة',
      'company.create.description.free': 'اكتب بحرية',
      'company.create.description.guided': 'أجب عن أربعة أسئلة',
      'company.create.description.free_label': 'الوصف',
      'company.create.description.hint': 'جملتان على الأقل: لمن تخدم، وماذا تبيع، وكيف تربح.',
      'company.create.description.example': 'نبني أدوات طلبات لمخابز الأحياء. يدفع المالكون رسماً شهرياً ونأخذ نسبة صغيرة من الطلبات الإلكترونية.',
      'company.create.guided.offer.label': 'ماذا تقدم؟',
      'company.create.guided.offer.hint': 'المنتج أو الخدمة بكلمات واضحة.',
      'company.create.guided.offer.example': 'برنامج طلبات وتوصيل للمخابز',
      'company.create.guided.audience.label': 'لمن؟',
      'company.create.guided.audience.hint': 'كن محدداً: نوع العميل، وليس الجميع.',
      'company.create.guided.audience.example': 'أصحاب مخابز مستقلون لديهم من متجر إلى ستة متاجر',
      'company.create.guided.difference.label': 'لماذا يختارونك؟',
      'company.create.guided.difference.hint': 'الشيء الوحيد الذي تفعله أفضل أو بشكل مختلف.',
      'company.create.guided.difference.example': 'الإعداد في يوم واحد دون أجهزة جديدة',
      'company.create.guided.revenue.label': 'كيف تربح؟',
      'company.create.guided.revenue.hint': 'التسعير أو الرسوم أو العمولة.',
      'company.create.guided.revenue.example': 'اشتراك شهري مع عمولة صغيرة على الطلبات',
      'company.create.guided.preview': 'هذا هو الوصف الذي سنستخدمه',
      'company.create.guided.empty': 'أجب عن الأسئلة أعلاه ليظهر الوصف هنا.',
      'company.create.guided.sentence.audience': 'تخدم',
      'company.create.guided.sentence.difference': 'تتميز لأنها',
      'company.create.guided.sentence.revenue': 'تربح من خلال',
      'company.create.you.title': 'أنت',
      'company.create.you.note': 'تُستخدم لسجل التدقيق ولنسخة التصدير من هذه الشركة.',
      'company.create.owner.label': 'اسمك',
      'company.create.owner.hint': 'الشخص المسؤول عن هذه الشركة.',
      'company.create.email.label': 'البريد الإلكتروني',
      'company.create.email.hint': 'مطلوب لنسخة تصدير موثقة لاحقاً. يمكنك إضافته حينها.',
      'company.create.email.example': 'you@company.com',
      'company.create.role.label': 'دورك',
      'company.create.role.hint': 'مثل المؤسس أو المدير أو مسؤول العمليات.',
      'company.create.role.example': 'مؤسس',
      'company.create.where.title': 'أين تعمل',
      'company.create.where.note': 'يحدد هذا المسودات القانونية والضريبية التي ستُعد.',
      'company.create.country.label': 'الدولة',
      'company.create.country.hint': 'رمز من حرفين أو اسم الدولة.',
      'company.create.industry.label': 'القطاع',
      'company.create.industry.hint': 'أقرب وصف بكلماتك.',
      'company.create.industry.example': 'الأغذية والمشروبات',
      'company.create.optional.title': 'تفاصيل اختيارية',
      'company.create.optional.note': 'الموقع والعملاء والميزانية والجدول والملاحظات. يمكنك إضافتها لاحقاً أيضاً.',
      'company.create.website.label': 'الموقع الإلكتروني',
      'company.create.website.hint': 'اتركه فارغاً إن لم يكن هناك موقع بعد.',
      'company.create.assets.label': 'روابط الملفات',
      'company.create.assets.hint': 'رابط واحد في كل سطر. هوية العلامة، العرض التقديمي، صور المنتجات، المستندات.',
      'company.create.customers.label': 'العملاء المستهدفون',
      'company.create.customers.hint': 'من تريد الوصول إليه أولاً.',
      'company.create.customers.example': 'متاجر تجزئة مستقلة في الهند لديها من متجر إلى ستة متاجر',
      'company.create.budget.label': 'الميزانية الأولية',
      'company.create.budget.hint': 'التقدير كافٍ. أرقام فقط.',
      'company.create.budget.currency': 'العملة',
      'company.create.budget.currency_hint': 'رمز من ثلاثة أحرف.',
      'company.create.timeline.label': 'الجدول المفضل',
      'company.create.timeline.hint': 'متى تريد أن تكون الشركة جاهزة.',
      'company.create.timeline.example': 'جاهزة خلال أسبوعين تقريباً',
      'company.create.notes.label': 'أي شيء آخر',
      'company.create.notes.hint': 'قيود أو التزامات قائمة أو أمور يجب تجنبها.',
      'company.create.review_button': 'مراجعة',
      'company.create.footnote': 'لم يُنشأ شيء بعد. تعرض الشاشة التالية ما سيُرسل بالضبط.',
      'company.create.review.title': 'راجع الإعداد',
      'company.create.review.subtitle': 'تحقق من التفاصيل. بعد التأكيد تُنشأ الشركة ويبدأ البناء.',
      'company.create.review.region': 'ملخص إعداد الشركة',
      'company.create.review.basics': 'الشركة',
      'company.create.review.edit': 'تعديل',
      'company.create.review.owner': 'المالك',
      'company.create.review.not_set': 'غير محدد',
      'company.create.review.next.title': 'ما يحدث بعد التأكيد',
      'company.create.review.next.one': 'تُنشأ الشركة بحالة قيد الإنشاء.',
      'company.create.review.next.two': 'يقرأ البناء الموجز ويضع الخطة ويعد المسودات القانونية لمراجعتك.',
      'company.create.review.next.three': 'أي خطوة تحتاج مزوداً متصلاً تظهر كمنتظرة لك، ولا تُعلَّم كمنجزة.',
      'company.create.review.next.estimate': 'التقدير من يوم إلى ثلاثة أيام. هذا تقدير وليس وعداً.',
      'company.create.review.footnote': 'يمكنك تعديل الشركة أو حذفها لاحقاً. الحذف محمي ويصدّر بياناتك أولاً.',
      'company.create.submitting': 'جارٍ إنشاء الشركة...',
      'company.create.submit': 'إنشاء الشركة وبدء البناء',
      'company.create.errors.title': 'يرجى إصلاح ما يلي قبل المتابعة',
      'company.create.denied.title': 'لا يمكنك إنشاء شركة',
      'company.create.denied.body': 'يمكن للمالك أو المسؤول المصرّح له فقط إنشاء شركة. الخادم هو من يفرض ذلك.',
      'company.create.draft.idle': 'تبقى إجاباتك على هذا الجهاز حتى تراجعها.',
      'company.create.draft.saving': 'جارٍ حفظ إجاباتك...',
      'company.create.draft.saved': 'تم حفظ المسودة',
      'company.create.draft.local': 'حُفظت على هذا الجهاز. ستتم المزامنة عند عودة الاتصال.',
      'company.create.draft.error': 'تعذر حفظ المسودة عبر الإنترنت. إجاباتك ما زالت على هذا الجهاز.',
      'company.create.error.name_required': 'أدخل اسم الشركة.',
      'company.create.error.name_short': 'يجب أن يكون الاسم حرفين على الأقل.',
      'company.create.error.title_required': 'أضف وصفاً من سطر واحد.',
      'company.create.error.description_required': 'صف ما تفعله الشركة.',
      'company.create.error.description_short': 'استخدم 20 حرفاً على الأقل ليكون لدى الخطة ما تعمل به.',
      'company.create.error.owner_required': 'أضف اسم الشخص المسؤول.',
      'company.create.error.email': 'أدخل بريداً إلكترونياً صالحاً.',
      'company.create.error.country_required': 'أضف الدولة التي تعمل فيها الشركة.',
      'company.create.error.industry_required': 'أضف أقرب قطاع.',
      'company.create.error.url': 'يجب أن تبدأ الروابط بـ http:// أو https://.',
      'company.create.error.assets': 'يجب أن يبدأ كل رابط ملف بـ http:// أو https://.',
      'company.create.error.budget': 'أدخل رقماً، أو اترك الميزانية فارغة.',
      'company.create.error.currency': 'استخدم رمز عملة من ثلاثة أحرف.',
      'company.create.error.duplicate': 'توجد شركة بهذا الاسم بالفعل. اختر اسماً آخر.',
      'company.create.error.submit_failed': 'أُنشئت الشركة كمسودة، لكن البناء لم يبدأ. يمكنك إرسالها من النظرة العامة.',
      'company.create.error.create_failed': 'تعذر إنشاء الشركة. لم يُحفظ شيء.',
      'company.create.error.network': 'تعذر الوصول إلى الخادم. إجاباتك ما زالت على هذا الجهاز.',
      'company.create.created': 'أُنشئت الشركة. بدأ البناء.',

      'company.build.back': 'النظرة العامة',
      'company.build.title': 'بناء الشركة',
      'company.build.eyebrow': 'تقدم البناء',
      'company.build.subtitle': 'كل مرحلة أدناه حقيقية. أي خطوة تحتاج مزوداً تظهر كمنتظرة لك.',
      'company.build.progress.title': 'التقدم',
      'company.build.progress.value': 'اكتمل {percent} بالمئة',
      'company.build.progress.caption': 'اكتملت {done} من {total} مراحل',
      'company.build.live': 'هذا البناء قيد التشغيل. تتحدث الصفحة تلقائياً.',
      'company.build.phases.title': 'المراحل',
      'company.build.phase.pending': 'لم تبدأ',
      'company.build.phase.running': 'قيد التشغيل',
      'company.build.phase.done': 'منجزة',
      'company.build.phase.done_with_gaps': 'منجزة مع فجوات',
      'company.build.phase.skipped': 'متجاوزة',
      'company.build.phase.failed': 'فاشلة',
      'company.build.phase_label.INTAKE': 'فهم موجزك',
      'company.build.phase_label.RESEARCH': 'بحث السوق',
      'company.build.phase_label.PLAN': 'تخطيط الشركة',
      'company.build.phase_label.BUILD': 'بناء الأنظمة الأساسية',
      'company.build.phase_label.LEGAL_PACK': 'إعداد الحزمة القانونية',
      'company.build.phase_label.VERIFY': 'التحقق من كل شيء',
      'company.build.phase_label.OPERATIONAL': 'بدء التشغيل',
      'company.build.phase_label.CONNECT_VERIFY': 'ربط المصادر والتحقق منها',
      'company.build.phase_label.STUDY': 'دراسة العمل',
      'company.build.phase_label.DIAGNOSE': 'تشخيص ما يحتاج إلى تحسين',
      'company.build.phase_label.ACT': 'تنفيذ العمل المعتمد',
      'company.build.run.pending': 'في الانتظار',
      'company.build.run.running': 'قيد التشغيل',
      'company.build.run.done': 'تعمل',
      'company.build.run.gaps': 'تحتاج إلى انتباه',
      'company.build.run.failed': 'فشل البناء',
      'company.build.waiting.title': 'بانتظارك',
      'company.build.waiting.note': 'هذه الخطوات تحتاج شيئاً متصلاً أو قراراً منك. لم يُختلق شيء لملء الفجوة.',
      'company.build.waiting.item': 'خطوة تحتاج إلى انتباه',
      'company.build.retry.button': 'إعادة محاولة البناء',
      'company.build.retry.running': 'جارٍ إعادة المحاولة...',
      'company.build.retry.started': 'بدأت محاولة بناء جديدة.',
      'company.build.error.title': 'تعذر تحميل البناء',
      'company.build.error.no_company': 'لم يتم اختيار شركة.',
      'company.build.error.not_found': 'لم يتم العثور على هذه الشركة في مؤسستك.',
      'company.build.error.load': 'تعذر تحميل تفاصيل البناء.',
      'company.build.error.offline': 'أنت غير متصل. أعد الاتصال وحاول مجدداً.',
      'company.build.error.network': 'تعذر الوصول إلى الخادم. حاول مجدداً.',
      'company.build.error.retry': 'تعذرت إعادة محاولة البناء.',
      'company.build.empty.title': 'لم يبدأ أي بناء',
      'company.build.empty.body': 'لا يوجد تشغيل بناء لهذه الشركة بعد. أرسل الشركة من نظرة عامة أو ابدأ شركة جديدة.',
      'company.build.done.title': 'اكتمل البناء',
      'company.build.done.body': 'نجحت كل المراحل. الشركة تعمل.',
      'company.build.failed.title': 'توقف البناء',
      'company.build.log.title': 'ما حدث',
      'company.build.log.all': 'عرض الكل',
      'company.build.log.less': 'عرض أقل',
      'company.build.log.empty': 'لا توجد سجلات بعد.',
      'company.build.estimate.range': 'التقدير: {min}-{max} أيام',
      'company.build.estimate.one': 'التقدير: {days} يوم',
      'company.build.attempt': 'المحاولة {attempt}',
      'company.build.overview': 'العودة إلى النظرة العامة',
      'company.build.footnote': 'تُعرض الأوقات بتوقيتك المحلي. لا يعلّم البناء أي خطوة متجاوزة كمنجزة.',
      'assistant.add_opened': 'جارٍ فتح صفحة إضافة شركة. لم يتم إنشاء أي شيء بعد.',
      'assistant.switch_opened': 'جارٍ فتح شركاتك. لم يتم تبديل أي شيء بعد.',

      'format.lakh': ' لك',
      'format.crore': ' كر',
      'format.thousand': ' ألف'
    }
  };

  const listeners = new Set();
  let language = 'en';

  function normaliseLanguage(value) {
    const raw = String(value || '').toLowerCase().split('-')[0];
    return SUPPORTED.indexOf(raw) >= 0 ? raw : 'en';
  }

  function readStoredLanguage() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return null;
    }
  }

  function writeStoredLanguage(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (err) {
      // Private mode / blocked storage: keep the in-memory choice.
    }
  }

  function lookup(dict, key) {
    if (!key) return '';
    if (Object.prototype.hasOwnProperty.call(dict, key)) return dict[key];
    // Allow a flat dictionary to be addressed with dotted keys.
    const parts = String(key).split('.');
    let node = dict;
    for (const part of parts) {
      if (node && typeof node === 'object' && Object.prototype.hasOwnProperty.call(node, part)) {
        node = node[part];
      } else {
        return '';
      }
    }
    return typeof node === 'string' ? node : '';
  }

  function interpolate(text, vars) {
    if (!vars || typeof text !== 'string') return text;
    return text.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) => {
      const value = vars[name];
      return value === undefined || value === null ? match : String(value);
    });
  }

  function t(key, vars) {
    const current = DICTIONARIES[language] || DICTIONARIES.en;
    const fallback = DICTIONARIES.en;
    const value = lookup(current, key) || lookup(fallback, key) || key;
    return interpolate(value, vars);
  }

  function dirFor(lang) {
    return lang === 'ar' ? 'rtl' : 'ltr';
  }

  function apply(root) {
    const scope = root && root.querySelectorAll ? root : document;
    if (!scope || !scope.querySelectorAll) return;

    scope.querySelectorAll('[data-i18n]').forEach((el) => {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    scope.querySelectorAll('[data-i18n-aria-label]').forEach((el) => {
      el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria-label')));
    });
    scope.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
    });
    scope.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder')));
    });
  }

  function setLanguage(next, options) {
    const value = normaliseLanguage(next);
    const changed = value !== language;
    language = value;
    writeStoredLanguage(value);

    const html = document.documentElement;
    if (html) {
      html.setAttribute('lang', value);
      html.setAttribute('dir', dirFor(value));
    }

    apply(document);
    listeners.forEach((fn) => {
      try {
        fn(value, dirFor(value));
      } catch (err) {
        console.warn('[I18n] listener failed', err);
      }
    });

    if (changed && options && options.announce === false) return value;
    document.dispatchEvent(new CustomEvent('zonata:languagechange', { detail: { language: value, dir: dirFor(value) } }));
    return value;
  }

  function onLanguageChange(fn) {
    if (typeof fn !== 'function') return () => {};
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  function getLanguage() {
    return language;
  }

  function getDir() {
    return dirFor(language);
  }

  function locale() {
    return language === 'ar' ? 'ar-IN' : 'en-IN';
  }

  function formatNumber(value, options) {
    const n = Number(value);
    const safe = Number.isFinite(n) ? n : 0;
    try {
      return new Intl.NumberFormat(locale(), options || {}).format(safe);
    } catch (err) {
      return String(safe);
    }
  }

  function formatCurrency(amount, currency, options) {
    const code = String(currency || 'INR').toUpperCase();
    const opts = options || {};
    const n = Number(amount);
    const safe = Number.isFinite(n) ? n : 0;

    if (opts.compact) {
      return formatCompactCurrency(safe, code);
    }

    try {
      return new Intl.NumberFormat(locale(), {
        style: 'currency',
        currency: code,
        maximumFractionDigits: opts.maximumFractionDigits === undefined ? 0 : opts.maximumFractionDigits,
        minimumFractionDigits: opts.minimumFractionDigits === undefined ? 0 : opts.minimumFractionDigits
      }).format(safe);
    } catch (err) {
      return `${code} ${formatNumber(safe, opts)}`;
    }
  }

  function currencySymbol(code) {
    try {
      const parts = new Intl.NumberFormat(locale(), { style: 'currency', currency: code, maximumFractionDigits: 0 })
        .formatToParts(0);
      const symbol = parts.find((part) => part.type === 'currency');
      return symbol ? symbol.value : code;
    } catch (err) {
      return code === 'INR' ? '₹' : code;
    }
  }

  /**
   * Indian compact notation: 1,00,000 -> 1 L, 1,00,00,000 -> 1 Cr.
   * Non-INR currencies fall back to the locale's compact notation.
   */
  function formatCompactCurrency(amount, currency) {
    const code = String(currency || 'INR').toUpperCase();
    const n = Number(amount);
    const safe = Number.isFinite(n) ? n : 0;
    const sign = safe < 0 ? '-' : '';
    const abs = Math.abs(safe);
    const symbol = currencySymbol(code);

    if (code === 'INR') {
      if (abs >= 1e7) {
        const value = abs / 1e7;
        return `${sign}${symbol}${formatNumber(value, { maximumFractionDigits: value >= 10 ? 0 : 1 })}${t('format.crore')}`;
      }
      if (abs >= 1e5) {
        const value = abs / 1e5;
        return `${sign}${symbol}${formatNumber(value, { maximumFractionDigits: value >= 10 ? 0 : 1 })}${t('format.lakh')}`;
      }
      if (abs >= 1e3) {
        return `${sign}${symbol}${formatNumber(abs / 1e3, { maximumFractionDigits: 0 })}${t('format.thousand')}`;
      }
      return `${sign}${symbol}${formatNumber(abs, { maximumFractionDigits: 0 })}`;
    }

    try {
      return new Intl.NumberFormat(locale(), {
        style: 'currency',
        currency: code,
        notation: 'compact',
        maximumFractionDigits: 1
      }).format(safe);
    } catch (err) {
      return `${sign}${symbol}${formatNumber(abs, { notation: 'compact', maximumFractionDigits: 1 })}`;
    }
  }

  function init() {
    const stored = readStoredLanguage();
    language = normaliseLanguage(stored || 'en');
    const html = document.documentElement;
    if (html) {
      html.setAttribute('lang', language);
      html.setAttribute('dir', dirFor(language));
    }
    apply(document);
    return language;
  }

  window.I18n = {
    SUPPORTED,
    t,
    apply,
    init,
    setLanguage,
    getLanguage,
    getDir,
    onLanguageChange,
    formatNumber,
    formatCurrency,
    formatCompactCurrency,
    locale
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
