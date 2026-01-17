# Testing Guide

## Overview

This project uses Jest and React Testing Library for unit and integration testing.

## Setup

Tests are configured in `jest.config.js` and `jest.setup.js`. The setup includes:
- Next.js Jest configuration
- React Testing Library DOM matchers
- Mocked Next.js router
- Mocked wagmi hooks
- Mocked RainbowKit components

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## Test Structure

Tests are located alongside the code they test:
- Component tests: `src/components/__tests__/`
- Hook tests: `src/hooks/__tests__/`
- Utility tests: `src/lib/__tests__/`

## Writing Tests

### Component Tests

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MyComponent from '../MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('handles user interaction', async () => {
    const handleClick = jest.fn();
    render(<MyComponent onClick={handleClick} />);
    
    await userEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalled();
  });
});
```

### Hook Tests

```typescript
import { renderHook, act } from '@testing-library/react';
import { useMyHook } from '../useMyHook';

describe('useMyHook', () => {
  it('returns initial state', () => {
    const { result } = renderHook(() => useMyHook());
    expect(result.current.value).toBe(0);
  });

  it('updates state', () => {
    const { result } = renderHook(() => useMyHook());
    
    act(() => {
      result.current.increment();
    });
    
    expect(result.current.value).toBe(1);
  });
});
```

## Mocking

### Web3/Wagmi

Wagmi hooks are automatically mocked in `jest.setup.js`. To customize:

```typescript
jest.mock('wagmi', () => ({
  useAccount: () => ({
    address: '0x...',
    isConnected: true,
  }),
  // ... other hooks
}));
```

### Next.js Router

Router is automatically mocked. To customize:

```typescript
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    // ... other methods
  }),
}));
```

## Coverage

Coverage reports are generated in the `coverage/` directory. Target coverage:
- Statements: 70%+
- Branches: 70%+
- Functions: 70%+
- Lines: 70%+

## Best Practices

1. **Test user behavior, not implementation**
   - Test what users see and do
   - Avoid testing internal state

2. **Use semantic queries**
   - Prefer `getByRole`, `getByLabelText`
   - Avoid `getByTestId` when possible

3. **Test error states**
   - Test error messages
   - Test error recovery

4. **Test accessibility**
   - Test keyboard navigation
   - Test screen reader compatibility

5. **Keep tests simple**
   - One assertion per test when possible
   - Clear test names

## Example Test Files

- `src/components/__tests__/Button.test.tsx` - Component test example
- `src/lib/__tests__/errors.test.ts` - Utility test example

## Future Enhancements

- [ ] E2E tests with Playwright
- [ ] Visual regression tests
- [ ] Performance tests
- [ ] Accessibility tests with axe-core

