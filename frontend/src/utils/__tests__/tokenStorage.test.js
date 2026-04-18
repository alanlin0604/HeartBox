import { describe, it, expect, beforeEach } from 'vitest'
import {
  getAccessToken,
  setAccessToken,
  getRefreshToken,
  setRefreshToken,
  clearAuthTokens,
  hasValidTokens,
} from '../tokenStorage'

describe('tokenStorage utilities', () => {
  beforeEach(() => {
    // Clear both localStorage and sessionStorage before each test
    localStorage.clear()
    sessionStorage.clear()
  })

  describe('Access Token', () => {
    it('should store and retrieve access token', () => {
      const token = 'test-access-token'
      setAccessToken(token)
      expect(getAccessToken()).toBe(token)
    })

    it('should remove access token when set to null', () => {
      setAccessToken('test-token')
      setAccessToken(null)
      expect(getAccessToken()).toBeNull()
    })

    it('should return null when no access token exists', () => {
      expect(getAccessToken()).toBeNull()
    })
  })

  describe('Refresh Token', () => {
    it('should store and retrieve refresh token', () => {
      const token = 'test-refresh-token'
      setRefreshToken(token)
      expect(getRefreshToken()).toBe(token)
    })

    it('should remove refresh token when set to null', () => {
      setRefreshToken('test-token')
      setRefreshToken(null)
      expect(getRefreshToken()).toBeNull()
    })

    it('should return null when no refresh token exists', () => {
      expect(getRefreshToken()).toBeNull()
    })
  })

  describe('clearAuthTokens', () => {
    it('should clear both access and refresh tokens', () => {
      setAccessToken('access-token')
      setRefreshToken('refresh-token')

      clearAuthTokens()

      expect(getAccessToken()).toBeNull()
      expect(getRefreshToken()).toBeNull()
    })
  })

  describe('hasValidTokens', () => {
    it('should return true when both tokens exist', () => {
      setAccessToken('access-token')
      setRefreshToken('refresh-token')
      expect(hasValidTokens()).toBe(true)
    })

    it('should return false when access token is missing', () => {
      setRefreshToken('refresh-token')
      expect(hasValidTokens()).toBe(false)
    })

    it('should return false when refresh token is missing', () => {
      setAccessToken('access-token')
      expect(hasValidTokens()).toBe(false)
    })

    it('should return false when both tokens are missing', () => {
      expect(hasValidTokens()).toBe(false)
    })
  })
})
