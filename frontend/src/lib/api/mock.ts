import type {
	ChatSource,
	CreateSessionResponse,
	FeedbackRequest,
	GetSessionResponse,
	HarmRef,
	Reflection,
	SendMessageResponse,
	Speed
} from './types';

const sessions = new Map<string, GetSessionResponse>();

const MOCK_TITLE = 'AI resume ranking tool';

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const jitter = (lo: number, hi: number) => lo + Math.random() * (hi - lo);
const newId = () =>
	typeof crypto !== 'undefined' && crypto.randomUUID
		? crypto.randomUUID()
		: `s_${Math.random().toString(36).slice(2, 10)}`;

const h = (category: HarmRef['category'], explanation: string): HarmRef => ({
	category,
	explanation
});

export function buildReflections(_description: string): Reflection[] {

	return [
		{
			dimension: 'tomorrow',
			title: 'Immediate bias in ranking',
			body: 'May disadvantage candidates whose profiles differ from historical hiring patterns, embedding past inequity into day-one decisions.',
			harms: [
				h(
					'Disparity',
					'The ranker scores candidates unlike past hires lower, handing existing in-groups an unequal advantage from day one.'
				),
				h(
					'Transparency',
					'Applicants are never told an algorithm filtered them, so the basis for rejection stays hidden.'
				)
			],
			mitigation: 'Run a bias audit on the training data and disparate-impact test the rankings before launch.',
			points: [
				{
					title: 'Non-traditional resumes penalized',
					point:
						'Candidates from non-traditional backgrounds are ranked lower because their resumes diverge from historical hires.',
					context_label: 'Affects',
					context: 'career-changers, self-taught applicants',
					harms: [
						h(
							'Disparity',
							'Diverging from historical hires is penalised, so career-changers get systematically lower scores than equally-qualified traditional applicants.'
						)
					],
					mitigation: 'Strip proxy features (school, employment gaps) and re-weight on skills.'
				},
				{
					title: 'Hidden automated rejection',
					point: 'Applicants cannot tell that an algorithm — not a person — filtered them out.',
					context_label: 'Affects',
					context: 'all applicants',
					harms: [
						h(
							'Transparency',
							'Candidates have no insight that automated screening decided their rejection, so they cannot question it.'
						)
					],
					mitigation: 'Disclose automated screening in the application flow.'
				},
				{
					title: 'Keyword gaming rewarded',
					point:
						'Applicants who stuff their resumes with the right keywords outrank better-qualified candidates who write naturally.',
					context_label: 'Affects',
					context: 'honest applicants, non-native speakers',
					harms: [
						h(
							'Manipulation',
							'The ranking can be reverse-engineered, so the score reflects keyword tactics rather than actual fit.'
						)
					],
					mitigation: 'Score on semantic skill matches rather than literal keyword frequency.'
				},
				{
					title: 'Disability accommodation gaps',
					point:
						'Resumes from assistive tools or with non-standard formatting get mangled by the parser and scored as incomplete.',
					context_label: 'Affects',
					context: 'disabled applicants',
					harms: [
						h(
							'Disparity',
							'Parsing failures penalise applicants for the format of their resume rather than its content.'
						)
					],
					mitigation: 'Offer a structured submission form and test the parser against assistive-tech output.'
				},
				{
					title: 'Sensitive data over-collection',
					point:
						'The ranker ingests entire resumes including birthdates, addresses, and photos that are never needed for scoring.',
					context_label: 'Affects',
					context: 'all applicants',
					harms: [
						h('Privacy', 'Collecting and retaining unnecessary personal data widens the blast radius of any breach.')
					],
					mitigation: 'Extract only job-relevant fields and discard the raw document after parsing.'
				},
				{
					title: 'Gendered language penalty',
					point: "Phrasing more common in women's resumes correlates with lower scores because past hires skewed male.",
					context_label: 'Affects',
					context: 'women applicants',
					harms: [
						h('Disparity', 'Learned correlations turn historical gender imbalance into an active scoring penalty.')
					],
					mitigation: 'Audit feature weights for gender-correlated language and neutralise them.'
				},
				{
					title: 'No route to appeal',
					point: 'A rejected candidate has no way to contest or even understand the score that filtered them out.',
					context_label: 'Affects',
					context: 'rejected applicants',
					harms: [
						h('Accountability', 'With no appeal path, an erroneous score becomes a final decision no one answers for.')
					],
					mitigation: 'Provide a human-review request channel for any automated rejection.'
				},
				{
					title: 'Overstated confidence',
					point:
						'Recruiters treat the numeric score as objective truth and stop reviewing borderline candidates themselves.',
					context_label: 'Affects',
					context: 'borderline candidates, recruiters',
					harms: [
						h(
							'Transparency',
							'A precise-looking score hides its uncertainty, so humans defer to it more than its accuracy warrants.'
						)
					],
					mitigation: 'Show confidence ranges and require human review for the middle band.'
				},
				{
					title: 'Stale skills mismatch',
					point: "The model rewards yesterday's in-demand skills and overlooks candidates with newer, equivalent ones.",
					context_label: 'Affects',
					context: 'early-adopter candidates',
					harms: [
						h(
							'Disparity',
							'Training on past job descriptions bakes in outdated skill expectations that disadvantage current talent.'
						)
					],
					mitigation: 'Refresh the skills taxonomy regularly and map equivalent technologies.'
				},
				{
					title: 'Misleading scoring claims',
					point: "Marketing copy promises 'unbiased, merit-based' ranking the system cannot actually deliver.",
					context_label: 'Affects',
					context: 'employers, applicants',
					harms: [
						h(
							'False information',
							'Claiming the tool is unbiased misrepresents a system that demonstrably inherits historical bias.'
						)
					],
					mitigation: 'Replace absolute claims with documented limitations and audit results.'
				}
			]
		},
		{
			dimension: 'in_five_years',
			title: 'Workforce homogenization',
			body: 'Could systematically influence which groups access certain professions, narrowing the pipeline before anyone notices the drift.',
			harms: [
				h(
					'Disparity',
					'Over years the tool steers whole demographic groups away from professions, widening access gaps across the labour market.'
				),
				h(
					'Manipulation',
					'Optimising for "fit" quietly shapes the applicant pool toward a narrow profile without anyone choosing that outcome.'
				)
			],
			mitigation: 'Track demographic drift in hires year-over-year and set guardrails that trigger review.',
			points: [
				{
					title: 'Self-reinforcing selection loop',
					point:
						'A feedback loop forms as the model learns from its own past selections, amplifying a narrow profile over years.',
					context_label: 'Affects',
					context: 'future applicant pools',
					harms: [
						h(
							'Disparity',
							'Each retrain on prior selections compounds the bias, so under-represented profiles fall ever further behind.'
						)
					],
					mitigation: 'Periodically retrain on outcome data, not prior model decisions.'
				}
			]
		},
		{
			dimension: 'public_scrutiny',
			title: 'Regulatory questions',
			body: 'Regulators may question whether the algorithm reinforces hiring biases — especially in jurisdictions with audit-rights legislation.',
			harms: [
				h(
					'Accountability',
					'When a biased ranking harms a candidate it is unclear who answers for it — the vendor, the employer, or the training data.'
				),
				h(
					'Transparency',
					'The model cannot explain its rankings, so neither auditors nor applicants can see how a decision was reached.'
				)
			],
			mitigation: 'Maintain an auditable decision log and publish a model card before scrutiny arrives.',
			points: [
				{
					title: 'Unexplainable rankings flagged',
					point: 'An automated hiring tool that cannot explain its rankings would be flagged under audit-rights laws.',
					context: 'EU data protection authorities / NYC Local Law 144 — "Black-box hiring AI breaks the law"',
					harms: [
						h(
							'Accountability',
							'Audit-rights laws demand a responsible party for automated decisions, which a black-box ranker cannot supply.'
						),
						h(
							'Transparency',
							'No per-decision explanation exists to hand a regulator or rejected applicant on request.'
						)
					],
					mitigation: 'Commission an independent bias audit and retain explanations per decision.'
				}
			]
		},
		{
			dimension: 'stakeholder_impact',
			title: 'Applicants left in the dark',
			body: 'Rejected applicants have no transparency about why they were ranked lower, eroding trust and foreclosing recourse.',
			harms: [
				h(
					'Transparency',
					'Rejected applicants receive no reason for their low ranking, so they cannot tell what went wrong or appeal.'
				),
				h(
					'Privacy',
					'Scoring pulls in online-presence and resume data for purposes applicants never explicitly agreed to.'
				)
			],
			mitigation: 'Give every rejected applicant a plain-language reason and an appeal path.',
			points: [
				{
					point:
						'Applicants relying on assistive tech may be scored lower due to resume formatting the parser mishandles.',
					context_label: 'Stakeholder',
					context: 'Disabled applicants',
					harms: [
						h(
							'Disparity',
							'Parser quirks penalise assistive-tech output, so disabled applicants are scored lower for reasons unrelated to merit.'
						)
					],
					mitigation: 'Test the parser against assistive-tech output and offer an alternative submission route.'
				}
			]
		}
	];
}

