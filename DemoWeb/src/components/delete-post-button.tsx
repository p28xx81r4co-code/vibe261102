"use client"

import { useActionState } from "react"
import { Trash2 } from "lucide-react"

import { deletePostAction } from "@/app/actions"
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function DeletePostButton({ id }: { id: number }) {
  const [state, formAction, pending] = useActionState(deletePostAction.bind(null, id), {})

  return (
    <AlertDialog>
      <AlertDialogTrigger render={<Button variant="destructive" />}>
        <Trash2 />
        삭제
      </AlertDialogTrigger>
      <AlertDialogContent>
        <form action={formAction} className="grid gap-4">
          <AlertDialogHeader>
            <AlertDialogTitle>글을 삭제할까요?</AlertDialogTitle>
            <AlertDialogDescription>
              삭제한 글은 되돌릴 수 없습니다. 글 작성 시 입력한 비밀번호를 입력하세요.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-2">
            <Input
              name="password"
              type="password"
              placeholder="비밀번호"
              aria-label="비밀번호"
              autoComplete="off"
              aria-invalid={!!state.error}
              autoFocus
            />
            {state.error && <p className="text-sm text-destructive">{state.error}</p>}
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel type="button">취소</AlertDialogCancel>
            <Button type="submit" variant="destructive" disabled={pending}>
              {pending ? "삭제 중..." : "삭제"}
            </Button>
          </AlertDialogFooter>
        </form>
      </AlertDialogContent>
    </AlertDialog>
  )
}
