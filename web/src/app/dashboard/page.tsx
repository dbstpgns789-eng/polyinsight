'use client';

import { useState } from 'react';
import Link from 'next/link';
import useUiStore from '@/store/uiStore';
import {
  IconEdit, IconDownload, IconRefresh, IconWarning,
  IconTrash, IconSearch,
} from '@/components/ui/Icons';

type Status = 'done' | 'draft' | 'processing' | 'failed';
type FilterTab = 'all' | Status;
type SortKey = 'newest' | 'oldest' | 'name';

interface Project {
  id: string;
  title: string;
  filename: string;
  date: string;
  cardCount: number;
  ratio: string;
  status: Status;
  thumbnailUrl?: string;
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
    ratio: '1:1',
    status: 'done',
  },
  {
    id: 'job-002',
    title: '탄소 포집 기술의 경제성 분석 및 상용화 전망',
    filename: 'lee2024_carbon_capture_econ.pdf',
    date: '2026.05.17',
    cardCount: 5,
    ratio: '1:1',
    status: 'done',
  },
  {
    id: 'job-003',
    title: '수소 연료전지 내구성 실증 연구',
    filename: 'park2026_hydrogen_fuel_durability.pdf',
    date: '2026.05.16',
    cardCount: 5,
    ratio: '1:1',
    status: 'draft',
  },
  {
    id: 'job-004',
    title: '초고강도 강재 레이저 용접 특성 평가',
    filename: 'choi2026_laser_welding_steel.pdf',
    date: '2026.05.20',
    cardCount: 5,
    ratio: '1:1',
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
    ratio: '1:1',
    status: 'failed',
    failedReason: '스캔 PDF는 처리할 수 없습니다.',
  },
];

const FILTER_LABELS: Record<FilterTab, string> = {
  all: '전체',
  done: '완성',
  draft: '임시저장',
  processing: '처리중',
  failed: '실패',
};

const STATUS_LABELS: Record<Status, string> = {
  done: '완성',
  draft: '임시저장',
  processing: '처리중',
  failed: '실패',
};

const FILTER_EMPTY: Record<FilterTab, string> = {
  all: '',
  done: '완성된 카드뉴스가 없습니다.',
  draft: '임시저장된 프로젝트가 없습니다.',
  processing: '처리 중인 프로젝트가 없습니다.',
  failed: '실패한 프로젝트가 없습니다.',
};

const FILTER_TABS: FilterTab[] = ['all', 'done', 'draft', 'processing', 'failed'];

function getResultCountText(filter: FilterTab, search: string, count: number): string {
  if (search.trim()) return `"${search.trim()}" 결과 ${count}개`;
  if (filter === 'all') return `총 ${count}개 카드뉴스`;
  return `${FILTER_LABELS[filter]} ${count}개`;
}

