import { Request, Response, NextFunction } from "express";
import { verifyMessage } from "ethers";

/**
 * Wallet authentication middleware
 *
 * Expects:
 *  - address: wallet address (0x...)
 *  - message: signed message
 *  - signature: wallet signature
 *
 * The message SHOULD include:
 *  - taskID
 *  - action
 *  - timestamp / nonce
 */
export function requireWalletAuth(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    // Accept either 'address' or 'publisher' as the wallet address
    const address = req.body.address || req.body.publisher;
    const { message, signature } = req.body;

    if (!address || !message || !signature) {
      return res.status(401).json({
        error: "Missing wallet authentication fields",
        details: { hasAddress: !!address, hasMessage: !!message, hasSignature: !!signature }
      });
    }

    // Verify message signature using ethers (EIP-191 personal sign format)
    // ethers.verifyMessage automatically handles the message encoding (EIP-191)
    let recovered: string;
    try {
      // Ensure message is a string (not object or other type)
      const messageStr = typeof message === 'string' ? message : String(message);
      
      // Ensure signature is a string with 0x prefix if needed
      let signatureStr = typeof signature === 'string' ? signature : String(signature);
      
      // verifyMessage expects signature with 0x prefix (ethers format)
      if (!signatureStr.startsWith('0x')) {
        signatureStr = '0x' + signatureStr;
      }
      
      recovered = verifyMessage(messageStr, signatureStr);
    } catch (verifyError: any) {
      console.error(`[requireWalletAuth] Signature verification failed:`, {
        error: verifyError.message,
        errorStack: verifyError.stack,
        messageType: typeof message,
        messageLength: typeof message === 'string' ? message.length : 'N/A',
        messagePreview: typeof message === 'string' ? message.substring(0, 100).replace(/\n/g, '\\n') : String(message).substring(0, 100),
        signatureType: typeof signature,
        signaturePreview: typeof signature === 'string' ? signature.substring(0, 30) : String(signature).substring(0, 30),
        address
      });
      return res.status(401).json({
        error: "Wallet authentication failed",
        details: `Signature verification error: ${verifyError.message}`,
        hint: "The message or signature format may be incorrect. Ensure the message matches exactly what was signed."
      });
    }

    if (recovered.toLowerCase() !== address.toLowerCase()) {
      console.error(`[requireWalletAuth] Address mismatch:`, {
        expected: address.toLowerCase(),
        recovered: recovered.toLowerCase()
      });
      return res.status(401).json({
        error: "Invalid wallet signature",
        details: `Address mismatch: expected ${address.toLowerCase()}, recovered ${recovered.toLowerCase()}`
      });
    }

    // Attach verified address for downstream usage
    (req as any).walletAddress = recovered;

    next();
  } catch (err: any) {
    console.error(`[requireWalletAuth] Unexpected error:`, err);
    return res.status(401).json({
      error: "Wallet authentication failed",
      details: err?.message || 'Unknown error'
    });
  }
}
