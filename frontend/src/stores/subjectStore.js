import { create } from 'zustand';
import { getSubjects, createSubject, updateSubject, deleteSubject, getSubject } from '../lib/api';

const useSubjectStore = create((set, get) => ({
    subjects: [],
    activeSubject: null,
    loading: false,
    error: null,

    fetchSubjects: async () => {
        set({ loading: true, error: null });
        try {
            const res = await getSubjects();
            set({ subjects: res.data, loading: false });
        } catch (err) {
            set({ error: err.message, loading: false });
        }
    },

    fetchSubject: async (id) => {
        set({ loading: true, error: null });
        try {
            const res = await getSubject(id);
            set({ activeSubject: res.data, loading: false });
        } catch (err) {
            set({ error: err.message, loading: false });
        }
    },

    addSubject: async (data) => {
        try {
            const res = await createSubject(data);
            // Instead of adding locally, refresh the list to ensure consistency
            await get().fetchSubjects();
            return res.data;
        } catch (err) {
            set({ error: err.message });
            throw err;
        }
    },

    editSubject: async (id, data) => {
        try {
            const res = await updateSubject(id, data);
            set((state) => ({
                subjects: state.subjects.map((s) => (s.id === id ? res.data : s)),
                activeSubject: state.activeSubject?.id === id ? res.data : state.activeSubject,
            }));
            return res.data;
        } catch (err) {
            set({ error: err.message });
            throw err;
        }
    },

    removeSubject: async (id) => {
        try {
            await deleteSubject(id);
            set((state) => ({
                subjects: state.subjects.filter((s) => s.id !== id),
                activeSubject: state.activeSubject?.id === id ? null : state.activeSubject,
            }));
        } catch (err) {
            set({ error: err.message });
            throw err;
        }
    },

    setActiveSubject: (subject) => set({ activeSubject: subject }),
    clearError: () => set({ error: null }),
}));

export default useSubjectStore;
