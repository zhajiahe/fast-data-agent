import { describe, expect, it } from 'vitest';
import { loginSchema, registerSchema } from './validations';

describe('验证 Schema 测试', () => {
  describe('loginSchema', () => {
    it('应该接受有效的登录数据', () => {
      const result = loginSchema.safeParse({
        username: 'testuser',
        password: 'password123',
      });
      expect(result.success).toBe(true);
    });

    it('应该拒绝无效的登录数据', () => {
      const result = loginSchema.safeParse({
        username: 'ab', // 太短
        password: '123', // 太短
      });
      expect(result.success).toBe(false);
    });
  });

  describe('registerSchema', () => {
    it('应该接受有效的注册数据', () => {
      const result = registerSchema.safeParse({
        username: 'newuser',
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
      });
      expect(result.success).toBe(true);
    });

    it('应该拒绝密码不匹配的注册数据', () => {
      const result = registerSchema.safeParse({
        username: 'newuser',
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'different',
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toBe('两次输入的密码不一致');
      }
    });
  });
});
