'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { getProjects, deleteJob, getDeckCardUrl, getCardImageUrl } from '@/lib/api';
import {
  IconEdit, IconDownload, IconRefresh, IconWarning,
  IconTrash, IconSearch,
} from '@/components/ui/Icons';
import AuthGuard from '@/components/auth/AuthGuard';
import { trialLabel, type PlanState } from '@/lib/plan';

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true';

type Status = 'done' | 'draft' | 'processing' | 'failed';
type FilterTab = 'all' | Status;
type SortKey = 'newest' | 'oldest' | 'name';

interface Project {
  id: string;
  title: string;
  status: Status;
  kind: 'deck' | 'legacy';
  date: string;
  cardCount?: number;
}

// 백엔드 status → 프론트 status
function mapStatus(s: string): Status {
  switch (s) {
    case 'DONE':    return 'done';
    case 'RUNNING': return 'processing';
    case 'ERROR':   return 'failed';
    default:        return 'draft';   // PENDING
  }
}

// ── Mock 데이터 (NEXT_PUBLIC_USE_MOCK=true 일 때만 사용) ──────────────────
const MOCK_PROJECTS: Project[] = [
  { id: 'job-001', title: '스마트팜 기반 식물 생장 최적화 연구', status: 'done',       kind: 'legacy', date: '2026.05.18', cardCount: 5 },
  { id: 'job-002', title: '탄소 포집 기술의 경제성 분석 및 상용화 전망',    status: 'done',       kind: 'deck',   date: '2026.05.17', cardCount: 5 },
  { id: 'job-003', title: '수소 연료전지 내구성 실증 연구',         status: 'draft',      kind: 'deck',   date: '2026.05.16', cardCount: 5 },
  { id: 'job-004', title: '초고강도 강재 레이저 용접 특성 평가',     status: 'processing', kind: 'deck',   date: '2026.05.20', cardCount: 5 },
  { id: 'job-005', title: '세라믹 소재 고온 기계적 특성 분석',       status: 'failed',     kind: 'deck',   date: '2026.05.15', cardCount: 5 },
];

const FILTER_LABELS: Record<FilterTab, string> = {
  all: '전체', done: '완성', draft: '대기', processing: '처리중', failed: '실패',
};
const STATUS_LABELS: Record<Status, string> = {
  done: '완성', draft: '대기', processing: '처리중', failed: '실패',
};
const FILTER_EMPTY: Record<FilterTab, string> = {
  all: '',
  done: '완성된 카드뉴스가 없습니다.',
  draft: '대기 중인 프로젝트가 없습니다.',
  processing: '처리 중인 프로젝트가 없습니다.',
  failed: '실패한 프로젝트가 없습니다.',
};
const FILTER_TABS: FilterTab[] = ['all', 'done', 'draft', 'processing', 'failed'];

function getResultCountText(filter: FilterTab, search: string, count: number): string {
  if (search.trim()) return `"${search.trim()}" 결과 ${count}개`;
  if (filter === 'all') return `총 ${count}개 카드뉴스`;
  return `${FILTER_LABELS[filter]} ${count}개`;
}

