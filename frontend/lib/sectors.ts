export const SECTOR_COLORS: Record<string, string> = {
  Technology:    "#185FA5",
  Financial:     "#0F6E56",
  Energy:        "#BA7517",
  Healthcare:    "#3B6D11",
  Consumer:      "#534AB7",
  Industrial:    "#5F5E5A",
  "Real Estate": "#8B4513",
  Utilities:     "#2F6B8F",
  Other:         "#888780",
};

export function sectorColor(sector: string | null | undefined): string {
  return SECTOR_COLORS[sector ?? "Other"] ?? SECTOR_COLORS.Other;
}
