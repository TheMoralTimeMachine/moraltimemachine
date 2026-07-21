import { marked } from 'marked';
import DOMPurify from 'isomorphic-dompurify';

marked.setOptions({
	gfm: true,

	breaks: true
});

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
	if (node.tagName === 'A') {
		node.setAttribute('target', '_blank');
		node.setAttribute('rel', 'noopener noreferrer');
	}
});

const ALLOWED_TAGS = [
	'p',
	'br',
	'strong',
	'em',
	'del',
	'code',
	'pre',
	'ul',
	'ol',
	'li',
	'blockquote',
	'h1',
	'h2',
	'h3',
	'h4',
	'h5',
	'h6',
	'a',
	'hr',
	'table',
	'thead',
	'tbody',
	'tr',
	'th',
	'td'
];

export function renderMarkdown(src: string): string {
	const html = marked.parse(src ?? '', { async: false }) as string;
	return DOMPurify.sanitize(html, {
		ALLOWED_TAGS,
		ALLOWED_ATTR: ['href', 'target', 'rel']
	});
}
