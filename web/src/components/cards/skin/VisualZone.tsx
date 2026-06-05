// VisualZone — 디자인된 이미지 존(focal 값 적용). 둥근 프레임 + 표면 플레이스홀더.
// focal {x,y}(0~1) → objectPosition. 드래그 UI는 후속.
import EditableImage from '../shared/EditableImage'

interface VisualZoneProps {
  imageUrl?: string
  slotKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  focal?: { x: number; y: number }
  radius?: boolean       // 둥근 모서리(기본 true)
  onImageRequest?: (slotKey: string) => void
}

export default function VisualZone({ imageUrl, slotKey, mode, focal, radius = true, onImageRequest }: VisualZoneProps) {
  const objectPosition = focal ? `${focal.x * 100}% ${focal.y * 100}%` : 'center'
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
        objectPosition={objectPosition}
        onImageRequest={onImageRequest}
      />
    </div>
  )
}