export default function DashboardPage() {
  const [filter, setFilter] = useState<FilterTab>('all');
  const [sort, setSort] = useState<SortKey>('newest');
  const [search, setSearch] = useState('');
  const { openUploadModal } = useUiStore();

  const projects = MOCK_PROJECTS;
  const isEmpty = projects.length === 0;

  const stats = {
    all: projects.length,
    done: projects.filter(p => p.status === 'done').length,
    draft: projects.filter(p => p.status === 'draft').length,
    processing: projects.filter(p => p.status === 'processing').length,
    failed: projects.filter(p => p.status === 'failed').length,
  };

  const trimmedSearch = search.trim().toLowerCase();
  const searched = trimmedSearch
    ? projects.filter(p =>
        p.title.toLowerCase().includes(trimmedSearch) ||
        p.filename.toLowerCase().includes(trimmedSearch)
      )
    : projects;

  const filtered = searched.filter(p => filter === 'all' || p.status === filter);
  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'name') return a.title.localeCompare(b.title, 'ko');
    const da = a.date.replace(/\./g, '');
    const db = b.date.replace(/\./g, '');
    return sort === 'oldest' ? da.localeCompare(db) : db.localeCompare(da);
  });

  const resultCountText = getResultCountText(filter, search, sorted.length);

  return (
    <div className="dash">
      <h1 className="dash__title">내 카드뉴스</h1>


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
          <div className="dash-search">
            <span className="dash-search__icon" aria-hidden="true">
              <IconSearch size={14} />
            </span>
            <input
              type="search"
              className="dash-search__input"
              placeholder="제목이나 파일명으로 검색"
              value={search}
              onChange={e => setSearch(e.target.value)}
              aria-label="카드뉴스 검색"
            />
          </div>

          <div className="dash-filters">
            <div className="dash-filters__tabs" role="tablist" aria-label="상태 필터">
              {FILTER_TABS.map(tab => (
                <button
                  key={tab}
                  role="tab"
                  aria-selected={filter === tab}
                  className={`dash-filter-tab${filter === tab ? ' is-active' : ''}`}
                  onClick={() => setFilter(tab)}
                >
                  {FILTER_LABELS[tab]}
                  <span className="dash-filter-tab__count" aria-hidden="true">
                    {tab === 'all' ? stats.all : stats[tab]}
                  </span>
                </button>
              ))}
            </div>

            <select
              className="dash-sort"
              value={sort}
              onChange={e => setSort(e.target.value as SortKey)}
              aria-label="정렬 기준"
            >
              <option value="newest">최신순</option>
              <option value="oldest">오래된 순</option>
              <option value="name">이름순</option>
            </select>
          </div>

          <p className="dash-result-count" role="status" aria-live="polite">
            {resultCountText}
          </p>

          <div className="dash-grid" role="list" aria-label="프로젝트 목록">
            {sorted.length === 0 ? (
              <p className="dash-filter-empty" role="status">
                {trimmedSearch
                  ? `"${search.trim()}"와 일치하는 카드뉴스가 없습니다.`
                  : FILTER_EMPTY[filter]}
              </p>
            ) : (
              sorted.map(project => (
                <ProjectCard key={project.id} project={project} />
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isBlurred = project.status === 'processing' || project.status === 'failed';

  function handleDelete() {
    // TODO: DELETE /api/jobs/:id
    setConfirmDelete(false);
  }

  return (
    <article
      className={`proj-card${project.status === 'processing' ? ' is-processing' : ''}`}
      role="listitem"
      aria-disabled={project.status === 'processing' ? 'true' : undefined}
      aria-busy={project.status === 'processing' ? 'true' : undefined}
    >
      <div
        className={`proj-strip${isBlurred ? ' is-blurred' : ''}${project.thumbnailUrl ? ' proj-strip--preview' : ''}`}
        aria-hidden="true"
      >
        {project.thumbnailUrl ? (
          <div
            className="proj-strip__preview"
            style={{ backgroundImage: `url(${project.thumbnailUrl})` }}
          />
        ) : (
          [1, 2, 3, 4, 5].map(n => (
            <div key={n} className="proj-strip__thumb" />
          ))
        )}

        {project.status === 'processing' && (
          <div className="proj-strip__overlay">
            <div className="proj-strip__progress-track">
              <div
                className="proj-strip__progress-fill"
                style={{ transform: `scaleX(${(project.processingPercent ?? 0) / 100})` }}
              />
            </div>
            <span className="proj-strip__stage">{project.processingStep}</span>
          </div>
        )}

        {project.status === 'failed' && (
          <div className="proj-strip__overlay">
            <span className="proj-strip__badge">
              <IconWarning size={10} />
              분석 실패
            </span>
          </div>
        )}

        <div className="proj-strip__badges" aria-hidden="true">
          <span className="proj-strip__badge-item">{project.ratio}</span>
          <span className="proj-strip__badge-item">{project.cardCount}장</span>
        </div>
      </div>

      <div className="proj-card__body">
        <h2 className="proj-card__title">{project.title}</h2>
        <p className="proj-card__file">{project.filename}</p>
        {project.status === 'failed' && project.failedReason && (
          <p className="proj-card__fail-reason">{project.failedReason}</p>
        )}
        <div className="proj-card__meta">
          <time dateTime={project.date.replace(/\./g, '-')}>{project.date}</time>
          <span aria-hidden="true">·</span>
          <span className={`proj-status proj-status--${project.status}`}>
            {STATUS_LABELS[project.status]}
          </span>
        </div>
      </div>

      {project.status !== 'processing' && (
        <div className={`proj-card__actions${confirmDelete ? ' proj-card__actions--confirm' : ''}`}>
          {confirmDelete ? (
            <>
              <span className="proj-confirm-text">정말 삭제하시겠습니까?</span>
              <button
                className="proj-action proj-action--danger"
                style={{ flex: '0 0 auto' }}
                onClick={handleDelete}
              >
                삭제
              </button>
              <button
                className="proj-action"
                style={{ flex: '0 0 auto' }}
                onClick={() => setConfirmDelete(false)}
              >
                취소
              </button>
            </>
          ) : (
            <>
              {project.status === 'done' && (
                <>
                  <Link
                    href={`/editor/${project.id}`}
                    className="proj-action proj-action--primary"
                  >
                    <IconEdit size={12} />
                    수정하기
                  </Link>
                  <Link
                    href={`/editor/${project.id}?export=1`}
                    className="proj-action"
                  >
                    <IconDownload size={12} />
                    다운로드
                  </Link>
                </>
              )}
              {project.status === 'draft' && (
                <Link
                  href={`/editor/${project.id}`}
                  className="proj-action proj-action--primary"
                  style={{ flex: 1 }}
                >
                  이어하기
                </Link>
              )}
              {project.status === 'failed' && (
                <button
                  className="proj-action proj-action--danger"
                  style={{ flex: 1 }}
                >
                  <IconRefresh size={12} />
                  재시도
                </button>
              )}
              <button
                className="proj-action proj-action--icon"
                onClick={() => setConfirmDelete(true)}
                aria-label={`${project.title} 삭제`}
                title="삭제"
              >
                <IconTrash size={12} />
              </button>
            </>
          )}
        </div>
      )}
    </article>
  );
}
