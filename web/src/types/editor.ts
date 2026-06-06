export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface FieldValue {
  value?: string
  confidence?: string
  risk_level?: RiskLevel
  source?: { section: string; page: number }
}

export interface Card {
  card_num: number
  template_type: string
  image_url?: string
  fields?: Record<string, FieldValue>
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
