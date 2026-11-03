import { notFound } from "next/navigation"

import { updatePostAction } from "@/app/actions"
import { PostForm } from "@/components/post-form"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getPost } from "@/lib/posts"

export default async function EditPostPage({ params }: PageProps<"/posts/[id]/edit">) {
  const { id } = await params
  const post = await getPost(Number(id))
  if (!post) notFound()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">글 수정</CardTitle>
      </CardHeader>
      <CardContent>
        <PostForm
          action={updatePostAction.bind(null, post.id)}
          initial={{ title: post.title, content: post.content, author: post.author }}
          submitLabel="수정"
          cancelHref={`/posts/${post.id}`}
        />
      </CardContent>
    </Card>
  )
}
