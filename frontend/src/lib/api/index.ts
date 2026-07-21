import * as mock from './mock';
import * as client from './client';

const useReal = Boolean(import.meta.env.VITE_API_BASE_URL);

export const api = useReal ? client : mock;
export type Api = typeof api;

export { DuplicateFeedbackError, OffTopicError, UnauthorizedError } from './client';
export * from './types';
