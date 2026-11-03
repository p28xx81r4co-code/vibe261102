import Link from "next/link"
import { PenSquare, Search } from "lucide-react"

import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { formatDate } from "@/lib/format"
import { listPosts } from "@/lib/posts"
import { cn } from "@/lib/utils"

export default async function PostsPage({ searchParams }: PageProps<"/posts">) {
  const { q, page } = await searchParams
  const query = typeof q === "string" ? q : ""
  const result = await listPosts({ query, page: Number(page) || 1 })

  const pageHref = (p: number) => {
    const params = new URLSearchParams()
    if (query) params.set("q", query)
    if (p > 1) params.set("page", String(p))
    const qs = params.toString()
    return qs ? `/posts?${qs}` : "/posts"
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">자유게시판</CardTitle>
        <CardDescription>
          {query ? `"${query}" 검색 결과 ` : "전체 글 "}
          {result.total}개
        </CardDescription>
        <CardAction>
          <Link href="/posts/new" className={buttonVariants()}>
            <PenSquare />
            글쓰기
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        <form action="/posts" className="flex gap-2">
          <Input
            name="q"
            defaultValue={query}
            placeholder="제목, 내용, 작성자 검색"
            aria-label="검색어"
          />
          <button type="submit" className={buttonVariants({ variant: "outline" })}>
            <Search />
            검색
          </button>
        </form>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16 text-center">번호</TableHead>
              <TableHead>제목</TableHead>
              <TableHead className="hidden w-28 sm:table-cell">작성자</TableHead>
              <TableHead className="hidden w-24 text-center sm:table-cell">작성일</TableHead>
              <TableHead className="w-16 text-center">조회</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.posts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                  {query ? "검색 결과가 없습니다." : "아직 작성된 글이 없습니다."}
                </TableCell>
              </TableRow>
            ) : (
              result.posts.map((post) => (
                <TableRow key={post.id}>
                  <TableCell className="text-center text-muted-foreground">{post.id}</TableCell>
                  <TableCell className="max-w-0 truncate">
                    <Link href={`/posts/${post.id}`} className="font-medium hover:underline">
                      {post.title}
                    </Link>
                    <span className="mt-0.5 block text-xs text-muted-foreground sm:hidden">
                      {post.author} · {formatDate(post.createdAt)}
                    </span>
                  </TableCell>
                  <TableCell className="hidden truncate sm:table-cell">{post.author}</TableCell>
                  <TableCell className="hidden text-center text-muted-foreground sm:table-cell">
                    {formatDate(post.createdAt)}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">{post.views}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {result.totalPages > 1 && (
          <nav className="flex justify-center gap-1" aria-label="페이지 이동">
            {Array.from({ length: result.totalPages }, (_, i) => i + 1).map((p) => (
              <Link
                key={p}
                href={pageHref(p)}
                aria-current={p === result.page ? "page" : undefined}
                className={cn(
                  buttonVariants({ variant: p === result.page ? "default" : "ghost", size: "icon" })
                )}
              >
                {p}
              </Link>
            ))}
          </nav>
        )}
      </CardContent>
    </Card>
  )
}
