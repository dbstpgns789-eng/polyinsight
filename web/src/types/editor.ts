export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface FieldValue {
  value?: string
  confidence?: string
  risk_level?: RiskLevel
  source?: { section: string; page: number }
}

export interface FieldStyle {
  size?: 'S' | 'M' | 'L' | 'XL'
  tracking?: number
  weight?: 'regular' | 'bold'
  align?: 'left' | 'center' | 'right'
  color?: 'ink-strong' | 'ink-muted' | 'accent'
}

export interface Card {
  card_num: number
  template_type: string
  image_url?: string
  focal?: { x: number; y: number }
  image_fit?: 'cover' | 'contain'
  fields?: Record<string, FieldValue>
  field_styles?: Record<string, FieldStyle>
}

export interface CardTheme {
  primary: string
  dark: string
}

export interface CardDataPayload {
  cards: Card[]
  theme?: CardTheme
  recommended_theme_key?: string
  bg_color?: string
}

export interface ApiResponse {
  filename?: string
  cardData?: CardDataPayload
}
