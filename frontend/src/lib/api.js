import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// ── Subjects ──
export const getSubjects = () => api.get('/subjects/');
export const getSubject = (id) => api.get(`/subjects/${id}`);
export const createSubject = (data) => api.post('/subjects/', data);
export const updateSubject = (id, data) => api.patch(`/subjects/${id}`, data);
export const deleteSubject = (id) => api.delete(`/subjects/${id}`);

// ── Marking Schemes ──
export const getMarkingSchemes = (subjectId) => api.get(`/subjects/${subjectId}/marking-schemes`);
export const createMarkingScheme = (subjectId, data) => api.post(`/subjects/${subjectId}/marking-schemes`, data);
export const deleteMarkingScheme = (subjectId, schemeId) => api.delete(`/subjects/${subjectId}/marking-schemes/${schemeId}`);

// ── Deadlines ──
export const getDeadlines = (subjectId) => api.get(`/subjects/${subjectId}/deadlines`);
export const createDeadline = (subjectId, data) => api.post(`/subjects/${subjectId}/deadlines`, data);

// ── Uploads ──
export const uploadFile = (subjectId, fileType, file) => {
    const formData = new FormData();
    formData.append('subject_id', subjectId);
    formData.append('file_type', fileType);
    formData.append('file', file);
    return api.post('/uploads/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};
export const getUploads = (subjectId) => api.get(`/uploads/${subjectId}`);
export const getUploadStatus = (uploadId) => api.get(`/uploads/status/${uploadId}`);
export const deleteUpload = (uploadId) => api.delete(`/uploads/${uploadId}`);

// ── Syllabus ──
export const getSyllabusUnits = (subjectId) => api.get(`/syllabus/${subjectId}/units`);
export const createUnit = (subjectId, data) => api.post(`/syllabus/${subjectId}/units`, data);
export const createTopic = (subjectId, unitId, data) => api.post(`/syllabus/${subjectId}/units/${unitId}/topics`, data);
export const parseSyllabus = (subjectId, data) => api.post(`/syllabus/${subjectId}/parse`, data);
export const getCoverage = (subjectId) => api.get(`/syllabus/${subjectId}/coverage`);

// ── Analytics ──
export const getAnalytics = (subjectId) => api.get(`/analytics/${subjectId}`);

// ── Quizzes ──
export const generateQuiz = (data) => api.post('/quizzes/generate', data);
export const generateMockPaper = (subjectId) => api.post(`/quizzes/mock-paper?subject_id=${subjectId}`);
export const generateExamPaper = (data) => api.post('/quizzes/generate-exam-paper', data);
export const submitQuiz = (sessionId, data) => api.post(`/quizzes/submit/${sessionId}`, data);
export const getQuizHistory = (subjectId) => api.get(`/quizzes/history/${subjectId}`);

// ── Flashcards ──
export const generateFlashcards = (data) => api.post('/flashcards/generate', data);
export const reviewFlashcard = (data) => api.post('/flashcards/review', data);
export const getDueFlashcards = (subjectId, limit = 20) => api.get(`/flashcards/due/${subjectId}?limit=${limit}`);
export const getAllFlashcards = (subjectId) => api.get(`/flashcards/${subjectId}`);
export const deleteFlashcard = (cardId) => api.delete(`/flashcards/card/${cardId}`);
export const clearFlashcards = (subjectId) => api.delete(`/flashcards/clear/${subjectId}`);

// ── PYQ ──
export const analyzePYQ = (subjectId) => api.post(`/pyq/analyze/${subjectId}`);

// ── Study Plan ──
export const generateStudyPlan = (data) => api.post('/study-plan/generate', data);
export const getStudyPlan = () => api.get('/study-plan/');
export const toggleStudyTask = (planId, topicId) => api.patch(`/study-plan/${planId}/tasks/${topicId}/toggle`);

// ── Syllabus Coverage ──
export const toggleTopicCovered = (topicId) => api.patch(`/syllabus/topics/${topicId}/toggle-covered`);
export const recalculateCoverage = (subjectId) => api.post(`/syllabus/${subjectId}/recalculate-coverage`);

// ── Deadlines (Enhanced) ──
export const getAllDeadlines = () => api.get('/subjects/deadlines/all');
export const toggleDeadline = (subjectId, deadlineId) => api.patch(`/subjects/${subjectId}/deadlines/${deadlineId}/toggle`);
export const deleteDeadline = (subjectId, deadlineId) => api.delete(`/subjects/${subjectId}/deadlines/${deadlineId}`);

export default api;

