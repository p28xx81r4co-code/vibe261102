# DemoWeb 게시판

Next.js(App Router) + shadcn/ui + TypeScript로 만든 게시판입니다.

## 기능

- 글 목록 (최신순, 10개씩 페이지네이션)
- 제목·내용·작성자 검색
- 글 상세 보기 (조회수)
- 글쓰기 / 수정 / 삭제 — 작성 시 입력한 비밀번호로 수정·삭제 확인
- `npm run db:setup` 실행 시 샘플 글 3개 생성 (비밀번호 `1234`)

## 실행

1. `.env.example` 을 `.env.local` 로 복사하고 Neon(PostgreSQL) 연결 문자열을 `DATABASE_URL` 에 넣습니다.
2. 테이블 생성 및 샘플 데이터 입력 후 실행합니다.

```bash
npm install
npm run db:setup
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
| `src/lib/posts.ts` | Neon PostgreSQL 데이터 접근 (비밀번호는 scrypt 해시) |
| `scripts/setup-db.mjs` | `posts` 테이블 생성 및 샘플 글 입력 |
| `src/components/` | 글 폼, 삭제 다이얼로그, shadcn/ui 컴포넌트 |

데이터는 Neon PostgreSQL의 `posts` 테이블에 저장됩니다. `.env.local` 은 git에 포함되지 않습니다.
