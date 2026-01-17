import { parseError, createError, ERROR_CODES, HealChainError } from '../errors';

describe('Error handling', () => {
  describe('parseError', () => {
    it('handles HealChainError', () => {
      const error = new HealChainError(
        'Test error',
        ERROR_CODES.WALLET_NOT_CONNECTED,
        'Please connect your wallet'
      );
      const parsed = parseError(error);
      
      expect(parsed.code).toBe(ERROR_CODES.WALLET_NOT_CONNECTED);
      expect(parsed.message).toBe('Please connect your wallet');
    });

    it('handles user rejected error', () => {
      const error = new Error('User rejected the request');
      const parsed = parseError(error);
      
      expect(parsed.code).toBe(ERROR_CODES.WALLET_SIGNATURE_REJECTED);
    });

    it('handles insufficient balance error', () => {
      const error = new Error('Insufficient funds');
      const parsed = parseError(error);
      
      expect(parsed.code).toBe(ERROR_CODES.INSUFFICIENT_BALANCE);
    });

    it('handles network error', () => {
      const error = new Error('Network error occurred');
      const parsed = parseError(error);
      
      expect(parsed.code).toBe(ERROR_CODES.NETWORK_ERROR);
    });

    it('handles unknown error', () => {
      const error = new Error('Unknown error');
      const parsed = parseError(error);
      
      expect(parsed.code).toBe('UNKNOWN_ERROR');
      expect(parsed.message).toBe('Unknown error');
    });
  });

  describe('createError', () => {
    it('creates HealChainError with correct code', () => {
      const error = createError(ERROR_CODES.WALLET_NOT_CONNECTED);
      
      expect(error).toBeInstanceOf(HealChainError);
      expect(error.code).toBe(ERROR_CODES.WALLET_NOT_CONNECTED);
      expect(error.userMessage).toBeTruthy();
    });
  });
});

