// VisualZone — 디자인된 이미지 존. 둥근 프레임 + 표면 플레이스홀더.
// focal/onFocalChange는 EditableImage로 위임(클릭 초점).
import EditableImage from '../shared/EditableImage'
import type { Focal } from '@/lib/focal'

interface VisualZoneProps {
  imageUrl?: string
  slotKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  focal?: Focal
  radius?: boolean       // 둥근 모서리(기본 true)
  onImageRequest?: (slotKey: string) => void
  onFocalChange?: (focal: Focal) => void
}

export default function VisualZone({
  imageUrl, slotKey, mode, focal, radius = true, onImageRequest, onFocalChange,
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
        objectFit="cover"
        focal={focal}
        onImageRequest={onImageRequest}
        onFocalChange={onFocalChange}
      />
    </div>
  )
}
