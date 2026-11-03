"use server"

import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"

import * as posts from "@/lib/posts"

export type FormState = {
  error?: string
  fieldErrors?: Partial<Record<"title" | "content" | "author" | "password", string>>
  values?: { title: string; content: string; author: string }
}

function readFields(formData: FormData) {
  const get = (key: string) => String(formData.get(key) ?? "").trim()
  return {
    title: get("title"),
    content: get("content"),
    author: get("author"),
    password: String(formData.get("password") ?? ""),
  }
}

function validate(fields: ReturnType<typeof readFields>) {
  const errors: FormState["fieldErrors"] = {}
  if (!fields.title) errors.title = "제목을 입력하세요."
  else if (fields.title.length > 100) errors.title = "제목은 100자 이내로 입력하세요."
  if (!fields.content) errors.content = "내용을 입력하세요."
  else if (fields.content.length > 10000) errors.content = "내용은 10,000자 이내로 입력하세요."
  if (!fields.author) errors.author = "작성자를 입력하세요."
  else if (fields.author.length > 20) errors.author = "작성자는 20자 이내로 입력하세요."
  if (fields.password.length < 4) errors.password = "비밀번호는 4자 이상 입력하세요."
  return Object.keys(errors).length ? errors : null
}

export async function createPostAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const fields = readFields(formData)
  const { password, ...values } = fields
  const fieldErrors = validate(fields)
  if (fieldErrors) return { fieldErrors, values }

  const id = await posts.createPost({ ...values, password })
  revalidatePath("/posts")
  redirect(`/posts/${id}`)
}

export async function updatePostAction(
  id: number,
  _prev: FormState,
  formData: FormData
): Promise<FormState> {
  const fields = readFields(formData)
  const { password, ...values } = fields
  const fieldErrors = validate(fields)
  if (fieldErrors) return { fieldErrors, values }

  const result = await posts.updatePost(id, password, values)
  if (result === "not-found") return { error: "게시글을 찾을 수 없습니다.", values }
  if (result === "wrong-password")
    return { fieldErrors: { password: "비밀번호가 일치하지 않습니다." }, values }

  revalidatePath("/posts")
  revalidatePath(`/posts/${id}`)
  redirect(`/posts/${id}`)
}

export async function deletePostAction(
  id: number,
  _prev: { error?: string },
  formData: FormData
): Promise<{ error?: string }> {
  const result = await posts.deletePost(id, String(formData.get("password") ?? ""))
  if (result === "not-found") return { error: "게시글을 찾을 수 없습니다." }
  if (result === "wrong-password") return { error: "비밀번호가 일치하지 않습니다." }

  revalidatePath("/posts")
  redirect("/posts")
}
