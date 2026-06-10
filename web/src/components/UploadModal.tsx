'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { uploadPdf, getStatus } from '@/lib/api';

type ModalState = 'idle' | 'file-selected' | 'processing' | 'done' | 'error';
type StepStatus = 'pending' | 'active' | 'done';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

const STEP_NAMES = ['텍스트 추출', 'AI 카드뉴스 생성', '렌더링 및 저장'];

// 백엔드 stage → 단계 인덱스 (0,1,2)
function stageToStepIndex(stage: string | null): number {
  if (!stage) return -1;
  if (stage === 'S1' || stage === 'S2') return 0;
  if (stage === 'S6') return 1;
  if (stage === 'S7' || stage === 'S8') return 2;
  return -1;
}

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith('.pdf')) return 'PDF 파일만 업로드할 수 있습니다.';
  const mb = file.size / (1024 * 1024);
  if (mb > 50) return `파일 크기가 50MB를 초과합니다. (${mb.toFixed(1)}MB)`;
  return null;
}

export default function UploadModal({ isOpen, onClose }: Props) {
  const router = useRouter();
  const [state, setState] = useState<ModalState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState('');
  const [cardCount, setCardCount] = useState(7);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stepStatuses, setStepStatuses] = useState<StepStatus[]>(['pending', 'pending', 'pending']);
  const [stepTags, setStepTags] = useState(['', '', '']);
  const [procTitle, setProcTitle] = useState('카드뉴스 생성');
  const [errorMsg, setErrorMsg] = useState('');

  const cardRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const jobIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    document.body.style.overflow = 'hidden';
    setTimeout(() => cardRef.current?.focus(), 40);

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') { handleClose(); return; }
      if (e.key !== 'Tab' || !cardRef.current) return;
      const focusable = Array.from(
        cardRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      ).filter(el => !el.closest('[hidden]') && el.offsetParent !== null);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => { window.removeEventListener('keydown', onKeyDown); document.body.style.overflow = ''; };
  }, [isOpen, state]);

  // 언마운트 시 폴링 정리
  useEffect(() => {
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, []);

  function handleClose() {
    if (state === 'processing') return;
    if (pollRef.current) clearTimeout(pollRef.current);
    onClose();
    setTimeout(resetAll, 230);
  }

  function resetAll() {
    if (pollRef.current) { clearTimeout(pollRef.current); pollRef.current = null; }
    jobIdRef.current = null;
    setState('idle');
    setSelectedFile(null);
    setFileError('');
    setErrorMsg('');
    setCardCount(5);
    setDragOver(false);
    setProgress(0);
    setStepStatuses(['pending', 'pending', 'pending']);
    setStepTags(['', '', '']);
    setProcTitle('카드뉴스 생성');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function handleFile(file: File | null) {
    if (!file) return;
    const err = validateFile(file);
    if (err) { setFileError(err); setSelectedFile(null); return; }
    setFileError('');
    setSelectedFile(file);
    setState('file-selected');
  }

  function applyStatus(status: string, stage: string | null, serverProgress: number) {
    const pct = serverProgress ?? 0;
    setProgress(pct);

    const stepIdx = stageToStepIndex(stage);

    if (status === 'DONE') {
      setProgress(100);
      setStepStatuses(['done', 'done', 'done']);
      setStepTags(['완료', '완료', '완료']);
      setProcTitle('카드뉴스 생성 완료!');
      setState('done');
      return;
    }

    if (status === 'FAILED' || status === 'ERROR') {
      const failIdx = Math.max(stepIdx, 0);
      setStepStatuses(prev => {
        const next = [...prev] as StepStatus[];
        for (let i = 0; i < failIdx; i++) next[i] = 'done';
        next[failIdx] = 'active';
        return next;
      });
      setProcTitle('처리 중 오류 발생');
      setState('error');
      return;
    }

    // RUNNING / PENDING
    setStepStatuses(prev => {
      const next = [...prev] as StepStatus[];
      for (let i = 0; i < stepIdx; i++) next[i] = 'done';
      if (stepIdx >= 0) next[stepIdx] = 'active';
      return next;
    });
    setStepTags(prev => {
      const next = [...prev];
      for (let i = 0; i < stepIdx; i++) next[i] = '완료';
      if (stepIdx >= 0) next[stepIdx] = '진행 중';
      return next;
    });
  }

  async function pollStatus(jobId: string) {
    try {
      const { data } = await getStatus(jobId);
      applyStatus(data.status, data.stage, data.progress);

      if (data.status === 'DONE' || data.status === 'FAILED') return;

      pollRef.current = setTimeout(() => pollStatus(jobId), 2000);
    } catch {
      setState('error');
      setErrorMsg('상태 확인 중 오류가 발생했습니다.');
    }
  }

  async function startProcessing() {
    if (!selectedFile) return;
    setState('processing');
    setProgress(0);
    setStepStatuses(['active', 'pending', 'pending']);
    setStepTags(['진행 중', '대기 중', '대기 중']);
    setProcTitle('카드뉴스 생성 중…');
    setErrorMsg('');

    try {
      const { data } = await uploadPdf(selectedFile, cardCount);
      const jobId: string = data.jobId;
      jobIdRef.current = jobId;
      pollRef.current = setTimeout(() => pollStatus(jobId), 2000);
    } catch (err) {
      setState('error');
      setErrorMsg(err instanceof Error ? err.message : '업로드 중 오류가 발생했습니다.');
    }
  }

  const sliderPct = ((cardCount - 3) / 4) * 100;
  const isProcessingView = state === 'processing' || state === 'done' || state === 'error';

  if (!isOpen && state === 'idle') return null;

  return (
    <div
      className={`modal-overlay${isOpen ? ' is-open' : ''}`}
      aria-hidden={!isOpen}
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
    >
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        ref={cardRef}
      >

        {/* Upload / File Selected view */}
        {!isProcessingView && (
          <div>
            <div className="modal-header">
              <h2 className="modal-title" id="modal-title">카드뉴스 생성</h2>
              <button className="modal-close" aria-label="모달 닫기" onClick={handleClose}>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                  <path d="M3 3l12 12M15 3L3 15" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
                </svg>
              </button>
            </div>

            <div className="modal-body">
              {state === 'idle' && (
                <div
                  className={`upload-zone${dragOver ? ' drag-over' : ''}`}
                  role="button"
                  tabIndex={0}
                  aria-label="PDF 파일 선택 — 클릭 또는 드래그&드롭"
                  aria-describedby="zone-hint"
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputRef.current?.click(); } }}
                  onDragEnter={(e) => { e.preventDefault(); dragCounterRef.current++; setDragOver(true); }}
                  onDragLeave={() => { dragCounterRef.current--; if (dragCounterRef.current <= 0) { dragCounterRef.current = 0; setDragOver(false); } }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); dragCounterRef.current = 0; setDragOver(false); handleFile(e.dataTransfer?.files[0] ?? null); }}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    accept=".pdf"
                    style={{ display: 'none' }}
                    aria-hidden="true"
                    tabIndex={-1}
                    onChange={() => handleFile(fileInputRef.current?.files?.[0] ?? null)}
                  />
                  <svg className="upload-zone__icon" width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
                    <rect x="8" y="3" width="20" height="27" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M22 3v8h6" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                    <path d="M20 23v-8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    <path d="M16 19l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  <p className="upload-zone__main">PDF 파일을 드래그하거나 클릭해서 선택</p>
                  <p className="upload-zone__hint" id="zone-hint">최대 50MB · PDF 형식만 허용</p>
                  <p className="upload-zone__drop-text" aria-hidden="true">여기에 놓으세요</p>
                </div>
              )}

              {state === 'file-selected' && selectedFile && (
                <div className="file-chip">
                  <svg width="20" height="22" viewBox="0 0 20 22" fill="none" aria-hidden="true">
                    <rect x="2" y="1" width="13" height="18" rx="1.5" stroke="currentColor" strokeWidth="1.25"/>
                    <path d="M10 1v6h5" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round"/>
                    <line x1="5" y1="10" x2="10" y2="10" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
                    <line x1="5" y1="13" x2="13" y2="13" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
                  </svg>
                  <div className="file-chip__info">
                    <p className="file-chip__name">{selectedFile.name}</p>
                    <p className="file-chip__size">{(selectedFile.size / (1024 * 1024)).toFixed(1)} MB</p>
                  </div>
                  <button
                    className="file-chip__remove"
                    aria-label="파일 제거"
                    onClick={() => { setSelectedFile(null); setState('idle'); setFileError(''); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                  >
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                      <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    </svg>
                  </button>
                </div>
              )}

              {fileError && (
                <p className="file-error" role="alert" aria-live="assertive">{fileError}</p>
              )}

              <div className="card-count">
                <div className="card-count__header">
                  <label className="card-count__label" htmlFor="card-slider">카드 수</label>
                  <span className="card-count__output">{cardCount}장</span>
                </div>
                <input
                  type="range"
                  id="card-slider"
                  className="card-slider"
                  min={3}
                  max={7}
                  value={cardCount}
                  step={1}
                  style={{ '--pct': `${sliderPct.toFixed(2)}%` } as React.CSSProperties}
                  onChange={(e) => setCardCount(parseInt(e.target.value, 10))}
                />
                <div className="card-count__range-labels" aria-hidden="true">
                  <span>3장 (간결)</span>
                  <span>7장 (상세)</span>
                </div>
              </div>

              <button
                className="btn btn-primary btn-lg modal-submit"
                disabled={state !== 'file-selected'}
                aria-disabled={state !== 'file-selected'}
                onClick={startProcessing}
              >
                카드뉴스 생성 시작
              </button>
            </div>
          </div>
        )}

        {/* Processing / Done / Error view */}
        {isProcessingView && (
          <div>
            <div className="modal-header modal-header--locked">
              <h2 className="modal-title" id="modal-title">{procTitle}</h2>
            </div>

            <div className="modal-body">
              <div className="pipeline">
                <div className="pipeline__meta">
                  <span className="pipeline__label">파이프라인 진행 중</span>
                  <span className="pipeline__pct" aria-live="polite">{Math.round(progress)}%</span>
                </div>
                <div
                  className="pipeline__bar"
                  role="progressbar"
                  aria-label="처리 진행률"
                  aria-valuenow={Math.round(progress)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div className="pipeline__fill" style={{ width: `${progress.toFixed(1)}%` }} />
                </div>

                <ol className="pipeline-steps" aria-label="처리 단계">
                  {STEP_NAMES.map((name, i) => (
                    <li key={i} className="pipeline-step" data-status={stepStatuses[i]}>
                      <span className="ps-dot" aria-hidden="true" />
                      <span className="ps-name">{name}</span>
                      <span className="ps-tag">{stepTags[i]}</span>
                    </li>
                  ))}
                </ol>
              </div>

              {state === 'done' && jobIdRef.current && (
                <button
                  className="btn btn-primary btn-lg editor-btn"
                  onClick={() => { handleClose(); router.push(`/editor/${jobIdRef.current}`); }}
                >
                  카드 에디터 열기 →
                </button>
              )}

              {state === 'error' && (
                <div className="proc-error">
                  <p className="proc-error__title">처리 중 오류가 발생했습니다.</p>
                  <p className="proc-error__desc">{errorMsg || 'PDF 파일을 확인하고 다시 시도해주세요.'}</p>
                  <div className="proc-error__actions">
                    <button className="btn btn-outline" onClick={handleClose}>닫기</button>
                    <button className="btn btn-primary" onClick={resetAll}>다시 시도</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
