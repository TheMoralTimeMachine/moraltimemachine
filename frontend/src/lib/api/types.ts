export const DIMENSIONS = ['tomorrow', 'in_five_years', 'public_scrutiny', 'stakeholder_impact'] as const;
export type Dimension = (typeof DIMENSIONS)[number];

export const SPEEDS = ['thinking', 'fast'] as const;
export type Speed = (typeof SPEEDS)[number];

export type GenerationMode = Speed | 'compare';

export const HARM_CATEGORIES = [
	'Accountability',
	'Censorship',
	'Disparity',
	'Disruptive activity',
	'False information',
	'Fraudulent activity',
	'Inappropriate content',
	'Manipulation',
	'Privacy',
	'Transparency'
] as const;
export type HarmCategory = (typeof HARM_CATEGORIES)[number];

export interface HarmRef {
	category: HarmCategory;
	explanation: string;
}

export interface ReflectionPoint {
	point: string;
	title?: string;
	context_label?: string;
	context?: string;
	context_detail?: string;
	harms: HarmRef[];
	mitigation: string;
}

export interface Reflection {
	dimension: Dimension;
	title: string;
	body: string;
	harms: HarmRef[];
	mitigation: string;
	points: ReflectionPoint[];
}

export interface ChatSource {
	source: string;
	title: string;
}

export interface ChatMessage {
	role: 'user' | 'assistant';
	content: string;

	sources?: ChatSource[];
}

export interface CreateSessionRequest {
	description: string;
	speed?: Speed;

	prolificPid?: string;
}

export interface CreateSessionResponse {
	sessionId: string;
	reflections: Reflection[];
}

export interface SendMessageRequest {
	message: string;
}

export interface SendMessageResponse {
	reply: string;

	structured?: unknown;
}

export interface GetSessionResponse {
	sessionId: string;
	description: string;
	featureTitle: string;
	reflections: Reflection[];
	chat: ChatMessage[];
}

export interface FeedbackRequest {
	sessionIds: { fast?: string; thinking?: string };
	mode: GenerationMode;
	likert: Record<string, number | null>;
	open: Record<string, string>;
	demographics: Record<string, string>;
	questions: Record<string, string>;
}

export const DIMENSION_META: Record<Dimension, { label: string; icon: string; accent: string }> = {
	tomorrow: { label: 'Tomorrow', icon: '⚡', accent: 'tomorrow' },
	in_five_years: {
		label: 'In Five Years',
		icon: '🔮',
		accent: 'in-five-years'
	},
	public_scrutiny: {
		label: 'Public Scrutiny',
		icon: '🔍',
		accent: 'public-scrutiny'
	},
	stakeholder_impact: {
		label: 'Stakeholders',
		icon: '👥',
		accent: 'stakeholder-impact'
	}
};

export const HARM_META: Record<HarmCategory, { label: string; description: string }> = {
	Accountability: {
		label: 'Accountability',
		description: 'The user experienced an issue with the software and could not find the company responsible.'
	},
	Censorship: {
		label: 'Censorship',
		description:
			'The user claims the software hides certain information, or their content or profiles are removed or demoted.'
	},
	Disparity: {
		label: 'Disparity',
		description:
			'The user claims the software creates unequal distribution of power, access, treatment, or outcomes between users.'
	},
	'Disruptive activity': {
		label: 'Disruptive activity',
		description:
			'The user describes persisting, unwanted digital activity that sabotages the normal functioning of software.'
	},
	'False information': {
		label: 'False information',
		description: 'The user claims that false information is being spread by or through the software.'
	},
	'Fraudulent activity': {
		label: 'Fraudulent activity',
		description:
			'The user describes fraudulent activities by software or its users, e.g., content theft, identity theft or scamming.'
	},
	'Inappropriate content': {
		label: 'Inappropriate content',
		description: 'The user describes seeing content in a software that is disturbing to them or other groups of people.'
	},
	Manipulation: {
		label: 'Manipulation',
		description:
			'The user claims that the software controls, or plays upon users by artful, unfair, or insidious means to someone’s advantage.'
	},
	Privacy: {
		label: 'Privacy',
		description:
			'The user claims that the software does not keep their data secure, or uses it for purposes other than what they agree to.'
	},
	Transparency: {
		label: 'Transparency',
		description: 'The user describes how motives, risks or implications are unclear when using the software.'
	}
};
