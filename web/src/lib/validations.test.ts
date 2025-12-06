import { describe, expect, it } from 'vitest';
import { emailSchema, loginSchema, passwordSchema, phoneSchema, registerSchema, usernameSchema } from './validations';

describe('验证 Schema 测试', () => {
  describe('usernameSchema', () => {
    it('应该接受有效的用户名', () => {
      expect(usernameSchema.safeParse('john_doe').success).toBe(true);
      expect(usernameSchema.safeParse('user123').success).toBe(true);
      expect(usernameSchema.safeParse('ABC').success).toBe(true);
    });

    it('应该拒绝过短的用户名', () => {
      const result = usernameSchema.safeParse('ab');
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toBe('用户名至少 3 个字符');
      }
    });

    it('应该拒绝包含特殊字符的用户名', () => {
      const result = usernameSchema.safeParse('user@name');
      expect(result.success).toBe(false);
    });
  });

  describe('emailSchema', () => {
    it('应该接受有效的邮箱', () => {
      expect(emailSchema.safeParse('test@example.com').success).toBe(true);
      expect(emailSchema.safeParse('user.name@domain.co.uk').success).toBe(true);
    });

    it('应该拒绝无效的邮箱', () => {
      expect(emailSchema.safeParse('invalid-email').success).toBe(false);
      expect(emailSchema.safeParse('test@').success).toBe(false);
      expect(emailSchema.safeParse('@domain.com').success).toBe(false);
    });
  });

  describe('passwordSchema', () => {
    it('应该接受有效的密码', () => {
      expect(passwordSchema.safeParse('password123').success).toBe(true);
      expect(passwordSchema.safeParse('123456').success).toBe(true);
    });

    it('应该拒绝过短的密码', () => {
      const result = passwordSchema.safeParse('12345');
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toBe('密码至少 6 个字符');
      }
    });
  });

  describe('phoneSchema', () => {
    it('应该接受有效的中国手机号', () => {
      expect(phoneSchema.safeParse('13812345678').success).toBe(true);
      expect(phoneSchema.safeParse('15912345678').success).toBe(true);
    });

    it('应该拒绝无效的手机号', () => {
      expect(phoneSchema.safeParse('1234567890').success).toBe(false);
      expect(phoneSchema.safeParse('12345678901').success).toBe(false);
    });
  });

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
