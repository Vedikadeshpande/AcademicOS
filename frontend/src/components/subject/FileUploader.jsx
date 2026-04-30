import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, CheckCircle, AlertCircle, Trash2 } from 'lucide-react';
import { uploadFile, getUploads, deleteUpload } from '../../lib/api';

/**
 * File uploader with drag-and-drop support + shows existing uploads.
 */
export default function FileUploader({ subjectId, onUploadComplete }) {
    const [isDragging, setIsDragging] = useState(false);
    const [pendingUploads, setPendingUploads] = useState([]); // In-progress uploads
    const [existingFiles, setExistingFiles] = useState([]);   // Persisted uploads from backend
    const [fileType, setFileType] = useState('pdf');

    // Load existing uploads from backend
    useEffect(() => {
        loadExistingFiles();
    }, [subjectId]);

    const loadExistingFiles = async () => {
        try {
            const res = await getUploads(subjectId);
            setExistingFiles(res.data || []);
        } catch (err) {
            console.error('Failed to load uploads:', err);
        }
    };

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback(() => setIsDragging(false), []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);
        const files = Array.from(e.dataTransfer.files);
        processFiles(files);
    }, [fileType, subjectId]);

    const handleFileSelect = (e) => {
        const files = Array.from(e.target.files);
        processFiles(files);
    };

    const processFiles = async (files) => {
        for (const file of files) {
            const ext = file.name.split('.').pop().toLowerCase();
            const type = ext === 'pdf' ? 'pdf' : (ext === 'pptx' || ext === 'ppt') ? 'ppt' : fileType;

            const uploadEntry = {
                id: Date.now() + Math.random(),
                name: file.name,
                status: 'uploading',
                fileType: type,
            };

            setPendingUploads((prev) => [...prev, uploadEntry]);

            try {
                await uploadFile(subjectId, type, file);
                setPendingUploads((prev) =>
                    prev.filter((u) => u.id !== uploadEntry.id)
                );
                // Refresh the existing files list from backend
                await loadExistingFiles();
                onUploadComplete?.();
            } catch (err) {
                setPendingUploads((prev) =>
                    prev.map((u) => u.id === uploadEntry.id ? { ...u, status: 'error' } : u)
                );
            }
        }
    };

    return (
        <div className="space-y-4">
            {/* File type selector */}
            <div className="flex gap-2">
                {['pdf', 'ppt', 'pyq'].map((t) => (
                    <button
                        key={t}
                        onClick={() => setFileType(t)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition-all
                        ${fileType === t
                                ? 'bg-accent-purple/20 text-accent-purple border border-accent-purple/30'
                                : 'glass-card text-gray-400 hover:text-gray-300'}`}
                    >
                        {t === 'pyq' ? 'PYQ Paper' : t.toUpperCase()}
                    </button>
                ))}
            </div>

            {/* Drop zone */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`relative border-2 border-dashed rounded-2xl p-8 text-center
                     transition-all duration-300 cursor-pointer
                     ${isDragging
                        ? 'border-accent-purple/60 bg-accent-purple/5'
                        : 'border-white/[0.1] hover:border-white/[0.2] hover:bg-white/[0.02]'}`}
                onClick={() => document.getElementById('file-input').click()}
            >
                <input
                    id="file-input"
                    type="file"
                    multiple
                    accept=".pdf,.pptx,.ppt"
                    onChange={handleFileSelect}
                    className="hidden"
                />
                <Upload className={`w-10 h-10 mx-auto mb-3 transition-colors
                           ${isDragging ? 'text-accent-purple' : 'text-gray-500'}`} />
                <p className="text-sm text-gray-400 mb-1">
                    Drop files here or <span className="text-accent-purple font-medium">browse</span>
                </p>
                <p className="text-xs text-gray-600">PDF, PPTX files supported</p>
            </div>

            {/* In-progress uploads */}
            <AnimatePresence>
                {pendingUploads.map((u) => (
                    <motion.div
                        key={u.id}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="flex items-center gap-3 px-4 py-3 rounded-xl glass-card"
                    >
                        <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <span className="text-sm text-gray-300 flex-1 truncate">{u.name}</span>
                        <span className="text-xs uppercase tracking-wider text-gray-500">{u.fileType}</span>
                        {u.status === 'uploading' && (
                            <div className="w-4 h-4 border-2 border-accent-purple border-t-transparent rounded-full animate-spin" />
                        )}
                        {u.status === 'error' && <AlertCircle className="w-4 h-4 text-red-400" />}
                    </motion.div>
                ))}
            </AnimatePresence>

            {/* Existing uploaded files from backend */}
            {existingFiles.length > 0 && (
                <div className="space-y-1.5">
                    <h4 className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                        {existingFiles.length} file{existingFiles.length !== 1 ? 's' : ''} uploaded
                    </h4>
                    {existingFiles.map((u) => (
                        <div key={u.id} className="group/file flex items-center gap-3 px-3 py-2.5 rounded-xl
                               bg-dark-700/40 border border-white/[0.04]">
                            <FileText className="w-4 h-4 text-gray-400" />
                            <div className="flex-1 min-w-0">
                                <p className="text-sm text-gray-300 truncate">{u.filename}</p>
                                <p className="text-xs text-gray-600">{u.file_type?.toUpperCase()}</p>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-full
                                ${u.status === 'done' ? 'bg-green-500/15 text-green-400' :
                                    u.status === 'processing' ? 'bg-yellow-500/15 text-yellow-400' :
                                        'bg-red-500/15 text-red-400'}`}>
                                {u.status}
                            </span>
                            <button
                                onClick={async () => {
                                    try {
                                        await deleteUpload(u.id);
                                        await loadExistingFiles();
                                        onUploadComplete?.();
                                    } catch (err) {
                                        console.error('Failed to delete upload:', err);
                                    }
                                }}
                                className="p-1 rounded-lg text-gray-600 hover:text-red-400
                                    hover:bg-red-500/10 transition-all opacity-0 group-hover/file:opacity-100"
                                title="Delete file"
                            >
                                <Trash2 className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
