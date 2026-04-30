import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Calendar, Clock, ChevronLeft, ChevronRight, CheckCircle, Circle,
    Sparkles, BookOpen, Timer, BarChart3, Zap
} from 'lucide-react';
import GlassCard from '../components/common/GlassCard';
import useSubjectStore from '../stores/subjectStore';
import { generateStudyPlan, getStudyPlan, toggleStudyTask } from '../lib/api';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

function formatDate(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export default function StudyPlanPage() {
    const { subjects, fetchSubjects } = useSubjectStore();
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [dailyHours, setDailyHours] = useState(3);
    const [selectedDate, setSelectedDate] = useState(formatDate(new Date()));
    const [calMonth, setCalMonth] = useState(new Date().getMonth());
    const [calYear, setCalYear] = useState(new Date().getFullYear());
    const [viewMode, setViewMode] = useState('day'); // 'day' or 'week'

    useEffect(() => {
        fetchSubjects();
        loadPlan();
    }, []);

    const loadPlan = async () => {
        setLoading(true);
        try {
            const res = await getStudyPlan();
            setPlan(res.data);
        } catch (err) {
            console.error('Failed to load plan:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            const subjectIds = subjects.filter(s => s.exam_date).map(s => s.id);
            const res = await generateStudyPlan({
                daily_hours: dailyHours,
                subject_ids: subjectIds,
            });
            setPlan(res.data);
        } catch (err) {
            console.error('Generate failed:', err);
        } finally {
            setGenerating(false);
        }
    };

    const handleToggleTask = async (planId, topicId) => {
        try {
            const res = await toggleStudyTask(planId, topicId);
            // Update local state
            setPlan(prev => ({
                ...prev,
                days: prev.days.map(d =>
                    d.plan_id === planId
                        ? { ...d, tasks: res.data.tasks, completion_pct: res.data.completion_pct }
                        : d
                ),
            }));
        } catch (err) {
            console.error('Toggle failed:', err);
        }
    };

    // Calendar data
    const planDaysMap = useMemo(() => {
        if (!plan?.days) return {};
        const map = {};
        plan.days.forEach(d => { map[d.plan_date] = d; });
        return map;
    }, [plan]);

    // Calendar grid
    const calendarDays = useMemo(() => {
        const firstDay = new Date(calYear, calMonth, 1).getDay();
        const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
        const days = [];

        for (let i = 0; i < firstDay; i++) days.push(null);
        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            days.push({ day: d, date: dateStr, plan: planDaysMap[dateStr] });
        }
        return days;
    }, [calMonth, calYear, planDaysMap]);

    // Get tasks for selected day/week
    const visibleTasks = useMemo(() => {
        if (!plan?.days) return [];
        if (viewMode === 'day') {
            const dayPlan = planDaysMap[selectedDate];
            return dayPlan ? [dayPlan] : [];
        } else {
            // Week view: get 7 days starting from selected date's Monday
            const d = new Date(selectedDate);
            const dayOfWeek = d.getDay();
            const monday = new Date(d);
            monday.setDate(d.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));

            const weekDays = [];
            for (let i = 0; i < 7; i++) {
                const wd = new Date(monday);
                wd.setDate(monday.getDate() + i);
                const dateStr = formatDate(wd);
                if (planDaysMap[dateStr]) weekDays.push(planDaysMap[dateStr]);
            }
            return weekDays;
        }
    }, [plan, selectedDate, viewMode, planDaysMap]);

    // Overall completion
    const overallCompletion = useMemo(() => {
        if (!plan?.days?.length) return 0;
        const total = plan.days.reduce((s, d) => s + d.tasks.length, 0);
        const done = plan.days.reduce((s, d) => s + d.tasks.filter(t => t.is_completed).length, 0);
        return total > 0 ? Math.round((done / total) * 100) : 0;
    }, [plan]);

    // Subject color lookup from tasks
    const subjectColors = useMemo(() => {
        if (!plan?.days) return {};
        const colors = {};
        plan.days.forEach(d => d.tasks.forEach(t => {
            colors[t.subject_id] = { name: t.subject_name, color: t.subject_color };
        }));
        return colors;
    }, [plan]);

    const today = formatDate(new Date());

    return (
        <div className="space-y-6">
            {/* Controls */}
            <div className="flex flex-col lg:flex-row gap-4">
                <GlassCard className="flex-1 !p-5">
                    <h3 className="text-sm font-display font-semibold text-gray-300 mb-4 flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-accent-purple" />
                        Generate Study Plan
                    </h3>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-xs font-medium text-gray-400 mb-2">
                                Daily Study Hours: <span className="text-accent-purple font-bold text-sm">{dailyHours}h</span>
                            </label>
                            <input
                                type="range" min="1" max="12" step="0.5"
                                value={dailyHours}
                                onChange={(e) => setDailyHours(parseFloat(e.target.value))}
                                className="w-full h-1.5 bg-dark-600 rounded-full appearance-none cursor-pointer
                                         [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4
                                         [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full
                                         [&::-webkit-slider-thumb]:bg-accent-purple [&::-webkit-slider-thumb]:shadow-glow-purple"
                            />
                            <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                                <span>1h</span><span>6h</span><span>12h</span>
                            </div>
                        </div>

                        {/* Subject credit summary */}
                        {subjects.filter(s => s.exam_date).length > 0 && (
                            <div className="space-y-1.5">
                                <span className="text-xs text-gray-500">Subjects with exams:</span>
                                {subjects.filter(s => s.exam_date).map(s => (
                                    <div key={s.id} className="flex items-center gap-2">
                                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                                        <span className="text-xs text-gray-300 flex-1">{s.name}</span>
                                        <span className="text-[10px] text-gray-500 font-mono">{s.credits} cr</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        <button
                            onClick={handleGenerate}
                            disabled={generating || subjects.filter(s => s.exam_date).length === 0}
                            className="btn-primary w-full flex items-center justify-center gap-2"
                        >
                            {generating ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                                <Zap className="w-4 h-4" />
                            )}
                            {generating ? 'Generating...' : 'Generate Plan'}
                        </button>

                        {subjects.filter(s => s.exam_date).length === 0 && (
                            <p className="text-xs text-gray-600 text-center">
                                Add exam dates to your subjects first.
                            </p>
                        )}
                    </div>
                </GlassCard>

                {/* Overall progress */}
                {plan?.days?.length > 0 && (
                    <GlassCard className="lg:w-72 !p-5">
                        <h3 className="text-sm font-display font-semibold text-gray-300 mb-4 flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-accent-green" />
                            Plan Progress
                        </h3>
                        <div className="flex flex-col items-center gap-3">
                            <div className="relative w-24 h-24">
                                <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
                                    <circle cx="50" cy="50" r="42" fill="none"
                                        stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
                                    <motion.circle
                                        cx="50" cy="50" r="42" fill="none"
                                        stroke="#5cffb1" strokeWidth="8" strokeLinecap="round"
                                        initial={{ strokeDashoffset: 264 }}
                                        animate={{ strokeDashoffset: 264 - (264 * overallCompletion / 100) }}
                                        strokeDasharray="264"
                                        transition={{ duration: 1, ease: 'easeOut' }}
                                    />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <span className="text-xl font-display font-bold text-gray-100">
                                        {overallCompletion}%
                                    </span>
                                </div>
                            </div>
                            <span className="text-xs text-gray-500">
                                {plan.total_days} days · {dailyHours || plan.daily_hours}h/day
                            </span>
                        </div>

                        {/* Subject legend */}
                        <div className="mt-4 space-y-1">
                            {Object.values(subjectColors).map(({ name, color }) => (
                                <div key={name} className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                                    <span className="text-[11px] text-gray-400">{name}</span>
                                </div>
                            ))}
                        </div>
                    </GlassCard>
                )}
            </div>

            {/* Calendar + Task list */}
            {plan?.days?.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Calendar */}
                    <GlassCard className="lg:col-span-1 !p-4">
                        <div className="flex items-center justify-between mb-4">
                            <button onClick={() => {
                                if (calMonth === 0) { setCalMonth(11); setCalYear(y => y - 1); }
                                else setCalMonth(m => m - 1);
                            }} className="p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-white/[0.06]">
                                <ChevronLeft className="w-4 h-4" />
                            </button>
                            <span className="text-sm font-display font-semibold text-gray-200">
                                {MONTHS[calMonth]} {calYear}
                            </span>
                            <button onClick={() => {
                                if (calMonth === 11) { setCalMonth(0); setCalYear(y => y + 1); }
                                else setCalMonth(m => m + 1);
                            }} className="p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-white/[0.06]">
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Day headers */}
                        <div className="grid grid-cols-7 gap-1 mb-1">
                            {DAYS.map(d => (
                                <div key={d} className="text-center text-[10px] text-gray-500 font-medium py-1">{d}</div>
                            ))}
                        </div>

                        {/* Day cells */}
                        <div className="grid grid-cols-7 gap-1">
                            {calendarDays.map((cell, i) => {
                                if (!cell) return <div key={`empty-${i}`} />;
                                const isSelected = cell.date === selectedDate;
                                const isToday = cell.date === today;
                                const hasPlan = !!cell.plan;
                                const taskColors = cell.plan?.tasks?.map(t => t.subject_color) || [];
                                const uniqueColors = [...new Set(taskColors)];
                                const allDone = cell.plan?.tasks?.every(t => t.is_completed);

                                return (
                                    <button
                                        key={cell.date}
                                        onClick={() => setSelectedDate(cell.date)}
                                        className={`relative aspect-square rounded-lg flex flex-col items-center justify-center
                                            text-xs transition-all duration-200
                                            ${isSelected ? 'bg-accent-purple/20 border border-accent-purple/40 text-white' :
                                                isToday ? 'bg-white/[0.06] border border-white/[0.1] text-gray-200' :
                                                    hasPlan ? 'hover:bg-white/[0.04] text-gray-300' : 'text-gray-600'}`}
                                    >
                                        <span className={`text-[11px] font-medium ${allDone && hasPlan ? 'text-accent-green' : ''}`}>
                                            {cell.day}
                                        </span>
                                        {hasPlan && (
                                            <div className="flex gap-0.5 mt-0.5">
                                                {uniqueColors.slice(0, 3).map((c, ci) => (
                                                    <div key={ci} className="w-1 h-1 rounded-full"
                                                        style={{ backgroundColor: c, opacity: allDone ? 0.4 : 1 }} />
                                                ))}
                                            </div>
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    </GlassCard>

                    {/* Task list */}
                    <GlassCard className="lg:col-span-2 !p-4">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-display font-semibold text-gray-300 flex items-center gap-2">
                                <Calendar className="w-4 h-4 text-accent-blue" />
                                {viewMode === 'day' ? 'Day View' : 'Week View'}
                            </h3>
                            <div className="flex gap-1 p-0.5 glass-card rounded-lg">
                                {['day', 'week'].map(mode => (
                                    <button
                                        key={mode}
                                        onClick={() => setViewMode(mode)}
                                        className={`px-3 py-1 rounded-md text-xs font-medium transition-all
                                            ${viewMode === mode ? 'bg-accent-purple/20 text-accent-purple' : 'text-gray-400 hover:text-gray-300'}`}
                                    >
                                        {mode.charAt(0).toUpperCase() + mode.slice(1)}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
                            {visibleTasks.length === 0 ? (
                                <div className="text-center py-12 text-gray-500">
                                    <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">No tasks for this {viewMode}.</p>
                                    <p className="text-xs mt-1">Select a day with colored dots on the calendar.</p>
                                </div>
                            ) : (
                                visibleTasks.map((dayPlan) => (
                                    <motion.div
                                        key={dayPlan.plan_id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                    >
                                        {/* Day header */}
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-xs font-display font-semibold text-gray-300">
                                                {new Date(dayPlan.plan_date + 'T00:00:00').toLocaleDateString('en-US', {
                                                    weekday: 'short', month: 'short', day: 'numeric'
                                                })}
                                            </span>
                                            {dayPlan.plan_date === today && (
                                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-accent-purple/15 text-accent-purple font-medium">
                                                    Today
                                                </span>
                                            )}
                                            <div className="flex-1 h-px bg-white/[0.06]" />
                                            <span className="text-[10px] text-gray-500">
                                                {Math.round(dayPlan.completion_pct)}% done
                                            </span>
                                        </div>

                                        {/* Tasks */}
                                        <div className="space-y-1.5">
                                            {dayPlan.tasks.map((task, tIdx) => (
                                                <motion.div
                                                    key={`${task.topic_id}-${tIdx}`}
                                                    initial={{ opacity: 0, x: -10 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    transition={{ delay: tIdx * 0.03 }}
                                                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl
                                                        border transition-all duration-200
                                                        ${task.is_completed
                                                            ? 'bg-white/[0.02] border-white/[0.04] opacity-60'
                                                            : 'bg-white/[0.03] border-white/[0.06] hover:border-white/[0.1]'}`}
                                                >
                                                    <button
                                                        onClick={() => handleToggleTask(dayPlan.plan_id, task.topic_id)}
                                                        className="flex-shrink-0 transition-all hover:scale-110"
                                                    >
                                                        {task.is_completed ? (
                                                            <CheckCircle className="w-4 h-4 text-accent-green" />
                                                        ) : (
                                                            <Circle className="w-4 h-4 text-gray-500 hover:text-gray-300" />
                                                        )}
                                                    </button>

                                                    <div className="w-1.5 h-8 rounded-full flex-shrink-0"
                                                        style={{ backgroundColor: task.subject_color }} />

                                                    <div className="flex-1 min-w-0">
                                                        <p className={`text-sm font-medium truncate ${task.is_completed ? 'line-through text-gray-500' : 'text-gray-200'}`}>
                                                            {task.topic_title}
                                                        </p>
                                                        <p className="text-[11px] text-gray-500">{task.subject_name}</p>
                                                    </div>

                                                    <div className="flex items-center gap-2 flex-shrink-0">
                                                        <div className="flex items-center gap-1 text-xs text-gray-400">
                                                            <Timer className="w-3 h-3" />
                                                            <span>{task.duration_min}m</span>
                                                        </div>
                                                        {task.complexity && (
                                                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-dark-600 text-gray-400 font-medium border border-white/5" title="Topic Complexity Level">
                                                                Lvl {task.complexity}
                                                            </span>
                                                        )}
                                                        {task.priority >= 0.7 && (
                                                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-500/15 text-red-400 font-medium" title="High Priority">
                                                                High
                                                            </span>
                                                        )}
                                                        {task.priority >= 0.4 && task.priority < 0.7 && (
                                                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-yellow-500/15 text-yellow-400 font-medium" title="Medium Priority">
                                                                Med
                                                            </span>
                                                        )}
                                                    </div>
                                                </motion.div>
                                            ))}
                                        </div>
                                    </motion.div>
                                ))
                            )}
                        </div>
                    </GlassCard>
                </div>
            )}

            {/* Empty state */}
            {!loading && (!plan || !plan.days?.length) && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-center min-h-[40vh]"
                >
                    <GlassCard className="max-w-md text-center !p-10">
                        <span className="text-5xl mb-4 block">📅</span>
                        <h2 className="text-xl font-display font-bold text-gradient-purple mb-2">
                            Study Planner
                        </h2>
                        <p className="text-sm text-gray-400 mb-4">
                            Set your daily study hours and generate an adaptive plan based on subject credits, topic priority, and exam dates.
                        </p>
                        <p className="text-xs text-gray-600">
                            Configure your hours above and click "Generate Plan" to get started.
                        </p>
                    </GlassCard>
                </motion.div>
            )}
        </div>
    );
}
