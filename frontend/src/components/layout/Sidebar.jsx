import { motion } from 'framer-motion';
import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard, BookOpen, FileText, Brain,
    BarChart3, Calendar, Sparkles, ChevronLeft, ChevronRight, Mic
} from 'lucide-react';
import useUIStore from '../../stores/uiStore';

const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/subjects', icon: BookOpen, label: 'Subjects' },
    { to: '/quizzes', icon: Brain, label: 'Quizzes' },
    { to: '/viva', icon: Mic, label: 'Viva Mode' },
    { to: '/flashcards', icon: FileText, label: 'Flashcards' },
    { to: '/study-plan', icon: Calendar, label: 'Study Plan' },
    { to: '/analytics', icon: BarChart3, label: 'Analytics' },
];

export default function Sidebar() {
    const { sidebarOpen, toggleSidebar } = useUIStore();

    return (
        <motion.aside
            animate={{ width: sidebarOpen ? 240 : 72 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="fixed left-0 top-0 h-screen z-40 flex flex-col
                 bg-dark-800/90 backdrop-blur-xl border-r border-white/[0.06]"
        >
            {/* Logo */}
            <div className="flex items-center gap-3 px-4 h-16 border-b border-white/[0.06]">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-purple to-accent-blue
                        flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-5 h-5 text-white" />
                </div>
                {sidebarOpen && (
                    <motion.span
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="font-display font-bold text-lg text-gradient-purple whitespace-nowrap"
                    >
                        Academic OS
                    </motion.span>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-3 space-y-1">
                {navItems.map(({ to, icon: Icon, label }) => (
                    <NavLink
                        key={to}
                        to={to}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium
               transition-all duration-200 group
               ${isActive
                                ? 'bg-accent-purple/15 text-accent-purple border border-accent-purple/20'
                                : 'text-gray-400 hover:text-gray-200 hover:bg-white/[0.04]'
                            }`
                        }
                    >
                        <Icon className="w-5 h-5 flex-shrink-0" />
                        {sidebarOpen && (
                            <motion.span
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.1 }}
                                className="whitespace-nowrap"
                            >
                                {label}
                            </motion.span>
                        )}
                    </NavLink>
                ))}
            </nav>

            {/* Collapse toggle */}
            <button
                onClick={toggleSidebar}
                className="m-3 p-2 rounded-xl glass-card-hover flex items-center justify-center
                   text-gray-400 hover:text-gray-200"
            >
                {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
        </motion.aside>
    );
}
