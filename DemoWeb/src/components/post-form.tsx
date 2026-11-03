"use client"

import Link from "next/link"
import { useActionState } from "react"

import type { FormState } from "@/app/actions"
import { Button, buttonVariants } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

type Props = {
  action: (prev: FormState, formData: FormData) => Promise<FormState>
  initial?: { title: string; content: string; author: string }
  submitLabel: string
  cancelHref: string
}

export function PostForm({ action, initial, submitLabel, cancelHref }: Props) {
  const [state, formAction, pending] = useActionState(action, {})
  const values = state.values ?? initial
  const errors = state.fieldErrors ?? {}

  return (
    // key resets uncontrolled inputs to the values returned with a validation error
    <form action={formAction} key={JSON.stringify(state.values)} className="space-y-5">
      {state.error && (
        <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{state.error}</p>
      )}

      <Field id="title" label="제목" error={errors.title}>
        <Input id="title" name="title" maxLength={100} defaultValue={values?.title} aria-invalid={!!errors.title} />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field id="author" label="작성자" error={errors.author}>
          <Input id="author" name="author" maxLength={20} defaultValue={values?.author} aria-invalid={!!errors.author} />
        </Field>
        <Field
          id="password"
          label="비밀번호"
          error={errors.password}
          hint={initial ? "글 작성 시 입력한 비밀번호" : "수정·삭제 시 필요합니다 (4자 이상)"}
        >
          <Input id="password" name="password" type="password" autoComplete="off" aria-invalid={!!errors.password} />
        </Field>
      </div>

      <Field id="content" label="내용" error={errors.content}>
        <Textarea
          id="content"
          name="content"
          rows={12}
          maxLength={10000}
          defaultValue={values?.content}
          aria-invalid={!!errors.content}
          className="min-h-64"
        />
      </Field>

      <div className="flex justify-end gap-2">
        <Link href={cancelHref} className={buttonVariants({ variant: "outline" })}>
          취소
        </Link>
        <Button type="submit" disabled={pending}>
          {pending ? "저장 중..." : submitLabel}
        </Button>
      </div>
    </form>
  )
}

function Field({
  id,
  label,
  error,
  hint,
  children,
}: {
  id: string
  label: string
  error?: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : (
        hint && <p className="text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  )
}