function DashboardPageInner() {
  const [filter, setFilter]   = useState<FilterTab>('all');
  const [sort, setSort]       = useState<SortKey>('newest');
  const [search, setSearch]   = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading]  = useState(!USE_MOCK);
  const [error, setError]      = useState('');
  // 무료체험 게이트 — 이 레포 관례대로 컴포넌트 단위 개별 fetch (전역 상태 미도입)
  const [me, setMe] = useState<(PlanState & { canAuthor: boolean; canExport: boolean }) | null>(null);

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setMe(d))
      .catch(() => {});
  }, []);

  const fetchProjects = useCallback(async () => {
    try {
      const { data } = await getProjects({ limit: 100 });
      const mapped: Project[] = (data.projects as Array<{
        jobId: string; title: string | null; status: string; kind?: string; updatedAt: string;
      }>).map(r => ({
        id:     r.jobId,
        title:  r.title || '(제목 없음)',
        status: mapStatus(r.status),
        kind:   r.kind === 'deck' ? 'deck' : 'legacy',
        date:   r.updatedAt
          ? new Date(r.updatedAt).toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/ /g, '').replace(/\.$/, '')
          : '',
      }));
      setProjects(mapped);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : '프로젝트 목록을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (USE_MOCK) {
      setProjects(MOCK_PROJECTS);
      return;
    }

    fetchProjects();

    // processing 중인 항목이 있으면 3초마다 폴링
    const id = setInterval(() => {
      if (projects.some(p => p.status === 'processing')) {
        fetchProjects();
      }
    }, 3000);
    return () => clearInterval(id);
  }, [fetchProjects]); // eslint-disable-line react-hooks/exhaustive-deps

  const isEmpty = !loading && !error && projects.length === 0;

  const stats = {
    all:        projects.length,
    done:       projects.filter(p => p.status === 'done').length,
    draft:      projects.filter(p => p.status === 'draft').length,
    processing: projects.filter(p => p.status === 'processing').length,
    failed:     projects.filter(p => p.status === 'failed').length,
  };

  const trimmedSearch = search.trim().toLowerCase();
  const searched = trimmedSearch
    ? projects.filter(p => p.title.toLowerCase().includes(trimmedSearch))
    : projects;
  const filtered = searched.filter(p => filter === 'all' || p.status === filter);
  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'name') return a.title.localeCompare(b.title, 'ko');
    return sort === 'oldest' ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date);
  });

  return (
    <div className="dash">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <h1 className="dash__title" style={{ margin: 0 }}>내 카드뉴스</h1>
        {USE_MOCK && (
          <span style={{ fontSize: 11, color: 'var(--text-3)', background: 'var(--border)', padding: '2px 8px', borderRadius: 4 }}>
            DEV (mock)
          </span>
        )}
      </div>

      {loading && (
        <p style={{ color: 'var(--text-3)', fontSize: 14, marginTop: 32 }}>불러오는 중…</p>
      )}

      {error && (
        <div style={{ marginTop: 32, padding: '16px 20px', background: 'var(--surface-subtle)', borderRadius: 10, border: '1px solid var(--border)' }}>
          <p style={{ fontSize: 14, color: 'var(--text-2)', margin: 0 }}>{error}</p>
          <button
            style={{ marginTop: 10, fontSize: 13, color: 'var(--accent)', cursor: 'pointer', background: 'none', border: 'none', padding: 0 }}
            onClick={fetchProjects}
          >
            다시 시도
          </button>
        </div>
      )}

      {isEmpty && (
        <div className="dash-empty">
          <svg className="dash-empty__icon" width="52" height="52" viewBox="0 0 52 52" fill="none" aria-hidden="true">
            <rect x="6" y="8" width="36" height="30" rx="4" stroke="currentColor" strokeWidth="1.6"/>
            <path d="M14 20h20M14 27h13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
            <circle cx="41" cy="41" r="9" fill="var(--surface)" stroke="currentColor" strokeWidth="1.6"/>
            <path d="M37.5 41h7M41 37.5v7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
          <h2 className="dash-empty__title">첫 논문을 업로드하세요</h2>
          <p className="dash-empty__desc">PDF를 올리면 카드뉴스를 자동으로 만들어 드립니다.</p>
          <Link href="/deck/new" className="btn btn-primary">
            새 카드뉴스 만들기
          </Link>
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <>
          <div className="dash-search">
            <span className="dash-search__icon" aria-hidden="true"><IconSearch size={14} /></span>
            <input
              type="search"
              className="dash-search__input"
              placeholder="제목으로 검색"
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
            {getResultCountText(filter, search, sorted.length)}
          </p>

          {me && trialLabel(me) && (
            <section className="trial-meter">
              <div className="trial-meter__left">
                <span className="trial-meter__badge">무료 체험</span>
                <p className="trial-meter__usage">
                  {me.freeDecksUsed}<span> / {me.freeDeckLimit} 덱 사용</span>
                </p>
                <div className="trial-meter__bar">
                  <i style={{ width: `${Math.min(100, (me.freeDecksUsed / me.freeDeckLimit) * 100)}%` }} />
                </div>
              </div>
              <div className="trial-meter__mid">
                <p className="trial-meter__t">
                  {me.canAuthor ? '카드뉴스 1덱을 무료로 만들어 보세요.' : '만들고 검증까지 무료로 다 봤어요.'}
                </p>
                <p className="trial-meter__d">
                  <strong>내보내기</strong>와 <strong>다음 카드뉴스</strong>는 업그레이드 후 이용할 수 있어요.
                  만든 덱은 그대로 보관돼요.
                </p>
              </div>
              <a className="btn btn-primary" href="/upgrade">업그레이드 →</a>
            </section>
          )}

          <div className="dash-grid" role="list" aria-label="프로젝트 목록">
            {sorted.length === 0 ? (
              <p className="dash-filter-empty" role="status">
                {trimmedSearch
                  ? `"${search.trim()}"와 일치하는 카드뉴스가 없습니다.`
                  : FILTER_EMPTY[filter]}
              </p>
            ) : (
              sorted.map(project => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onDeleted={fetchProjects}
                  exportLocked={me?.canExport === false}
                />
              ))
            )}
            {me && !me.canAuthor && (
              <a className="new-deck-card new-deck-card--locked" href="/upgrade">
                <span className="new-deck-card__lock">🔒</span>
                <strong>다음 카드뉴스</strong>
                <span>무료 체험 1덱을 다 썼어요. 업그레이드하면 계속 만들 수 있어요.</span>
              </a>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// 기약분수 비율 라벨 (1080×1350 → 4:5, 1080×1080 → 1:1)
function simplifyRatio(w: number, h: number): string {
  const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b));
  const d = gcd(w, h) || 1;
  return `${Math.round(w / d)}:${Math.round(h / d)}`;
}

// 대시보드 썸네일 = 첫 카드 1장. 비율은 실제 이미지 크기에서 유도(하드코딩 1:1 폐기).
function ProjThumb({ project }: { project: Project }) {
  const [dim, setDim] = useState<{ w: number; h: number } | null>(null);
  const [failedImg, setFailedImg] = useState(false);
  const showImg = project.status === 'done' && !failedImg;
  const src = project.kind === 'deck'
    ? getDeckCardUrl(project.id, 1)
    : getCardImageUrl(project.id, 1);
  const blurred = project.status === 'processing' || project.status === 'failed';

  return (
    <div
      className={`proj-strip${blurred ? ' is-blurred' : ''}`}
      style={{ aspectRatio: dim ? `${dim.w} / ${dim.h}` : '4 / 5' }}
      aria-hidden="true"
    >
      {showImg
        ? <img
            className="proj-strip__cover"
            src={src}
            alt=""
            loading="lazy"
            onLoad={e => setDim({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
            onError={() => setFailedImg(true)}
          />
        : <div className="proj-strip__placeholder" />}

      {project.status === 'processing' && (
        <div className="proj-strip__overlay">
          <div className="proj-strip__progress-track">
            <div className="proj-strip__progress-fill" style={{ transform: 'scaleX(0.5)' }} />
          </div>
          <span className="proj-strip__stage">처리 중…</span>
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

      {(dim || project.cardCount) && (
        <div className="proj-strip__badges">
          {dim ? <span className="proj-strip__badge-item">{simplifyRatio(dim.w, dim.h)}</span> : <span />}
          {project.cardCount && <span className="proj-strip__badge-item">{project.cardCount}장</span>}
        </div>
      )}
    </div>
  );
}

function ProjectCard({ project, onDeleted, exportLocked }: { project: Project; onDeleted: () => void; exportLocked: boolean }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  // v3 덱 잡은 /deck, 옛 파이프라인 잡(card_data 보유)은 기존 /editor 유지
  const base = project.kind === 'deck' ? '/deck' : '/editor';

  async function handleDelete() {
    try {
      await deleteJob(project.id);
      setConfirmDelete(false);
      onDeleted();
    } catch {
      alert('삭제에 실패했습니다. 잠시 후 다시 시도해 주세요.');
    }
  }

  return (
    <article
      className={`proj-card${project.status === 'processing' ? ' is-processing' : ''}`}
      role="listitem"
      aria-disabled={project.status === 'processing' ? 'true' : undefined}
      aria-busy={project.status === 'processing' ? 'true' : undefined}
    >
      <ProjThumb project={project} />

      <div className="proj-card__body">
        <h2 className="proj-card__title">{project.title}</h2>
        <div className="proj-card__meta">
          <time>{project.date}</time>
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
              <button className="proj-action proj-action--danger" style={{ flex: '0 0 auto' }} onClick={handleDelete}>삭제</button>
              <button className="proj-action" style={{ flex: '0 0 auto' }} onClick={() => setConfirmDelete(false)}>취소</button>
            </>
          ) : (
            <>
              {project.status === 'done' && (
                <>
                  <Link href={`${base}/${project.id}`} className="proj-action proj-action--primary">
                    <IconEdit size={12} />수정하기
                  </Link>
                  {exportLocked ? (
                    <Link
                      href="/upgrade"
                      className="proj-action proj-action--locked"
                      title="업그레이드 후 다운로드할 수 있어요"
                    >
                      <span aria-hidden="true">🔒</span>다운로드
                    </Link>
                  ) : (
                    <Link
                      href={project.kind === 'deck' ? `/deck/${project.id}` : `/editor/${project.id}?export=1`}
                      className="proj-action"
                    >
                      <IconDownload size={12} />다운로드
                    </Link>
                  )}
                </>
              )}
              {project.status === 'draft' && (
                <Link href={`${base}/${project.id}`} className="proj-action proj-action--primary" style={{ flex: 1 }}>
                  이어하기
                </Link>
              )}
              {project.status === 'failed' && (
                <button className="proj-action proj-action--danger" style={{ flex: 1 }}>
                  <IconRefresh size={12} />재시도
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

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardPageInner />
    </AuthGuard>
  );
}
