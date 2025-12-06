import { z } from 'zod';

/**
 * 表单验证 Schema
 */

// 用户名验证
export const usernameSchema = z
  .string()
  .min(3, '用户名至少 3 个字符')
  .max(20, '用户名最多 20 个字符')
  .regex(/^[a-zA-Z0-9_]+$/, '用户名只能包含字母、数字和下划线');

// 邮箱验证
export const emailSchema = z.string().email('请输入有效的邮箱地址');

// 密码验证
export const passwordSchema = z.string().min(6, '密码至少 6 个字符').max(50, '密码最多 50 个字符');

// 登录表单 Schema
export const loginSchema = z.object({
  username: usernameSchema,
  password: passwordSchema,
});

// 注册表单 Schema
export const registerSchema = z
  .object({
    username: usernameSchema,
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: '两次输入的密码不一致',
    path: ['confirmPassword'],
  });

// 类型导出
export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;
