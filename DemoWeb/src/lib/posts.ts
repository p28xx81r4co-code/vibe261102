import "server-only"

import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto"
import { neon } from "@neondatabase/serverless"

export type PublicPost = {
  id: number
  title: string
  content: string
  author: string
  views: number
  createdAt: string
  updatedAt: string
}

type PostRow = {
  id: number
  title: string
  content: string
  author: string
  views: number
  created_at: Date
  updated_at: Date
}

if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL is not set. Add it to .env.local.")
}

const sql = neon(process.env.DATABASE_URL)

export const PAGE_SIZE = 10

function hashPassword(password: string) {
  const salt = randomBytes(16).toString("hex")
  const hash = scryptSync(password, salt, 32).toString("hex")
  return `${salt}:${hash}`
}

function verifyPassword(password: string, stored: string) {
  const [salt, hash] = stored.split(":")
  const expected = Buffer.from(hash, "hex")
  const actual = scryptSync(password, salt, expected.length)
  return timingSafeEqual(expected, actual)
}

function toPublic(row: PostRow): PublicPost {
  return {
    id: row.id,
    title: row.title,
    content: row.content,
    author: row.author,
    views: row.views,
    createdAt: new Date(row.created_at).toISOString(),
    updatedAt: new Date(row.updated_at).toISOString(),
  }
}

export async function listPosts({ query = "", page = 1 }: { query?: string; page?: number }) {
  // Escape LIKE wildcards so the search term matches literally
  const pattern = `%${query.trim().replace(/[\\%_]/g, "\\$&")}%`
  const [{ total }] = (await sql`
    SELECT count(*)::int AS total FROM posts
    WHERE title ILIKE ${pattern} OR content ILIKE ${pattern} OR author ILIKE ${pattern}
  `) as { total: number }[]

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const current = Math.min(Math.max(1, page), totalPages)
  const rows = (await sql`
    SELECT id, title, content, author, views, created_at, updated_at FROM posts
    WHERE title ILIKE ${pattern} OR content ILIKE ${pattern} OR author ILIKE ${pattern}
    ORDER BY id DESC
    LIMIT ${PAGE_SIZE} OFFSET ${(current - 1) * PAGE_SIZE}
  `) as PostRow[]

  return { posts: rows.map(toPublic), total, page: current, totalPages }
}

export async function getPost(id: number) {
  if (!Number.isSafeInteger(id)) return null
  const [row] = (await sql`
    SELECT id, title, content, author, views, created_at, updated_at FROM posts WHERE id = ${id}
  `) as PostRow[]
  return row ? toPublic(row) : null
}

export async function incrementViews(id: number) {
  if (!Number.isSafeInteger(id)) return
  await sql`UPDATE posts SET views = views + 1 WHERE id = ${id}`
}

export async function createPost(input: { title: string; content: string; author: string; password: string }) {
  const [{ id }] = (await sql`
    INSERT INTO posts (title, content, author, password_hash)
    VALUES (${input.title}, ${input.content}, ${input.author}, ${hashPassword(input.password)})
    RETURNING id
  `) as { id: number }[]
  return id
}

type MutationResult = "ok" | "not-found" | "wrong-password"

async function checkPassword(id: number, password: string): Promise<MutationResult> {
  const [row] = (await sql`SELECT password_hash FROM posts WHERE id = ${id}`) as { password_hash: string }[]
  if (!row) return "not-found"
  return verifyPassword(password, row.password_hash) ? "ok" : "wrong-password"
}

export async function updatePost(
  id: number,
  password: string,
  input: { title: string; content: string; author: string }
): Promise<MutationResult> {
  const result = await checkPassword(id, password)
  if (result !== "ok") return result
  await sql`
    UPDATE posts
    SET title = ${input.title}, content = ${input.content}, author = ${input.author}, updated_at = now()
    WHERE id = ${id}
  `
  return "ok"
}

export async function deletePost(id: number, password: string): Promise<MutationResult> {
  const result = await checkPassword(id, password)
  if (result !== "ok") return result
  await sql`DELETE FROM posts WHERE id = ${id}`
  return "ok"
}
