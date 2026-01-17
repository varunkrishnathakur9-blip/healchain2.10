// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      pathname: '/',
      query: {},
      asPath: '/',
    }
  },
  usePathname() {
    return '/'
  },
  useParams() {
    return {}
  },
}))

// Mock wagmi hooks
jest.mock('wagmi', () => ({
  useAccount: () => ({
    address: '0x1234567890123456789012345678901234567890',
    isConnected: true,
    chainId: 31337,
  }),
  useConnect: () => ({
    connect: jest.fn(),
    connectors: [],
    isPending: false,
  }),
  useDisconnect: () => ({
    disconnect: jest.fn(),
  }),
  useSignMessage: () => ({
    signMessageAsync: jest.fn().mockResolvedValue('0xsignature'),
    isPending: false,
  }),
  useWriteContract: () => ({
    writeContract: jest.fn(),
    data: null,
    isPending: false,
    error: null,
  }),
  useWaitForTransactionReceipt: () => ({
    isLoading: false,
    isSuccess: false,
  }),
  useReadContract: () => ({
    data: null,
    isLoading: false,
    error: null,
  }),
}))

// Mock RainbowKit
jest.mock('@rainbow-me/rainbowkit', () => ({
  ConnectButton: {
    Custom: ({ children }) => children({
      account: { displayName: '0x1234...5678', displayBalance: '1.0 ETH' },
      chain: { name: 'Localhost', hasIcon: false },
      openAccountModal: jest.fn(),
      openChainModal: jest.fn(),
      openConnectModal: jest.fn(),
      authenticationStatus: 'authenticated',
      mounted: true,
    }),
  },
  getDefaultConfig: jest.fn(() => ({})),
}))

