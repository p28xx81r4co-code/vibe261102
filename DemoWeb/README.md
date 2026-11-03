# DemoWeb 게시판

Next.js(App Router) + shadcn/ui + TypeScript로 만든 게시판입니다.

## 기능

- 글 목록 (최신순, 10개씩 페이지네이션)
- 제목·내용·작성자 검색
- 글 상세 보기 (조회수)
- 글쓰기 / 수정 / 삭제 — 작성 시 입력한 비밀번호로 수정·삭제 확인
- 샘플 글 3개 자동 생성 (비밀번호 `1234`)

## 실행

```bash
npm install
npm run dev
```

http://localhost:3000 에 접속하면 `/posts` 로 이동합니다.

## 구조

| 경로 | 설명 |
| --- | --- |
| `src/app/posts/page.tsx` | 목록·검색·페이지네이션 |
| `src/app/posts/new/page.tsx` | 글쓰기 |
| `src/app/posts/[id]/page.tsx` | 상세 보기 |
| `src/app/posts/[id]/edit/page.tsx` | 수정 |
| `src/app/actions.ts` | 등록·수정·삭제 Server Actions (입력 검증 포함) |
| `src/lib/posts.ts` | 데이터 저장소 (`data/posts.json`, 비밀번호는 scrypt 해시) |
| `src/components/` | 글 폼, 삭제 다이얼로그, shadcn/ui 컴포넌트 |

데이터는 `data/posts.json` 파일에 저장됩니다 (git 제외). 파일을 지우면 샘플 글로 초기화됩니다.
실서비스에서는 `src/lib/posts.ts` 를 DB(Prisma, Drizzle 등)로 교체하세요.
