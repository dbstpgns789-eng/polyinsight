'use client';

import { useState } from 'react';
import Link from 'next/link';
import useUiStore from '@/store/uiStore';
import { IconEdit, IconDownload, IconRefresh, IconWarning } from '@/components/ui/Icons';

type Status = 'done' | 'draft' | 'processing' | 'failed';
type FilterStatus = 'all' | Status;
type SortKey = 'newest' | 'oldest' | 'name';

interface Project {
  id: string;
  title: string;
  filename: string;
  date: string;
  cardCount: number;
  status: Status;
  processingStep?: string;
  processingPercent?: number;
  failedReason?: string;
}

const MOCK_PROJECTS: Project[] = [
  {
    id: 'job-001',
    title: '스마트팜 기반 식물 생장 최적화 연구',
    filename: 'kim2024_smartfarm_review.pdf',
    date: '2026.05.18',
    cardCount: 5,
    status: 'done',
  },
  {
    id: 'job-002',
    title: '탄소 포집 기술의 경제성 분석 및 상용화 전망',
    filename: 'lee2024_carbon_capture_econ.pdf',
    date: '2026.05.17',
    cardCount: 5,
    status: 'done',
  },
  {
    id: 'job-003',
    title: '수소 연료전지 내구성 실증 연구',
    filename: 'park2026_hydrogen_fuel_durability.pdf',
    date: '2026.05.16',
    cardCount: 5,
    status: 'draft',
  },
  {
    id: 'job-004',
    title: '초고강도 강재 레이저 용접 특성 평가',
    filename: 'choi2026_laser_welding_steel.pdf',
    date: '2026.05.20',
    cardCount: 5,
    status: 'processing',
    processingStep: '핵심 내용 분석 중...',
    processingPercent: 65,
  },
  {
    id: 'job-005',
    title: '세라믹 소재 고온 기계적 특성 분석',
    filename: 'jung2025_ceramic_hightemp.pdf',
    date: '2026.05.15',
    cardCount: 5,
    status: 'failed',
    failedReason: '스캔 PDF는 처리할 수 없습니다.',
  },
];

const STATUS_LABELS: Record<Status, string> = {
  done: '완성',
  draft: '임시저장',
  processing: '처리중',
  failed: '실패',
};

const FILTER_LABELS: Record<FilterStatus, string> = {
  all: '전체 상태',
  done: '완성',
  draft: '임시저장',
  processing: '처리중',
  failed: '실패',
};

const FILTER_EMPTY: Record<FilterStatus, string> = {
  all: '',
  done: '완성된 카드뉴스가 없습니다.',
  draft: '임시저장된 프로젝트가 없습니다.',
  processing: '처리 중인 프로젝트가 없습니다.',
  failed: '실패한 프로젝트가 없습니다.',
};