export async function createSession(description: string, _speed: Speed = 'fast'): Promise<CreateSessionResponse> {
	await sleep(jitter(700, 1200));
	const sessionId = newId();
	const reflections = buildReflections(description);
	sessions.set(sessionId, {
		sessionId,
		description,
		featureTitle: MOCK_TITLE,
		reflections,
		chat: []
	});
	return { sessionId, reflections };
}

export async function createSessionStream(
	description: string,
	speed: Speed,
	onReflection: (reflection: Reflection) => void,
	onTitle?: (featureTitle: string) => void
): Promise<{ sessionId: string; featureTitle: string }> {
	const sessionId = newId();
	const reflections = buildReflections(description);

	await sleep(jitter(400, 800));
	onTitle?.(MOCK_TITLE);

	const emitConcurrently = async (rs: Reflection[]) => {
		await Promise.all(
			rs.map(async (r) => {
				await sleep(jitter(600, 1100));
				onReflection(r);
			})
		);
	};
	if (speed === 'thinking') {
		for (const reflection of reflections) {
			await sleep(jitter(600, 1100));
			onReflection(reflection);
		}
	} else {
		await emitConcurrently(reflections);
	}
	sessions.set(sessionId, {
		sessionId,
		description,
		featureTitle: MOCK_TITLE,
		reflections,
		chat: []
	});
	return { sessionId, featureTitle: MOCK_TITLE };
}

