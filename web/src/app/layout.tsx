import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "PolyInsight — 논문 PDF 하나로, 카드뉴스 완성",
  description:
    "학술 논문을 업로드하면 AI가 원문에서 핵심 내용을 직접 추출해 카드뉴스를 만듭니다. 수치와 근거는 논문 그대로, 편집 가능한 형태로 제공됩니다.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="dns-prefetch" href="https://cdn.jsdelivr.net" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic.min.css"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
        />
        {/* 덱 글꼴 페어링(--set-font 오버라이드)용 — Noto Serif KR(명조), Gothic A1(기하학 고딕) */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700;900&family=Gothic+A1:wght@400;700;800;900&display=swap"
        />
      </head>
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
