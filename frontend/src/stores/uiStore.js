import { create } from 'zustand';

const useUIStore = create((set) => ({
    sidebarOpen: true,
    createModalOpen: false,
    uploadModalOpen: false,

    toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
    openCreateModal: () => set({ createModalOpen: true }),
    closeCreateModal: () => set({ createModalOpen: false }),
    openUploadModal: () => set({ uploadModalOpen: true }),
    closeUploadModal: () => set({ uploadModalOpen: false }),
}));

export default useUIStore;
