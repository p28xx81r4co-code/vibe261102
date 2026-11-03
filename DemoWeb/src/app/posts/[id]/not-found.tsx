import Link from "next/link"

import { buttonVariants } from "@/components/ui/button"

export default function PostNotFound() {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <h1 className="text-xl font-semibold">게시글을 찾을 수 없습니다</h1>
      <p className="text-sm text-muted-foreground">삭제되었거나 존재하지 않는 글입니다.</p>
      <Link href="/posts" className={buttonVariants({ variant: "outline" })}>
        목록으로
      </Link>
    </div>
  )
}
