export const LIKERT_SCALE = [
	{ value: 1, label: 'Strongly disagree' },
	{ value: 2, label: 'Disagree' },
	{ value: 3, label: 'Neutral' },
	{ value: 4, label: 'Agree' },
	{ value: 5, label: 'Strongly agree' }
] as const;

export type LikertQuestion = { id: string; text: string; allowNa?: boolean };

export const LIKERT_QUESTIONS: readonly LikertQuestion[] = [
	{
		id: 'likert_1',
		text: 'The reflections were relevant to the feature I described.'
	},
	{
		id: 'likert_2',
		text: 'The reflections were specific, not generic warnings that could apply to any software.'
	},
	{
		id: 'likert_3',
		text: 'The reflections helped me see consequences I had not previously considered.'
	},
	{
		id: 'likert_4',
		text: 'The mitigation strategies were actionable and realistic for a development team.'
	},
	{
		id: 'likert_5',
		text: 'The harm categories (e.g., Disparity, Privacy, Manipulation) made sense for the identified harms.'
	},
	{
		id: 'likert_6',
		text: 'The reflections felt trustworthy and well-grounded, not speculative or exaggerated.'
	},
	{
		id: 'likert_8',
		text: 'The Explore Deeper chat helped me understand or pressure-test the risks. (Mark “did not use” if you didn’t try it.)',
		allowNa: true
	},
	{
		id: 'likert_7',
		text: 'I would use this tool during my development process.'
	}
];

export type OpenQuestion = { id: string; label: string; optional?: boolean };

export const OPEN_QUESTIONS: readonly OpenQuestion[] = [
	{
		id: 'open_1',
		label: "Did the reflections raise anything you hadn't considered before? If so, what?"
	},
	{
		id: 'open_2',
		label: 'Was anything missing, irrelevant, or wrong?'
	},
	{
		id: 'open_3',
		label: 'Would you use this in your workflow? Why or why not?'
	},
	{
		id: 'open_5',
		label: 'Briefly describe a recent software project you have worked on. (verification check)'
	},
	{
		id: 'open_4',
		label: 'Is there anything else you would like to share about your experience using the tool? (Optional)',
		optional: true
	}
];

export type DemographicQuestion = {
	id: string;
	question: string;
	options: readonly string[];

	other?: { label: string; placeholder?: string };

	optional?: boolean;
};

export const DEMOGRAPHIC_QUESTIONS: readonly DemographicQuestion[] = [
	{
		id: 'role',
		question: 'What is your current role?',
		options: [
			'Software developer / engineer',
			'Senior / lead developer',
			"Bachelor's student (CS or related)",
			"Master's student (CS or related)",
			'PhD student / researcher (CS or related)'
		],
		other: { label: 'Other', placeholder: 'Your role' }
	},
	{
		id: 'experience',
		question: 'How many years of programming / software development experience do you have?',
		options: ['Less than 1 year', '1–2 years', '3–4 years', '5–10 years', 'More than 10 years']
	},
	{
		id: 'ethics_familiarity',
		question: 'How familiar were you with software ethics before this session?',
		options: ['Not familiar', 'Somewhat familiar', 'Very familiar']
	},
	{
		id: 'age',
		question: 'What is your age?',
		options: ['Under 18', '18–24', '25–34', '35–44', '45–54', '55–64', '65 or older']
	},
	{
		id: 'gender',
		question: 'What is your gender?',
		options: ['Woman', 'Man', 'Non-binary'],
		other: { label: 'Prefer to self-describe', placeholder: 'Your gender' },
		optional: true
	}
];
