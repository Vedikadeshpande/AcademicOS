import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Brain, Play, CheckCircle, XCircle, Trophy,
    ArrowRight, RefreshCw, BarChart3, Globe, FolderOpen, FileText
} from 'lucide-react';
import GlassCard from '../components/common/GlassCard';
import AnimatedCounter from '../components/common/AnimatedCounter';
import useSubjectStore from '../stores/subjectStore';
import { generateQuiz, submitQuiz, getQuizHistory, getSyllabusUnits, generateExamPaper } from '../lib/api';


export default function QuizPage() {
    const { subjects, fetchSubjects } = useSubjectStore();
    const [phase, setPhase] = useState('setup'); // setup, quiz, results
    const [selectedSubject, setSelectedSubject] = useState('');
    const [numQuestions, setNumQuestions] = useState(10);
    const [difficulty, setDifficulty] = useState('medium');
    const [quizType, setQuizType] = useState('topic');
    const [examType, setExamType] = useState('end_sem');
    const [sessionId, setSessionId] = useState(null);
    const [questions, setQuestions] = useState([]);
    const [answers, setAnswers] = useState({});
    const [currentQ, setCurrentQ] = useState(0);
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [history, setHistory] = useState([]);
    const [units, setUnits] = useState([]);

    // Scope state
    const [scope, setScope] = useState('all'); // 'all', 'unit', 'topic'
    const [selectedUnit, setSelectedUnit] = useState('');
    const [selectedTopic, setSelectedTopic] = useState('');

    useEffect(() => { fetchSubjects(); }, []);

    useEffect(() => {
        if (selectedSubject) {
            getQuizHistory(selectedSubject).then(res => setHistory(res.data)).catch(() => { });
            getSyllabusUnits(selectedSubject).then(res => setUnits(res.data || [])).catch(() => { });
        }
    }, [selectedSubject]);

    const startQuiz = async () => {
        if (!selectedSubject) return;
        if (scope === 'unit' && !selectedUnit) return;
        if (scope === 'topic' && !selectedTopic) return;
        setLoading(true);
        try {
            // Build topic_ids based on scope
            let topicIds = null;
            if (scope === 'unit' && selectedUnit) {
                const unit = units.find(u => u.id === selectedUnit);
                topicIds = (unit?.topics || []).map(t => t.id);
            } else if (scope === 'topic' && selectedTopic) {
                topicIds = [selectedTopic];
            }

            let res;
            if (quizType === 'mock') {
                res = await generateExamPaper({
                    subject_id: selectedSubject,
                    exam_type: examType,
                });
            } else {
                const payload = {
                    subject_id: selectedSubject,
                    num_questions: numQuestions,
                    quiz_type: quizType,
                    difficulty,
                };
                if (topicIds && topicIds.length > 0) {
                    payload.topic_ids = topicIds;
                }
                res = await generateQuiz(payload);
            }

            setSessionId(res.data.session_id);
            setQuestions(res.data.questions);
            setAnswers({});
            setCurrentQ(0);
            setPhase(quizType === 'mock' ? 'exam_view' : 'quiz');
        } catch (err) {
            const msg = err.response?.data?.detail;
            alert(typeof msg === 'string' ? msg : 'Failed to generate quiz/exam. Make sure you have topics with content in this subject.');
        } finally {
            setLoading(false);
        }
    };


    const handleAnswer = (questionId, answer) => {
        setAnswers(prev => ({ ...prev, [questionId]: answer }));
    };

    const submitAnswers = async () => {
        setLoading(true);
        try {
            const res = await submitQuiz(sessionId, {
                answers: Object.entries(answers).map(([question_id, user_answer]) => ({
                    question_id,
                    user_answer,
                })),
            });
            setResults(res.data);
            setPhase('results');
        } catch (err) {
            alert('Failed to submit quiz.');
        } finally {
            setLoading(false);
        }
    };

    const resetQuiz = () => {
        setPhase('setup');
        setQuestions([]);
        setAnswers({});
        setResults(null);
        setSessionId(null);
        setCurrentQ(0);
    };

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            <AnimatePresence mode="wait">
                {/* ── SETUP PHASE ── */}
                {phase === 'setup' && (
                    <motion.div key="setup" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
                        <GlassCard>
                            <h2 className="text-lg font-display font-bold text-gradient-purple mb-6">
                                <Brain className="w-5 h-5 inline mr-2" />Configure Quiz
                            </h2>

                            <div className="space-y-5">
                                {/* Subject selector */}
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 mb-1.5">Subject</label>
                                    <select
                                        value={selectedSubject}
                                        onChange={(e) => setSelectedSubject(e.target.value)}
                                        className="input-field"
                                    >
                                        <option value="">Select a subject...</option>
                                        {subjects.map(s => (
                                            <option key={s.id} value={s.id}>{s.name}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Quiz Type */}
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 mb-1.5">Quiz Type</label>
                                    <div className="flex gap-2">
                                        {[
                                            { id: 'topic', label: 'Topic-based (MCQ)' },
                                            { id: 'short', label: 'Short Answer Mode' },
                                            { id: 'pyq', label: 'PYQ-focused' },
                                            { id: 'mock', label: 'Mock Test' },
                                        ].map(t => (
                                            <button
                                                key={t.id}
                                                onClick={() => setQuizType(t.id)}
                                                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all
                          ${quizType === t.id
                                                    ? 'bg-accent-purple/20 text-accent-purple border border-accent-purple/30'
                                                    : 'glass-card text-gray-400 hover:text-gray-300'}`}
                                            >
                                                {t.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {quizType === 'mock' ? (
                                    <div className="space-y-4">
                                        <div className="p-4 rounded-xl border border-white/10 bg-dark-600/30">
                                            <h4 className="text-sm font-medium text-gray-300 mb-3">Mock Test Configuration</h4>
                                            
                                            <label className="block text-xs font-medium text-gray-400 mb-1.5 mt-3">Duration (Minutes)</label>
                                            <input 
                                                type="number" 
                                                className="input-field mb-3" 
                                                defaultValue={120}
                                            />
                                            
                                            <label className="block text-xs font-medium text-gray-400 mb-1.5">Exam Schema Structure</label>
                                            <select
                                                value={examType}
                                                onChange={(e) => setExamType(e.target.value)}
                                                className="input-field"
                                            >
                                                <option value="mid_sem">Mid Semester Setup (30 Marks)</option>
                                                <option value="end_sem">End Semester Setup (80 Marks - Default)</option>
                                            </select>
                                            <p className="text-xs text-gray-400 mt-2">
                                                * This uses Bloom's Taxonomy to dynamically generate the correct spread of questions and evaluate based on your configuration.
                                            </p>
                                        </div>
                                    </div>
                                ) : (
                                    <>
                                        {/* ── Scope selector ── */}
                                        <div>
                                            <label className="block text-xs font-medium text-gray-400 mb-3">Quiz Scope</label>
                                            <div className="grid grid-cols-3 gap-3">
                                                {[
                                                    { key: 'all', icon: Globe, label: 'Entire Syllabus', desc: 'All topics' },
                                                    { key: 'unit', icon: FolderOpen, label: 'By Unit', desc: 'Pick a unit' },
                                                    { key: 'topic', icon: FileText, label: 'By Topic', desc: 'Single topic' },
                                                ].map(({ key, icon: Icon, label, desc }) => (
                                                    <button
                                                        key={key}
                                                        onClick={() => { setScope(key); setSelectedUnit(''); setSelectedTopic(''); }}
                                                        className={`p-3 rounded-xl border text-left transition-all
                                                            ${scope === key
                                                                ? 'border-accent-purple/50 bg-accent-purple/10 shadow-glow-purple'
                                                                : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] hover:bg-white/[0.04]'
                                                            }`}
                                                    >
                                                        <Icon className={`w-4 h-4 mb-1.5 ${scope === key ? 'text-accent-purple' : 'text-gray-500'}`} />
                                                        <div className={`text-sm font-medium ${scope === key ? 'text-accent-purple' : 'text-gray-300'}`}>{label}</div>
                                                        <div className="text-[10px] text-gray-500 mt-0.5">{desc}</div>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        {/* ── Conditional unit/topic selector ── */}
                                        {scope === 'unit' && (
                                            <div>
                                                <label className="block text-xs font-medium text-gray-400 mb-1.5">Select Unit</label>
                                                <select
                                                    value={selectedUnit}
                                                    onChange={(e) => setSelectedUnit(e.target.value)}
                                                    className="input-field"
                                                >
                                                    <option value="">Choose a unit...</option>
                                                    {units.map(u => (
                                                        <option key={u.id} value={u.id}>
                                                            Unit {u.unit_number}: {u.title} ({u.topics?.length || 0} topics)
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                        )}

                                        {scope === 'topic' && (
                                            <div>
                                                <label className="block text-xs font-medium text-gray-400 mb-1.5">Select Topic</label>
                                                <select
                                                    value={selectedTopic}
                                                    onChange={(e) => setSelectedTopic(e.target.value)}
                                                    className="input-field"
                                                >
                                                    <option value="">Choose a topic...</option>
                                                    {units.map(u => (
                                                        <optgroup key={u.id} label={`Unit ${u.unit_number}: ${u.title}`}>
                                                            {(u.topics || []).map(t => (
                                                                <option key={t.id} value={t.id}>{t.title}</option>
                                                            ))}
                                                        </optgroup>
                                                    ))}
                                                </select>
                                            </div>
                                        )}

                                        {/* Format determines difficulty explicitly now */}

                                        {/* Question count */}
                                        <div>
                                            <label className="block text-xs font-medium text-gray-400 mb-1.5">
                                                Number of Questions: {numQuestions}
                                            </label>
                                            <input
                                                type="range"
                                                min="5" max="30" step="5"
                                                value={numQuestions}
                                                onChange={(e) => setNumQuestions(parseInt(e.target.value))}
                                                className="w-full accent-accent-purple"
                                            />
                                            <div className="flex justify-between text-xs text-gray-600 mt-1">
                                                <span>5</span><span>15</span><span>30</span>
                                            </div>
                                        </div>
                                    </>
                                )}

                                <button
                                    onClick={startQuiz}
                                    disabled={!selectedSubject || loading || (scope === 'unit' && !selectedUnit) || (scope === 'topic' && !selectedTopic)}
                                    className="btn-primary w-full flex items-center justify-center gap-2"
                                >
                                    {loading ? (
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    ) : (
                                        <><Play className="w-4 h-4" /> Start Quiz</>
                                    )}
                                </button>
                            </div>
                        </GlassCard>

                        {/* Quiz history */}
                        {history.length > 0 && (
                            <GlassCard>
                                <h3 className="text-sm font-display font-semibold text-gray-300 mb-4">
                                    <BarChart3 className="w-4 h-4 inline mr-2" />Recent Quizzes
                                </h3>
                                <div className="space-y-2">
                                    {history.slice(0, 5).map(h => (
                                        <div key={h.id} className="flex items-center justify-between px-3 py-2 rounded-xl bg-dark-700/40">
                                            <div className="flex items-center gap-3">
                                                <span className="text-xs text-gray-500 capitalize">{h.quiz_type}</span>
                                                <span className="text-sm text-gray-300">{h.total_questions} Qs</span>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className={`text-sm font-bold ${h.score_pct >= 70 ? 'text-accent-green' : h.score_pct >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                    {h.score_pct}%
                                                </span>
                                                <span className="text-xs text-gray-600">{new Date(h.taken_at).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </GlassCard>
                        )}
                    </motion.div>
                )}

                {/* ── EXAM VIEW PHASE (Document) ── */}
                {phase === 'exam_view' && questions.length > 0 && (
                    <motion.div key="exam_view" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-6">
                        <GlassCard className="!p-8">
                            <div className="text-center mb-8 border-b border-white/10 pb-6">
                                <h1 className="text-3xl font-display font-bold text-gradient-purple mb-2">
                                    {subjects.find(s => s.id === selectedSubject)?.name || 'Subject'} Exam Paper
                                </h1>
                                <p className="text-gray-400 font-medium">
                                    {examType === 'mid_sem' ? 'Mid-Semester Examination (30 Marks)' : 'End-Semester Examination (80 Marks)'}
                                </p>
                            </div>
                            
                            <div className="space-y-8">
                                {/* Group questions logically by marks */}
                                {[2, 4, 8, 20].map(markValue => {
                                    const qsForMark = questions.filter(q => q.marks === markValue);
                                    if (qsForMark.length === 0) return null;
                                    
                                    return (
                                        <div key={markValue} className="mb-8">
                                            <h3 className="text-lg font-bold text-accent-blue mb-4 pb-2 border-b border-white/5">
                                                Section - {markValue} Markers
                                            </h3>
                                            <div className="space-y-6 pl-2">
                                                {qsForMark.map((q, idx) => {
                                                    let bloomExtracted = 'Analyze';
                                                    if (q.explanation) {
                                                        const match = q.explanation.match(/Level:\s*([A-Za-z]+)/);
                                                        if (match) bloomExtracted = match[1];
                                                    }
                                                    return (
                                                        <div key={q.id || idx} className="flex gap-4">
                                                            <span className="font-bold text-gray-500 w-6 flex-shrink-0 mt-0.5">Q.</span>
                                                            <div className="flex-1">
                                                                <p className="text-gray-200 leading-relaxed font-medium mb-2">{q.question_text}</p>
                                                                <div className="flex gap-2">
                                                                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-accent-purple/20 text-accent-purple">
                                                                        {bloomExtracted}
                                                                    </span>
                                                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-dark-600 text-gray-400">
                                                                        [{q.marks} Marks]
                                                                    </span>
                                                                    {q.topic_title && (
                                                                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full border border-white/5 text-gray-500">
                                                                            {q.topic_title}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            <div className="mt-10 pt-6 border-t border-white/10 flex flex-col items-center gap-4">
                                <button onClick={() => window.print()} className="btn-primary flex items-center gap-2 px-8">
                                    <FileText className="w-4 h-4" /> Save as PDF / Print
                                </button>
                                <button onClick={resetQuiz} className="text-sm font-medium text-gray-400 hover:text-white transition-colors">
                                    Configure New Paper
                                </button>
                            </div>
                        </GlassCard>
                    </motion.div>
                )}

                {/* ── QUIZ PHASE ── */}
                {phase === 'quiz' && questions.length > 0 && (
                    <motion.div key="quiz" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                        {/* Progress */}
                        <div className="mb-4">
                            <div className="flex items-center justify-between text-sm mb-2">
                                <span className="text-gray-400">Question {currentQ + 1} of {questions.length}</span>
                                <span className="text-gray-500">{Object.keys(answers).length} answered</span>
                            </div>
                            <div className="h-1.5 bg-dark-600 rounded-full overflow-hidden">
                                <motion.div
                                    className="h-full bg-accent-purple rounded-full"
                                    animate={{ width: `${((currentQ + 1) / questions.length) * 100}%` }}
                                />
                            </div>
                        </div>

                        <GlassCard className="!p-6">
                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={currentQ}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                >
                                    <div className="flex items-center gap-3 mb-4">
                                        <span className="px-2 py-0.5 rounded-lg bg-accent-purple/15 text-accent-purple text-xs font-medium uppercase">
                                            {questions[currentQ].question_type}
                                        </span>
                                        <span className="text-xs text-gray-500">
                                            {questions[currentQ].marks} mark{questions[currentQ].marks > 1 ? 's' : ''}
                                        </span>
                                        {questions[currentQ].topic_title && (
                                            <span className="text-xs text-gray-600 ml-auto">
                                                {questions[currentQ].topic_title}
                                            </span>
                                        )}
                                    </div>

                                    <p className="text-gray-200 font-medium mb-6 leading-relaxed">
                                        {questions[currentQ].question_text}
                                    </p>

                                    {/* MCQ options */}
                                    {questions[currentQ].options && (() => {
                                        try {
                                            const opts = JSON.parse(questions[currentQ].options);
                                            return (
                                                <div className="space-y-2 mb-6">
                                                    {Object.entries(opts).map(([letter, text]) => (
                                                        <button
                                                            key={letter}
                                                            onClick={() => handleAnswer(questions[currentQ].id, letter)}
                                                            className={`w-full text-left px-4 py-3 rounded-xl transition-all flex items-center gap-3
                                ${answers[questions[currentQ].id] === letter
                                                                    ? 'bg-accent-purple/20 border border-accent-purple/40 text-gray-100'
                                                                    : 'glass-card text-gray-300 hover:bg-white/[0.04]'}`}
                                                        >
                                                            <span className="w-7 h-7 rounded-lg bg-dark-600 flex items-center justify-center text-xs font-bold">
                                                                {letter}
                                                            </span>
                                                            <span className="text-sm">{text}</span>
                                                        </button>
                                                    ))}
                                                </div>
                                            );
                                        } catch { return null; }
                                    })()}

                                    {/* Text answer for non-MCQ */}
                                    {!questions[currentQ].options && (
                                        <textarea
                                            value={answers[questions[currentQ].id] || ''}
                                            onChange={(e) => handleAnswer(questions[currentQ].id, e.target.value)}
                                            placeholder="Type your answer here..."
                                            className="input-field min-h-[100px] resize-y mb-4"
                                        />
                                    )}
                                </motion.div>
                            </AnimatePresence>

                            {/* Navigation */}
                            <div className="flex items-center justify-between pt-4 border-t border-white/[0.06]">
                                <button
                                    onClick={() => setCurrentQ(prev => Math.max(0, prev - 1))}
                                    disabled={currentQ === 0}
                                    className="btn-secondary"
                                >
                                    Previous
                                </button>

                                <div className="flex gap-1">
                                    {questions.map((_, i) => (
                                        <button
                                            key={i}
                                            onClick={() => setCurrentQ(i)}
                                            className={`w-7 h-7 rounded-lg text-xs font-medium transition-all
                        ${i === currentQ ? 'bg-accent-purple text-white' :
                                                    answers[questions[i]?.id] ? 'bg-accent-green/20 text-accent-green' :
                                                        'bg-dark-600 text-gray-500 hover:bg-dark-500'}`}
                                        >
                                            {i + 1}
                                        </button>
                                    ))}
                                </div>

                                {currentQ < questions.length - 1 ? (
                                    <button
                                        onClick={() => setCurrentQ(prev => prev + 1)}
                                        className="btn-primary flex items-center gap-2"
                                    >
                                        Next <ArrowRight className="w-4 h-4" />
                                    </button>
                                ) : (
                                    <button
                                        onClick={submitAnswers}
                                        disabled={loading || Object.keys(answers).length === 0}
                                        className="btn-primary flex items-center gap-2"
                                    >
                                        {loading ? (
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        ) : (
                                            <><CheckCircle className="w-4 h-4" /> Submit Quiz</>
                                        )}
                                    </button>
                                )}
                            </div>
                        </GlassCard>
                    </motion.div>
                )}

                {/* ── RESULTS PHASE ── */}
                {phase === 'results' && results && (
                    <motion.div key="results" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-6">
                        {/* Score card */}
                        <GlassCard className="text-center !p-8">
                            <Trophy className={`w-12 h-12 mx-auto mb-4 ${results.score_pct >= 70 ? 'text-yellow-400' : results.score_pct >= 40 ? 'text-accent-blue' : 'text-gray-500'}`} />
                            <h2 className="text-2xl font-display font-bold text-gradient-purple mb-2">Quiz Complete!</h2>
                            <div className="flex items-center justify-center gap-6 mt-4">
                                <div>
                                    <AnimatedCounter value={results.score_pct} suffix="%" className="text-4xl text-accent-green" />
                                    <p className="text-xs text-gray-500 mt-1">Score</p>
                                </div>
                                <div className="w-px h-12 bg-white/10" />
                                <div>
                                    <span className="text-4xl font-display font-bold text-gray-200">
                                        {results.correct_answers}/{results.total_questions}
                                    </span>
                                    <p className="text-xs text-gray-500 mt-1">Correct</p>
                                </div>
                            </div>
                        </GlassCard>

                        {/* Detailed results */}
                        <GlassCard>
                            <h3 className="text-sm font-display font-semibold text-gray-300 mb-4">Detailed Results</h3>
                            <div className="space-y-3">
                                {results.results.map((r, i) => (
                                    <motion.div
                                        key={r.question_id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: i * 0.05 }}
                                        className={`px-4 py-3 rounded-xl border
                      ${r.is_correct
                                                ? 'bg-green-500/5 border-green-500/20'
                                                : 'bg-red-500/5 border-red-500/20'}`}
                                    >
                                        <div className="flex items-start gap-3">
                                            {r.is_correct
                                                ? <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                                                : <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm text-gray-300 mb-1">{r.question_text}</p>
                                                <p className="text-xs text-gray-500">Your answer: {r.user_answer || '(no answer)'}</p>
                                                {typeof r.awarded_marks === 'number' && typeof r.max_marks === 'number' && (
                                                    <p className="text-xs text-gray-400 mt-1">Marks: {r.awarded_marks}/{r.max_marks}</p>
                                                )}
                                                {r.feedback && (
                                                    <div className="mt-3 p-3 rounded-lg bg-dark-600/50 border border-white/5">
                                                        <p className="text-xs text-gray-300 font-medium mb-2">Professor's Analysis:</p>
                                                        <p className="text-xs text-gray-400 mb-3">{r.feedback}</p>
                                                        
                                                        {r.good_points && r.good_points.length > 0 && (
                                                            <div className="mb-2">
                                                                <p className="text-[10px] uppercase font-bold text-accent-green mb-1">Points Covered Well:</p>
                                                                <ul className="list-disc pl-4 space-y-0.5">
                                                                    {r.good_points.map((pt, j) => <li key={j} className="text-xs text-gray-400">{pt}</li>)}
                                                                </ul>
                                                            </div>
                                                        )}
                                                        
                                                        {r.missing_points && r.missing_points.length > 0 && (
                                                            <div className="mb-2">
                                                                <p className="text-[10px] uppercase font-bold text-red-400 mb-1">Points Missed:</p>
                                                                <ul className="list-disc pl-4 space-y-0.5">
                                                                    {r.missing_points.map((pt, j) => <li key={j} className="text-xs text-gray-400">{pt}</li>)}
                                                                </ul>
                                                            </div>
                                                        )}
                                                        
                                                        {r.mistakes && r.mistakes.length > 0 && (
                                                            <div className="mb-2">
                                                                <p className="text-[10px] uppercase font-bold text-yellow-400 mb-1">Factual Mistakes:</p>
                                                                <ul className="list-disc pl-4 space-y-0.5">
                                                                    {r.mistakes.map((pt, j) => <li key={j} className="text-xs text-gray-400">{pt}</li>)}
                                                                </ul>
                                                            </div>
                                                        )}
                                                        
                                                        {r.suggestions && r.suggestions.length > 0 && (
                                                            <div>
                                                                <p className="text-[10px] uppercase font-bold text-accent-blue mb-1">Suggestions for Improvement:</p>
                                                                <ul className="list-disc pl-4 space-y-0.5">
                                                                    {r.suggestions.map((pt, j) => <li key={j} className="text-xs text-gray-400">{pt}</li>)}
                                                                </ul>
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                                {!r.is_correct && r.correct_answer && (
                                                    <p className="text-xs text-accent-green mt-1">Correct: {r.correct_answer}</p>
                                                )}
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </GlassCard>

                        <button onClick={resetQuiz} className="btn-primary w-full flex items-center justify-center gap-2">
                            <RefreshCw className="w-4 h-4" /> Take Another Quiz
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
