import type { ChatSource, HarmRef, Reflection } from './types';

export const BACKUP_TRIGGER = 'backup';

export const BACKUP_PARTICIPANT_KEY = BACKUP_TRIGGER;

export function isBackupTrigger(value: string): boolean {
	return value.trim().toLowerCase() === BACKUP_TRIGGER;
}

let autoStartPending = false;

export function markBackupAutoStart(): void {
	autoStartPending = true;
}

export function consumeBackupAutoStart(): boolean {
	if (!autoStartPending) return false;
	autoStartPending = false;
	return true;
}

const BACKUP_SESSION_PREFIX = 'backup-';

export function backupSessionId(speed: string): string {
	return `${BACKUP_SESSION_PREFIX}${speed}`;
}

export function isBackupSessionId(sessionId: string | null | undefined): boolean {
	return !!sessionId && sessionId.startsWith(BACKUP_SESSION_PREFIX);
}

export const BACKUP_DESCRIPTION =
	'An AI app that allows users to specify their own symptoms and get AI medical advice.';

export const BACKUP_TITLE = 'AI Symptom Checker';

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const jitter = (lo: number, hi: number) => lo + Math.random() * (hi - lo);

const h = (category: HarmRef['category'], explanation: string): HarmRef => ({ category, explanation });

const BACKUP_REFLECTIONS: Reflection[] = [
	{
		dimension: 'tomorrow',
		title: 'AI symptom checker safety risks',
		body: "On launch, the app risks under-triaging genuine emergencies and confidently delivering wrong or contraindicated advice, mirroring documented ChatGPT and Babylon Health harms where users nearly died or were hospitalized. Vulnerable groups—people in mental health crisis, those with addiction histories, women, and users without other healthcare access—face the sharpest immediate danger, compounded by the AI's persuasive, authoritative tone and buried disclaimers.",
		harms: [
			h(
				'False information',
				'The model can generate confident but clinically wrong triage, diagnoses, and medication advice that delays life-saving care.'
			),
			h(
				'Manipulation',
				'Its sycophantic, empathetic tone can persuade hesitant, vulnerable users into harmful actions against their own instincts.'
			),
			h(
				'Accountability',
				'Harmed users have no clear responsible party when disclaimers are hidden and no external audit exists.'
			)
		],
		mitigation:
			'Implement hard-coded safety overrides for emergency and self-harm keywords that halt AI advice and direct users to emergency services or crisis lines, with prominent point-of-answer disclaimers.',
		points: [
			{
				title: 'Under-triaged medical emergencies',
				point:
					'On day one, the app may reassure users with serious emergencies (diabetic ketoacidosis, impending respiratory failure, heart attack) to wait or self-treat rather than seek immediate care, causing dangerous delays. The Mount Sinai study of ChatGPT Health found it under-triaged about 52% of cases physicians deemed emergencies, and two Vietnamese women nearly died in 2025 after ChatGPT led them to stop life-saving medication.',
				context_label: 'Affects',
				context:
					'Elderly people with multiple comorbidities, Parents and caregivers of children with serious conditions, Low-income and uninsured populations, Undocumented immigrants and migrant workers, Emergency departments and hospital systems',
				harms: [
					h(
						'False information',
						'The AI can confidently issue clinically wrong triage guidance that downplays a genuine emergency.'
					),
					h(
						'Accountability',
						'When a user is harmed by delayed care, there is no clear responsible party since disclaimers are buried in terms of service.'
					)
				],
				mitigation:
					'Implement hard-coded emergency triggers: when red-flag symptoms (chest pain, difficulty breathing, stroke signs, pediatric high-fever/lethargy) are detected, override the conversation with an unmissable instruction to call emergency services rather than generating advice.'
			},
			{
				title: 'Inconsistent suicide-crisis response',
				point:
					"Users disclosing self-harm plans may receive no crisis resources while lower-risk users get false alerts, mirroring ChatGPT Health's unpredictable, severity-miscalibrated suicide-alert triggering. A person in acute crisis could be falsely reassured or left without the 988 lifeline at the exact moment they need it.",
				context_label: 'Affects',
				context: 'Individuals experiencing mental health crises or suicidal ideation',
				harms: [
					h(
						'False information',
						'The system may fail to convey the true severity of a self-harm situation or omit accurate crisis guidance.'
					),
					h(
						'Accountability',
						'A failed crisis response leaves no accountable safeguard when a vulnerable user is missed.'
					)
				],
				mitigation:
					'Deploy a dedicated, tested self-harm classifier that reliably surfaces crisis hotlines (e.g. 988) for any explicit or implicit self-harm content, calibrated to err toward showing resources.'
			},
			{
				title: 'Dangerous medication recommendations',
				point:
					"The AI may recommend or endorse medications that interact dangerously with a user's disclosed conditions or addiction history, then persuade a hesitant user to proceed—exactly as ChatGPT did in 2024, downplaying risk and driving a man with addiction history into psychosis and hospitalization after taking pseudoephedrine.",
				context_label: 'Affects',
				context: 'People with addiction histories or substance use disorders, People with limited digital literacy',
				harms: [
					h(
						'Manipulation',
						"The AI's sycophantic, persuasive tone can talk a hesitant, vulnerable user into a harmful action against their own instincts."
					),
					h(
						'False information',
						"The model may present contraindicated drugs as safe without weighing the user's stated medical history."
					)
				],
				mitigation:
					'Block specific medication/dosage recommendations entirely; when substance or contraindication keywords (addiction, stimulant sensitivity, psychosis, hypertension) appear, trigger a hard stop directing users to a pharmacist or physician.'
			},
			{
				title: 'Gender-biased triage',
				point:
					"Women and gender minorities may receive systematically less accurate or deprioritized triage, as documented with Babylon Health's symptom checker, delaying treatment for conditions that present differently by sex (e.g. atypical cardiac symptoms in women).",
				context_label: 'Affects',
				context: 'Women and gender minorities',
				harms: [
					h(
						'Disparity',
						'Biased training data can produce systematically worse outcomes for women and gender minorities using the same feature.'
					),
					h(
						'False information',
						'Sex-blind reasoning can yield inaccurate diagnoses for conditions with sex-specific presentations.'
					)
				],
				mitigation:
					'Test triage accuracy across sex/gender subgroups on clinician-authored vignettes before launch and publish the disparity results; correct prompts to account for sex-specific presentations.'
			},
			{
				title: 'False expert authority',
				point:
					"Users with limited digital literacy or those relying on the app as their only healthcare option may treat the confident, conversational AI as a vetted clinician, ignoring their own instincts—as with the tech-savvy Vietnamese patients who placed 'absolute trust' in AI over prescriptions.",
				context_label: 'Affects',
				context:
					'People with limited digital literacy, Low-income and uninsured populations, Undocumented immigrants and migrant workers',
				harms: [
					h(
						'Transparency',
						'The empathetic, authoritative tone obscures that this is a statistical text engine, not a qualified medical professional.'
					),
					h(
						'Manipulation',
						'The empathy illusion plays on user trust, leading them to substitute AI output for professional care.'
					)
				],
				mitigation:
					'Show a persistent, plainly worded disclaimer at the point of every answer (not buried in fine print) stating this is not medical advice, and avoid overly confident phrasing in outputs.'
			}
		]
	},
	{
		dimension: 'in_five_years',
		title: 'Long-term systemic health drift',
		body: "Over years, widespread use quietly displaces professional care, hardens biased triage through retraining feedback loops, and seeds population-scale health myths that clinicians and regulators must later untangle. The heaviest cumulative burden falls on the uninsured, women, elderly, and safety-net hospitals, while the app's consumer framing lets accountability gaps persist unaddressed until harms compound.",
		harms: [
			h(
				'Disparity',
				'Feedback loops and reliance-by-necessity entrench a two-tier system where vulnerable groups receive systematically worse AI care while others keep human doctors.'
			),
			h(
				'False information',
				'Repeated confident errors at scale calcify into durable public health myths and anchor clinician reasoning over time.'
			),
			h(
				'Accountability',
				'Consumer-app framing avoids medical-device oversight, leaving accumulated systemic harms with no responsible or auditable party.'
			)
		],
		mitigation:
			'Adopt medical-device-grade governance now—independent audits, published accuracy/disparity labels, no retraining on unverified outcomes, and metrics that reward routing users toward human care rather than dependency.',
		points: [
			{
				title: 'Erosion of professional care-seeking',
				point:
					"Over years, habitual reliance on the app normalizes self-diagnosis and displaces primary care visits, so users increasingly bypass clinicians for chronic condition management. As emotional reliance grows (the 'digital companion' effect noted in the Mount Sinai study), each individual hallucination becomes more consequential because users have stopped cross-checking with professionals entirely.",
				context_label: 'Affects',
				context:
					'Low-income and uninsured populations, Undocumented immigrants and migrant workers, People with limited digital literacy, Primary care physicians and clinicians',
				harms: [
					h(
						'Manipulation',
						'The convenient, always-available empathetic interface cultivates dependency that steers users away from human care over time.'
					),
					h(
						'Disparity',
						'Those without other options substitute a lower-quality tier of care, entrenching a two-track health system where the poor get AI and the wealthy get doctors.'
					)
				],
				mitigation:
					'Design the product to route users toward, not away from, human care: cap consecutive self-management sessions, surface local low-cost/free clinics and telehealth options, and measure whether the app increases or decreases appropriate care-seeking as a core success metric.'
			},
			{
				title: 'Compounding bias feedback loop',
				point:
					"If the app logs interactions to retrain or fine-tune models, systematically biased triage (the gender bias seen in Babylon Health) gets reinforced as normal, because under-served groups who get worse advice generate the training signal. Over years the disparity widens silently and becomes baked into the model's baseline.",
				context_label: 'Affects',
				context:
					'Women and gender minorities, Elderly people with multiple comorbidities, People with addiction histories or substance use disorders',
				harms: [
					h(
						'Disparity',
						'Retraining on skewed usage data amplifies existing sex, age, and condition-based accuracy gaps rather than correcting them.'
					),
					h(
						'False information',
						'Feedback-reinforced errors propagate as increasingly confident wrong advice for already disadvantaged groups.'
					)
				],
				mitigation:
					'Freeze any retraining behind mandatory subgroup fairness audits on clinician-authored vignettes, publish periodic disparity metrics, and never treat unverified user outcomes as ground-truth training labels.'
			},
			{
				title: 'Population-scale misinformation myths',
				point:
					"At scale, repeated AI advice creates widely-shared 'AI-generated health myths' (as with Google's hallucinated liver-function ranges) that clinicians must spend years debunking. Bad substitutions like the bromide-for-salt case spread from individual harm to community folklore when thousands receive similar confident-but-wrong guidance.",
				context_label: 'Affects',
				context:
					'Primary care physicians and clinicians, Regulatory bodies and public health authorities, People with limited digital literacy',
				harms: [
					h(
						'False information',
						'Consistent hallucinated advice delivered to millions seeds durable false health beliefs across the population.'
					),
					h(
						'Accountability',
						'Once myths diffuse socially, no party is traceable or liable for the downstream public-health damage.'
					)
				],
				mitigation:
					'Log and monitor for recurring dangerous recommendation patterns, publish a transparent correction feed, and share aggregate anomaly data with public-health authorities to catch emerging myths early.'
			},
			{
				title: 'Delayed regulatory accountability gap',
				point:
					"Marketed as a 'search feature' or wellness app rather than a regulated medical device, the product can operate for years without external audits or 'nutritional labels,' exactly the accountability void experts flagged after ChatGPT Health's mass deployment. When harms accumulate, liability remains unallocated among developer, user, and health system.",
				context_label: 'Affects',
				context:
					'Regulatory bodies and public health authorities, Emergency departments and hospital systems, Low-income and uninsured populations',
				harms: [
					h(
						'Accountability',
						'Absent device-grade oversight, systemic harms accrue with no responsible party as the bromism case liability question showed.'
					),
					h(
						'Transparency',
						'Positioning a de facto diagnostic tool as a consumer app hides its clinical risk profile from regulators and users for years.'
					)
				],
				mitigation:
					'Voluntarily adopt medical-device-grade governance now: commission independent external audits, publish an accuracy/limitations label, and maintain a documented incident-reporting and liability pathway before regulation forces it.'
			},
			{
				title: 'Systemic downstream care burden',
				point:
					"As false reassurance drives users to arrive at emergency departments only in advanced crisis states, hospitals face years of higher-acuity, more complex, costlier presentations. Physician reasoning also becomes anchored by patients' AI pre-diagnoses, degrading clinical decision-making across the system over time.",
				context_label: 'Affects',
				context:
					'Emergency departments and hospital systems, Primary care physicians and clinicians, Elderly people with multiple comorbidities, Parents and caregivers of children with serious conditions',
				harms: [
					h(
						'False information',
						'Cumulative under-triage shifts the timing of care so the health system absorbs sicker patients and AI-anchored misdiagnoses.'
					),
					h(
						'Disparity',
						'The added burden falls hardest on safety-net hospitals serving the very populations most reliant on the free app.'
					)
				],
				mitigation:
					'Build clinician-facing handoff summaries that flag AI uncertainty, partner with health systems to study downstream acuity effects, and tune the model to err toward earlier care-seeking rather than reassurance.'
			}
		]
	},
	{
		dimension: 'public_scrutiny',
		title: 'Public scrutiny exposure',
		body: 'External parties would frame this app as an unlicensed medical device marketed with unproven accuracy claims to the people least able to seek alternatives, mirroring the MHRA/ASA/Lancet backlash against Babylon Health and post-ChatGPT-Health calls for device-grade regulation. The sharpest reputational risks come from regulatory-classification evasion, hostility toward safety critics, equity exploitation, and mishandling of deeply sensitive health data.',
		harms: [
			h(
				'Accountability',
				'Consumer-app framing dodges medical-device oversight, leaving no responsible party and inviting regulator and journalist condemnation when harms surface.'
			),
			h(
				'Transparency',
				"Absent peer-reviewed evidence and hidden data reuse make the tool's true risk profile invisible to users and regulators."
			),
			h(
				'Privacy',
				'Intimate symptom, addiction, and mental-health disclosures create major special-category data exposure that data-protection authorities would investigate.'
			)
		],
		mitigation:
			'Proactively pursue medical-device-grade governance and regulatory engagement — independent peer-reviewed validation, honest marketing pre-cleared against advertising standards, a responsible-disclosure channel for safety critics, and strict special-category data protections — before external scrutiny forces it.',
		points: [
			{
				title: 'Unregulated medical device dodge',
				point:
					'Journalists and regulators would flag that a consumer app giving individualized symptom-based medical advice is functionally a diagnostic/triage medical device but marketed to evade classification, avoiding the safety validation, clinical trials, and audits that device rules require.',
				context_label: 'Raised by',
				context:
					"UK MHRA and US FDA, echoing the MHRA's publicly stated concerns about Babylon Health's symptom checker and calls after ChatGPT Health for AI health tools to be regulated as medical devices",
				context_detail:
					"'App sold as wellness tool is really an unlicensed diagnostic device' — an investigative exposé on how the company sidestepped medical-device law while millions took its advice",
				harms: [
					h(
						'Accountability',
						'Positioning a de facto triage tool as a consumer app leaves no regulated responsible party when users are harmed, exactly the gap regulators flagged with Babylon and ChatGPT Health.'
					),
					h(
						'Transparency',
						"The consumer framing conceals the tool's true clinical risk profile from regulators and users."
					)
				],
				mitigation:
					'Proactively engage MHRA/FDA on classification, pursue device certification or clearly scope the product below the medical-advice threshold, and publish the regulatory basis for whatever path is chosen before a journalist frames it as evasion.'
			},
			{
				title: 'No peer-reviewed evidence',
				point:
					"Advocacy groups and clinicians would attack any marketing accuracy claims (e.g. 'as good as a doctor') as unproven, demanding peer-reviewed randomized studies the company never conducted — the precise criticism that drew an ASA ruling and Lancet rebuke against Babylon Health.",
				context_label: 'Raised by',
				context:
					'Royal College of General Practitioners, British Medical Association, medical academics, and the UK Advertising Standards Authority',
				context_detail:
					"'Company exaggerated AI accuracy without a single peer-reviewed trial' — a campaign accusing the developer of misleading vulnerable patients through marketing hype",
				harms: [
					h(
						'False information',
						'Unsubstantiated performance claims mislead users into trusting triage accuracy that has never been independently validated.'
					),
					h('Transparency', 'Marketing hides the absence of clinical evidence behind confident effectiveness claims.')
				],
				mitigation:
					'Commission independent, peer-reviewed clinical-vignette validation before launch, only make accuracy claims backed by published data, and pre-clear all health marketing against advertising-standards rules.'
			},
			{
				title: 'Silencing critics as trolls',
				point:
					"If the company dismisses whistleblowing clinicians or safety researchers who raise concerns, that response itself becomes the scandal — Babylon Health branding oncologist Dr Watkins a 'troll' for flagging safety issues drew heavy reputational damage and vindication when the MHRA agreed with him.",
				context_label: 'Raised by',
				context: 'Investigative journalists, patient-safety advocates, and independent clinicians who test the tool',
				context_detail:
					"'AI health firm smeared the doctor who warned it was unsafe' — a story about corporate hostility to legitimate safety criticism",
				harms: [
					h(
						'Accountability',
						'Attacking critics instead of addressing flagged safety defects shows the company evading responsibility for real risks.'
					),
					h(
						'Censorship',
						"Discrediting or silencing safety researchers suppresses information the public needs about the tool's dangers."
					)
				],
				mitigation:
					'Establish a public responsible-disclosure channel, respond substantively to clinician safety reports, and commit in writing never to characterize good-faith safety critics as bad actors.'
			},
			{
				title: 'Exploiting the uninsured',
				point:
					"Equity advocates would frame the app as profiting from healthcare inaccessibility — offering the poor, uninsured, and undocumented a substandard AI substitute for real care, deepening the 'digital health inequality' The Guardian identified in Google's AI Overviews harms.",
				context_label: 'Raised by',
				context: 'Health-equity NGOs, patient advocacy groups, and public-health researchers',
				context_detail:
					"'The two-tier health system: doctors for the rich, chatbots for the poor' — a campaign exposing how the app entrenches disparity for those with no alternative",
				harms: [
					h(
						'Disparity',
						'Those without other options receive a lower-quality tier of AI care while others access clinicians, widening health inequity.'
					),
					h(
						'Manipulation',
						'Marketing an always-available free tool to people with no alternative steers the most vulnerable toward substituting it for professional care.'
					)
				],
				mitigation:
					'Surface free/low-cost clinic and telehealth referrals prominently, avoid targeting marketing at populations without healthcare access, and publish equity-impact commitments reviewed by community health advocates.'
			},
			{
				title: 'Sensitive health data exposure',
				point:
					"Data-protection regulators would scrutinize how intimate symptom disclosures — addiction history, mental-health crises, reproductive and immigration-sensitive details — are stored, shared, or reused for model training, especially given undocumented users' fears about data reaching authorities.",
				context_label: 'Raised by',
				context:
					'EU/UK data protection authorities (ICO, EDPB) and digital-rights groups like EFF or Privacy International',
				context_detail:
					"'Symptom app harvested millions of people's most private health confessions' — an investigation into consent, retention, and secondary use of special-category health data",
				harms: [
					h(
						'Privacy',
						'Highly sensitive health, addiction, and mental-health disclosures may be retained, reused for training, or exposed beyond what users understood they consented to.'
					),
					h(
						'Transparency',
						"Users are unlikely to grasp that their crisis disclosures could feed model retraining or be legally accessible, echoing consent concerns raised over Google's AI health answers."
					)
				],
				mitigation:
					'Apply special-category data protections: explicit granular consent, on-device or minimized retention, no training reuse without opt-in, clear plain-language privacy notices, and legal safeguards against third-party disclosure.'
			}
		]
	},
	{
		dimension: 'stakeholder_impact',
		title: 'Vulnerable users bear sharpest harm',
		body: 'The people most dependent on this free tool — the uninsured, undocumented, elderly, digitally illiterate, and those with addiction or mental-health histories — face harms tailored to their circumstances: compulsive information loops, isolation-deepening reliance, data-exposure fears, and referrals they cannot act on. Marginalized groups repeatedly turn to accessible online tools for care they cannot get elsewhere, and this app risks re-enacting the dismissiveness, misinformation, and privacy exposure those communities already experience.',
		harms: [
			h(
				'Disparity',
				'Users with no healthcare alternative receive advice they cannot safely execute while insured users keep human clinicians, entrenching a two-tier system.'
			),
			h(
				'Privacy',
				'Addiction, mental-health, reproductive, and immigration-sensitive disclosures create acute exposure for the very groups most endangered by data reuse or leakage.'
			),
			h(
				'Manipulation',
				'An always-available, affirming interface fosters compulsive querying and isolating dependency among users already prone to it.'
			)
		],
		mitigation:
			'Tailor safeguards to the most vulnerable: anonymous no-data-collection use for undocumented users, guided accessible intake for elderly and low-literacy users, prominent free-clinic referrals for the uninsured, and human-connection routing plus session limits for those in crisis or with addiction histories.',
		points: [
			{
				point:
					'Beyond the acute risk of contraindicated drug advice already noted, these users are especially prone to the compulsive information-seeking loop documented in marginalized online communities, where a need for medical answers becomes an addictive pursuit of self-diagnosis. An always-available, non-judgmental chatbot may become a repeated crutch that mirrors the reward-seeking patterns of their disorder, and its sycophantic tone can validate rationalizations for risky self-medication.',
				context_label: 'Stakeholder',
				context: 'People with addiction histories or substance use disorders',
				harms: [
					h(
						'Manipulation',
						'The endlessly available, affirming interface can feed a compulsive query loop that echoes the addictive information-seeking seen in health-focused communities.'
					),
					h(
						'Privacy',
						'Disclosing an addiction history to the app creates a permanent sensitive record that, if retained or reused, could stigmatize or expose them.'
					)
				],
				mitigation:
					'Detect repeat high-frequency sessions on the same symptom cluster and interrupt with a warm hand-off to human addiction support (e.g. SAMHSA helpline), and store addiction disclosures under strict minimized, non-training retention.'
			},
			{
				point:
					'Distinct from the crisis-alert misfires already covered, these users may turn to the app precisely because it feels like a private, shame-free companion when they feel isolated — a dynamic documented among communities who substitute online spaces for human connection. That emotional reliance can deepen isolation and delay real human contact, and exposure to distressing algorithmic content correlates with worsened anxiety and depression in vulnerable users.',
				context_label: 'Stakeholder',
				context: 'Individuals experiencing mental health crises or suicidal ideation',
				harms: [
					h(
						'Manipulation',
						'An empathetic bot positioned as a confidant can substitute for human support and deepen the social isolation these users already report.'
					),
					h(
						'Inappropriate content',
						'Symptom exploration can surface distressing prognosis or self-harm-adjacent content that worsens anxiety and depression, as documented among neurodivergent users.'
					)
				],
				mitigation:
					'For flagged mental-health contexts, steer explicitly toward human connection — peer support lines, warm transfers, and prompts to contact a trusted person — rather than continuing an isolating one-on-one chat with the AI.'
			},
			{
				point:
					'Adding to the documented triage bias, women managing chronic conditions often rely on online spaces for community and validation because their symptoms are dismissed in traditional care; an AI that reproduces that dismissiveness re-enacts a familiar harm at a moment of vulnerability. Gender minorities may also face inaccurate advice when the model assumes a binary sex, misjudging hormone therapy interactions or reproductive symptoms.',
				context_label: 'Stakeholder',
				context: 'Women and gender minorities',
				harms: [
					h(
						'Disparity',
						"Sex-blind or binary-assuming reasoning produces systematically worse guidance for women and gender minorities, echoing Babylon Health's documented gender bias."
					),
					h(
						'False information',
						'The app may give clinically wrong advice for sex-specific or hormone-related presentations it was not trained to handle.'
					)
				],
				mitigation:
					'Ask for and correctly incorporate sex-at-birth, gender identity, and hormone-therapy context, test accuracy across these subgroups, and route uncertain gender-specific cases to specialist referral rather than guessing.'
			},
			{
				point:
					'Beyond under-triage of complex presentations, elderly users with lower digital literacy may struggle to phrase symptoms in the free-text format the app expects, causing the model to miss critical details. Polypharmacy interactions common in this group are exactly the contraindication scenario the model handles poorly, and confusion over the interface can lead to misreporting.',
				context_label: 'Stakeholder',
				context: 'Elderly people with multiple comorbidities',
				harms: [
					h(
						'False information',
						'Incomplete symptom entry by users unaccustomed to chatbots yields confidently wrong triage for medically complex patients.'
					),
					h(
						'Accountability',
						'An elderly user harmed by a missed interaction has little recourse and may not even understand the tool was non-authoritative.'
					)
				],
				mitigation:
					'Offer a structured, guided intake (large-text, voice-enabled, one-question-at-a-time) that explicitly asks about current medications and existing conditions, and default complex polypharmacy cases to a clinician referral.'
			},
			{
				point:
					"Already flagged for two-tier care, these users face an added trap: when the app surfaces advice they cannot afford to act on (expensive tests, prescriptions), they may follow cheaper, dangerous substitutions — paralleling the harmful 'call the cops' or bad-substitute advice documented for vulnerable communities online. The free tool becomes not a bridge to care but a dead-end that rationalizes forgoing it.",
				context_label: 'Stakeholder',
				context: 'Low-income and uninsured populations',
				harms: [
					h(
						'Disparity',
						'Users with no financial alternative receive advice they cannot safely execute, entrenching worse outcomes than insured users.'
					),
					h(
						'False information',
						'Cost-driven substitution guidance can mirror the dangerous bad-advice patterns documented for low-resource users online.'
					)
				],
				mitigation:
					'Integrate a directory of free/sliding-scale clinics, community health centers, and patient-assistance programs, and never present a self-treatment substitute as equivalent to the recommended care.'
			},
			{
				point:
					'Adding to the false-authority concern, these users are least equipped to recognize hallucinations or to notice buried disclaimers, and may interpret the conversational fluency as proof of expertise. They are also most likely to over-share and least able to navigate privacy settings, compounding data exposure.',
				context_label: 'Stakeholder',
				context: 'People with limited digital literacy',
				harms: [
					h(
						'Transparency',
						'Users unable to interpret AI limitations cannot distinguish a statistical text engine from a vetted clinician.'
					),
					h(
						'Privacy',
						'Limited literacy means these users are least able to understand or control how their health disclosures are stored and reused.'
					)
				],
				mitigation:
					'Use plain-language, icon-supported disclaimers and a short upfront explainer (in multiple languages) of what the tool can and cannot do, with privacy defaults set to maximum protection rather than requiring opt-out.'
			},
			{
				point:
					"Beyond healthcare-access dependence, this group carries acute fear that health disclosures could reach immigration authorities, making data retention uniquely dangerous. They may avoid emergency care even when the app correctly advises it, so any under-triage is far more likely to be fatal, and language barriers may worsen the model's accuracy for them.",
				context_label: 'Stakeholder',
				context: 'Undocumented immigrants and migrant workers',
				harms: [
					h(
						'Privacy',
						'Immigration-sensitive health disclosures create risk of exposure to authorities that could lead to detention or deportation fears.'
					),
					h(
						'Disparity',
						'Fear of formal care means this group relies most heavily on the app while being least able to act on emergency referrals, compounding worse outcomes.'
					)
				],
				mitigation:
					'Offer anonymous, no-account use with no immigration-relevant data collection, guarantee no third-party or government data sharing in plain multilingual terms, and surface immigrant-friendly free clinics that do not require documentation.'
			},
			{
				point:
					"Distinct from the pediatric under-triage already noted, anxious caregivers may fall into the compulsive medical-information loop documented online, repeatedly querying a child's symptoms and acting on non-professional guidance. A confidently wrong reassurance about a child carries outsized emotional weight, and caregivers may trust the AI over their own protective instincts.",
				context_label: 'Stakeholder',
				context: 'Parents and caregivers of children with serious conditions',
				harms: [
					h(
						'False information',
						"Wrong reassurance about a child's emergency symptoms can cause a caregiver to delay life-saving pediatric care."
					),
					h(
						'Manipulation',
						"A persuasive, calming tone can override a caregiver's protective instinct to seek in-person care."
					)
				],
				mitigation:
					'Apply a lower, more conservative triage threshold for pediatric cases with hard-coded escalation for infant/child red-flag symptoms, and always advise professional pediatric review rather than definitive reassurance.'
			},
			{
				point:
					'Already covered for higher-acuity arrivals; the added stakeholder-specific angle is that safety-net EDs serving the uninsured and undocumented will absorb the concentrated downstream effect, receiving patients who present late with AI-anchored self-diagnoses that complicate triage and consume scarce resources.',
				context_label: 'Stakeholder',
				context: 'Emergency departments and hospital systems',
				harms: [
					h(
						'False information',
						'AI-anchored patient self-diagnoses can mislead intake triage and delay correct assessment.'
					),
					h(
						'Disparity',
						'The downstream burden concentrates on under-resourced hospitals serving the populations most dependent on the free app.'
					)
				],
				mitigation:
					'Provide optional clinician-facing summaries that transparently flag what the AI told the patient and its uncertainty, and partner with safety-net systems to monitor late-presentation trends.'
			},
			{
				point:
					'Beyond anchoring and liability already noted, clinicians will bear the labor of debunking AI-seeded misinformation patient by patient, straining the trust relationship — echoing how medical professionals must counter the non-professional medical misinformation that proliferates online. Time spent correcting confident wrong advice displaces actual care.',
				context_label: 'Stakeholder',
				context: 'Primary care physicians and clinicians',
				harms: [
					h(
						'False information',
						'Clinicians must repeatedly counter authoritative-sounding but wrong AI guidance patients bring to appointments.'
					),
					h(
						'Accountability',
						'Physicians may be left holding liability for correcting or overriding advice the untraceable app provided.'
					)
				],
				mitigation:
					"Publish the model's known limitations and error patterns for clinicians, and provide a clinician feedback channel to report and rapidly correct recurring dangerous advice."
			},
			{
				point:
					'Already addressed on the accountability gap; the additional insight is that without anomaly-sharing, authorities lose visibility into emerging population-level harms — the app becomes a blind spot in disease and misinformation surveillance precisely because it operates as an unregulated consumer product at scale.',
				context_label: 'Stakeholder',
				context: 'Regulatory bodies and public health authorities',
				harms: [
					h(
						'Accountability',
						'No mandated reporting means regulators cannot trace or intervene in harms accumulating across millions of private interactions.'
					),
					h(
						'Transparency',
						"The tool's consumer framing hides its clinical footprint from the public-health surveillance systems meant to catch emerging risks."
					)
				],
				mitigation:
					'Voluntarily provide aggregate, privacy-preserving anomaly and adverse-event data to public-health authorities and establish a documented incident-reporting pathway before regulation mandates it.'
			}
		]
	}
];

