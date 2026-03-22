import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL,
});

export const getClients = () => api.get('/clients');
export const getProperties = () => api.get('/properties');
export const checkAnniversaries = () => api.get('/check-anniversaries');
export const getMorningBriefing = () => api.get('/assistant/morning-briefing');
export const sendAgentReply = (content: string) => api.post('/assistant/reply', { agent_id: 'karen', content });
export const rewriteContent = (content: string, tone: string = 'professional') => api.post('/assistant/rewrite', { content, tone });

// New Functionalities
export const createLead = (data: any) => api.post('/leads', data);
export const bulkImport = (data: any[]) => api.post('/bulk-import', data);
export const bookAppraisal = (data: any) => api.post('/appraisals/book', data);
export const getLeads = () => api.get('/leads');
export const getInteractions = () => api.get('/interactions');

export default api;
