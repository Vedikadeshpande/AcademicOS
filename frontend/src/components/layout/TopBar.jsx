import { Search, Bell, Plus } from 'lucide-react';
import useUIStore from '../../stores/uiStore';

export default function TopBar({ title, subtitle }) {
    const { openCreateModal } = useUIStore();

    return (
        <header className="h-16 flex items-center justify-between px-6 border-b border-white/[0.06]
                        bg-dark-800/50 backdrop-blur-md sticky top-0 z-30">
            <div>
                <h1 className="text-lg font-display font-semibold text-gray-100">{title}</h1>
                {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
            </div>

            <div className="flex items-center gap-3">
                {/* Search */}
                <div className="relative hidden md:block">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input
                        type="text"
                        placeholder="Search subjects, topics..."
                        className="pl-9 pr-4 py-2 w-64 rounded-xl text-sm
                       bg-dark-700/60 border border-white/[0.06] text-gray-300
                       placeholder-gray-500 focus:outline-none focus:border-accent-purple/40
                       transition-all"
                    />
                </div>

                {/* Notifications */}
                <button className="p-2 rounded-xl glass-card-hover text-gray-400 hover:text-gray-200 relative">
                    <Bell className="w-5 h-5" />
                    <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-accent-pink animate-pulse-soft" />
                </button>

                {/* Add subject */}
                <button
                    onClick={openCreateModal}
                    className="btn-primary flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" />
                    <span className="hidden sm:inline">New Subject</span>
                </button>
            </div>
        </header>
    );
}
