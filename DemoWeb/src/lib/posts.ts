import "server-only"

import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto"
import { promises as fs } from "node:fs"
import path from "node:path"

export type Post = {
  id: number
  title: string
  content: string
  author: string
  passwordHash: string
  views: number
  createdAt: string
  updatedAt: string
}

export type PublicPost = Omit<Post, "passwordHash">

type Store = { nextId: number; posts: Post[] }

const DATA_FILE = path.join(process.cwd(), "data", "posts.json")

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

function toPublic(post: Post): PublicPost {
  const { passwordHash, ...rest } = post
  void passwordHash
  return rest
}

function seed(): Store {
  const now = Date.now()
  const samples = [
    ["게시판에 오신 것을 환영합니다", "Next.js, shadcn/ui, TypeScript로 만든 데모 게시판입니다.\n\n글을 작성할 때 입력한 비밀번호로 수정과 삭제를 할 수 있습니다. 샘플 글의 비밀번호는 1234 입니다.", "관리자"],
    ["공지: 게시판 이용 규칙", "서로 존중하는 대화를 부탁드립니다.\n광고성 글은 삭제될 수 있습니다.", "관리자"],
    ["첫 번째 질문 있습니다", "검색 기능은 제목과 내용, 작성자를 모두 찾나요?", "홍길동"],
  ] as const
  const posts = samples.map(([title, content, author], i) => {
    const date = new Date(now - (samples.length - i) * 3600_000).toISOString()
    return {
      id: i + 1,
      title,
      content,
      author,
      passwordHash: hashPassword("1234"),
      views: 0,
      createdAt: date,
      updatedAt: date,
    }
  })
  return { nextId: posts.length + 1, posts }
}

async function readStore(): Promise<Store> {
  try {
    return JSON.parse(await fs.readFile(DATA_FILE, "utf8")) as Store
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error
    const store = seed()
    await writeStore(store)
    return store
  }
}

async function writeStore(store: Store) {
  await fs.mkdir(path.dirname(DATA_FILE), { recursive: true })
  await fs.writeFile(DATA_FILE, JSON.stringify(store, null, 2), "utf8")
}

export async function listPosts({ query = "", page = 1 }: { query?: string; page?: number }) {
  const { posts } = await readStore()
  const q = query.trim().toLowerCase()
  const filtered = posts
    .filter(
      (p) =>
        !q ||
        p.title.toLowerCase().includes(q) ||
        p.content.toLowerCase().includes(q) ||
        p.author.toLowerCase().includes(q)
    )
    .sort((a, b) => b.id - a.id)
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const current = Math.min(Math.max(1, page), totalPages)
  return {
    posts: filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE).map(toPublic),
    total: filtered.length,
    page: current,
    totalPages,
  }
}

export async function getPost(id: number) {
  const { posts } = await readStore()
  const post = posts.find((p) => p.id === id)
  return post ? toPublic(post) : null
}

export async function incrementViews(id: number) {
  const store = await readStore()
  const post = store.posts.find((p) => p.id === id)
  if (!post) return
  post.views += 1
  await writeStore(store)
}

export async function createPost(input: { title: string; content: string; author: string; password: string }) {
  const store = await readStore()
  const now = new Date().toISOString()
  const post: Post = {
    id: store.nextId++,
    title: input.title,
    content: input.content,
    author: input.author,
    passwordHash: hashPassword(input.password),
    views: 0,
    createdAt: now,
    updatedAt: now,
  }
  store.posts.push(post)
  await writeStore(store)
  return post.id
}

type MutationResult = "ok" | "not-found" | "wrong-password"

export async function updatePost(
  id: number,
  password: string,
  input: { title: string; content: string; author: string }
): Promise<MutationResult> {
  const store = await readStore()
  const post = store.posts.find((p) => p.id === id)
  if (!post) return "not-found"
  if (!verifyPassword(password, post.passwordHash)) return "wrong-password"
  Object.assign(post, input, { updatedAt: new Date().toISOString() })
  await writeStore(store)
  return "ok"
}

export async function deletePost(id: number, password: string): Promise<MutationResult> {
  const store = await readStore()
  const index = store.posts.findIndex((p) => p.id === id)
  if (index === -1) return "not-found"
  if (!verifyPassword(password, store.posts[index].passwordHash)) return "wrong-password"
  store.posts.splice(index, 1)
  await writeStore(store)
  return "ok"
}