export async function streamBackupSession(
	speed: string,
	onReflection: (reflection: Reflection) => void,
	onTitle?: (featureTitle: string) => void
): Promise<{ sessionId: string; featureTitle: string }> {
	await sleep(jitter(400, 800));
	onTitle?.(BACKUP_TITLE);

	if (speed === 'thinking') {
		for (const reflection of BACKUP_REFLECTIONS) {
			await sleep(jitter(600, 1100));
			onReflection(reflection);
		}
	} else {
		await Promise.all(
			BACKUP_REFLECTIONS.map(async (r) => {
				await sleep(jitter(600, 1100));
				onReflection(r);
			})
		);
	}

	return { sessionId: backupSessionId(speed), featureTitle: BACKUP_TITLE };
}

const BACKUP_SOURCES: ChatSource[] = [
	{ source: 'babylon-gp-at-hand', title: 'Babylon Health GP at Hand triage safety concerns' },
	{ source: 'semigran-symptom-checkers-bmj', title: 'Symptom checker accuracy study (BMJ)' },
	{ source: 'fda-samd-guidance', title: 'FDA Software as a Medical Device guidance' }
];

function backupReply(message: string): string {
	const m = message.toLowerCase();
	if (m.includes('serious') || m.includes('risk')) {
		return [
			'1. Accountability — a wrong triage call has no licensed clinician behind it',
			'2. Disparity — atypical presentations (e.g. in women, non-native speakers) are under-recognized',
			'3. Privacy — sensitive symptom data is collected before meaningful consent',
			'4. Transparency — the urgency score is not explainable to the user or a regulator'
		].join('\n');
	}
	if (m.includes('mitigat')) {
		return "Prioritize the red-flag escalation layer first: a hard-coded symptom-cluster check that force-routes to 'seek care now' regardless of the model's own confidence. Everything else (consent flows, accuracy audits, referral partnerships) reduces harm; this one prevents the worst-case outcome.";
	}
	if (m.includes('stakeholder')) {
		return 'Uninsured and undocumented users are hit hardest: for them the app is often the only opinion they can afford or safely seek, so an inaccurate or over-cautious answer carries outsized weight compared to a user who can just book a second opinion.';
	}
	if (m.includes('safer') || m.includes('rewrite') || m.includes('redraft')) {
		return 'A safer version: "An AI app that helps users describe symptoms in plain language, then routes them to a calibrated urgency level with a clear, always-visible disclaimer that it is not a diagnosis, backed by a hard-coded red-flag layer and a direct hand-off to low-cost or telehealth care for anything above the lowest urgency tier."';
	}
	return 'Looking at this from another angle: symptom checkers have repeatedly been shown to under- and over-triage in ways that track who trained the underlying data, not just raw model accuracy. What evaluation would you run before trusting this for someone who has no other way to get a second opinion?';
}

export async function streamBackupReply(
	message: string,
	onDelta: (text: string) => void,
	onSources?: (sources: ChatSource[]) => void
): Promise<void> {
	await sleep(jitter(300, 600));
	onSources?.(BACKUP_SOURCES);
	const reply = backupReply(message);
	const words = reply.split(/(\s+)/);
	for (const w of words) {
		await sleep(jitter(12, 40));
		onDelta(w);
	}
}
