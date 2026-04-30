import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, TrendingUp, BookOpen, Brain, Calendar, CheckCircle, Circle, Trash2, Clock } from 'lucide-react';
import useSubjectStore from '../stores/subjectStore';
import useUIStore from '../stores/uiStore';
import SubjectCard from '../components/subject/SubjectCard';
import GlassCard from '../components/common/GlassCard';
import AnimatedCounter from '../components/common/AnimatedCounter';
import CountdownTimer from '../components/common/CountdownTimer';
import { getAllDeadlines, toggleDeadline, deleteDeadline } from '../lib/api';

const container = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
};

export default function Dashboard() {
    const { subjects, loading, fetchSubjects, removeSubject } = useSubjectStore();
    const { openCreateModal } = useUIStore();
    const [deadlines, setDeadlines] = useState([]);

    useEffect(() => {
        fetchSubjects();
        loadDeadlines();
    }, [fetchSubjects]);

    const loadDeadlines = async () => {
        try {
            const res = await getAllDeadlines();
            setDeadlines(res.data);
        } catch (err) { /* silent */ }
    };

    const handleToggleDeadline = async (d) => {
        try {
            await toggleDeadline(d.subject_id, d.id);
            setDeadlines(prev => prev.map(dl =>
                dl.id === d.id ? { ...dl, is_completed: !dl.is_completed } : dl
            ));
        } catch (err) { console.error(err); }
    };

    const handleDeleteDeadline = async (d) => {
        try {
            await deleteDeadline(d.subject_id, d.id);
            setDeadlines(prev => prev.filter(dl => dl.id !== d.id));
        } catch (err) { console.error(err); }
    };

    // Find nearest exam
    const upcomingExam = subjects
        .filter((s) => s.exam_date)
        .sort((a, b) => new Date(a.exam_date) - new Date(b.exam_date))[0];

    // Aggregate stats
    const totalTopics = subjects.reduce((sum, s) => sum + (s.total_topics || 0), 0);
    const avgCoverage = subjects.length > 0
        ? subjects.reduce((sum, s) => sum + (s.coverage_pct || 0), 0) / subjects.length
        : 0;

    return (
        <div className="space-y-6">
            {/* Welcome + stats */}
            <div className="flex flex-col lg:flex-row gap-4">
                {/* Main hero */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex-1 glass-card p-6 relative overflow-hidden"
                >
                    <div className="relative z-10">
                        <h2 className="text-2xl font-display font-bold text-gray-100 mb-1">
                            Welcome back 👋
                        </h2>
                        <p className="text-gray-400 text-sm mb-6">
                            Here's your academic overview. Stay on top of your game.
                        </p>

                        <div className="grid grid-cols-3 gap-4">
                            <div className="space-y-1">
                                <div className="flex items-center gap-1.5 text-gray-500 text-xs">
                                    <BookOpen className="w-3.5 h-3.5" />
                                    <span>Subjects</span>
                                </div>
                                <AnimatedCounter
                                    value={subjects.length}
                                    className="text-2xl text-gray-100"
                                />
                            </div>
                            <div className="space-y-1">
                                <div className="flex items-center gap-1.5 text-gray-500 text-xs">
                                    <Brain className="w-3.5 h-3.5" />
                                    <span>Topics</span>
                                </div>
                                <AnimatedCounter
                                    value={totalTopics}
                                    className="text-2xl text-gray-100"
                                />
                            </div>
                            <div className="space-y-1">
                                <div className="flex items-center gap-1.5 text-gray-500 text-xs">
                                    <TrendingUp className="w-3.5 h-3.5" />
                                    <span>Avg Coverage</span>
                                </div>
                                <AnimatedCounter
                                    value={avgCoverage}
                                    suffix="%"
                                    className="text-2xl text-accent-green"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Background gradient decoration */}
                    <div className="absolute -top-20 -right-20 w-60 h-60 rounded-full
                          bg-accent-purple/10 blur-3xl pointer-events-none" />
                    <div className="absolute -bottom-10 -left-10 w-40 h-40 rounded-full
                          bg-accent-blue/8 blur-3xl pointer-events-none" />
                </motion.div>

                {/* Upcoming exam countdown */}
                {upcomingExam && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="glass-card p-6 flex flex-col items-center justify-center min-w-[280px]"
                    >
                        <p className="text-xs text-gray-500 mb-1 font-medium">Next Exam</p>
                        <p className="text-sm font-display font-semibold text-gray-200 mb-4">
                            {upcomingExam.name}
                        </p>
                        <CountdownTimer targetDate={upcomingExam.exam_date} />
                    </motion.div>
                )}
            </div>

            {/* Subject grid */}
            <div>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-display font-semibold text-gray-200">
                        Your Subjects
                    </h3>
                    <button
                        onClick={openCreateModal}
                        className="flex items-center gap-1.5 text-xs text-accent-purple hover:text-accent-blue
                       transition-colors font-medium"
                    >
                        <Plus className="w-3.5 h-3.5" />
                        Add Subject
                    </button>
                </div>

                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-44 skeleton rounded-2xl" />
                        ))}
                    </div>
                ) : subjects.length === 0 ? (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="glass-card p-12 text-center"
                    >
                        <BookOpen className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                        <h3 className="text-lg font-display font-semibold text-gray-300 mb-2">
                            No subjects yet
                        </h3>
                        <p className="text-sm text-gray-500 mb-5">
                            Create your first subject to start building your intelligent workspace.
                        </p>
                        <button onClick={openCreateModal} className="btn-primary">
                            <Plus className="w-4 h-4 inline mr-2" />
                            Create First Subject
                        </button>
                    </motion.div>
                ) : (
                    <motion.div
                        variants={container}
                        initial="hidden"
                        animate="visible"
                        className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
                    >
                        {subjects.map((subject) => (
                            <motion.div key={subject.id} variants={item}>
                                <SubjectCard
                                    subject={subject}
                                    onDelete={(id) => {
                                        if (confirm('Delete this subject and all its data?')) {
                                            removeSubject(id);
                                        }
                                    }}
                                />
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </div>

            {/* Upcoming Deadlines */}
            {deadlines.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-base font-display font-semibold text-gray-200 flex items-center gap-2">
                            <Clock className="w-4 h-4 text-accent-orange" />
                            Upcoming Deadlines
                        </h3>
                        <span className="text-xs text-gray-500">
                            {deadlines.filter(d => !d.is_completed).length} pending
                        </span>
                    </div>

                    <div className="space-y-2">
                        {deadlines.slice(0, 8).map((d) => {
                            const dueDate = new Date(d.due_date);
                            const now = new Date();
                            const daysLeft = Math.ceil((dueDate - now) / (1000 * 60 * 60 * 24));
                            const urgency = d.is_completed ? 'border-white/[0.04]' :
                                daysLeft <= 3 ? 'border-red-500/30' :
                                    daysLeft <= 7 ? 'border-yellow-500/20' : 'border-white/[0.08]';
                            const urgencyText = d.is_completed ? 'text-gray-600' :
                                daysLeft <= 3 ? 'text-red-400' :
                                    daysLeft <= 7 ? 'text-yellow-400' : 'text-gray-400';

                            return (
                                <motion.div
                                    key={d.id}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className={`flex items-center gap-3 px-4 py-3 rounded-xl glass-card border ${urgency}
                                        ${d.is_completed ? 'opacity-50' : ''} transition-all duration-200 group`}
                                >
                                    <button
                                        onClick={() => handleToggleDeadline(d)}
                                        className="flex-shrink-0 transition-all hover:scale-110"
                                    >
                                        {d.is_completed ? (
                                            <CheckCircle className="w-4 h-4 text-accent-green" />
                                        ) : (
                                            <Circle className="w-4 h-4 text-gray-500 hover:text-gray-300" />
                                        )}
                                    </button>

                                    <div className="w-2 h-6 rounded-full flex-shrink-0"
                                        style={{ backgroundColor: d.subject_color }} />

                                    <div className="flex-1 min-w-0">
                                        <p className={`text-sm font-medium ${d.is_completed ? 'line-through text-gray-500' : 'text-gray-200'}`}>
                                            {d.title}
                                        </p>
                                        <p className="text-[11px] text-gray-500">{d.subject_name} · {d.deadline_type}</p>
                                    </div>

                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        <span className={`text-xs font-medium ${urgencyText}`}>
                                            {d.is_completed ? 'Done' :
                                                daysLeft <= 0 ? 'Overdue' :
                                                    daysLeft === 1 ? 'Tomorrow' :
                                                        `${daysLeft}d left`}
                                        </span>
                                        <button
                                            onClick={() => handleDeleteDeadline(d)}
                                            className="p-1 rounded-lg text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </div>
                </motion.div>
            )}
        </div>
    );
}
