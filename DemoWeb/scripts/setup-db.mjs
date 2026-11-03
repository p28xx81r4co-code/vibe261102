// Creates the posts table and seeds sample posts when it is empty.
// Usage: npm run db:setup  (reads DATABASE_URL from .env.local)
import { randomBytes, scryptSync } from "node:crypto"
import { neon } from "@neondatabase/serverless"

if (!process.env.DATABASE_URL) {
  console.error("DATABASE_URL is not set. Add it to .env.local.")
  process.exit(1)
}

const sql = neon(process.env.DATABASE_URL)

// Same format as hashPassword in src/lib/posts.ts
function hashPassword(password) {
  const salt = randomBytes(16).toString("hex")
  return `${salt}:${scryptSync(password, salt, 32).toString("hex")}`
}

await sql`
  CREATE TABLE IF NOT EXISTS posts (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(100) NOT NULL,
    content       TEXT NOT NULL,
    author        VARCHAR(20) NOT NULL,
    password_hash TEXT NOT NULL,
    views         INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  )
`

const [{ count }] = await sql`SELECT count(*)::int AS count FROM posts`
if (count === 0) {
  const samples = [
    ["게시판에 오신 것을 환영합니다", "Next.js, shadcn/ui, TypeScript로 만든 데모 게시판입니다.\n\n글을 작성할 때 입력한 비밀번호로 수정과 삭제를 할 수 있습니다. 샘플 글의 비밀번호는 1234 입니다.", "관리자"],
    ["공지: 게시판 이용 규칙", "서로 존중하는 대화를 부탁드립니다.\n광고성 글은 삭제될 수 있습니다.", "관리자"],
    ["첫 번째 질문 있습니다", "검색 기능은 제목과 내용, 작성자를 모두 찾나요?", "홍길동"],
  ]
  for (const [title, content, author] of samples) {
    await sql`
      INSERT INTO posts (title, content, author, password_hash)
      VALUES (${title}, ${content}, ${author}, ${hashPassword("1234")})
    `
  }
  console.log(`Seeded ${samples.length} sample posts.`)
}

console.log("posts table is ready.")
