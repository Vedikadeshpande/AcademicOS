import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, Play, CheckCircle, XCircle, AlertCircle, RefreshCw, Volume2, Sparkles, Brain } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = 'http://localhost:8000';

export default function VivaPage() {
    const [subjects, setSubjects] = useState([]);
    const [selectedSubjectId, setSelectedSubjectId] = useState('');
    const [topics, setTopics] = useState([]);
    const [selectedTopicId, setSelectedTopicId] = useState('');

    const [status, setStatus] = useState('idle'); // idle, generating, ready, recording, evaluating, result
    const [questionData, setQuestionData] = useState(null); // { question, ideal_answer }
    const [evaluation, setEvaluation] = useState(null); // { score, transcription, good_points, missing_points, mistakes, suggestions }
    
    const [recordingTime, setRecordingTime] = useState(0);

    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const timerRef = useRef(null);
    
    // Only MediaRecorder will be used now

    useEffect(() => {
        // Fetch subjects
        const fetchSubjects = async () => {
            try {
                const res = await axios.get(`${BACKEND_URL}/api/subjects`);
                setSubjects(res.data);
            } catch (err) {
                console.error("Failed to load subjects:", err);
            }
        };
        fetchSubjects();
    }, []);

    useEffect(() => {
        if (!selectedSubjectId) {
            setTopics([]);
            return;
        }
        const fetchSubjectDetails = async () => {
            try {
                const res = await axios.get(`${BACKEND_URL}/api/syllabus/${selectedSubjectId}/units`);
                if (Array.isArray(res.data)) {
                    const allTopics = res.data.flatMap(u => u.topics);
                    setTopics(allTopics);
                }
            } catch (e) {
                console.error("Failed to load topics:", e);
            }
        };
        fetchSubjectDetails();
    }, [selectedSubjectId]);

    useEffect(() => {
        if (status === 'recording') {
            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);
        } else {
            clearInterval(timerRef.current);
        }
        return () => clearInterval(timerRef.current);
    }, [status]);

    const handleGenerate = async () => {
        if (!selectedTopicId) return;
        setStatus('generating');
        
        try {
            const res = await axios.post(`${BACKEND_URL}/viva-question`, {
                topic_id: selectedTopicId
            });
            setQuestionData(res.data);
            setStatus('ready');
            playTTS(res.data.question);
        } catch (e) {
            console.error("Generate error", e);
            setStatus('idle');
            alert("Failed to generate question. Please try again.");
        }
    };

    const playTTS = (text) => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        window.speechSynthesis.speak(utterance);
    };

    const startRecording = async () => {
        try {
            navigator.mediaDevices.getUserMedia({ audio: true })
              .then(() => console.log("Mic works"))
              .catch(err => console.error("Mic blocked", err));

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream, {
              mimeType: "audio/webm"
            });
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                console.log("Chunk size:", e.data.size);
                if (e.data.size > 0) {
                    audioChunksRef.current.push(e.data);
                }
            };

            mediaRecorder.onstop = processAudio;
            mediaRecorder.start();
            
            setRecordingTime(0);
            setStatus('recording');
        } catch (err) {
            console.error("Microphone access denied:", err);
            alert("Microphone access is required for Viva mode.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
    };

    const processAudio = async () => {
        setStatus('evaluating');
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        const file = new File([audioBlob], 'answer.webm', { type: 'audio/webm' });
        
        const formData = new FormData();
        formData.append('audio', file);
        formData.append('question', questionData.question);
        formData.append('ideal_answer', questionData.ideal_answer);

        try {
            const res = await axios.post(`${BACKEND_URL}/viva-evaluate`, formData);
            setEvaluation(res.data);
            setStatus('result');
            console.log("Response:", res.data);
        } catch (e) {
            console.error("FULL ERROR:", e);
            setStatus('ready');
            alert("Evaluation failed. Check console for FULL ERROR.");
        }
    };

    const resetState = () => {
        setStatus('idle');
        setQuestionData(null);
        setEvaluation(null);
    };

    const formatTime = (seconds) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    };

    return (
        <div className="max-w-4xl mx-auto h-full flex flex-col items-center overflow-y-auto w-full pb-32 px-4 scrollbar-hide">
            
            {/* Header Area */}
            {status === 'idle' && (
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-xl glass-card p-8 rounded-3xl mt-12 mb-8 bg-dark-800/60 border border-white/5 shadow-2xl relative flex flex-col items-center"
                >
                    <div className="absolute top-0 right-0 w-32 h-32 bg-accent-purple/20 rounded-full blur-3xl -z-10" />
                    <div className="absolute bottom-0 left-0 w-32 h-32 bg-accent-blue/20 rounded-full blur-3xl -z-10" />
                    
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-purple/20 to-accent-blue/20 flex items-center justify-center mb-6">
                        <Mic className="w-8 h-8 text-accent-purple" />
                    </div>
                    
                    <h2 className="text-2xl font-display font-bold text-white mb-2">Start an AI Viva</h2>
                    <p className="text-gray-400 text-center mb-8">Select a topic below. The AI will generate a thought-provoking oral exam question and instantly evaluate your spoken answer.</p>

                    <div className="w-full space-y-4">
                        <select 
                            className="w-full bg-dark-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-accent-purple outline-none appearance-none cursor-pointer"
                            value={selectedSubjectId}
                            onChange={(e) => {
                                setSelectedSubjectId(e.target.value);
                                setSelectedTopicId('');
                            }}
                        >
                            <option value="">Select a Subject...</option>
                            {subjects.map(s => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>

                        <select 
                            className="w-full bg-dark-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-accent-purple outline-none appearance-none cursor-pointer"
                            value={selectedTopicId}
                            onChange={(e) => setSelectedTopicId(e.target.value)}
                            disabled={!selectedSubjectId}
                        >
                            <option value="">Select a Topic...</option>
                            {topics.map(t => (
                                <option key={t.id} value={t.id}>{t.title}</option>
                            ))}
                        </select>

                        <button 
                            onClick={handleGenerate}
                            disabled={!selectedTopicId}
                            className="w-full disabled:opacity-50 disabled:cursor-not-allowed bg-white text-dark-950 font-bold py-3.5 rounded-xl hover:bg-gray-100 transition-colors mt-4 flex justify-center items-center gap-2"
                        >
                            <Sparkles className="w-4 h-4" />
                            Start Viva Session
                        </button>
                    </div>
                </motion.div>
            )}

            {/* Interaction Area */}
            <AnimatePresence mode="wait">
                {(status === 'generating' || status === 'evaluating') && (
                    <motion.div 
                        key="loader"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="flex-1 flex flex-col items-center justify-center -mt-20"
                    >
                        <div className="w-20 h-20 relative flex items-center justify-center">
                            <div className="absolute inset-0 border-4 border-accent-purple/20 rounded-full"></div>
                            <motion.div 
                                className="absolute inset-0 border-4 border-accent-purple rounded-full border-t-transparent"
                                animate={{ rotate: 360 }}
                                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                            />
                            {status === 'generating' ? <Brain className="w-8 h-8 text-accent-purple" /> : <RefreshCw className="w-8 h-8 text-accent-purple" />}
                        </div>
                        <h3 className="text-xl font-bold text-white mt-6">
                            {status === 'generating' ? "Crafting question..." : "Analyzing answer..."}
                        </h3>
                    </motion.div>
                )}

                {(status === 'ready' || status === 'recording') && questionData && (
                    <motion.div 
                        key="interaction"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="w-full max-w-3xl flex flex-col items-center mt-12 gap-8"
                    >
                        {/* Question Card */}
                        <div className="glass-card w-full p-8 rounded-3xl bg-dark-800/80 border border-white/5 relative group hover:border-white/10 transition-colors">
                            <div className="flex justify-between items-start gap-4 mb-4">
                                <span className="px-3 py-1 bg-accent-blue/10 text-accent-blue rounded-full text-xs font-semibold tracking-wider uppercase">Viva Question</span>
                                <button 
                                    onClick={() => playTTS(questionData.question)}
                                    className="p-2 rounded-full bg-dark-900 text-gray-400 hover:text-white transition-colors"
                                >
                                    <Volume2 className="w-5 h-5" />
                                </button>
                            </div>
                            <h2 className="text-3xl font-display font-medium text-white leading-tight">
                                {questionData.question}
                            </h2>
                        </div>

                        {/* Controls */}
                        <div className="flex flex-col items-center gap-6 mt-8">
                            <AnimatePresence mode="popLayout">
                                {status === 'recording' && (
                                    <motion.div 
                                        initial={{ opacity: 0, scale: 0.5 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.5 }}
                                        className="flex items-center gap-4 bg-red-500/10 text-red-400 px-6 py-2 rounded-full border border-red-500/20"
                                    >
                                        <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                                        <span className="font-mono font-bold font-lg tabular-nums tracking-widest">{formatTime(recordingTime)}</span>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            <button
                                onClick={status === 'recording' ? stopRecording : startRecording}
                                className={`w-20 h-20 rounded-full flex items-center justify-center transition-all ${
                                    status === 'recording' 
                                    ? 'bg-red-500 hover:bg-red-600 shadow-[0_0_30px_rgba(239,68,68,0.4)]' 
                                    : 'bg-white hover:scale-105 hover:bg-gray-100 shadow-[0_0_40px_rgba(255,255,255,0.15)]'
                                }`}
                            >
                                {status === 'recording' 
                                    ? <Square className="w-8 h-8 text-white fill-current" /> 
                                    : <Mic className="w-8 h-8 text-dark-950" />
                                }
                            </button>
                            
                            <p className="text-gray-400 font-medium tracking-wide">
                                {status === 'recording' ? 'Tap to finish answering' : 'Hold to record or tap to start'}
                            </p>
                        </div>
                    </motion.div>
                )}

                {status === 'result' && evaluation && (
                    <motion.div
                        key="result"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-3 gap-6 pt-6 pb-20"
                    >
                        {/* Left column - Score & Actions */}
                        <div className="glass-card rounded-3xl p-6 bg-dark-800/80 border border-white/5 flex flex-col items-center justify-center text-center">
                            <div className="relative w-32 h-32 flex items-center justify-center mb-4">
                                <svg width="128" height="128" className="rotate-[-90deg]">
                                    <circle cx="64" cy="64" r="58" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="12" />
                                    <motion.circle 
                                        cx="64" cy="64" r="58" fill="none" 
                                        stroke={evaluation.score >= 8 ? '#10B981' : evaluation.score >= 5 ? '#F59E0B' : '#EF4444'} 
                                        strokeWidth="12" 
                                        strokeLinecap="round"
                                        initial={{ strokeDasharray: "364", strokeDashoffset: "364" }}
                                        animate={{ strokeDashoffset: 364 - (364 * evaluation.score) / 10 }}
                                        transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
                                    />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-4xl font-black text-white">{evaluation.score}</span>
                                    <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider">/ 10</span>
                                </div>
                            </div>
                            <h3 className="text-xl font-bold text-white mb-8">
                                {evaluation.score >= 8 ? "Excellent!" : evaluation.score >= 5 ? "Good Effort" : "Needs Review"}
                            </h3>

                            <button onClick={resetState} className="w-full bg-white/10 hover:bg-white/20 text-white px-4 py-3 rounded-xl font-semibold transition-colors flex items-center justify-center gap-2">
                                <RefreshCw className="w-4 h-4" /> Try Another
                            </button>
                        </div>

                        {/* Right column - Feedback chunks */}
                        <div className="md:col-span-2 flex flex-col gap-4">
                            {/* Professor Analysis */}
                            <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-accent-purple/10 to-transparent border border-accent-purple/20 shadow-inner">
                                <h4 className="text-sm font-bold text-accent-purple tracking-wide flex items-center gap-2 mb-3">
                                    <Sparkles className="w-4 h-4" /> Professor's Analysis
                                </h4>
                                <p className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
                                    {evaluation.analysis}
                                </p>
                            </div>

                            {/* Transcription */}
                            <div className="glass-card rounded-2xl p-5 bg-dark-800/60 border border-white/5">
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Transcribed Answer</h4>
                                <p className="text-gray-200 text-sm italic leading-relaxed">{evaluation.transcription || "[No clear audio detected]"}</p>
                            </div>

                            {/* Good Points */}
                            {evaluation.good_points?.length > 0 && (
                                <div className="glass-card rounded-2xl p-5 border border-emerald-500/20 bg-emerald-500/5">
                                    <h4 className="flex items-center gap-2 text-sm font-bold text-emerald-400 mb-3">
                                        <CheckCircle className="w-4 h-4" /> What You Did Well
                                    </h4>
                                    <ul className="space-y-2">
                                        {evaluation.good_points.map((p, i) => (
                                            <li key={i} className="text-emerald-100 flex items-start gap-2 text-sm">
                                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                                                {p}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Missing or Mistakes */}
                            {(evaluation.missing_points?.length > 0 || evaluation.mistakes?.length > 0) && (
                                <div className="glass-card rounded-2xl p-5 border border-red-500/20 bg-red-500/5">
                                    {evaluation.mistakes?.length > 0 && (
                                        <div className="mb-4">
                                            <h4 className="flex items-center gap-2 text-sm font-bold text-red-400 mb-3">
                                                <XCircle className="w-4 h-4" /> Mistakes
                                            </h4>
                                            <ul className="space-y-2">
                                                {evaluation.mistakes.map((p, i) => (
                                                    <li key={i} className="text-red-100 flex items-start gap-2 text-sm">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 flex-shrink-0" />
                                                        {p}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    
                                    {evaluation.missing_points?.length > 0 && (
                                        <div>
                                            <h4 className="flex items-center gap-2 text-sm font-bold text-orange-400 mb-3">
                                                <AlertCircle className="w-4 h-4" /> Missing Points
                                            </h4>
                                            <ul className="space-y-2">
                                                {evaluation.missing_points.map((p, i) => (
                                                    <li key={i} className="text-orange-100 flex items-start gap-2 text-sm">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-orange-400 mt-1.5 flex-shrink-0" />
                                                        {p}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Suggestions */}
                            {evaluation.suggestions?.length > 0 && (
                                <div className="glass-card rounded-2xl p-5 border border-accent-blue/20 bg-accent-blue/5">
                                    <h4 className="text-sm font-bold text-accent-blue mb-3">Suggestions for Next Time</h4>
                                    <ul className="space-y-2 text-gray-300 text-sm">
                                        {evaluation.suggestions.map((p, i) => <li key={i}>• {p}</li>)}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