export default function DashboardV2Page() {
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [sort, setSort] = useState<SortKey>('newest');
  const { openUploadModal } = useUiStore();

  const projects = MOCK_PROJECTS;
  const isEmpty = projects.length === 0;

  const counts = {
    all: projects.length,
    done: projects.filter(p => p.status === 'done').length,
    draft: projects.filter(p => p.status === 'draft').length,
    processing: projects.filter(p => p.status === 'processing').length,
    failed: projects.filter(p => p.status === 'failed').length,
  };

  const filtered = projects.filter(p => filter === 'all' || p.status === filter);
  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'name') return a.title.localeCompare(b.title, 'ko');
    const da = a.date.replace(/\./g, '');
    const db = b.date.replace(/\./g, '');
    return sort === 'oldest' ? da.localeCompare(db) : db.localeCompare(da);
  });

  return (
    <div className="dash-v2">
      <div className="dash-v2__head">
        <h1 className="dash-v2__title">내 카드뉴스</h1>
        {!isEmpty && (
          <p className="dash-v2__summary" aria-label="프로젝트 현황">
            <span className="dash-v2__summary-item">{counts.all}개 프로젝트</span>
            {counts.done > 0 && (
              <>
                <span className="dash-v2__summary-sep" aria-hidden="true">·</span>
                <span className="dash-v2__summary-item">완성 {counts.done}</span>
              </>
            )}
            {counts.draft > 0 && (
              <>
                <span className="dash-v2__summary-sep" aria-hidden="true">·</span>
                <span className="dash-v2__summary-item">임시저장 {counts.draft}</span>
              </>
            )}
            {counts.processing > 0 && (
              <>
                <span className="dash-v2__summary-sep" aria-hidden="true">·</span>
                <span className="dash-v2__summary-item">처리중 {counts.processing}</span>
              </>
            )}
          </p>
        )}
      </div>

      {isEmpty ? (
        <div className="dash-empty">
          <svg
            className="dash-empty__icon"
            width="52" height="52" viewBox="0 0 52 52"
            fill="none" aria-hidden="true"
          >
            <rect x="6" y="8" width="36" height="30" rx="4" stroke="currentColor" strokeWidth="1.6"/>
            <path d="M14 20h20M14 27h13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
            <circle cx="41" cy="41" r="9" fill="var(--surface)" stroke="currentColor" strokeWidth="1.6"/>
            <path d="M37.5 41h7M41 37.5v7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
          <h2 className="dash-empty__title">첫 논문을 업로드하세요</h2>
          <p className="dash-empty__desc">PDF를 올리면 카드뉴스를 자동으로 만들어 드립니다.</p>
          <button className="btn btn-primary" onClick={openUploadModal}>
            새 카드뉴스 만들기
          </button>
        </div>
      ) : (
        <>
          <div className="dash-v2__toolbar">
            <select
              className="dash-v2__select"
              value={filter}
              onChange={e => setFilter(e.target.value as FilterStatus)}
              aria-label="상태 필터"
            >
              {(['all', 'done', 'draft', 'processing', 'failed'] as FilterStatus[]).map(f => (
                <option key={f} value={f}>
                  {FILTER_LABELS[f]}{f !== 'all' ? ` (${counts[f]})` : ''}
                </option>
              ))}
            </select>

            <select
              className="dash-v2__select"
              value={sort}
              onChange={e => setSort(e.target.value as SortKey)}
              aria-label="정렬 기준"
            >
              <option value="newest">최신순</option>
              <option value="oldest">오래된 순</option>
              <option value="name">이름순</option>
            </select>
          </div>

          <div className="proj-list" role="list" aria-label="프로젝트 목록">
            {sorted.length === 0 ? (
              <p className="dash-filter-empty" role="status">
                {FILTER_EMPTY[filter]}
              </p>
            ) : (
              sorted.map(project => (
                <ProjectRow key={project.id} project={project} />
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: Status }) {
  if (status === 'done') {
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <circle cx="9" cy="9" r="7.5" stroke="currentColor" strokeWidth="1.3"/>
        <path d="M5.5 9l2.5 2.5 4.5-4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
  }
  if (status === 'draft') {
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <circle cx="9" cy="9" r="7.5" stroke="currentColor" strokeWidth="1.3" strokeDasharray="3 2"/>
      </svg>
    );
  }
  if (status === 'processing') {
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" className="icon-spin">
        <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.3" strokeOpacity="0.2"/>
        <path d="M9 2a7 7 0 0 1 7 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    );
  }
  return <IconWarning size={16} aria-hidden="true" />;
}

function ProjectRow({ project }: { project: Project }) {
  return (
    <article
      className={`proj-row${project.status === 'processing' ? ' is-processing' : ''}`}
      role="listitem"
    >
      <div className={`proj-row__icon proj-row__icon--${project.status}`}>
        <StatusIcon status={project.status} />
      </div>

      <div className="proj-row__body">
        <p className="proj-row__title">{project.title}</p>

        {project.status === 'processing' ? (
          <div className="proj-row__progress" aria-label={`진행률 ${project.processingPercent}%`}>
            <span className="proj-row__progress-label">{project.processingStep}</span>
            <div className="proj-row__progress-track" aria-hidden="true">
              <div
                className="proj-row__progress-fill"
                style={{ width: `${project.processingPercent ?? 0}%` }}
              />
            </div>
          </div>
        ) : project.status === 'failed' ? (
          <p className="proj-row__sub proj-row__sub--error">{project.failedReason}</p>
        ) : (
          <p className="proj-row__sub">{project.filename}</p>
        )}
      </div>

      <div className="proj-row__right">
        <p className="proj-row__meta">
          <time dateTime={project.date.replace(/\./g, '-')}>{project.date}</time>
          <span aria-hidden="true">·</span>
          <span>{project.cardCount}장</span>
        </p>

        {project.status !== 'processing' && (
          <div className="proj-row__actions">
            {project.status === 'done' && (
              <>
                <Link href={`/editor/${project.id}`} className="proj-row__btn proj-row__btn--primary">
                  <IconEdit size={11} />
                  수정하기
                </Link>
                <Link href={`/editor/${project.id}?export=1`} className="proj-row__btn">
                  <IconDownload size={11} />
                  다운로드
                </Link>
              </>
            )}
            {project.status === 'draft' && (
              <Link href={`/editor/${project.id}`} className="proj-row__btn proj-row__btn--primary">
                이어하기
              </Link>
            )}
            {project.status === 'failed' && (
              <button className="proj-row__btn proj-row__btn--danger">
                <IconRefresh size={11} />
                재시도
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
