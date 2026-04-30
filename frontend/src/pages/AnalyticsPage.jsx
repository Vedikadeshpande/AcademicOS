import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, BookOpen, Brain, TrendingUp, AlertTriangle } from 'lucide-react';
import GlassCard from '../components/common/GlassCard';
import ProgressRing from '../components/analytics/ProgressRing';
import RiskBadge from '../components/analytics/RiskBadge';
import CountdownTimer from '../components/common/CountdownTimer';
import useSubjectStore from '../stores/subjectStore';
import { getAnalytics } from '../lib/api';

const container = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const item = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
};

export default function AnalyticsPage() {
    const { subjects, fetchSubjects } = useSubjectStore();
    const [selectedSubject, setSelectedSubject] = useState(null);
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchSubjects();
    }, []);

    useEffect(() => {
        if (subjects.length > 0 && !selectedSubject) {
            setSelectedSubject(subjects[0]);
        }
    }, [subjects]);

    useEffect(() => {
        if (selectedSubject) {
            loadAnalytics(selectedSubject.id);
        }
    }, [selectedSubject]);

    const loadAnalytics = async (subjectId) => {
        setLoading(true);
        try {
            const res = await getAnalytics(subjectId);
            setAnalytics(res.data);
        } catch (err) {
            console.error('Failed to load analytics:', err);
        } finally {
            setLoading(false);
        }
    };

    if (subjects.length === 0) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-center min-h-[60vh]"
            >
                <GlassCard className="max-w-md text-center !p-10">
                    <span className="text-5xl mb-4 block">📊</span>
                    <h2 className="text-xl font-display font-bold text-gradient-purple mb-2">
                        Analytics Dashboard
                    </h2>
                    <p className="text-sm text-gray-400">Create a subject and take quizzes to see your analytics.</p>
                </GlassCard>
            </motion.div>
        );
    }

    // Weak topics (accuracy < 60%)
    const weakTopics = analytics?.topic_breakdown?.filter(t => t.quiz_accuracy > 0 && t.quiz_accuracy < 60) || [];
    // All topics sorted by accuracy
    const sortedTopics = [...(analytics?.topic_breakdown || [])].sort((a, b) => b.quiz_accuracy - a.quiz_accuracy);

    return (
        <div className="space-y-6">
            {/* Subject selector */}
            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
                {subjects.map(s => (
                    <button
                        key={s.id}
                        onClick={() => setSelectedSubject(s)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap
                            transition-all duration-200 flex-shrink-0
                            ${selectedSubject?.id === s.id
                                ? 'bg-accent-purple/15 text-accent-purple border border-accent-purple/30'
                                : 'glass-card text-gray-400 hover:text-gray-200 hover:bg-white/[0.06]'}`}
                    >
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                        {s.name}
                    </button>
                ))}
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[1, 2, 3].map(i => <div key={i} className="h-48 skeleton rounded-2xl" />)}
                </div>
            ) : analytics && (
                <motion.div variants={container} initial="hidden" animate="visible" className="space-y-4">
                    {/* Row 1: Progress Rings */}
                    <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <GlassCard className="!p-6 flex flex-col items-center">
                            <ProgressRing value={analytics.coverage_pct} color="#5cffb1" label="Coverage" />
                            <p className="text-xs text-gray-500 mt-3">Syllabus covered</p>
                        </GlassCard>
                        <GlassCard className="!p-6 flex flex-col items-center">
                            <ProgressRing value={analytics.avg_quiz_accuracy} color="#5c9cff" label="Quiz Accuracy" />
                            <p className="text-xs text-gray-500 mt-3">Average across quizzes</p>
                        </GlassCard>
                        <GlassCard className="!p-6 flex flex-col items-center">
                            <ProgressRing value={analytics.readiness_pct} color="#7c5cff" label="Readiness" />
                            <p className="text-xs text-gray-500 mt-3">Exam readiness score</p>
                        </GlassCard>
                    </motion.div>

                    {/* Row 2: Risk + Countdown + Stats */}
                    <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <GlassCard className="!p-5">
                            <h3 className="text-xs font-display font-semibold text-gray-400 mb-3">Exam Risk</h3>
                            <RiskBadge level={analytics.risk_level} />
                        </GlassCard>

                        <GlassCard className="!p-5 flex flex-col items-center justify-center">
                            <h3 className="text-xs font-display font-semibold text-gray-400 mb-3">Exam Countdown</h3>
                            {selectedSubject?.exam_date ? (
                                <CountdownTimer targetDate={selectedSubject.exam_date} compact />
                            ) : (
                                <p className="text-xs text-gray-500">No exam date set</p>
                            )}
                        </GlassCard>

                        <GlassCard className="!p-5">
                            <h3 className="text-xs font-display font-semibold text-gray-400 mb-3">Quick Stats</h3>
                            <div className="space-y-2">
                                {[
                                    { label: 'Quizzes Taken', value: analytics.total_quizzes_taken, icon: Brain, color: '#ff9f5c' },
                                    { label: 'Flashcard Mastery', value: `${analytics.flashcard_mastery_pct.toFixed(0)}%`, icon: BookOpen, color: '#5cdcff' },
                                    { label: 'Days Left', value: analytics.days_until_exam ?? '—', icon: TrendingUp, color: '#5cffb1' },
                                ].map(({ label, value, icon: Icon, color }) => (
                                    <div key={label} className="flex items-center gap-2">
                                        <Icon className="w-3.5 h-3.5" style={{ color }} />
                                        <span className="text-xs text-gray-400 flex-1">{label}</span>
                                        <span className="text-sm font-display font-semibold text-gray-200">{value}</span>
                                    </div>
                                ))}
                            </div>
                        </GlassCard>
                    </motion.div>

                    {/* Row 3: Topic Accuracy Chart */}
                    {sortedTopics.length > 0 && (
                        <motion.div variants={item}>
                            <GlassCard className="!p-5">
                                <h3 className="text-sm font-display font-semibold text-gray-300 mb-4 flex items-center gap-2">
                                    <BarChart3 className="w-4 h-4 text-accent-blue" />
                                    Topic Accuracy
                                </h3>
                                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                                    {sortedTopics.map((topic, i) => {
                                        const accuracy = topic.quiz_accuracy;
                                        const barColor = accuracy >= 80 ? '#5cffb1' :
                                            accuracy >= 60 ? '#5c9cff' :
                                                accuracy >= 40 ? '#ff9f5c' : '#ff5ca0';
                                        return (
                                            <div key={topic.topic_id} className="flex items-center gap-3">
                                                <span className="text-xs text-gray-400 w-32 truncate flex-shrink-0" title={topic.topic_title}>
                                                    {topic.topic_title}
                                                </span>
                                                <div className="flex-1 h-2 bg-dark-600 rounded-full overflow-hidden">
                                                    <motion.div
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${accuracy}%` }}
                                                        transition={{ duration: 0.8, delay: i * 0.05, ease: 'easeOut' }}
                                                        className="h-full rounded-full"
                                                        style={{ backgroundColor: barColor }}
                                                    />
                                                </div>
                                                <span className="text-xs font-mono w-10 text-right" style={{ color: barColor }}>
                                                    {accuracy.toFixed(0)}%
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            </GlassCard>
                        </motion.div>
                    )}

                    {/* Row 4: Weak Topics */}
                    {weakTopics.length > 0 && (
                        <motion.div variants={item}>
                            <GlassCard className="!p-5">
                                <h3 className="text-sm font-display font-semibold text-gray-300 mb-3 flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 text-red-400" />
                                    Weak Topics
                                </h3>
                                <p className="text-xs text-gray-500 mb-3">Topics with quiz accuracy below 60%. Focus on these!</p>
                                <div className="flex flex-wrap gap-2">
                                    {weakTopics.map(t => (
                                        <span key={t.topic_id}
                                            className="px-3 py-1.5 rounded-xl text-xs font-medium
                                                bg-red-500/10 border border-red-500/20 text-red-400">
                                            {t.topic_title}
                                            <span className="ml-1.5 text-red-500/60">{t.quiz_accuracy.toFixed(0)}%</span>
                                        </span>
                                    ))}
                                </div>
                            </GlassCard>
                        </motion.div>
                    )}
                </motion.div>
            )}
        </div>
    );
}
