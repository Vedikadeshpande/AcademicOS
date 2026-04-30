import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    ArrowLeft, Upload, FileText, BookOpen, Brain, BarChart3,
    Plus, Clock, CheckCircle, AlertTriangle, CalendarDays
} from 'lucide-react';
import useSubjectStore from '../stores/subjectStore';
import GlassCard from '../components/common/GlassCard';
import ProgressRing from '../components/analytics/ProgressRing';
import CountdownTimer from '../components/common/CountdownTimer';
import AnimatedCounter from '../components/common/AnimatedCounter';
import FileUploader from '../components/subject/FileUploader';
import SyllabusViewer from '../components/subject/SyllabusViewer';
import { getSyllabusUnits, getUploads, getAnalytics, parseSyllabus, updateSubject } from '../lib/api';

export default function SubjectWorkspace() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { activeSubject, fetchSubject } = useSubjectStore();
    const [activeTab, setActiveTab] = useState('overview');
    const [units, setUnits] = useState([]);
    const [uploads, setUploads] = useState([]);
    const [analytics, setAnalytics] = useState(null);
    const [syllabusText, setSyllabusText] = useState('');
    const [parsing, setParsing] = useState(false);
    const [showDatePicker, setShowDatePicker] = useState(false);
    const [examDateInput, setExamDateInput] = useState('');

    useEffect(() => {
        fetchSubject(id);
        loadData();
    }, [id]);

    const loadData = async () => {
        try {
            const [unitsRes, uploadsRes, analyticsRes] = await Promise.all([
                getSyllabusUnits(id),
                getUploads(id),
                getAnalytics(id).catch(() => ({ data: null })),
            ]);
            setUnits(unitsRes.data);
            setUploads(uploadsRes.data);
            setAnalytics(analyticsRes.data);
        } catch (err) {
            console.error('Failed to load subject data:', err);
        }
    };

    const handleParseSyllabus = async () => {
        if (!syllabusText.trim()) return;
        setParsing(true);
        try {
            const res = await parseSyllabus(id, { raw_text: syllabusText });
            setUnits(res.data);
            // Don't clear — text stays in the box for editing and re-parsing
        } catch (err) {
            console.error('Parse failed:', err);
        } finally {
            setParsing(false);
        }
    };

    const tabs = [
        { id: 'overview', label: 'Overview', icon: BarChart3 },
        { id: 'syllabus', label: 'Syllabus', icon: BookOpen },
        { id: 'uploads', label: 'Uploads', icon: Upload },
    ];

    if (!activeSubject) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-2 border-accent-purple border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start gap-4">
                <button
                    onClick={() => navigate('/')}
                    className="p-2 rounded-xl glass-card-hover text-gray-400 hover:text-gray-200 mt-1"
                >
                    <ArrowLeft className="w-5 h-5" />
                </button>
                <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                        <div
                            className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ backgroundColor: `${activeSubject.color}20` }}
                        >
                            <BookOpen className="w-5 h-5" style={{ color: activeSubject.color }} />
                        </div>
                        <div>
                            <h1 className="text-xl font-display font-bold text-gray-100">
                                {activeSubject.name}
                            </h1>
                            {activeSubject.code && (
                                <span className="text-xs text-gray-500 font-mono">{activeSubject.code}</span>
                            )}
                        </div>
                    </div>
                </div>
                {showDatePicker ? (
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="flex items-center gap-2"
                    >
                        <input
                            type="date"
                            value={examDateInput}
                            onChange={(e) => setExamDateInput(e.target.value)}
                            className="bg-dark-600 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-gray-200
                                focus:outline-none focus:border-accent-purple/50"
                            min={new Date().toISOString().split('T')[0]}
                        />
                        <button
                            onClick={async () => {
                                if (!examDateInput) return;
                                try {
                                    await updateSubject(id, { exam_date: examDateInput });
                                    fetchSubject(id);
                                    setShowDatePicker(false);
                                } catch (err) {
                                    console.error('Failed to set exam date:', err);
                                }
                            }}
                            disabled={!examDateInput}
                            className="px-3 py-1.5 rounded-lg bg-accent-purple/20 text-accent-purple text-sm
                                font-medium hover:bg-accent-purple/30 transition-colors disabled:opacity-40"
                        >
                            Save
                        </button>
                        <button
                            onClick={() => setShowDatePicker(false)}
                            className="px-2 py-1.5 rounded-lg text-gray-500 hover:text-gray-300 text-sm transition-colors"
                        >
                            ✕
                        </button>
                    </motion.div>
                ) : activeSubject.exam_date ? (
                    <button
                        onClick={() => {
                            setExamDateInput(activeSubject.exam_date.split('T')[0]);
                            setShowDatePicker(true);
                        }}
                        className="group/date relative"
                        title="Click to change exam date"
                    >
                        <CountdownTimer targetDate={activeSubject.exam_date} compact />
                        <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] text-gray-600
                            opacity-0 group-hover/date:opacity-100 transition-opacity whitespace-nowrap">
                            click to change
                        </span>
                    </button>
                ) : (
                    <button
                        onClick={() => setShowDatePicker(true)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass-card-hover
                            text-gray-400 hover:text-accent-purple transition-colors text-sm"
                    >
                        <CalendarDays className="w-4 h-4" />
                        <span>Add Exam Date</span>
                    </button>
                )}
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                    { label: 'Topics', value: activeSubject.total_topics || 0, icon: Brain, color: '#7c5cff' },
                    { label: 'Coverage', value: `${activeSubject.coverage_pct?.toFixed(1) || 0}%`, icon: CheckCircle, color: '#5cffb1' },
                    { label: 'Files', value: uploads.length, icon: FileText, color: '#5c9cff' },
                    { label: 'Quizzes', value: analytics?.total_quizzes_taken || 0, icon: BarChart3, color: '#ff9f5c' },
                ].map(({ label, value, icon: Icon, color }) => (
                    <GlassCard key={label} className="!p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Icon className="w-4 h-4" style={{ color }} />
                            <span className="text-xs text-gray-500">{label}</span>
                        </div>
                        <span className="text-lg font-display font-bold text-gray-100">{value}</span>
                    </GlassCard>
                ))}
            </div>

            {/* Tabs */}
            <div className="flex gap-1 p-1 glass-card rounded-xl w-fit">
                {tabs.map(({ id: tabId, label, icon: Icon }) => (
                    <button
                        key={tabId}
                        onClick={() => setActiveTab(tabId)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                        ${activeTab === tabId
                                ? 'bg-accent-purple/20 text-accent-purple'
                                : 'text-gray-400 hover:text-gray-300 hover:bg-white/[0.04]'}`}
                    >
                        <Icon className="w-4 h-4" />
                        {label}
                    </button>
                ))}
            </div>

            {/* Tab content */}
            <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
            >
                {activeTab === 'overview' && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {/* Analytics rings */}
                        <GlassCard className="lg:col-span-2">
                            <h3 className="text-sm font-display font-semibold text-gray-300 mb-6">
                                Subject Analytics
                            </h3>
                            <div className="flex items-center justify-around">
                                <ProgressRing
                                    value={activeSubject.coverage_pct || 0}
                                    color="#5cffb1"
                                    label="Coverage"
                                />
                                <ProgressRing
                                    value={analytics?.avg_quiz_accuracy || 0}
                                    color="#5c9cff"
                                    label="Quiz Accuracy"
                                />
                                <ProgressRing
                                    value={analytics?.readiness_pct || 0}
                                    color="#7c5cff"
                                    label="Readiness"
                                />
                            </div>
                        </GlassCard>

                        {/* Risk card */}
                        <GlassCard>
                            <h3 className="text-sm font-display font-semibold text-gray-300 mb-4">
                                Exam Risk
                            </h3>
                            <div className="flex flex-col items-center gap-3">
                                <div className={`text-3xl font-display font-bold
                  ${analytics?.risk_level === 'Low' ? 'text-green-400' :
                                        analytics?.risk_level === 'Medium' ? 'text-yellow-400' :
                                            analytics?.risk_level === 'High' ? 'text-red-400' : 'text-gray-400'}`}>
                                    {analytics?.risk_level || 'N/A'}
                                </div>
                                <span className="text-xs text-gray-500 text-center">
                                    {analytics?.risk_level === 'Low' ? 'You\'re on track! Keep going.' :
                                        analytics?.risk_level === 'Medium' ? 'Some areas need attention.' :
                                            analytics?.risk_level === 'High' ? 'Focus on weak topics urgently!' :
                                                'Take quizzes to assess risk.'}
                                </span>
                            </div>
                        </GlassCard>
                    </div>
                )}

                {activeTab === 'syllabus' && (
                    <div className="space-y-4">
                        {/* Parse syllabus input */}
                        <GlassCard>
                            <h3 className="text-sm font-display font-semibold text-gray-300 mb-2">
                                Add Syllabus
                            </h3>
                            <p className="text-xs text-gray-500 mb-3">
                                Enter unit names followed by comma-separated topics. Example:
                            </p>
                            <div className="px-3 py-2 rounded-lg bg-dark-700/60 text-xs text-gray-500 font-mono mb-3 leading-relaxed">
                                Unit 1: Introduction<br />
                                Arrays, Linked Lists, Stacks, Queues<br />
                                <br />
                                Unit 2: Algorithms<br />
                                Sorting, Searching, Graph Traversal
                            </div>
                            <textarea
                                value={syllabusText}
                                onChange={(e) => setSyllabusText(e.target.value)}
                                placeholder={"Unit 1: Data Structures\nArrays, Linked Lists, Stacks, Queues\n\nUnit 2: Algorithms\nBubble Sort, Quick Sort, Binary Search"}
                                className="input-field min-h-[140px] resize-y font-mono text-xs"
                            />
                            <div className="flex items-center gap-3 mt-3">
                                <button
                                    onClick={handleParseSyllabus}
                                    disabled={parsing || !syllabusText.trim()}
                                    className="btn-primary flex items-center gap-2"
                                >
                                    {parsing ? (
                                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    ) : (
                                        <Plus className="w-3.5 h-3.5" />
                                    )}
                                    {parsing ? 'Parsing...' : 'Parse & Add'}
                                </button>
                                <span className="text-xs text-gray-600">
                                    Text stays in the box — edit and re-parse anytime
                                </span>
                            </div>
                        </GlassCard>

                        {/* Editable syllabus viewer */}
                        <GlassCard>
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-display font-semibold text-gray-300">
                                    Syllabus Structure
                                </h3>
                                {units.length > 0 && (
                                    <span className="text-xs text-gray-500">
                                        {units.length} unit{units.length !== 1 ? 's' : ''} •{' '}
                                        {units.reduce((sum, u) => sum + (u.topics?.length || 0), 0)} topics
                                    </span>
                                )}
                            </div>
                            <SyllabusViewer units={units} onUnitsChange={setUnits} editable />
                        </GlassCard>
                    </div>
                )}

                {activeTab === 'uploads' && (
                    <GlassCard>
                        <h3 className="text-sm font-display font-semibold text-gray-300 mb-4">
                            Upload & Manage Files
                        </h3>
                        <FileUploader subjectId={id} onUploadComplete={loadData} />
                    </GlassCard>
                )}
            </motion.div>
        </div>
    );
}
