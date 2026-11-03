import Link from "next/link"
import { notFound } from "next/navigation"
import { ArrowLeft, Pencil } from "lucide-react"

import { DeletePostButton } from "@/components/delete-post-button"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { formatDateTime } from "@/lib/format"
import { getPost, incrementViews } from "@/lib/posts"

export async function generateMetadata({ params }: PageProps<"/posts/[id]">) {
  const { id } = await params
  const post = await getPost(Number(id))
  return { title: post ? `${post.title} | DemoWeb 게시판` : "DemoWeb 게시판" }
}

export default async function PostPage({ params }: PageProps<"/posts/[id]">) {
  const { id } = await params
  await incrementViews(Number(id))
  const post = await getPost(Number(id))
  if (!post) notFound()

  const edited = post.updatedAt !== post.createdAt

  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">#{post.id}</Badge>
          {edited && <Badge variant="outline">수정됨</Badge>}
        </div>
        <CardTitle className="text-2xl break-words">{post.title}</CardTitle>
        <CardDescription className="flex flex-wrap gap-x-3 gap-y-1">
          <span className="font-medium text-foreground">{post.author}</span>
          <span>{formatDateTime(post.createdAt)}</span>
          <span>조회 {post.views}</span>
        </CardDescription>
      </CardHeader>
      <Separator />
      <CardContent className="min-h-48 py-6 leading-relaxed break-words whitespace-pre-wrap">
        {post.content}
      </CardContent>
      <CardFooter className="justify-between gap-2 border-t">
        <Link href="/posts" className={buttonVariants({ variant: "outline" })}>
          <ArrowLeft />
          목록
        </Link>
        <div className="flex gap-2">
          <Link href={`/posts/${post.id}/edit`} className={buttonVariants({ variant: "secondary" })}>
            <Pencil />
            수정
          </Link>
          <DeletePostButton id={post.id} />
        </div>
      </CardFooter>
    </Card>
  )
}
