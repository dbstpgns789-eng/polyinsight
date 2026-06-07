// VisualZone — 디자인된 이미지 존. 둥근 프레임 + 표면 플레이스홀더.
// focal/fit는 EditableImage로 위임(클릭 초점 + 채움/전체 토글).
import EditableImage from '../shared/EditableImage'
import type { Focal } from '@/lib/focal'

interface VisualZoneProps {
  imageUrl?: string
  slotKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  focal?: Focal
  fit?: 'cover' | 'contain'
  radius?: boolean       // 둥근 모서리(기본 true)
  onImageRequest?: (slotKey: string) => void
  onFocalChange?: (focal: Focal) => void
  onFitChange?: (fit: 'cover' | 'contain') => void
}

export default function VisualZone({
  imageUrl, slotKey, mode, focal, fit, radius = true, onImageRequest, onFocalChange, onFitChange,
}: VisualZoneProps) {
  return (
    <div style={{
      width: '100%', height: '100%', overflow: 'hidden',
      borderRadius: radius ? 'var(--set-radius-box)' : 0,
      background: 'var(--set-surface)',
    }}>
      <EditableImage
        imageUrl={imageUrl}
        slotKey={slotKey}
        mode={mode}
        objectFit={fit ?? 'cover'}
        focal={focal}
        onImageRequest={onImageRequest}
        onFocalChange={onFocalChange}
        onFitChange={onFitChange}
      />
    </div>
  )
}