export async function sendMessage(sessionId: string, message: string): Promise<SendMessageResponse> {
	await sleep(jitter(600, 1100));
	const session = sessions.get(sessionId);
	if (session) {
		session.chat.push({ role: 'user', content: message });
	}
	const reply = mockReply(message);
	if (session) {
		session.chat.push({ role: 'assistant', content: reply });
	}
	return { reply };
}

export async function sendMessageStream(
	sessionId: string,
	message: string,
	onDelta: (text: string) => void,
	onSources?: (sources: ChatSource[]) => void
): Promise<void> {
	const session = sessions.get(sessionId);
	if (session) session.chat.push({ role: 'user', content: message });

	await sleep(jitter(300, 600));
	const sources: ChatSource[] = [
		{ source: 'amazon-resume-ai', title: 'Amazon scraps biased recruiting AI' },
		{
			source: 'nyc-ll144',
			title: 'NYC Local Law 144 (automated hiring audits)'
		}
	];
	onSources?.(sources);

	const reply = mockReply(message);
	const words = reply.split(/(\s+)/);
	let acc = '';
	for (const w of words) {
		await sleep(jitter(12, 40));
		acc += w;
		onDelta(w);
	}
	if (session) session.chat.push({ role: 'assistant', content: acc, sources });
}

export async function getSession(sessionId: string): Promise<GetSessionResponse> {
	await sleep(jitter(150, 300));
	const session = sessions.get(sessionId);
	if (!session) throw new Error(`Unknown session ${sessionId}`);
	return session;
}

export async function checkAuth(_key: string): Promise<boolean> {
	await sleep(jitter(150, 300));
	return true;
}

export async function submitFeedback(_payload: FeedbackRequest): Promise<void> {
	await sleep(jitter(400, 800));
}

function mockReply(message: string): string {
	const m = message.toLowerCase();
	if (m.includes('rank') && m.includes('harm')) {
		return [
			'1. Disparity — direct impact on who gets hired',
			"2. Transparency — applicants can't understand rankings",
			'3. Accountability — unclear responsibility',
			'4. Privacy — use of online presence data'
		].join('\n');
	}
	if (m.includes('accessib')) {
		return 'Accessibility considerations: candidates relying on assistive tech may produce resumes the model scores lower simply due to formatting quirks. Audit input parsing for assistive-tech artifacts before ranking.';
	}
	if (m.includes('healthcare') || m.includes('medical')) {
		return 'In healthcare hiring the stakes shift: licensing checks, mandatory reporting, and unionized workforces all push toward higher transparency requirements. The same model used in retail hiring may be unlawful in clinical contexts.';
	}
	if (m.includes('human review') || m.includes('review step')) {
		return "A human-in-the-loop step helps but does not erase the model's influence — anchoring effects mean reviewers tend to defer to the ranking. Consider showing reviewers the input WITHOUT the ranking first, and only revealing the score after they've scored independently.";
	}
	return 'Good question. Looking at this from another angle: the harm cases retrieved suggest similar systems failed when teams underestimated downstream effects on people who had no relationship with the deploying org. What constraint would force you to discover those people early?';
}
